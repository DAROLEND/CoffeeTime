import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { qk } from '@/api/queries';
import type { ProfileOrder } from '@/api/types';
import { useToast } from '@/components/Toast';
import { useReveal } from '@/hooks/useReveal';
import { fmtDateTime, money } from '@/lib/format';

function OrderItems({ orderId }: { orderId: number }) {
  const items = useQuery({
    queryKey: ['profile', 'order-items', orderId],
    queryFn: () => unwrap(api.GET('/api/profile/orders/{order_id}/items', { params: { path: { order_id: orderId } } })),
    staleTime: Infinity,
  });
  if (items.isPending) return <div className="oi-loading">Завантаження…</div>;
  if (items.error) return <div className="oi-loading">Помилка завантаження</div>;
  if (!items.data.items.length) return <p className="oi-empty">Товари не знайдено</p>;
  return (
    <div className="oi-list">
      {items.data.items.map((item, i) => (
        <div className="oi-row" key={i}>
          <div className="oi-img-wrap">
            {item.image ? <img className="oi-img" src={item.image} alt="" loading="lazy" /> : <div className="oi-img-ph">{(item.name || '?').charAt(0).toUpperCase()}</div>}
          </div>
          <span className="oi-name">
            {item.name}
            {item.opts.length > 0 && <small style={{ display: 'block', color: '#aaa', fontSize: 11 }}>{item.opts.join(' · ')}</small>}
          </span>
          <span className="oi-qty">×{item.quantity}</span>
          <span className="oi-price">{money(item.quantity * item.price)}</span>
        </div>
      ))}
    </div>
  );
}

function Rating({ order }: { order: ProfileOrder }) {
  const client = useQueryClient();
  const toast = useToast();
  const [hover, setHover] = useState(0);
  const [picked, setPicked] = useState(0);
  const rate = useMutation({
    mutationFn: (rating: number) =>
      unwrap(api.POST('/api/profile/orders/{order_id}/rating', { params: { path: { order_id: order.order_id } }, body: { rating } })),
    onSuccess: () => client.invalidateQueries({ queryKey: qk.profile }),
    onError: (err) => {
      setPicked(0);
      toast(errorMessage(err));
    },
  });

  const value = order.rating ?? (rate.isSuccess ? picked : 0);
  if (value) {
    return (
      <div className="order-card__rating order-card__rating--done">
        <div className="ocr-result">
          <div className="ocr-stars-static" aria-label={`Оцінка ${value} з 5`}>
            {'★'.repeat(value)}
            <span className="ocr-stars-empty">{'★'.repeat(5 - value)}</span>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="order-card__rating">
      <div className="ocr-prompt">
        <span className="ocr-label">Оцінити:</span>
        <div className="ocr-stars" style={rate.isPending ? { pointerEvents: 'none', opacity: 0.6 } : undefined} onMouseLeave={() => setHover(0)}>
          {[1, 2, 3, 4, 5].map((v) => (
            <button
              key={v}
              type="button"
              className={`ocr-star${v <= hover ? ' hovered' : ''}${!hover && v <= picked ? ' selected' : ''}`}
              aria-label={`${v} з 5`}
              onMouseEnter={() => setHover(v)}
              onClick={() => {
                setPicked(v);
                rate.mutate(v);
              }}
            >
              ★
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function OrderCard({ order, index, delayStep }: { order: ProfileOrder; index: number; delayStep: number }) {
  const ref = useReveal<HTMLDivElement>({ className: 'revealed', threshold: 0.05 });
  const navigate = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const names = order.preview_names;
  const dishLine = names.length >= 2 ? `${names[0]}, ${names[1]}` : (names[0] ?? 'Замовлення');

  const repay = useMutation({
    mutationFn: () => unwrap(api.POST('/api/profile/orders/{order_id}/repay', { params: { path: { order_id: order.order_id } } })),
    onSuccess: (res) => navigate(res.redirect),
    onError: (err) => toast(errorMessage(err)),
  });

  return (
    <div ref={ref} className="order-card" style={{ ['--reveal-delay' as string]: `${index * delayStep}s` }}>
      <div className="order-card__top">
        <div className="order-card__top-left">
          <div className="order-card__num">
            #{order.order_id} &middot; {order.items_count} поз.
          </div>
          <div className="order-card__dish">{dishLine}</div>
          {order.preview_remaining > 0 && <div className="order-card__dish-extra">та ще {order.preview_remaining}</div>}
        </div>
        <div className="order-card__price">{money(order.total)}</div>
      </div>

      <div className="order-card__meta">
        <div className="order-card__tags">
          {order.is_pending ? <span className="ppay ppay-pending">Не оплачено</span> : <span className={`ppay ${order.pay_badge.cls}`}>{order.pay_badge.label}</span>}
          {order.status_label && <span className={`pstat pstat-${order.status}`}>{order.status_label}</span>}
        </div>
        <div className="order-card__time">
          {fmtDateTime(order.created_at)}
          {order.ready_time && (
            <>
              {' · '}
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg> до {order.ready_time}
            </>
          )}
        </div>
      </div>

      <div className="order-card__footer">
        {order.is_done && <Rating order={order} />}
        <div className="oc-btn-group">
          {order.is_pending && (
            <button type="button" className="oc-btn oc-btn--pay" onClick={() => repay.mutate()} disabled={repay.isPending}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><rect x="1" y="4" width="22" height="16" rx="2" /><line x1="1" y1="10" x2="23" y2="10" /></svg>
              Оплатити
            </button>
          )}
          <button
            type="button"
            className={`oc-btn oc-btn--details${open ? ' active' : ''}`}
            aria-expanded={open}
            onClick={() => {
              setOpen((o) => !o);
              setLoaded(true);
            }}
          >
            Деталі
            <svg className="toggle-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ transform: open ? 'rotate(180deg)' : undefined }}><polyline points="6 9 12 15 18 9" /></svg>
          </button>
        </div>
      </div>

      <div className={`order-card__details${open ? ' open' : ''}`}>
        <div className="order-card__details-inner">
          {order.comment && <div className="order-card__comment">💬 {order.comment}</div>}
          {loaded && <OrderItems orderId={order.order_id} />}
        </div>
      </div>
    </div>
  );
}
