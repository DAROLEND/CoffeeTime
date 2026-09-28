import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { qk, useLogout } from '@/api/queries';
import type { ProfileOrder, ProfileView } from '@/api/types';
import { PageError, PageLoader } from '@/components/Spinner';
import { useCountUp } from '@/hooks/useCountUp';
import { usePageTitle } from '@/hooks/usePageTitle';
import { formatPhone } from '@/lib/phone';
import { PasswordInput } from '../auth/AuthShell';
import '@/styles/pages/profile/profile.css';
import { OrderCard } from './OrderCard';

type Range = { from: string; to: string };
const pad = (n: number) => String(n).padStart(2, '0');
const ymd = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

function quickRange(kind: string): Range {
  const today = new Date();
  if (kind === 'today') return { from: ymd(today), to: ymd(today) };
  if (kind === 'week') {
    const d = new Date(today);
    d.setDate(d.getDate() - 6);
    return { from: ymd(d), to: ymd(today) };
  }
  if (kind === 'month') return { from: ymd(new Date(today.getFullYear(), today.getMonth(), 1)), to: ymd(today) };
  return { from: '', to: '' };
}

function inRange(o: ProfileOrder, r: Range): boolean {
  const day = o.created_at.slice(0, 10);
  return (!r.from || day >= r.from) && (!r.to || day <= r.to);
}

const STRENGTH = [null, { label: 'Слабкий', color: '#f44336' }, { label: 'Середній', color: '#FF9800' }, { label: 'Сильний', color: '#FFC107' }, { label: 'Відмінний', color: '#4CAF50' }] as const;
function profileStrength(pw: string): number {
  let s = 0;
  if (pw.length >= 6) s++;
  if (pw.length >= 10) s++;
  if (/[A-ZА-ЯІЇЄҐ]/u.test(pw)) s++;
  if (/[0-9]/.test(pw)) s++;
  if (/[^a-zA-Zа-яА-ЯіїєґІЇЄҐ0-9]/u.test(pw)) s++;
  return Math.min(4, Math.max(1, s));
}

function Stat({ value, suffix, label, onClick }: { value: number; suffix?: string; label: string; onClick: () => void }) {
  const [ref, current] = useCountUp<HTMLDivElement>(value, { startOnView: false });
  return (
    <button className="prof-stat-card" title="Переглянути замовлення" onClick={onClick}>
      <div className="prof-stat-card__val" ref={ref}>
        {Math.round(current).toLocaleString('uk-UA')}
        {suffix ? ` ${suffix}` : ''}
      </div>
      <div className="prof-stat-card__label">{label}</div>
    </button>
  );
}

function OrdersPanel({ data }: { data: ProfileView }) {
  const [quick, setQuick] = useState('all');
  const [range, setRange] = useState<Range>({ from: '', to: '' });
  const hasOtherOrders = data.groups.some((g) => g.key !== 'earlier');
  const [earlierOpen, setEarlierOpen] = useState(!hasOtherOrders);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [bodyHeight, setBodyHeight] = useState<string>(earlierOpen ? 'none' : '0');
  const hasRange = !!(range.from || range.to);

  // Animate the "Раніше" group open/closed via max-height.
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    if (earlierOpen) {
      setBodyHeight(`${el.scrollHeight}px`);
      const t = window.setTimeout(() => setBodyHeight('none'), 450);
      return () => window.clearTimeout(t);
    }
    setBodyHeight(`${el.scrollHeight}px`);
    const raf = requestAnimationFrame(() => setBodyHeight('0'));
    return () => cancelAnimationFrame(raf);
  }, [earlierOpen]);

  useEffect(() => {
    if (hasRange) setEarlierOpen(true);
  }, [hasRange]);

  if (!data.has_orders) {
    return (
      <div className="prof-empty">
        <div className="prof-empty__icon">
          <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#D4A853" strokeWidth="1.4" strokeLinecap="round"><circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" /><path d="M1 1h4l2.68 13.39a2 2 0 001.99 1.61h9.72a2 2 0 001.99-1.61L23 6H6" /></svg>
        </div>
        <p className="prof-empty-title">Замовлень ще немає</p>
        <p className="prof-empty-sub">Додайте щось смачне з нашого меню ☕</p>
        <Link to="/menu" className="prof-empty-btn">Перейти до меню</Link>
      </div>
    );
  }

  const groups = data.groups.map((g) => ({ ...g, orders: g.orders.filter((o) => inRange(o, range)) }));
  const anyVisible = groups.some((g) => g.orders.length);

  return (
    <>
      <div className="orders-filter-bar">
        <div className="ofilter-quick">
          {[['all', 'Усі'], ['today', 'Сьогодні'], ['week', 'Тиждень'], ['month', 'Місяць']].map(([key, label]) => (
            <button
              key={key}
              className={`ofilter-btn${quick === key ? ' active' : ''}`}
              onClick={() => {
                setQuick(key);
                setRange(quickRange(key));
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="ofilter-range">
          <input type="date" className="ofilter-date" title="від" value={quick === 'custom' ? range.from : ''} onChange={(e) => { setQuick('custom'); setRange((r) => ({ ...r, from: e.target.value })); }} />
          <span className="ofilter-sep">—</span>
          <input type="date" className="ofilter-date" title="до" value={quick === 'custom' ? range.to : ''} onChange={(e) => { setQuick('custom'); setRange((r) => ({ ...r, to: e.target.value })); }} />
        </div>
        <button className={`ofilter-clear${hasRange ? ' visible' : ''}`} onClick={() => { setQuick('all'); setRange({ from: '', to: '' }); }}>
          ✕ Скинути
        </button>
      </div>
      {!anyVisible && hasRange && <div className="orders-empty-filter">Замовлень за вибраний період не знайдено</div>}

      <div className="orders-grid">
        {groups.map((g) => {
          if (!g.orders.length) return null;
          if (g.key === 'earlier') {
            return (
              <div key={g.key} className={`order-group order-group--collapsible${earlierOpen ? ' expanded' : ''}`}>
                <div className="order-group__label order-group__label--toggle" role="button" tabIndex={0} aria-expanded={earlierOpen}
                  onClick={() => setEarlierOpen((o) => !o)} onKeyDown={(e) => e.key === 'Enter' && setEarlierOpen((o) => !o)}>
                  {g.label}
                  <span className="order-group__count">{g.orders.length}</span>
                  <svg className="order-group__chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="6 9 12 15 18 9" /></svg>
                </div>
                <div className="order-group__body" ref={bodyRef} style={{ maxHeight: bodyHeight }}>
                  <div className="orders-grid-inner">
                    {g.orders.map((o, i) => <OrderCard key={o.order_id} order={o} index={i} delayStep={0.06} />)}
                  </div>
                </div>
              </div>
            );
          }
          return (
            <div key={g.key} className="order-group">
              <div className="order-group__label">{g.label}</div>
              {g.orders.map((o, i) => <OrderCard key={o.order_id} order={o} index={i} delayStep={0.05} />)}
            </div>
          );
        })}
      </div>
    </>
  );
}

function SettingsPanel({ data, onSaved }: { data: ProfileView; onSaved: (kind: 'profile' | 'password') => void }) {
  const client = useQueryClient();
  const [profile, setProfile] = useState({ first_name: data.user.client_name, last_name: data.user.client_surname, phone: data.user.client_PhoneNumber });
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm_password: '' });

  const saveProfile = useMutation({
    mutationFn: () => unwrap(api.PATCH('/api/profile', { body: profile })),
    onSuccess: async () => {
      await Promise.all([client.invalidateQueries({ queryKey: qk.profile }), client.invalidateQueries({ queryKey: qk.session })]);
      onSaved('profile');
    },
  });
  const savePassword = useMutation({
    mutationFn: () => unwrap(api.POST('/api/profile/password', { body: pw })),
    onSuccess: () => {
      setPw({ current_password: '', new_password: '', confirm_password: '' });
      onSaved('password');
    },
  });

  const strength = pw.new_password ? profileStrength(pw.new_password) : 0;
  const cfg = strength ? STRENGTH[strength] : null;
  const setP = (k: keyof typeof pw) => (e: React.ChangeEvent<HTMLInputElement>) => setPw((v) => ({ ...v, [k]: e.target.value }));

  return (
    <>
      <div className="prof-section">
        <div className="prof-section__title">Особисті дані</div>
        {saveProfile.error && <div className="prof-alert prof-alert--error">{errorMessage(saveProfile.error)}</div>}
        <form noValidate onSubmit={(e: FormEvent) => { e.preventDefault(); saveProfile.mutate(); }}>
          <div className="prof-form-row">
            <div className="prof-field">
              <label htmlFor="pf-first">Ім'я</label>
              <input id="pf-first" type="text" value={profile.first_name} placeholder="Ім'я" onChange={(e) => setProfile((p) => ({ ...p, first_name: e.target.value }))} />
            </div>
            <div className="prof-field">
              <label htmlFor="pf-last">Прізвище</label>
              <input id="pf-last" type="text" value={profile.last_name} placeholder="Прізвище" onChange={(e) => setProfile((p) => ({ ...p, last_name: e.target.value }))} />
            </div>
          </div>
          <div className="prof-field">
            <label htmlFor="pf-phone">Телефон</label>
            <input id="pf-phone" type="tel" value={profile.phone} placeholder="+38 (0XX) XXX-XX-XX" onChange={(e) => setProfile((p) => ({ ...p, phone: formatPhone(e.target.value) }))} />
          </div>
          <button type="submit" className={`prof-btn prof-btn--dark${saveProfile.isPending ? ' loading' : ''}`} disabled={saveProfile.isPending}>
            Зберегти зміни
          </button>
        </form>
      </div>

      <div className="prof-section">
        <div className="prof-section__title">Безпека</div>
        {savePassword.error && <div className="prof-alert prof-alert--error">{errorMessage(savePassword.error)}</div>}
        <form noValidate onSubmit={(e: FormEvent) => { e.preventDefault(); savePassword.mutate(); }}>
          <div className="prof-field">
            <label htmlFor="pwCurrent">Поточний пароль</label>
            <PasswordInput id="pwCurrent" toggleClassName="eye-btn" placeholder="••••••••" autoComplete="current-password" value={pw.current_password} onChange={setP('current_password')} />
          </div>
          <div className="prof-field">
            <label htmlFor="pwNew">Новий пароль</label>
            <PasswordInput id="pwNew" toggleClassName="eye-btn" placeholder="••••••••" autoComplete="new-password" value={pw.new_password} onChange={setP('new_password')} />
            {cfg && (
              <div className="pw-strength" style={{ display: 'block' }}>
                <div className="pw-strength-bar">
                  {[0, 1, 2, 3].map((i) => <span key={i} style={{ background: i < strength ? cfg.color : '#e8e0d8' }} />)}
                </div>
                <div className="pw-strength-label" style={{ color: cfg.color }}>{cfg.label}</div>
              </div>
            )}
          </div>
          <div className="prof-field">
            <label htmlFor="pwConfirm">Підтвердіть новий пароль</label>
            <PasswordInput id="pwConfirm" toggleClassName="eye-btn" placeholder="••••••••" autoComplete="new-password" value={pw.confirm_password} onChange={setP('confirm_password')} />
          </div>
          <button type="submit" className={`prof-btn prof-btn--dark${savePassword.isPending ? ' loading' : ''}`} disabled={savePassword.isPending}>
            Змінити пароль
          </button>
        </form>
      </div>
    </>
  );
}

export default function ProfilePage() {
  usePageTitle('Профіль — Coffee Time');
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const logout = useLogout();
  const tab = params.get('tab') === 'settings' ? 'settings' : 'orders';
  const [toast, setToast] = useState<{ text: string; out: boolean } | null>(null);
  const profile = useQuery({ queryKey: qk.profile, queryFn: () => unwrap(api.GET('/api/profile')) });

  useEffect(() => {
    if (!toast || toast.out) return;
    const t1 = window.setTimeout(() => setToast((t) => (t ? { ...t, out: true } : t)), 3200);
    const t2 = window.setTimeout(() => setToast(null), 3700);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [toast]);

  if (profile.isPending) return <PageLoader />;
  if (profile.error) return <PageError message={errorMessage(profile.error)} onRetry={() => profile.refetch()} />;
  const data = profile.data;
  const switchTab = (t: string) => setParams({ tab: t }, { replace: true });

  return (
    <div className={`pg-profile${tab === 'settings' ? ' tab-settings' : ''}`}>
      {toast && (
        <div className={`prof-toast prof-toast--success${toast.out ? ' prof-toast--out' : ''}`} role="status">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
          {toast.text}
        </div>
      )}
      <div className="prof-wrap">
        <aside className="prof-sidebar">
          <div className="prof-avatar">{data.initials}</div>
          <div className="prof-name">{data.display_name}</div>
          <div className="prof-email">{data.user.email}</div>
          {data.user.client_PhoneNumber && <div className="prof-phone">{data.user.client_PhoneNumber}</div>}
          <hr className="prof-divider" />
          <div className="prof-stats-grid">
            <Stat value={data.order_count} label="Замовлень" onClick={() => switchTab('orders')} />
            <Stat value={Math.round(data.total_spent)} suffix="₴" label="Витрачено" onClick={() => switchTab('orders')} />
          </div>
          <div className="prof-since-pill">
            <span className="prof-since-dot" />З нами з {data.joined_at}
          </div>
          <hr className="prof-divider" />
          <button type="button" className="prof-logout-btn" onClick={() => logout.mutate(undefined, { onSuccess: () => navigate('/') })}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
            Вийти
          </button>
        </aside>

        <main className="prof-main">
          <div className="prof-tabs-wrap">
            <div className="prof-tabs" role="tablist">
              <button role="tab" aria-selected={tab === 'orders'} className={`prof-tab${tab === 'orders' ? ' active' : ''}`} onClick={() => switchTab('orders')}>
                Мої замовлення
              </button>
              <button role="tab" aria-selected={tab === 'settings'} className={`prof-tab${tab === 'settings' ? ' active' : ''}`} onClick={() => switchTab('settings')}>
                Налаштування
              </button>
            </div>
          </div>
          <div className={`prof-tab-panel${tab === 'orders' ? ' active' : ''}`}>
            <OrdersPanel data={data} />
          </div>
          <div className={`prof-tab-panel${tab === 'settings' ? ' active' : ''}`}>
            <SettingsPanel
              key={`${data.user.client_name}|${data.user.client_surname}|${data.user.client_PhoneNumber}`}
              data={data}
              onSaved={(kind) => setToast({ text: kind === 'profile' ? 'Профіль успішно оновлено' : 'Пароль успішно змінено', out: false })}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
