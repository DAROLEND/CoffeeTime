import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fragment, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { invalidateCart, qk } from '@/api/queries';
import type { CartLine, UpdateCartItemRequest } from '@/api/types';
import { Icon } from '@/components/Icon';
import { PageError, PageLoader } from '@/components/Spinner';
import { useToast } from '@/components/Toast';
import { usePageTitle } from '@/hooks/usePageTitle';
import { money, plural } from '@/lib/format';
import '@/styles/pages/cart/cart.css';
import '@/styles/pages/cart/cart-edit.css';
import { CartEditModal } from './CartEditModal';

const REMOVE_MS = 520;

/** Adds a class for a moment whenever `value` changes (price "flash", qty "bump"). */
function useBlink(value: unknown, ms = 380) {
  const [on, setOn] = useState(false);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    setOn(true);
    const t = window.setTimeout(() => setOn(false), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return on;
}

type RowProps = {
  item: CartLine;
  order: number;
  removing: boolean;
  onQty: (item: CartLine, qty: number) => void;
  onRemove: (item: CartLine) => void;
  onEdit: (item: CartLine) => void;
};

function CartRow({ item, order, removing, onQty, onRemove, onEdit }: RowProps) {
  const [visible, setVisible] = useState(false);
  const [draft, setDraft] = useState(String(item.quantity));
  const flash = useBlink(item.subtotal);
  const bump = useBlink(item.quantity, 300);
  const isCake = item.category === 'cake_items';

  useEffect(() => {
    const t = window.setTimeout(() => setVisible(true), 30 + order * 40);
    return () => window.clearTimeout(t);
  }, [order]);
  useEffect(() => setDraft(String(item.quantity)), [item.quantity]);

  const commitDraft = () => {
    const n = Math.max(1, Math.min(99, parseInt(draft, 10) || 1));
    setDraft(String(n));
    if (n !== item.quantity) onQty(item, n);
  };

  return (
    <div className={`cart-item${visible ? ' visible' : ''}${removing ? ' removing' : ''}`}>
      {item.image ? <img src={item.image} alt={item.name} loading="lazy" /> : <div className="cart-item-no-img" aria-hidden="true" />}
      <div className="cart-item-body">
        <h3>{item.name}</h3>
        {item.opt_tags.length > 0 && (
          <div className="cart-item-opts">
            {item.opt_tags.map((t) => (
              <span key={t} className="cart-opt-tag">{t}</span>
            ))}
          </div>
        )}
        {item.description && <p className="item-desc">{item.description}</p>}
        {!isCake && (
          <div className="qty-control">
            <button className="qty-btn qty-dec" disabled={item.quantity <= 1} aria-label="Зменшити" onClick={() => onQty(item, item.quantity - 1)}>
              −
            </button>
            <input
              type="number"
              className={`qty-value${bump ? ' bumping' : ''}`}
              value={draft}
              min={1}
              max={99}
              aria-label="Кількість товару"
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitDraft}
              onFocus={(e) => e.target.select()}
              onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
            />
            <button className="qty-btn qty-inc" disabled={item.quantity >= 99} aria-label="Збільшити" onClick={() => onQty(item, item.quantity + 1)}>
              +
            </button>
          </div>
        )}
      </div>
      <div className="cart-item-right">
        <span className={`item-subtotal${flash ? ' flash' : ''}`}>{money(item.subtotal)}</span>
        {item.editable && (
          <button className="edit-cart-item" aria-label="Змінити опції товару" onClick={() => onEdit(item)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
          </button>
        )}
        <button className="remove-btn" aria-label="Видалити товар" onClick={() => onRemove(item)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6M14 11v6" /><path d="M9 6V4h6v2" /></svg>
        </button>
      </div>
    </div>
  );
}

export default function CartPage() {
  usePageTitle('Кошик — Coffee Time');
  const client = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const cart = useQuery({ queryKey: qk.cart, queryFn: () => unwrap(api.GET('/api/cart')) });
  const [removing, setRemoving] = useState<Set<number>>(new Set());
  const [confirmClear, setConfirmClear] = useState(false);
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [leaving, setLeaving] = useState(false);
  const totalFlash = useBlink(cart.data?.total);

  const patch = useMutation({
    mutationFn: ({ index, body }: { index: number; body: UpdateCartItemRequest }) =>
      unwrap(api.PATCH('/api/cart/items/{index}', { params: { path: { index } }, body })),
    onSettled: () => invalidateCart(client),
    onError: (err) => toast(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (index: number) => unwrap(api.DELETE('/api/cart/items/{index}', { params: { path: { index } } })),
    onSettled: () => invalidateCart(client).then(() => setRemoving(new Set())),
  });

  const clear = useMutation({
    mutationFn: () => unwrap(api.DELETE('/api/cart')),
    onSettled: () => invalidateCart(client),
  });

  if (cart.isPending) return <PageLoader />;
  if (cart.error) return <PageError message={errorMessage(cart.error)} onRetry={() => cart.refetch()} />;

  const data = cart.data;
  const empty = data.item_count === 0;

  const onRemove = (item: CartLine) => {
    setRemoving((s) => new Set(s).add(item.session_index));
    toast('Товар видалено з кошика');
    // Let the slide-out animation play before the line disappears.
    window.setTimeout(() => remove.mutate(item.session_index), REMOVE_MS);
  };

  const onClear = () => {
    setRemoving(new Set(data.items.map((i) => i.session_index)));
    setConfirmClear(false);
    window.setTimeout(() => clear.mutate(), 60 * data.items.length + 340);
  };

  const goCheckout = () => {
    setLeaving(true);
    navigate('/checkout');
  };

  let order = 0;

  return (
    <div className="pg-cart">
      <main className="cart-page">
        <div className="cart-header">
          <h1>Ваша корзина</h1>
          <p className="cart-count-label">
            {empty ? 'Порожньо' : `${data.item_count} ${plural(data.item_count, ['товар', 'товари', 'товарів'])}`}
          </p>
        </div>

        {empty ? (
          <div className="cart-empty">
            <Icon name="cart" size={72} color="#d4c4b0" className="cart-empty-icon" />
            <h2>Ваша корзина порожня</h2>
            <p>Додайте щось смачне з нашого меню</p>
            <Link to={`/menu?category=${data.back_category}`} className="empty-menu-btn">
              Перейти до меню
            </Link>
          </div>
        ) : (
          <div className="cart-layout">
            <div className="cart-items-col">
              {data.groups.map((group) => (
                <Fragment key={group.key}>
                  <div className="cart-category-header">{group.label}</div>
                  {group.items.map((item) => (
                    <CartRow
                      key={`${item.session_index}-${item.category}-${item.id}`}
                      item={item}
                      order={order++}
                      removing={removing.has(item.session_index)}
                      onQty={(it, qty) => patch.mutate({ index: it.session_index, body: { quantity: qty } })}
                      onRemove={onRemove}
                      onEdit={(it) => setEditIndex(it.session_index)}
                    />
                  ))}
                </Fragment>
              ))}
            </div>

            <div className="cart-summary-col">
              <div className="cart-summary-box visible">
                <h3>Підсумок</h3>
                <div className="summary-row">
                  <span>Товарів:</span>
                  <span>{data.total_qty} шт.</span>
                </div>
                <div className="summary-row muted">
                  <span>Знижка:</span>
                  <span>0 ₴</span>
                </div>
                <div className="summary-divider" />
                <div className="summary-total-row">
                  <span>Загальна сума:</span>
                  <span className={`cart-total${totalFlash ? ' flash' : ''}`}>{money(data.total)}</span>
                </div>
                <button type="button" className={`checkout-btn${leaving ? ' loading' : ''}`} onClick={goCheckout}>
                  {leaving ? '' : 'Оформити замовлення'}
                </button>
                <Link to={`/menu?category=${data.back_category}`} className="back-to-menu-btn">
                  Повернутись до меню
                </Link>
                <div className="clear-cart-wrap">
                  {confirmClear ? (
                    <div className="clear-confirm" style={{ display: 'flex' }}>
                      <span>Ви впевнені?</span>
                      <button className="clear-confirm-yes" onClick={onClear}>
                        Так, очистити
                      </button>
                      <button className="clear-confirm-no" onClick={() => setConfirmClear(false)}>
                        Скасувати
                      </button>
                    </div>
                  ) : (
                    <button className="clear-cart-link" onClick={() => setConfirmClear(true)}>
                      Очистити корзину
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {!empty && (
        <div className="cart-sticky-bar">
          <div className="cart-sticky-total">
            <span className="cart-sticky-label">Сума:</span>
            <span className="cart-sticky-amount">{money(data.total)}</span>
          </div>
          <button type="button" className="cart-sticky-btn" onClick={goCheckout}>
            Оформити замовлення
          </button>
        </div>
      )}

      <CartEditModal
        index={editIndex}
        onClose={() => setEditIndex(null)}
        onSave={async (index, body) => {
          try {
            await patch.mutateAsync({ index, body });
            toast('Товар оновлено');
            return true;
          } catch {
            return false;
          }
        }}
      />
    </div>
  );
}
