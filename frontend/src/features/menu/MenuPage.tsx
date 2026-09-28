import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { ApiError, errorMessage, unwrap } from '@/api/errors';
import { qk, useAddToCart, useSession } from '@/api/queries';
import type { AddToCartRequest, MenuCard } from '@/api/types';
import { PageError, PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/menu/menu.css';
import '@/styles/pages/menu/menu-layout.css';
import { FilterBar } from './FilterBar';
import { ItemModal } from './ItemModal';
import { MenuCardView } from './MenuCardView';
import {
  DEFAULT_FILTERS, LAZY_BATCH, SAUCE_CATEGORIES, fmtWeight, hasActiveFilters, matchesFilters,
  positionsWord, searchSections, sortCards, type MenuFilters,
} from './menuLogic';
import { SaucePicker, type PickedSauce } from './SaucePicker';
import { SaucePopup } from './SaucePopup';

/** Products the menu shows inside another tab. */
const PARENT_TAB: Record<string, string> = { mini_pizza_items: 'pizza_items', ice_cream_items: 'dessert_items' };

const truncName = (n: string) => (n.length > 16 ? `${n.slice(0, 16)}…` : n);

function EmptyCategory() {
  return (
    <div className="menu-empty-state">
      <div className="mes-icon">
        <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
          <circle cx="36" cy="36" r="32" stroke="#e8ddd5" strokeWidth="2" />
          <path d="M22 36c0-7.732 6.268-14 14-14s14 6.268 14 14-6.268 14-14 14-14-6.268-14-14z" stroke="#d4c4b8" strokeWidth="2" />
          <path d="M30 36h12M36 30v12" stroke="#d4c4b8" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>
      <h3>Ця категорія поки порожня</h3>
      <p>Скоро тут з'являться нові позиції</p>
    </div>
  );
}

/** Reveals `batch` more cards whenever the sentinel under the grid scrolls into view. */
function LazySentinel({ onReveal }: { onReveal: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([entry]) => entry.isIntersecting && onReveal(), { rootMargin: '200px' });
    io.observe(el);
    return () => io.disconnect();
  }, [onReveal]);
  return (
    <div className="lazy-sentinel" ref={ref}>
      <div className="lazy-loader" />
    </div>
  );
}

type Toast = { text: string; key: number } | null;

export default function MenuPage() {
  usePageTitle('Меню — Coffee Time');
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const menu = useQuery({ queryKey: qk.menu, queryFn: () => unwrap(api.GET('/api/menu')), staleTime: 60_000 });
  const { data: session } = useSession();
  const addToCart = useAddToCart();

  const data = menu.data;
  const tabKeys = useMemo(() => data?.tabs.map((t) => t.key) ?? [], [data]);
  const resolveTab = useCallback(
    (raw: string | null) => {
      const key = raw ? (PARENT_TAB[raw] ?? raw) : '';
      return tabKeys.includes(key) ? key : (tabKeys[0] ?? 'coffee_items');
    },
    [tabKeys],
  );

  const category = resolveTab(params.get('category'));
  const group = data?.groups.find((g) => g.categories.includes(category))?.id ?? 'drinks';

  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<MenuFilters>(DEFAULT_FILTERS);
  const [shown, setShown] = useState<Record<string, number>>({});
  const [animKey, setAnimKey] = useState(0);
  const [modalCard, setModalCard] = useState<MenuCard | null>(null);
  const [picker, setPicker] = useState<{ name: string; onDone: (s: PickedSauce[]) => void } | null>(null);
  const [popup, setPopup] = useState<{ title: string; options: string[]; index: number } | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [spotlight, setSpotlight] = useState<{ key: string; phase: 'on' | 'off' } | null>(null);
  const [stuck, setStuck] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const cartKeys = useMemo(() => new Set(session?.cart.keys ?? []), [session]);

  // ── search (300 ms debounce, across every category) ──
  useEffect(() => {
    const t = window.setTimeout(() => setQuery(searchInput.trim().toLowerCase()), 300);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // ── sticky tabs shadow ──
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([e]) => setStuck(!e.isIntersecting), { rootMargin: '-76px 0px 0px 0px', threshold: 0 });
    io.observe(el);
    return () => io.disconnect();
  }, [data]);

  // ── toast ──
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(t);
  }, [toast]);

  const switchCategory = (cat: string) => {
    setParams({ category: cat }, { replace: true });
    setSearchInput('');
    setQuery('');
    // Filters are per-category: leaving pizza/coffee resets theirs; sort stays.
    setFilters((f) => ({ ...DEFAULT_FILTERS, sort: f.sort }));
    setAnimKey((k) => k + 1);
  };

  // ── "view in menu" deep link from the homepage: scroll + spotlight ──
  const scrollTo = Number(params.get('scroll_to') || 0);
  useEffect(() => {
    if (!data || !scrollTo) return;
    const section = data.sections[category] ?? [];
    const target = section.find((c) => c.id === scrollTo && (c.category === params.get('category') || c.category === category)) ?? section.find((c) => c.id === scrollTo);
    if (!target) return;
    const key = `${target.category}-${target.id}`;
    setShown((s) => ({ ...s, [category]: section.length }));
    setSpotlight({ key, phase: 'on' });
    const scrollTimer = window.setTimeout(() => {
      const el = document.getElementById(`item-${key}`);
      if (!el) return;
      const stickyH = (document.querySelector('.menu-tabs-outer') as HTMLElement | null)?.offsetHeight ?? 60;
      window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - stickyH - 96), behavior: 'smooth' });
    }, 150);
    const offTimer = window.setTimeout(() => setSpotlight({ key, phase: 'off' }), 2300);
    const clearTimer = window.setTimeout(() => setSpotlight(null), 3500);
    const next = new URLSearchParams(params);
    next.delete('scroll_to');
    setParams(next, { replace: true });
    return () => {
      window.clearTimeout(scrollTimer);
      window.clearTimeout(offTimer);
      window.clearTimeout(clearTimer);
    };
    // Runs once per deep link.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, scrollTo]);

  // ── cart actions ──
  const add = useCallback(
    async (request: AddToCartRequest, name: string): Promise<number | null> => {
      try {
        const res = await addToCart.mutateAsync(request);
        const weight = request.weight ? ` (${fmtWeight(request.weight)} кг)` : '';
        setToast({ text: `✓ «${truncName(name)}»${weight} додано${weight ? '!' : ' в кошик!'}`, key: Date.now() });
        return res.index ?? null;
      } catch (err) {
        setToast({ text: err instanceof ApiError ? err.message : errorMessage(err), key: Date.now() });
        return null;
      }
    },
    [addToCart],
  );

  const addSauces = useCallback(
    async (sauces: PickedSauce[]) => {
      for (const s of sauces) await add({ category: 'sauces', id: s.id, quantity: s.qty }, s.name);
    },
    [add],
  );

  /** Offer paid sauces first (pizza/fast food), then add item + sauces. */
  const withSaucePicker = useCallback(
    (name: string, addItem: () => Promise<unknown>) => {
      if (!data?.sauces.length) {
        void addItem();
        return;
      }
      setPicker({
        name,
        onDone: async (sauces) => {
          setPicker(null);
          const index = await addItem();
          if (index !== null) await addSauces(sauces);
        },
      });
    },
    [data, addSauces],
  );

  const quickAdd = useCallback(
    (card: MenuCard) => {
      if (cartKeys.has(`${card.category}_${card.id}`)) {
        navigate('/cart');
        return;
      }
      const request: AddToCartRequest = { category: card.category, id: card.id, quantity: 1 };
      if (card.has_sauce_variant && card.variant_options) {
        const vo = card.variant_options;
        void add(request, card.name).then((index) => {
          if (index !== null) setPopup({ title: vo.label, options: vo.options.map((o) => o.label), index });
        });
        return;
      }
      if (SAUCE_CATEGORIES.has(card.category)) withSaucePicker(card.name, () => add(request, card.name));
      else void add(request, card.name);
    },
    [add, cartKeys, navigate, withSaucePicker],
  );

  const modalAdd = useCallback(
    async (request: AddToCartRequest, card: MenuCard): Promise<boolean> => {
      const sizedPizza = card.is_pizza && card.has_size;
      if (SAUCE_CATEGORIES.has(card.category) && !sizedPizza && data?.sauces.length) {
        setModalCard(null);
        withSaucePicker(card.name, () => add(request, card.name));
        return true;
      }
      const index = await add(request, card.name);
      if (index === null) return false;
      window.setTimeout(() => setModalCard(null), 250);
      return true;
    },
    [add, data, withSaucePicker],
  );

  const pickFreeSauce = async (label: string) => {
    if (!popup) return;
    const index = popup.index;
    setPopup(null);
    await api.PATCH('/api/cart/items/{index}', {
      params: { path: { index } },
      body: { selected_variant: JSON.stringify({ type: 'sauce', label }) },
    });
  };
  const closePopup = useCallback(() => setPopup(null), []);

  if (menu.isPending) return <PageLoader />;
  if (menu.error || !data) return <PageError message={errorMessage(menu.error)} onRetry={() => menu.refetch()} />;

  const searching = query.length > 0;
  const results = searching ? searchSections(data.sections, query) : {};
  const totalFound = Object.values(results).reduce((n, cards) => n + cards.length, 0);
  const labelOf = (key: string) => data.tabs.find((t) => t.key === key)?.label ?? key;
  const filtersOn = hasActiveFilters(filters);

  const renderGrid = (key: string, cards: MenuCard[], limitLazy: boolean) => {
    const limit = limitLazy ? (shown[key] ?? LAZY_BATCH) : cards.length;
    const visible = cards.slice(0, limit);
    return (
      <>
        <div className="menu-grid" id={`grid-${key}`}>
          {visible.map((card, i) => {
            const cardKey = `${card.category}-${card.id}`;
            return (
              <MenuCardView
                key={`${cardKey}-${animKey}`}
                card={card}
                inCart={cartKeys.has(`${card.category}_${card.id}`)}
                position={i}
                spotlight={spotlight?.phase === 'on' && spotlight.key === cardKey}
                dimmed={spotlight?.phase === 'on' && spotlight.key !== cardKey}
                onOpen={setModalCard}
                onQuickAdd={quickAdd}
              />
            );
          })}
        </div>
        {limit < cards.length && <LazySentinel onReveal={() => setShown((s) => ({ ...s, [key]: (s[key] ?? LAZY_BATCH) + LAZY_BATCH }))} />}
      </>
    );
  };

  const activeCards = data.sections[category] ?? [];
  const filtered = sortCards(activeCards.filter((c) => matchesFilters(c, category, filters)), filters.sort);

  return (
    <div className="pg-menu">
      <main className="menu-page">
        <div className="menu-hero">
          <h1 className="menu-title">Наше меню</h1>
          <p className="menu-subtitle">Свіжа кава, смачна їжа та затишна атмосфера</p>
        </div>

        <div className="menu-search-wrap">
          <svg className="msw-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
          <input
            type="search"
            className="menu-search-input"
            placeholder="Пошук по меню…"
            aria-label="Пошук по меню"
            autoComplete="off"
            spellCheck={false}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <button className="msw-clear" aria-label="Очистити" style={{ display: 'flex' }} onClick={() => setSearchInput('')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          )}
        </div>

        <div ref={sentinelRef} style={{ height: 1, marginBottom: -1, pointerEvents: 'none' }} />
        <div className={`menu-tabs-outer${stuck ? ' stuck' : ''}`}>
          <div className={`menu-tabs-wrap${searching ? ' search-active' : ''}`}>
            <div className="menu-nav">
              <div className="menu-main-tabs" role="tablist" aria-label="Групи меню">
                {data.groups.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    role="tab"
                    aria-selected={g.id === group}
                    className={`mmt-btn${g.id === group ? ' active' : ''}`}
                    onClick={() => g.id !== group && switchCategory(g.categories.find((c) => tabKeys.includes(c)) ?? g.categories[0])}
                  >
                    {/* Server-provided static SVG icon (app/routers/public/menu.py GROUPS). */}
                    <span className="mmt-icon" dangerouslySetInnerHTML={{ __html: g.icon }} />
                    <span className="mmt-label">{g.label}</span>
                  </button>
                ))}
              </div>
              {data.groups.map((g) => {
                const cats = g.categories.filter((c) => tabKeys.includes(c));
                if (cats.length < 2) return null;
                return (
                  <div key={g.id} className={`menu-sub-tabs${g.id === group ? ' active' : ''}`} role="tablist">
                    {cats.map((c) => (
                      <button
                        key={c}
                        type="button"
                        role="tab"
                        aria-selected={c === category}
                        className={`menu-tab${c === category ? ' active' : ''}`}
                        onClick={() => c !== category && switchCategory(c)}
                      >
                        {labelOf(c)}
                        <span className="tab-badge">{data.tabs.find((t) => t.key === c)?.count ?? 0}</span>
                      </button>
                    ))}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className={`menu-body${searching ? ' global-search-active' : ''}`}>
          {!searching && (
            <FilterBar
              category={category}
              filters={filters}
              ingredientTags={data.ingredient_tags}
              onChange={(f) => {
                setFilters(f);
                setAnimKey((k) => k + 1);
              }}
              onReset={() => {
                setFilters(DEFAULT_FILTERS);
                setAnimKey((k) => k + 1);
              }}
            />
          )}

          {searching ? (
            <>
              <div className="global-search-banner">
                <span className="gsb-icon">🔍</span>{' '}
                <span className="gsb-text">
                  {totalFound > 0
                    ? `Знайдено ${totalFound} ${positionsWord(totalFound)} у всіх категоріях`
                    : `Нічого не знайдено за запитом «${query}»`}
                </span>
              </div>
              {totalFound === 0 ? (
                <div className="menu-search-empty" style={{ display: 'flex' }}>
                  <span className="mse-emoji">🔍</span>
                  <p className="mse-text">Спробуйте інший запит</p>
                  <button className="mse-reset" onClick={() => setSearchInput('')}>
                    Скинути пошук
                  </button>
                </div>
              ) : (
                Object.entries(results).map(([key, cards]) => (
                  <section key={key} className="menu-cat-section search-visible" data-label={labelOf(key)}>
                    {renderGrid(key, cards, false)}
                  </section>
                ))
              )}
            </>
          ) : (
            <section className="menu-cat-section active" data-cat={category} data-label={labelOf(category)} id={`cat-${category}`}>
              {activeCards.length === 0 ? (
                <EmptyCategory />
              ) : (
                <>
                  {renderGrid(category, filtered, !filtersOn)}
                  {filtered.length === 0 && (
                    <div className="no-pizza-results" style={{ display: 'flex' }}>
                      <span className="npr-icon" />
                      <p>Нічого не знайдено за заданими фільтрами</p>
                      <button className="pf-reset-link" onClick={() => setFilters(DEFAULT_FILTERS)}>
                        Скинути фільтри
                      </button>
                    </div>
                  )}
                </>
              )}
            </section>
          )}
        </div>
      </main>

      <ItemModal
        card={modalCard}
        inCart={!!modalCard && cartKeys.has(`${modalCard.category}_${modalCard.id}`)}
        onClose={() => setModalCard(null)}
        onAdd={modalAdd}
      />
      <SaucePicker open={!!picker} itemName={picker?.name ?? ''} sauces={data.sauces} onDone={(s) => picker?.onDone(s)} />
      <SaucePopup open={!!popup} title={popup?.title ?? ''} options={popup?.options ?? []} onPick={pickFreeSauce} onClose={closePopup} />

      <div className={`menu-toast${toast ? ' show' : ''}`} role="status" aria-live="polite">
        {toast && (
          <>
            <span>{toast.text}</span>
            <Link to="/cart" className="toast-cart-link">
              До кошику →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
