import { useState } from 'react';
import { Link } from 'react-router';
import { useCartPreview, useRemoveCartItem } from '@/api/queries';

const NO_PHOTO = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
    <rect x="3" y="3" width="18" height="18" rx="3" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <path d="M21 15l-5-5L5 21" />
  </svg>
);

/** Hover dropdown under the header's cart icon. */
export function CartMiniDropdown({ open, loadEnabled }: { open: boolean; loadEnabled: boolean }) {
  const preview = useCartPreview(loadEnabled);
  const remove = useRemoveCartItem();
  const [removing, setRemoving] = useState<number | null>(null);
  const data = preview.data;

  const onRemove = (index: number) => {
    setRemoving(index);
    remove.mutate(index, { onSettled: () => setRemoving(null) });
  };

  return (
    <div className={`cart-mini-dropdown${open ? ' open' : ''}`} aria-hidden={!open}>
      <div className="cmd-inner">
        {!data ? (
          <div className="cmd-loading">
            <div className="cmd-spinner" />
          </div>
        ) : data.items.length === 0 ? (
          <div className="cmd-empty">
            <p>Кошик порожній</p>
          </div>
        ) : (
          <>
            <div className="cmd-scroll-wrap">
              <div className="cmd-items">
                {data.items.map((it) => (
                  <div key={`${it.session_index}-${it.id}`} className={`cmd-item${removing === it.session_index ? ' removing' : ''}`}>
                    {it.image ? (
                      <img className="cmd-item-img" src={it.image} alt="" />
                    ) : (
                      <span className="cmd-item-placeholder">{NO_PHOTO}</span>
                    )}
                    <div className="cmd-item-info">
                      <div className="cmd-item-name">{it.name}</div>
                      <div className="cmd-item-qty">{it.qty} шт.</div>
                    </div>
                    <div className="cmd-item-price">{Math.round(it.price * it.qty)} ₴</div>
                    <button
                      type="button"
                      className="cmd-remove-btn"
                      title="Видалити"
                      aria-label={`Видалити ${it.name}`}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        onRemove(it.session_index);
                      }}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className="cmd-footer">
              <div className="cmd-total">
                <span>Разом:</span>
                <strong className="cmd-total-price">{Math.round(data.total)} ₴</strong>
              </div>
              <Link to="/cart" className="cmd-checkout-btn">
                Перейти до кошика
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
