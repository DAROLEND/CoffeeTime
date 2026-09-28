import { Link } from 'react-router';
import type { HomeProduct } from '@/api/types';
import { Icon } from '@/components/Icon';
import { useReveal } from '@/hooks/useReveal';
import { truncate } from '@/lib/format';

type Props = {
  item: HomeProduct;
  kind: 'food' | 'drink' | 'dessert';
  index: number;
  badge?: boolean;
  /** Inside the drinks slider the slider reveals cards itself. */
  revealed?: boolean;
};

export function ProductCard({ item, kind, index, badge, revealed }: Props) {
  const ref = useReveal<HTMLDivElement>({ delay: index * 0.1 });
  return (
    <div ref={revealed === undefined ? ref : undefined} className={`item-card ${kind}-item${revealed ? ' visible' : ''}`}>
      {badge && (
        <span className="card-badge">
          <Icon name="fire" size={13} color="#e65100" /> Хіт
        </span>
      )}
      {item.image ? <img src={item.image} alt={item.name} loading="lazy" /> : <div className="item-no-img" aria-hidden="true" />}
      <div className="card-info">
        <p className="card-name">{item.name}</p>
        {item.description && <p className="card-desc">{truncate(item.description, 72)}</p>}
        <div className="card-footer">
          <span className="card-price">{Math.round(item.price)} грн</span>
          <Link to={`/menu?category=${item.table}&scroll_to=${item.id}`} className="btn-add-cart">
            Переглянути в меню →
          </Link>
        </div>
      </div>
    </div>
  );
}
