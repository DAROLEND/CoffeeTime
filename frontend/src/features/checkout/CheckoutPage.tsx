import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { ApiError, errorMessage, unwrap } from '@/api/errors';
import { invalidateCart, qk } from '@/api/queries';
import type { CheckoutRequest, CheckoutView } from '@/api/types';
import { Icon } from '@/components/Icon';
import { PageError, PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import { money } from '@/lib/format';
import { formatPhone, PHONE_RE } from '@/lib/phone';
import '@/styles/pages/checkout/checkout.css';
import { Drum } from './Drum';
import {
  asapSlot, availableDays, availableHours, availableMinutes, cafeClock, dayDrumLabel, dayLabel, fmtDate,
  isAdvanceOrder, needsReminderEmail, type Schedule,
} from './timeSlots';

const TRAVEL_CHIPS = [5, 15, 25, 35];
const MISSING_FIELDS = 'missing_fields';

type Pick = { day: string; hour: number; min: number };
type FieldState = 'valid' | 'error' | '';
const pad = (n: number) => String(n).padStart(2, '0');

function parseReadyTime(v: string): Pick | null {
  const m = v.match(/^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})$/);
  return m ? { day: m[1], hour: Number(m[2]), min: Number(m[3]) } : null;
}

function Field({ id, state, msg, children }: { id: string; state: FieldState; msg?: string; children: React.ReactNode }) {
  return (
    <div>
      <div className={`field-group${state === 'valid' ? ' co-valid' : state === 'error' ? ' co-error' : ''}`} id={id}>
        {children}
      </div>
      <div className={`field-msg${state === 'error' ? ' err' : state === 'valid' ? ' ok' : ''}`}>{msg ?? ''}</div>
    </div>
  );
}

function CheckoutForm({ view }: { view: CheckoutView }) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const prefill = view.prefill;
  const schedule = view.schedule as Schedule;
  const clock = useMemo(() => cafeClock(view.server_now), [view.server_now]);

  const [orderType, setOrderType] = useState(prefill.order_type);
  const [firstName, setFirstName] = useState(prefill.first_name);
  const [lastName, setLastName] = useState(prefill.last_name);
  const [phone, setPhone] = useState(formatPhone(prefill.phone));
  const [email, setEmail] = useState(prefill.customer_email);
  const [comment, setComment] = useState(prefill.comment);
  const [payment, setPayment] = useState(prefill.payment);
  const [travel, setTravel] = useState(15);
  const [fieldState, setFieldState] = useState<Record<string, FieldState>>({});
  const [timeError, setTimeError] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [serverError, setServerError] = useState('');
  const [sectionsIn, setSectionsIn] = useState(0);
  const commentRef = useRef<HTMLTextAreaElement>(null);

  const ctx = { now: clock(), schedule, prepMinutes: view.prep_minutes, travelMinutes: travel };
  const days = availableDays(ctx, view.max_days_ahead);

  const asapPick = (): Pick | null => {
    const slot = asapSlot({ ...ctx, now: clock() });
    return slot ? { day: fmtDate(slot), hour: slot.getHours(), min: slot.getMinutes() } : null;
  };

  const [pick, setPick] = useState<Pick | null>(() => parseReadyTime(prefill.ready_time) ?? asapPick());
  const hours = pick ? availableHours(pick.day, ctx) : [];
  const mins = pick ? availableMinutes(pick.day, pick.hour, ctx) : [];
  const readyTime = pick ? `${pick.day} ${pad(pick.hour)}:${pad(pick.min)}` : '';
  const asapNow = asapPick();
  const asapActive = !!pick && !!asapNow && asapNow.day === pick.day && asapNow.hour === pick.hour && asapNow.min === pick.min;
  const today = fmtDate(ctx.now);
  const advance = isAdvanceOrder(readyTime, ctx.now);
  const showEmail = needsReminderEmail(readyTime, ctx.now);

  // Staggered section entrance.
  useEffect(() => {
    const timers = [0, 1, 2, 3, 4, 5].map((i) => window.setTimeout(() => setSectionsIn(i + 1), 100 + i * 110));
    return () => timers.forEach(window.clearTimeout);
  }, []);

  // A later-day pickup can only be prepaid online.
  useEffect(() => {
    if (advance && payment === 'cash_on_pickup') setPayment('card_online');
  }, [advance, payment]);

  // The reminder email is prefilled from the account when it becomes relevant.
  useEffect(() => {
    if (showEmail && !email && view.user_email) setEmail(view.user_email);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showEmail]);

  useEffect(() => {
    const el = commentRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [comment]);

  /** Re-fit hour/minute when the day (or earlier wheel) changes. */
  const choose = (day: string, hour: number | null, min: number | null) => {
    const hs = availableHours(day, ctx);
    const h = hour !== null && hs.includes(hour) ? hour : hs[0];
    if (h === undefined) return;
    const ms = availableMinutes(day, h, ctx);
    const m = min !== null && ms.includes(min) ? min : ms[0];
    setPick({ day, hour: h, min: m });
    setTimeError('');
  };

  const chooseAsap = (travelMinutes = travel) => {
    const slot = asapSlot({ ...ctx, now: clock(), travelMinutes });
    if (!slot) {
      setTimeError('Кафе зачинене найближчим часом.');
      return;
    }
    setPick({ day: fmtDate(slot), hour: slot.getHours(), min: slot.getMinutes() });
    setTimeError('');
  };

  const validateName = (key: string, v: string) => {
    const ok = v.trim().length >= 2;
    setFieldState((s) => ({ ...s, [key]: ok ? 'valid' : 'error' }));
    return ok;
  };
  const validatePhone = () => {
    const ok = PHONE_RE.test(phone);
    setFieldState((s) => ({ ...s, phone: ok ? 'valid' : 'error' }));
    return ok;
  };

  const place = useMutation({
    mutationFn: (body: CheckoutRequest) => unwrap(api.POST('/api/checkout', { body })),
  });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const checks = [
      validateName('first', firstName),
      validateName('last', lastName),
      validatePhone(),
      (() => {
        if (!readyTime) setTimeError('Оберіть дату та час отримання');
        return !!readyTime;
      })(),
      (() => {
        if (!payment) setPaymentError('Оберіть спосіб оплати');
        return !!payment;
      })(),
    ];
    if (!checks.every(Boolean)) {
      window.setTimeout(() => document.querySelector('.field-msg.err')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0);
      return;
    }
    // "As soon as possible" means as of *now*, not when the page was opened.
    let finalTime = readyTime;
    if (asapActive) {
      const fresh = asapPick();
      if (fresh) finalTime = `${fresh.day} ${pad(fresh.hour)}:${pad(fresh.min)}`;
    }
    setServerError('');
    try {
      const res = await place.mutateAsync({
        first_name: firstName, last_name: lastName, phone, customer_email: showEmail ? email : '',
        ready_time: finalTime, comment, payment, order_type: orderType, travel_minutes: travel,
      });
      await invalidateCart(client);
      navigate(res.next === 'liqpay' ? '/liqpay-checkout' : '/payment-success');
    } catch (err) {
      if (!(err instanceof ApiError) || err.code !== MISSING_FIELDS) setServerError(errorMessage(err));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const isCard = payment === 'card_online';
  const sectionClass = (i: number) => `form-section${sectionsIn > i ? ' visible' : ''}`;
  const dayIdx = pick ? Math.max(0, days.indexOf(pick.day)) : 0;

  return (
    <div className="checkout-layout">
      <div className="checkout-form-col">
        {serverError && <div className="checkout-error">{serverError}</div>}
        {view.has_cakes && (
          <div style={{ background: '#fff8e1', borderRadius: 10, padding: '14px 18px', borderLeft: '4px solid #FFC107', marginBottom: 20, fontSize: 14, lineHeight: 1.55, color: '#5a4000' }}>
            Торти на замовлення готуються від 1 до 3 днів. Менеджер зв'яжеться з вами після підтвердження замовлення для уточнення деталей.
          </div>
        )}

        <form id="checkoutForm" noValidate onSubmit={submit}>
          <div className={`${sectionClass(0)} order-type-section`}>
            <h2 className="section-title" style={{ marginBottom: 14 }}>
              <span className="section-num">1</span> Тип замовлення
            </h2>
            <div className="order-type-btns">
              <button type="button" className={`ot-btn${orderType === 'dine_in' ? ' active' : ''}`} aria-pressed={orderType === 'dine_in'} onClick={() => setOrderType('dine_in')}>
                <Icon name="dine-in" size={32} color="#8B4513" className="ot-icon" />
                <span className="ot-label">В кафе</span>
                <span className="ot-sub">Їжте на місці</span>
              </button>
              <button type="button" className={`ot-btn${orderType === 'takeaway' ? ' active' : ''}`} aria-pressed={orderType === 'takeaway'} onClick={() => setOrderType('takeaway')}>
                <Icon name="takeaway" size={32} color="#8B4513" className="ot-icon" />
                <span className="ot-label">З собою</span>
                <span className="ot-sub">Заберіть замовлення</span>
              </button>
            </div>
          </div>

          <div className={sectionClass(1)}>
            <h2 className="section-title">
              <span className="section-num">2</span> Контактні дані
            </h2>
            <div className="form-row">
              <Field id="fg-first" state={fieldState.first ?? ''} msg={fieldState.first === 'error' ? 'Мінімум 2 символи' : ''}>
                <input type="text" id="first_name" placeholder=" " value={firstName} autoComplete="given-name" onChange={(e) => setFirstName(e.target.value)} onBlur={() => validateName('first', firstName)} />
                <label htmlFor="first_name">Ім'я *</label>
              </Field>
              <Field id="fg-last" state={fieldState.last ?? ''} msg={fieldState.last === 'error' ? 'Мінімум 2 символи' : ''}>
                <input type="text" id="last_name" placeholder=" " value={lastName} autoComplete="family-name" onChange={(e) => setLastName(e.target.value)} onBlur={() => validateName('last', lastName)} />
                <label htmlFor="last_name">Прізвище *</label>
              </Field>
            </div>
            <Field id="fg-phone" state={fieldState.phone ?? ''} msg={fieldState.phone === 'error' ? 'Формат: +38 (0XX) XXX-XX-XX' : ''}>
              <input type="tel" id="phone" placeholder="+38 (0XX) XXX-XX-XX" value={phone} autoComplete="tel" onChange={(e) => setPhone(formatPhone(e.target.value))} onBlur={validatePhone} />
              <label htmlFor="phone">Телефон *</label>
            </Field>
            <div className={`field-group${showEmail ? '' : ' fg-hidden'}`} id="fg-email" style={{ marginTop: 4 }}>
              <input type="email" id="customer_email" placeholder="your@email.com" value={email} autoComplete="email" disabled={!showEmail} onChange={(e) => setEmail(e.target.value)} />
              <label htmlFor="customer_email">Email для нагадувань (необов'язково)</label>
            </div>
          </div>

          <div className={sectionClass(2)}>
            <h2 className="section-title">
              <span className="section-num">3</span> Дата та час отримання
            </h2>
            <button type="button" className={`dt-asap-btn${asapActive ? ' active' : ''}`} onClick={() => chooseAsap()}>
              <span className="dt-asap-label">Якнайшвидше</span>
              <span className="dt-asap-time">{asapActive && pick ? `~${pad(pick.hour)}:${pad(pick.min)}` : ''}</span>
            </button>
            <div className={`dt-travel${asapActive && pick?.day === today ? ' visible' : ''}`}>
              <span className="dt-travel-label">Час до кафе:</span>
              <div className="dt-travel-chips">
                {TRAVEL_CHIPS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    className={`dt-travel-chip${travel === m ? ' active' : ''}`}
                    onClick={() => {
                      setTravel(m);
                      chooseAsap(m);
                    }}
                  >
                    {m} хв
                  </button>
                ))}
              </div>
            </div>

            <div className="dt-drums">
              <div className="dt-drum-col">
                <div className="dt-drum-lbl">Дата</div>
                <Drum label="Дата" duration={380} items={days.map((d) => dayDrumLabel(d, ctx.now))} selected={dayIdx} onChange={(i) => choose(days[i], pick?.hour ?? null, pick?.min ?? null)} />
              </div>
              <div className="dt-drum-sep" />
              <div className="dt-drum-col" style={{ flex: '0 0 68px' }}>
                <div className="dt-drum-lbl">Год</div>
                <Drum label="Година" duration={300} items={hours.map(pad)} selected={Math.max(0, hours.indexOf(pick?.hour ?? -1))} onChange={(i) => pick && choose(pick.day, hours[i], pick.min)} />
              </div>
              <div className="dt-drum-colon">
                <span>:</span>
              </div>
              <div className="dt-drum-col" style={{ flex: '0 0 58px' }}>
                <div className="dt-drum-lbl">Хв</div>
                <Drum label="Хвилини" duration={240} items={mins.map(pad)} selected={Math.max(0, mins.indexOf(pick?.min ?? -1))} onChange={(i) => pick && setPick({ ...pick, min: mins[i] })} />
              </div>
            </div>

            {pick && (
              <div className="dt-summary" style={{ display: 'flex' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                <span>
                  {dayLabel(pick.day, ctx.now)} о {pad(pick.hour)}:{pad(pick.min)}
                </span>
              </div>
            )}
            <div className={`field-msg${timeError ? ' err' : ''}`}>{timeError}</div>
            <p className="time-hint">Пн–Пт 08:00–20:00 &nbsp;·&nbsp; Сб 10:00–20:00 &nbsp;·&nbsp; Нд 12:00–20:00</p>
          </div>

          <div className={sectionClass(3)}>
            <h2 className="section-title">
              <span className="section-num">4</span> Коментар до замовлення
            </h2>
            <div className="field-group" id="fg-comment">
              <textarea ref={commentRef} id="comment" placeholder=" " rows={3} className={comment.trim() ? 'has-value' : ''} value={comment} onChange={(e) => setComment(e.target.value)} />
              <label htmlFor="comment">Додаткові побажання (необов'язково)</label>
            </div>
          </div>

          <div className={sectionClass(4)}>
            <h2 className="section-title">
              <span className="section-num">5</span> Спосіб оплати
            </h2>
            <div className="payment-cards">
              <label className="payment-card" style={advance ? { opacity: 0.4, pointerEvents: 'none' } : undefined}>
                <input type="radio" name="payment" value="cash_on_pickup" checked={payment === 'cash_on_pickup'} disabled={advance} onChange={() => { setPayment('cash_on_pickup'); setPaymentError(''); }} />
                <span className="pay-checkmark"><svg viewBox="0 0 12 10"><polyline points="1.5 5 4.5 8.5 10.5 1.5" /></svg></span>
                <Icon name="cash" size={32} color="#8B4513" className="pay-icon" />
                <div className="pay-name">При отриманні</div>
                <div className="pay-desc">Готівка або картка на місці</div>
              </label>
              <label className="payment-card">
                <input type="radio" name="payment" value="card_online" checked={payment === 'card_online'} onChange={() => { setPayment('card_online'); setPaymentError(''); }} />
                <span className="pay-checkmark"><svg viewBox="0 0 12 10"><polyline points="1.5 5 4.5 8.5 10.5 1.5" /></svg></span>
                <Icon name="card" size={32} color="#8B4513" className="pay-icon" />
                <div className="pay-name">Картка онлайн</div>
                <div className="pay-desc">Visa / Mastercard через LiqPay</div>
              </label>
            </div>
            {advance && (
              <p style={{ fontSize: 12, color: '#b07840', margin: '10px 0 0', lineHeight: 1.5 }}>
                ⚠ Замовлення на майбутній день приймаються лише з онлайн-оплатою карткою.
              </p>
            )}
            <div className={`field-msg${paymentError ? ' err' : ''}`}>{paymentError}</div>
            <div className={`liqpay-info${isCard ? ' show' : ''}`}>
              <Icon name="lock" size={16} color="#aaa" className="liqpay-lock" />
              <p>
                Ви будете перенаправлені на захищену сторінку оплати LiqPay. Дані вашої картки обробляються безпечно за стандартом <strong>PCI DSS</strong>.
              </p>
            </div>
          </div>
        </form>
      </div>

      <div className="checkout-summary-col">
        <div className={`checkout-summary-box${sectionsIn > 1 ? ' visible' : ''}`}>
          <h3 className="summary-title">Ваше замовлення</h3>
          <ul className="order-items-list">
            {view.items.map((it, i) => (
              <li className="order-item" key={`${it.category}-${it.id}-${i}`}>
                {it.image ? <img src={it.image} alt={it.name} loading="lazy" /> : <div className="order-item-no-img" aria-hidden="true" />}
                <div className="order-item-info">
                  <div className="order-item-name">{it.name}</div>
                  <div className="order-item-qty">{it.quantity} шт.</div>
                </div>
                <div className="order-item-price">{money(it.subtotal)}</div>
              </li>
            ))}
          </ul>
          <div className="summary-divider" />
          <div className="summary-total-row">
            <span className="summary-total-label">Загальна сума:</span>
            <span className="summary-total-price">{money(view.total)}</span>
          </div>
          <button type="submit" form="checkoutForm" className={`btn-checkout${place.isPending ? ' loading' : ''}`} disabled={place.isPending}>
            {place.isPending ? '' : isCard ? 'Перейти до оплати →' : 'Оформити замовлення'}
          </button>
        </div>
      </div>

      <div className="checkout-sticky-bar">
        <div className="checkout-sticky-total">
          <span className="checkout-sticky-label">Сума:</span>
          <span className="checkout-sticky-amount">{money(view.total)}</span>
        </div>
        <button type="submit" form="checkoutForm" className="checkout-sticky-submit" disabled={place.isPending}>
          Оформити замовлення
        </button>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  usePageTitle('Оформлення замовлення — Coffee Time');
  const [params, setParams] = useSearchParams();
  const client = useQueryClient();
  const cancelling = params.get('cancel') === '1';
  const [cancelled, setCancelled] = useState(!cancelling);

  // Back from the LiqPay page: cancel the unpaid order, keep the form draft.
  useEffect(() => {
    if (!cancelling) return;
    void unwrap(api.POST('/api/checkout/cancel-pending'))
      .catch(() => undefined)
      .finally(() => {
        setParams({}, { replace: true });
        void client.invalidateQueries({ queryKey: qk.checkout });
        setCancelled(true);
      });
  }, [cancelling, client, setParams]);

  const checkout = useQuery({
    queryKey: qk.checkout,
    queryFn: () => unwrap(api.GET('/api/checkout')),
    enabled: cancelled,
    staleTime: 0,
  });

  if (!cancelled || checkout.isPending) return <PageLoader />;
  if (checkout.error instanceof ApiError && checkout.error.code === 'cart_empty') return <Navigate to="/cart" replace />;
  if (checkout.error) return <PageError message={errorMessage(checkout.error)} onRetry={() => checkout.refetch()} />;

  return (
    <div className="pg-checkout">
      <main className="checkout-page">
        <nav className="breadcrumb" aria-label="Навігація">
          <Link to="/cart">Кошик</Link>
          <span className="bc-sep">›</span>
          <span className="bc-current">Оформлення</span>
          <span className="bc-sep">›</span>
          <span className="bc-future">Підтвердження</span>
        </nav>
        <CheckoutForm view={checkout.data} />
      </main>
    </div>
  );
}
