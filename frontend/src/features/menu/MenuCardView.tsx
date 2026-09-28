import { memo, useEffect, useRef, useState, type CSSProperties } from 'react';
import type { MenuCard } from '@/api/types';
import { Icon } from '@/components/Icon';
import { fmtPrice } from '@/lib/format';

type Props = {
  card: MenuCard;
  inCart: boolean;
  /** Position within the visible grid; staggers the entrance animation. */
  position: number;
  spotlight?: boolean;
  dimmed?: boolean;
  onOpen: (card: MenuCard) => void;
  onQuickAdd: (card: MenuCard) => void;
};

const NO_IMG = (
  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d4c4b0" strokeWidth="1.5" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
);

/** Plays `menuCardIn` the first time the card scrolls into view. */
function useEntrance(position: number, skip: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  const [style, setStyle] = useState<CSSProperties | undefined>(skip ? { opacity: 1 } : undefined);

  useEffect(() => {
    if (skip) return;
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') {
      setStyle({ opacity: 1 });
      return;
    }
    const delay = Math.floor(position / 3) * 0.08 + (position % 3) * 0.05;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        setStyle({ animation: `menuCardIn .44s ease ${delay.toFixed(3)}s forwards` });
      },
      { threshold: 0.06, rootMargin: '40px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [position, skip]);

  return [ref, style] as const;
}

function actionFor(card: MenuCard): { label: string; kind: 'order' | 'choose' | 'add' } {
  if (card.category === 'cake_items') return { label: 'Замовити', kind: 'order' };
  if (card.has_size || card.has_ice_cream_scoop || card.has_fast_food_size) return { label: 'Обрати', kind: 'choose' };
  return { label: 'Додати', kind: 'add' };
}

function PriceBlock({ card }: { card: MenuCard }) {
  if (card.is_pizza && card.price_large > 0 && card.has_size) {
    return (
      <div className="mc-price-dual">
        <span className="mc-price">{fmtPrice(card.price)}</span>
        <span className="mc-price-sep">/</span>
        <span className="mc-price mc-price-large">{fmtPrice(card.price_large)}</span>
        <span className="mc-price-sizes">30 / 40 см</span>
      </div>
    );
  }
  if (card.has_fast_food_size && card.ff_large_price > card.ff_small_price) {
    return (
      <div className="mc-price-dual">
        <span className="mc-price">{fmtPrice(card.ff_small_price)}</span>
        <span className="mc-price-sep">/</span>
        <span className="mc-price mc-price-large">{fmtPrice(card.ff_large_price)}</span>
        {card.ff_size_str && <span className="mc-price-sizes">{card.ff_size_str}</span>}
      </div>
    );
  }
  return <span className="mc-price">{fmtPrice(card.price)}</span>;
}

function MenuCardViewImpl({ card, inCart, position, spotlight, dimmed, onOpen, onQuickAdd }: Props) {
  const [ref, entranceStyle] = useEntrance(position, !!spotlight);
  const [justAdded, setJustAdded] = useState(false);
  const action = actionFor(card);
  // A "choose" product can go in the cart in several variants, but the
  // button still reflects that at least one is there.
  const showInCart = inCart && action.kind !== 'order' && !card.has_size;

  const onClick = () => {
    if (action.kind === 'add' && !showInCart) {
      setJustAdded(true);
      window.setTimeout(() => setJustAdded(false), 600);
    }
    if (action.kind === 'add') onQuickAdd(card);
    else onOpen(card);
  };

  const style: CSSProperties = {
    ...entranceStyle,
    ...(spotlight ? { opacity: 1, boxShadow: '0 0 0 3px #FFC107, 0 0 32px 8px rgba(255,193,7,0.5)', transform: 'scale(1.04)', transition: 'box-shadow .3s ease, transform .3s ease' } : {}),
    ...(dimmed ? { opacity: 0.15, transition: 'opacity .4s ease', animation: 'none' } : {}),
  };

  return (
    <div
      ref={ref}
      id={`item-${card.category}-${card.id}`}
      className={`menu-card${card.is_pizza_type ? ' pizza-card' : ''}`}
      style={style}
    >
      <div className="mc-img-zone">
        {card.image ? (
          <img src={card.image} alt={card.name} loading="lazy" />
        ) : (
          <div className="mc-no-img">
            {NO_IMG}
            <span>{card.name}</span>
          </div>
        )}
        {card.is_pizza_type && (
          <>
            {card.is_spicy && (
              <span className="mc-badge mc-badge-spicy">
                <Icon name="filter-spicy" size={16} color="#e53935" /> Гостра
              </span>
            )}
            {card.sauce_type === 'cream' && <span className="mc-badge mc-badge-cream">Вершковий</span>}
            {card.sauce_type === 'bbq' && <span className="mc-badge mc-badge-bbq">BBQ</span>}
            {card.is_mini_pizza && <span className="mc-badge mc-badge-mini">20 см</span>}
          </>
        )}
        {card.is_cold_coffee && (
          <span className="mc-badge mc-badge-cold">
            <Icon name="snowflake" size={16} color="#1565c0" /> Холодна
          </span>
        )}
        {card.is_ice_cream && (
          <span className="mc-badge mc-badge-icecream">
            <Icon name="icecream" size={16} color="#880e4f" /> Морозиво
          </span>
        )}
        <button type="button" className="mc-img-overlay" onClick={() => onOpen(card)} aria-label={`Детальніше: ${card.name}`}>
          <span className="mc-overlay-label">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            Детальніше
          </span>
        </button>
      </div>

      <div className="mc-content">
        <h3 className="mc-name">{card.name}</h3>
        {card.description && <p className="mc-desc">{card.description}</p>}
        {card.is_pizza_type && card.tags.length > 0 && (
          <div className="mc-tags">
            {card.tags.slice(0, 4).map((t) => (
              <span key={t} className="mc-tag">{t}</span>
            ))}
          </div>
        )}
        {card.sushi_tags.length > 0 && (
          <div className="mc-tags mc-tags-sushi">
            {card.sushi_tags.map((t) => (
              <span key={t} className="mc-tag mc-tag-sushi">{t}</span>
            ))}
          </div>
        )}
        <div className="mc-footer">
          <PriceBlock card={card} />
          <button
            type="button"
            className={`mc-add-btn${showInCart ? ' in-cart' : ''}${justAdded ? ' just-added' : ''}`}
            onClick={onClick}
          >
            {showInCart ? 'В кошику ✓' : action.label}
          </button>
        </div>
      </div>
    </div>
  );
}

export const MenuCardView = memo(MenuCardViewImpl);
