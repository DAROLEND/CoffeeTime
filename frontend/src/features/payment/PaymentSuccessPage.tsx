import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { invalidateCart } from '@/api/queries';
import { PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import { money } from '@/lib/format';
import '@/styles/pages/payment/payment.css';

const CONFETTI_COLORS = ['#FFC107', '#FF7043', '#66BB6A', '#42A5F5', '#AB47BC', '#FF8A65'];

function Confetti() {
  // Generated once per mount.
  const pieces = useRef(
    Array.from({ length: 80 }, (_, i) => ({
      left: (Math.random() * 100).toFixed(1),
      size: (6 + Math.random() * 7).toFixed(1),
      dur: (1.6 + Math.random() * 1.6).toFixed(2),
      delay: (Math.random() * 0.8).toFixed(2),
      round: Math.random() > 0.45,
      color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    })),
  ).current;
  return (
    <div aria-hidden="true">
      {pieces.map((p, i) => (
        <div
          key={i}
          className="confetti-piece"
          style={{
            left: `${p.left}vw`, top: -20, width: `${p.size}px`, height: `${p.size}px`, background: p.color,
            borderRadius: p.round ? '50%' : '2px', ['--dur' as string]: `${p.dur}s`, ['--delay' as string]: `${p.delay}s`,
          }}
        />
      ))}
    </div>
  );
}

/**
 * Order placed. Calls /api/payments/complete once (clears the cart and
 * returns the summary; the endpoint is idempotent, so StrictMode's double
 * effect or a refresh is harmless). A card payment LiqPay hasn't
 * confirmed yet is polled until the webhook lands.
 */
export default function PaymentSuccessPage() {
  usePageTitle('Замовлення прийнято — Coffee Time');
  const client = useQueryClient();
  const complete = useMutation({
    mutationFn: () => unwrap(api.POST('/api/payments/complete')),
    onSuccess: () => invalidateCart(client),
  });
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    complete.mutate();
  }, [complete]);

  const order = complete.data?.order;
  const awaitingCard = !!order && order.payment_method === 'card_online' && order.payment_status === 'pending' && !complete.data?.is_dev_bypass;
  const status = useQuery({
    queryKey: ['payment-status', order?.order_id],
    queryFn: () => unwrap(api.GET('/api/payments/status', { params: { query: { order_id: order!.order_id } } })),
    enabled: awaitingCard,
    refetchInterval: (q) => (q.state.data?.status === 'pending' && q.state.dataUpdateCount < 36 ? 5000 : false),
  });

  if (complete.isPending || complete.isIdle) return <PageLoader />;
  const isDev = !!complete.data?.is_dev_bypass;
  const paymentStatus = status.data?.status && status.data.status !== 'unknown' ? status.data.status : order?.payment_status;

  return (
    <div className="pg-payment">
      {!isDev && order && <Confetti />}
      <main className="success-page-wrap">
        <div className="success-card">
          <div className="sv-icon">
            <svg className="sv-svg" viewBox="0 0 52 52">
              <circle className="sv-circle" cx="26" cy="26" r="25" />
              <path className="sv-check" d="M14 27l7.5 7.5 16.5-17" />
            </svg>
          </div>
          {isDev ? (
            <>
              <h2 className="sv-title">Замовлення створено</h2>
              <p className="sv-sub" style={{ color: '#e65100' }}>
                <strong>⚠ Тестовий режим</strong> — LiqPay не налаштовано.
                <br />
                Оплата картою не була оброблена. Для реальних платежів
                <br />
                вкажіть валідні ключі в <code>.env</code>.
              </p>
            </>
          ) : (
            <>
              <h2 className="sv-title">Замовлення прийнято!</h2>
              <p className="sv-sub">
                Дякуємо за замовлення в Coffee Time.
                <br />
                Ми вже розпочали готувати для вас ☕
              </p>
            </>
          )}
          {order && (
            <div className="sv-details">
              <div className="sv-row">
                <span>Номер замовлення</span>
                <strong>#{order.order_id}</strong>
              </div>
              <div className="sv-row">
                <span>Сума оплати</span>
                <strong>{money(order.total)}</strong>
              </div>
              <div className="sv-row">
                <span>Статус оплати</span>
                {paymentStatus === 'paid' ? (
                  <span className="sv-status-paid">✓ Оплачено</span>
                ) : order.payment_method === 'cash_on_pickup' ? (
                  <span className="sv-status-pending">Готівка при отриманні</span>
                ) : (
                  <span className="sv-status-pending">Очікує підтвердження</span>
                )}
              </div>
              {order.ready_time && (
                <div className="sv-row">
                  <span>Час готовності</span>
                  <strong>🕐 {order.ready_time}</strong>
                </div>
              )}
            </div>
          )}
          <div className="sv-actions">
            <Link to="/" className="sv-btn-primary">
              На головну
            </Link>
            <Link to="/menu" className="sv-btn-outline">
              Продовжити покупки
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
