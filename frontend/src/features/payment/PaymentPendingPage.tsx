import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/payment/payment.css';

const POLL_MS = 5000;
const MAX_CHECKS = 72; // 6 minutes

/** Waits for LiqPay's confirmation, polling the order's payment status. */
export default function PaymentPendingPage() {
  usePageTitle('Очікуємо оплату — Coffee Time');
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const orderId = Number(params.get('order_id') || 0) || undefined;
  const [message, setMessage] = useState('');

  const info = useQuery({
    queryKey: ['payment-pending', orderId],
    queryFn: () => unwrap(api.GET('/api/payments/pending', { params: { query: { order_id: orderId } } })),
    retry: false,
  });
  const id = info.data?.order_id;

  const status = useQuery({
    queryKey: ['payment-status', id],
    queryFn: () => unwrap(api.GET('/api/payments/status', { params: { query: { order_id: id! } } })),
    enabled: !!id,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      if (s === 'paid' || s === 'failed') return false;
      return q.state.dataUpdateCount < MAX_CHECKS ? POLL_MS : false;
    },
  });

  useEffect(() => {
    const s = status.data?.status;
    if (s === 'paid') {
      setMessage('✅ Оплата підтверджена! Переходимо…');
      const t = window.setTimeout(() => navigate('/payment-success'), 800);
      return () => window.clearTimeout(t);
    }
    if (s === 'failed') {
      setMessage('❌ Оплата не пройшла. Переходимо…');
      const t = window.setTimeout(() => navigate('/payment-failure'), 800);
      return () => window.clearTimeout(t);
    }
  }, [status.data, navigate]);

  // Polling stops after MAX_CHECKS answers that are still "pending".
  const client = useQueryClient();
  const checks = client.getQueryState(['payment-status', id])?.dataUpdateCount ?? 0;
  const timedOut = status.data?.status === 'pending' && checks >= MAX_CHECKS;

  if (info.isPending) return <PageLoader />;
  if (info.error) return <Navigate to="/cart" replace />;

  return (
    <div className="pg-payment">
      <main>
        <div className="pending-wrap">
          <div className="pending-icon">💳</div>
          <h1>Очікуємо оплату</h1>
          <p>Вікно оплати LiqPay відкрилось у новій вкладці.</p>
          <p className="sub">Після успішної оплати ця сторінка оновиться автоматично.</p>
          <div className="pulse-dots" style={{ marginBottom: 32 }}>
            <span />
            <span />
            <span />
          </div>
          {(message || timedOut) && (
            <div id="statusMsg" style={{ display: 'block' }} role="status">
              {message || 'Час очікування вичерпано. Перевірте стан замовлення або зверніться до підтримки.'}
            </div>
          )}
          {info.data?.liqpay_data && (
            <form method="POST" action="https://www.liqpay.ua/api/3/checkout" acceptCharset="utf-8" target="_blank" style={{ marginBottom: 16 }}>
              <input type="hidden" name="data" value={info.data.liqpay_data} />
              <input type="hidden" name="signature" value={info.data.liqpay_signature} />
              <button type="submit" className="btn-reopen">
                Відкрити вікно оплати ще раз
              </button>
            </form>
          )}
          <Link to="/checkout" className="btn-back">
            ← Повернутись до оформлення
          </Link>
        </div>
      </main>
    </div>
  );
}
