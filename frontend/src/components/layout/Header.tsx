import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';
import { useLogout, useSession } from '@/api/queries';
import { CartMiniDropdown } from './CartMiniDropdown';

const NAV = [
  { to: '/', label: 'Головна', end: true },
  { to: '/menu', label: 'Меню' },
  { to: '/gallery', label: 'Галерея' },
  { to: '/reviews', label: 'Відгуки' },
];

function CartIcon({ count }: { count: number }) {
  // Bounce + badge pop whenever the count goes up.
  const [bump, setBump] = useState(false);
  const prev = useRef(count);
  useEffect(() => {
    if (count > prev.current) {
      setBump(true);
      const t = window.setTimeout(() => setBump(false), 420);
      prev.current = count;
      return () => window.clearTimeout(t);
    }
    prev.current = count;
  }, [count]);

  return (
    <Link to="/cart" aria-label={`Кошик${count ? `, товарів: ${count}` : ''}`}>
      <img src="/static/images/main/cart.png" alt="Кошик" />
      {count > 0 && <span className={`cart-count${bump ? ' pop' : ''}`}>{count}</span>}
    </Link>
  );
}

export function Header() {
  const { data: session } = useSession();
  const logout = useLogout();
  const navigate = useNavigate();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [cartLoad, setCartLoad] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<number | undefined>(undefined);

  const user = session?.user;
  const cartCount = session?.cart.count ?? 0;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Preload the mini-cart shortly after the first paint.
  useEffect(() => {
    const t = window.setTimeout(() => setCartLoad(true), 900);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    setNavOpen(false);
    setUserOpen(false);
    setCartOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!userOpen) return;
    const close = (e: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(e.target as Node)) setUserOpen(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [userOpen]);

  const hoverCapable = typeof window !== 'undefined' && window.matchMedia?.('(hover: hover)').matches;
  const openCart = () => {
    if (!hoverCapable) return;
    window.clearTimeout(hideTimer.current);
    setCartLoad(true);
    setCartOpen(true);
  };
  const scheduleClose = () => {
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setCartOpen(false), 280);
  };

  const onLogout = () => {
    logout.mutate(undefined, { onSuccess: () => navigate('/') });
  };

  return (
    <header className={`site-header${navOpen ? ' open' : ''}${scrolled ? ' scrolled' : ''}`}>
      <div className="header__inner container d-flex justify-content-between align-items-center">
        <div className="logo">
          <Link to="/">
            <img src="/static/images/main/logo.svg" alt="Coffee Time" />
          </Link>
        </div>

        <nav className="site-nav" aria-label="Головна навігація">
          <ul className="nav-list d-flex gap-3 mb-0">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : '')}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="auth-buttons d-flex gap-2 align-items-center">
          <button className="menu-toggle" aria-label="Відкрити меню" aria-expanded={navOpen} onClick={() => setNavOpen((v) => !v)}>
            <span className="bar" />
            <span className="bar" />
            <span className="bar" />
          </button>

          <div className="cart-wrapper position-relative" onMouseEnter={openCart} onMouseLeave={scheduleClose}>
            <CartIcon count={cartCount} />
            <CartMiniDropdown open={cartOpen} loadEnabled={cartLoad} />
          </div>

          {user ? (
            <div className={`nav-user-menu${userOpen ? ' open' : ''}`} ref={userRef}>
              <button
                className="nav-user-trigger"
                type="button"
                aria-haspopup="menu"
                aria-expanded={userOpen}
                onClick={(e) => {
                  e.stopPropagation();
                  setUserOpen((v) => !v);
                }}
              >
                <span className="nav-user-avatar">{user.initials}</span>
                <span className="nav-user-name">{user.display_name}</span>
                <span className="nav-user-arrow">▾</span>
              </button>
              <div className="nav-dropdown" role="menu">
                <Link to="/profile" className="nav-dd-item" role="menuitem">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" /><path d="M1 1h4l2.68 13.39a2 2 0 001.99 1.61h9.72a2 2 0 001.99-1.61L23 6H6" /></svg>
                  Мої замовлення
                </Link>
                <Link to="/profile?tab=settings" className="nav-dd-item" role="menuitem">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></svg>
                  Налаштування
                </Link>
                <div className="nav-dd-divider" />
                <button type="button" className="nav-dd-item nav-dd-logout" role="menuitem" onClick={onLogout}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                  Вийти
                </button>
              </div>
            </div>
          ) : session?.admin ? (
            <Link to="/admin/dashboard" className="auth-link">
              Адмінка
            </Link>
          ) : (
            <>
              <Link to="/login" className="auth-link auth-link--ghost">
                Увійти
              </Link>
              <Link to="/register" className="auth-link">
                Реєстрація
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
