import type { components } from '@/api/schema';

type Row = components['schemas']['AdminOrderRow'];

const grn = (v: number) => Math.round(v).toLocaleString('uk-UA');

export function payMethodLabel(pm: string) {
  if (pm.includes('cash')) return 'При отриманні';
  if (pm === 'card_online') return 'Картка онлайн (LiqPay)';
  if (pm === 'card_on_pickup') return 'Картка у кафе';
  return pm || '—';
}

/** The expandable "od-wrap" block under an order row. */
export function OrderDetails({ order }: { order: Row }) {
  const pm = order.payment_method;
  const ps = order.payment_status;
  const items = order.line_items;
  return (
    <div className="od-wrap">
      <div className="od-info">
        <div className="od-block-title">Клієнт</div>
        <div className="od-row"><span className="od-key">Ім'я</span><span className="od-val">{order.full_name || '—'}</span></div>
        <div className="od-row"><span className="od-key">Телефон</span><span className="od-val">{order.phone || '—'}</span></div>
        <div className="od-row"><span className="od-key">Оплата</span><span className="od-val">{payMethodLabel(pm)}</span></div>
        {!pm.includes('cash') && ps && (
          <div className="od-row">
            <span className="od-key">Статус оплати</span>
            <span className="od-val">
              {ps === 'paid' && <span style={{ color: '#2e7d32', fontWeight: 700 }}>✓ Оплачено</span>}
              {ps === 'pending' && <span style={{ color: '#e65100' }}>⏳ Очікує оплати</span>}
              {ps === 'failed' && <span style={{ color: '#c62828' }}>✗ Не оплачено</span>}
            </span>
          </div>
        )}
        {order.ready_time && <div className="od-row"><span className="od-key">Час готовності</span><span className="od-val">⏰ {order.ready_time}</span></div>}
        {order.comment && <div className="od-row"><span className="od-key">Коментар</span><span className="od-val">{order.comment}</span></div>}
        <div className="od-row">
          <span className="od-key">Сума</span>
          <span className="od-val" style={{ fontWeight: 700, color: '#8B4513', fontSize: 15 }}>{grn(order.total)} ₴</span>
        </div>
      </div>
      <div className="od-items-wrap">
        <div className="od-block-title">Склад замовлення ({items.length})</div>
        {items.length ? (
          <div className="od-cards">
            {items.map((it, i) => (
              <div key={i} className="od-card">
                <div className="od-card__img">
                  {it.product_image ? (
                    <img src={it.product_image} alt="" style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 8, display: 'block' }} />
                  ) : (
                    <div className="od-card__placeholder">{it.product_name.charAt(0).toUpperCase()}</div>
                  )}
                </div>
                <div className="od-card__body">
                  <div className="od-card__name">{it.product_name}</div>
                  {it.opts.length > 0 && <div className="od-card__opts">{it.opts.join(' · ')}</div>}
                  <div className="od-card__price">
                    {grn(it.price)} ₴ × {it.quantity} = <strong>{grn(it.price * it.quantity)} ₴</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#aaa', fontSize: 13, padding: '8px 0' }}>Товари не знайдено</p>
        )}
      </div>
    </div>
  );
}
