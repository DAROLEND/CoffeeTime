import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Icon, type IconName } from '@/components/Icon';
import type { CoffeeType, MenuFilters, SauceFilter, SortKey } from './menuLogic';

type Props = {
  category: string;
  filters: MenuFilters;
  ingredientTags: string[];
  onChange: (next: MenuFilters) => void;
  onReset: () => void;
};

const SORTS: { value: SortKey; label: string; icon: IconName }[] = [
  { value: 'default', label: 'За замовчуванням', icon: 'default-sort' },
  { value: 'price_asc', label: 'Ціна: від дешевших', icon: 'arrow-up' },
  { value: 'price_desc', label: 'Ціна: від дорожчих', icon: 'arrow-down' },
  { value: 'popular', label: 'За популярністю', icon: 'trending' },
];
const COFFEE: { value: CoffeeType; label: string; icon: IconName; color: string }[] = [
  { value: 'all', label: 'Всі', icon: 'coffee-cup', color: 'currentColor' },
  { value: 'hot', label: 'Тепла', icon: 'coffee-cup', color: '#c0623d' },
  { value: 'cold', label: 'Холодна', icon: 'snowflake', color: '#1565c0' },
];
const SAUCES: { value: SauceFilter; label: string; icon: IconName; color: string }[] = [
  { value: 'all', label: 'Всі', icon: 'filter-sauce-tomato', color: 'currentColor' },
  { value: 'tomato', label: 'Томатний', icon: 'filter-sauce-tomato', color: '#c0392b' },
  { value: 'cream', label: 'Вершковий', icon: 'filter-sauce-cream', color: '#b8860b' },
  { value: 'bbq', label: 'BBQ', icon: 'filter-bbq', color: '#6d2f00' },
];

const ARROW = (open: boolean) => (
  <svg className="fd-arrow" width="12" height="12" viewBox="0 0 12 12" style={{ transform: open ? 'rotate(180deg)' : undefined }}>
    <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" />
  </svg>
);

type DropdownProps = { id: string; open: string | null; setOpen: (id: string | null) => void; button: ReactNode; active: boolean; wide?: boolean; children: ReactNode };

function Dropdown({ id, open, setOpen, button, active, wide, children }: DropdownProps) {
  const isOpen = open === id;
  return (
    <div className="filter-dropdown" style={{ position: 'relative', display: 'flex' }}>
      <button
        type="button"
        className={`filter-btn${active ? ' has-value' : ''}`}
        aria-expanded={isOpen}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(isOpen ? null : id);
        }}
      >
        {button}
        {ARROW(isOpen)}
      </button>
      {isOpen && (
        <div className={`filter-dropdown-menu${wide ? ' fdm-wide' : ''}`} onClick={(e) => e.stopPropagation()}>
          {children}
        </div>
      )}
    </div>
  );
}

export function FilterBar({ category, filters, ingredientTags, onChange, onReset }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const isPizza = category === 'pizza_items';
  const isCoffee = category === 'coffee_items';

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(null);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [open]);

  const set = (patch: Partial<MenuFilters>) => onChange({ ...filters, ...patch });
  const sortLabel = filters.sort === 'default' ? 'Сортування' : SORTS.find((s) => s.value === filters.sort)!.label;
  const coffeeLabel = filters.coffeeType === 'all' ? 'Тип' : COFFEE.find((c) => c.value === filters.coffeeType)!.label;
  const sauceLabel = filters.sauce === 'all' ? 'Соус' : SAUCES.find((s) => s.value === filters.sauce)!.label;

  const badges: { label: string; clear: () => void }[] = [];
  if (isCoffee && filters.coffeeType !== 'all') badges.push({ label: coffeeLabel, clear: () => set({ coffeeType: 'all' }) });
  if (isPizza && filters.sauce !== 'all') badges.push({ label: sauceLabel, clear: () => set({ sauce: 'all' }) });
  if (isPizza && filters.spicy) badges.push({ label: 'Гострі', clear: () => set({ spicy: false }) });
  if (isPizza) filters.ingredients.forEach((ing) => badges.push({ label: ing, clear: () => set({ ingredients: filters.ingredients.filter((i) => i !== ing) }) }));

  return (
    <div id="menu-filter-bar" style={{ margin: '12px 0 4px' }} ref={barRef}>
      <div className="mfb-inner">
        <Dropdown
          id="sort"
          open={open}
          setOpen={setOpen}
          active={filters.sort !== 'default'}
          button={
            <>
              <Icon name="sort" size={18} />
              <span>{sortLabel}</span>
            </>
          }
        >
          {SORTS.map((s) => (
            <div
              key={s.value}
              className={`sort-option${filters.sort === s.value ? ' active' : ''}`}
              role="option"
              aria-selected={filters.sort === s.value}
              onClick={() => {
                set({ sort: s.value });
                setOpen(null);
              }}
            >
              <Icon name={s.icon} size={16} className="fo-icon" /> {s.label}
            </div>
          ))}
        </Dropdown>

        {isCoffee && (
          <>
            <div className="mfb-sep" style={{ display: 'flex' }} />
            <Dropdown
              id="coffee"
              open={open}
              setOpen={setOpen}
              active={filters.coffeeType !== 'all'}
              button={
                <>
                  <Icon name="coffee-cup" size={18} />
                  <span>{coffeeLabel}</span>
                </>
              }
            >
              {COFFEE.map((c) => (
                <div
                  key={c.value}
                  className={`filter-option${filters.coffeeType === c.value ? ' active' : ''}`}
                  onClick={() => {
                    set({ coffeeType: c.value });
                    setOpen(null);
                  }}
                >
                  <Icon name={c.icon} size={16} color={c.color} className="fo-icon" /> {c.label}
                </div>
              ))}
            </Dropdown>
          </>
        )}

        {isPizza && (
          <>
            <div className="mfb-sep" style={{ display: 'flex' }} />
            <Dropdown
              id="sauce"
              open={open}
              setOpen={setOpen}
              active={filters.sauce !== 'all'}
              button={
                <>
                  <Icon name="filter-sauce-tomato" size={18} />
                  <span>{sauceLabel}</span>
                </>
              }
            >
              {SAUCES.map((s) => (
                <div
                  key={s.value}
                  className={`filter-option${filters.sauce === s.value ? ' active' : ''}`}
                  onClick={() => {
                    set({ sauce: s.value });
                    setOpen(null);
                  }}
                >
                  <Icon name={s.icon} size={16} color={s.color} className="fo-icon" /> {s.label}
                </div>
              ))}
            </Dropdown>

            <Dropdown
              id="ing"
              open={open}
              setOpen={setOpen}
              wide
              active={filters.ingredients.length > 0}
              button={
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><circle cx="11" cy="11" r="8" /><path d="M8 11h6M11 8v6" /></svg>
                  <span>{filters.ingredients.length ? `Склад (${filters.ingredients.length})` : 'Склад'}</span>
                </>
              }
            >
              <div className="fdm-hint">Мультивибір інгредієнтів</div>
              <div className="fdm-chips">
                {ingredientTags.map((tag) => {
                  const key = tag.toLowerCase().trim();
                  const active = filters.ingredients.includes(key);
                  return (
                    <button
                      key={tag}
                      type="button"
                      className={`ingredient-chip${active ? ' active' : ''}`}
                      aria-pressed={active}
                      onClick={() => set({ ingredients: active ? filters.ingredients.filter((i) => i !== key) : [...filters.ingredients, key] })}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </Dropdown>

            <button
              type="button"
              className={`filter-btn${filters.spicy ? ' active' : ''}`}
              id="spicy-toggle"
              style={{ display: 'flex' }}
              aria-pressed={filters.spicy}
              onClick={() => set({ spicy: !filters.spicy })}
            >
              <Icon name="filter-spicy" size={18} /> Гострі
            </button>
          </>
        )}

        {badges.length > 0 && (
          <div id="active-filters-bar" style={{ display: 'flex' }}>
            {badges.map((b) => (
              <span key={b.label} className="afb-badge" role="button" tabIndex={0} onClick={b.clear} onKeyDown={(e) => e.key === 'Enter' && b.clear()}>
                {b.label} <span className="afb-x">✕</span>
              </span>
            ))}
            <button type="button" className="afb-reset" onClick={onReset}>
              ✕ Скинути
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
