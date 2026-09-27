import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/payment/payment.css';

export default function PaymentFailurePage() {
  usePageTitle('Оплату не завершено — Coffee Time');
  const info = useQuery({ queryKey: ['payment-failure'], queryFn: () => unwrap(api.GET('/api/payments/failure')) });

  return (
    <div className="pg-payment">
      <main className="fail-page-wrap">
        <div className="fail-card">
          <div className="fail-icon">✕</div>
          <h2 className="fail-title">Оплату не завершено</h2>
          <p className="fail-sub">
            На жаль, платіж не пройшов або був скасований.
            <br />
            Спробуйте ще раз або оберіть оплату готівкою при отриманні.
          </p>
          <div className="fail-actions">
            {!!info.data?.order_id && (
              <Link to="/liqpay-checkout" className="fail-btn-primary">
                Спробувати ще раз
              </Link>
            )}
            <Link to="/checkout?cancel=1" className="fail-btn-outline">
              Повернутись до оформлення
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
