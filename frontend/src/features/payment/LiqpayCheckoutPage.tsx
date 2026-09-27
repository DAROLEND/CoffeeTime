import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { ApiError, errorMessage, unwrap } from '@/api/errors';
import { PageError, PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import { money } from '@/lib/format';
import '@/styles/pages/liqpay/liqpay.css';

/**
 * Hand-off to LiqPay. The payment page lives on LiqPay's domain and
 * expects a signed `data`/`signature` POST, so this renders a real hidden
 * <form> and calls `.submit()` on it — a top-level navigation, not a
 * fetch (which could neither follow LiqPay's pages nor send cookies there).
 *
 * If the customer comes back (Back button / bfcache) the form is not
 * re-submitted automatically; a button appears instead.
 */
export default function LiqpayCheckoutPage() {
  usePageTitle('Перехід до оплати — Coffee Time');
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const back = params.get('back') ?? undefined;
  const formRef = useRef<HTMLFormElement>(null);
  const [status, setStatus] = useState('Переходимо до сторінки оплати…');
  const [showButton, setShowButton] = useState(false);

  const q = useQuery({
    queryKey: ['liqpay', back ?? ''],
    queryFn: () => unwrap(api.GET('/api/liqpay/checkout', { params: { query: { back } } })),
    staleTime: Infinity,
    gcTime: 0,
  });
  const data = q.data;

  useEffect(() => {
    if (!data) return;
    if (data.dev_bypass) {
      navigate('/payment-success', { replace: true });
      return;
    }
    const sentKey = `liqpay_sent_${data.order_id}`;
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        setStatus('Якщо хочете оплатити — натисніть кнопку нижче.');
        setShowButton(true);
      }
    };
    window.addEventListener('pageshow', onPageShow);

    if (sessionStorage.getItem(sentKey)) {
      setStatus('Якщо сторінка оплати не відкрилась — натисніть кнопку нижче.');
      setShowButton(true);
      return () => window.removeEventListener('pageshow', onPageShow);
    }

    let dots = 0;
    const dotsTimer = window.setInterval(() => {
      dots = (dots + 1) % 4;
      setStatus(`Переходимо до сторінки оплати${'.'.repeat(dots)}`);
    }, 400);
    const submitTimer = window.setTimeout(() => {
      window.clearInterval(dotsTimer);
      sessionStorage.setItem(sentKey, '1');
      formRef.current?.submit();
      window.setTimeout(() => {
        setStatus('Якщо сторінка оплати не відкрилась — натисніть кнопку нижче.');
        setShowButton(true);
      }, 2000);
    }, 800);
    return () => {
      window.clearInterval(dotsTimer);
      window.clearTimeout(submitTimer);
      window.removeEventListener('pageshow', onPageShow);
    };
  }, [data, navigate]);

  if (q.error instanceof ApiError && q.error.code === 'no_pending_order') return <Navigate to="/cart" replace />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  if (!data || data.dev_bypass) return <PageLoader />;

  return (
    <div className="pg-liqpay">
      <div className="pay-box">
        <div className="pay-icon">💳</div>
        <h2>Оплата замовлення #{data.order_id}</h2>
        <p className="pay-sub" aria-live="polite">
          {status}
        </p>
        <div className="pay-amount">{money(data.total)}</div>

        <form ref={formRef} method="POST" action={data.action_url} acceptCharset="utf-8">
          <input type="hidden" name="data" value={data.data} />
          <input type="hidden" name="signature" value={data.signature} />
          <button type="submit" className={`pay-btn${showButton ? ' visible' : ''}`} style={{ marginTop: 8 }}>
            Перейти до оплати →
          </button>
        </form>

        {data.is_localhost && (
          <p style={{ fontSize: 12, color: '#bbb', marginTop: 20 }}>
            Після оплати поверніться на сайт вручну:
            <br />
            <Link to="/payment-pending" style={{ color: '#8B4513' }}>
              → Перевірити статус оплати
            </Link>
          </p>
        )}
        <Link to={data.back_href} className="pay-back">
          {data.back_label}
        </Link>
        <div className="liqpay-badge">
          Powered by <strong>LiqPay</strong> · PCI DSS
        </div>
      </div>
    </div>
  );
}
