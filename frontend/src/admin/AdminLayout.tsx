import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { useLogout } from '@/api/queries';
import { useAdminToast } from './AdminToast';
import { adminKeys, useAdminLayout } from './useAdmin';

const POLL_MS = 30_000;

const TitleCtx = createContext<(title: string) => void>(() => {});

/** Sets the topbar title and the tab title for an admin screen. */
export function useAdminTitle(title: string) {
  const set = useContext(TitleCtx);
  useEffect(() => {
    set(title);
    document.title = `${title} — Coffee Time`;
  }, [set, title]);
}

/** New-orders counter shared by the sidebar badge, the bell and the orders screens. */
export function useNewOrdersCount(enabled = true) {
  return useQuery({
    queryKey: adminKeys.newCount,
    queryFn: () => unwrap(api.GET('/api/admin/dashboard/new-orders-count')),
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
    enabled,
  });
}

function playBeep() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.18, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch {
    /* autoplay policy or no audio: the toast is enough */
  }
}

const readCollapsed = () => {
  try {
    return window.innerWidth > 700 && localStorage.getItem('sb_collapsed') !== '0';
  } catch {
    return window.innerWidth > 700;
  }
};

const svg = (children: ReactNode) => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);

const ICONS = {
  dashboard: svg(<><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></>),
  orders: svg(<><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></>),
  products: svg(<><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></>),
  sauces: svg(<><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" /><path d="M8 12s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></>),
  users: svg(<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>),
  backup: svg(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>),
  reviews: svg(<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />),
  gallery: svg(<><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></>),
  slides: svg(<><rect x="2" y="7" width="20" height="10" rx="2" /><path d="M17 7V5a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v2" /><polyline points="9 12 12 15 15 12" /></>),
  about: svg(<><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></>),
  dessert: svg(<><path d="M18 8h1a4 4 0 0 1 0 8h-1" /><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" /><line x1="6" y1="1" x2="6" y2="4" /><line x1="10" y1="1" x2="10" y2="4" /><line x1="14" y1="1" x2="14" y2="4" /></>),
};

type LinkProps = { to: string; icon: ReactNode; label: string; badge?: ReactNode; onTip: (label: string | null, el?: HTMLElement) => void };

function SideLink({ to, icon, label, badge, onTip }: LinkProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
      data-tooltip={label}
      onMouseEnter={(e) => onTip(label, e.currentTarget)}
      onMouseLeave={() => onTip(null)}
      onClick={() => onTip(null)}
    >
      {icon}
      <span className="sl-text">{label}</span>
      {badge}
    </NavLink>
  );
}

export function AdminLayout({ children }: { children: ReactNode }) {
  const layout = useAdminLayout();
  const client = useQueryClient();
  const toast = useAdminToast();
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const [title, setTitle] = useState('');
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [noTransition, setNoTransition] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [tip, setTip] = useState<{ text: string; top: number } | null>(null);
  const [showTop, setShowTop] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const data = layout.data;
  const canSeeOrders = !!data?.can_see_orders;
  const polled = useNewOrdersCount(canSeeOrders);
  const newCount = polled.data?.count ?? data?.new_orders_count ?? 0;

  // Beep + toast when the polled count grows (the first value is the baseline).
  const known = useRef<number | null>(null);
  useEffect(() => {
    const count = polled.data?.count;
    if (count === undefined) return;
    if (known.current !== null && count > known.current) {
      playBeep();
      toast(
        <>
          Нове замовлення! Всього нових: <strong>{count}</strong>&nbsp;{' '}
          <Link to="/admin/orders" style={{ color: '#fff', textDecoration: 'underline' }}>
            Переглянути →
          </Link>
        </>,
        'success',
        6000,
      );
      client.invalidateQueries({ queryKey: adminKeys.layout });
      client.invalidateQueries({ queryKey: ['admin', 'orders'] });
    }
    known.current = count;
  }, [polled.data?.count, toast, client]);

  // Skip the width transition on first paint (restored collapsed state).
  useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setNoTransition(false)));
    return () => cancelAnimationFrame(id);
  }, []);

  useEffect(() => {
    let lastW = window.innerWidth;
    const onResize = () => {
      const w = window.innerWidth;
      if (w === lastW) return;
      lastW = w;
      if (w <= 700) {
        setCollapsed(false);
        setMobileOpen(false);
        setTip(null);
      }
    };
    const onScroll = () => setShowTop(window.scrollY > 300);
    window.addEventListener('resize', onResize);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  useEffect(() => {
    if (!notifOpen) return;
    const close = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [notifOpen]);

  // Navigating closes the mobile drawer and the dropdown.
  useEffect(() => {
    setMobileOpen(false);
    setNotifOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    setTip(null);
    try {
      localStorage.setItem('sb_collapsed', next ? '1' : '0');
    } catch {
      /* private mode */
    }
  };

  const onTip = (label: string | null, el?: HTMLElement) => {
    if (!label || !el || !collapsed || window.innerWidth <= 700) return setTip(null);
    const rect = el.getBoundingClientRect();
    setTip({ text: label, top: Math.round(rect.top + rect.height / 2) });
  };

  const doLogout = () =>
    logout.mutate(undefined, {
      onSettled: () => navigate('/login', { replace: true }),
    });

  const perms = data?.perms;
  const ordersBadge = newCount > 0 ? <span className="nav-badge orders-badge pulse">{newCount}</span> : null;

  return (
    <TitleCtx.Provider value={setTitle}>
      <div className="admin-wrapper">
        <aside className={`admin-sidebar${collapsed ? ' collapsed' : ''}${noTransition ? ' sb-notransition' : ''}${mobileOpen ? ' mobile-open' : ''}`}>
          <button className="sidebar-collapser" title="Згорнути/розгорнути" onClick={toggleCollapsed}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
          </button>
          <div className="sidebar-inner">
            <div className="sidebar-brand">
              <img src="/static/images/main/logo-cup.svg" alt="Coffee Time" className="sidebar-logo" />
              <div className="sidebar-subtitle">Панель адміна</div>
            </div>

            <nav className="sidebar-nav">
              <div className="nav-section-label">Головне</div>
              <SideLink to="/admin/dashboard" icon={ICONS.dashboard} label="Головна" onTip={onTip} />
              {perms?.orders_view && <SideLink to="/admin/orders" icon={ICONS.orders} label="Замовлення" badge={ordersBadge} onTip={onTip} />}
              {perms?.products && (
                <>
                  <SideLink to="/admin/manage-items" icon={ICONS.products} label="Товари" onTip={onTip} />
                  <SideLink to="/admin/sauces" icon={ICONS.sauces} label="Соуси" onTip={onTip} />
                </>
              )}

              {data?.is_super && (
                <>
                  <div className="nav-section-label">Адміністрація</div>
                  <SideLink to="/admin/users" icon={ICONS.users} label="Персонал" onTip={onTip} />
                  {/* A plain download link: the session cookie rides along. */}
                  <a
                    href="/api/admin/backup"
                    className="sidebar-link"
                    data-tooltip="Резервна копія"
                    download
                    onMouseEnter={(e) => onTip('Резервна копія', e.currentTarget)}
                    onMouseLeave={() => onTip(null)}
                  >
                    {ICONS.backup}
                    <span className="sl-text">Резервна копія</span>
                  </a>
                </>
              )}

              {(perms?.reviews || perms?.content) && <div className="nav-section-label">Контент</div>}
              {perms?.reviews && (
                <SideLink
                  to="/admin/reviews"
                  icon={ICONS.reviews}
                  label="Відгуки"
                  badge={data && data.pending_reviews > 0 ? <span className="nav-badge">{data.pending_reviews}</span> : null}
                  onTip={onTip}
                />
              )}
              {perms?.content && (
                <>
                  <SideLink to="/admin/gallery" icon={ICONS.gallery} label="Галерея" onTip={onTip} />
                  <SideLink to="/admin/hero-slides" icon={ICONS.slides} label="Хіро слайдер" onTip={onTip} />
                  <SideLink to="/admin/about-section" icon={ICONS.about} label="Про нас" onTip={onTip} />
                  <SideLink to="/admin/dessert-banner" icon={ICONS.dessert} label="Десерт дня" onTip={onTip} />
                </>
              )}
            </nav>

            <div className="sidebar-bottom">
              <div
                className="sidebar-avatar"
                onClick={() => {
                  if (collapsed && window.confirm('Вийти з панелі адміна?')) doLogout();
                }}
              >
                {data?.initial ?? ''}
              </div>
              <div className="sidebar-bottom-info">
                <span className="sidebar-admin-name">{data?.display_name ?? ''}</span>
                <button type="button" className="sidebar-logout-inline" onClick={doLogout}>
                  Вийти
                </button>
              </div>
            </div>
          </div>
        </aside>

        <div className={`sidebar-overlay${mobileOpen ? ' visible' : ''}`} onClick={() => setMobileOpen(false)} />

        <div className="admin-main">
          <header className="admin-topbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button className="topbar-hamburger" aria-label="Меню" onClick={() => setMobileOpen(true)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
              </button>
              <div className="topbar-title">{title}</div>
            </div>
            <div className="topbar-right">
              {canSeeOrders && (
                <div className="notif-wrap" ref={notifRef}>
                  <button
                    className="topbar-bell"
                    title="Нові замовлення"
                    type="button"
                    onClick={() => {
                      if (!notifOpen) client.invalidateQueries({ queryKey: adminKeys.layout });
                      setNotifOpen((o) => !o);
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
                    {newCount > 0 && <span className="topbar-bell-badge orders-badge">{newCount}</span>}
                  </button>
                  <div className={`notif-dropdown${notifOpen ? ' notif-dropdown--open' : ''}`}>
                    <div className="notif-header">
                      <span className="notif-title">Нові замовлення</span>
                      {newCount > 0 && <span className="notif-count">{newCount}</span>}
                    </div>
                    <div className="notif-list">
                      {!data?.notif_orders.length ? (
                        <div className="notif-empty">Нових замовлень немає</div>
                      ) : (
                        data.notif_orders.map((no) => (
                          <Link key={no.order_id} to={`/admin/orders/${no.order_id}`} className="notif-item">
                            <div className="notif-item__dot" />
                            <div className="notif-item__body">
                              <span className="notif-item__id">#{no.order_id}</span>
                              <span className="notif-item__name">{no.name}</span>
                              <span className="notif-item__price">{Math.round(no.total).toLocaleString('uk-UA')} ₴</span>
                            </div>
                            <span className="notif-item__time">{no.time_label}</span>
                          </Link>
                        ))
                      )}
                    </div>
                    <Link to="/admin/orders" className="notif-footer">
                      Переглянути всі замовлення →
                    </Link>
                  </div>
                </div>
              )}
              <div className="topbar-admin">
                <div className="topbar-admin-avatar">{data?.initial ?? ''}</div>
                <span className="topbar-admin-name">{data?.display_name ?? ''}</span>
              </div>
            </div>
          </header>

          <main className="admin-content">{children}</main>
        </div>
      </div>

      <div className="sb-tooltip" style={{ top: tip?.top ?? 0, opacity: tip ? 1 : 0 }}>
        {tip?.text}
      </div>

      <button className={`admin-scroll-top${showTop ? ' visible' : ''}`} aria-label="Вгору" title="Вгору" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15" /></svg>
      </button>
    </TitleCtx.Provider>
  );
}
