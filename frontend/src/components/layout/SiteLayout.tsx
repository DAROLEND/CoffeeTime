import { Suspense, useEffect, useState } from 'react';
import { Outlet, ScrollRestoration } from 'react-router';
import { PageLoader } from '../Spinner';
import { ToastProvider } from '../Toast';
import '@/styles/pages/site/style.css';
import '@/styles/pages/site/footer.css';
import '@/styles/pages/site/animations.css';
import '@/styles/pages/site/header.css';
import { Footer } from './Footer';
import { Header } from './Header';

function ScrollTopButton() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 300);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return (
    <button
      type="button"
      className={`scroll-top-btn${visible ? ' visible' : ''}`}
      aria-label="Вгору"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
    >
      ↑
    </button>
  );
}

/**
 * Storefront shell: header, page, scroll-to-top button, footer. The
 * `.pg-site` wrapper scopes the storefront-wide stylesheets (style.css
 * etc.) so they don't leak into the admin panel.
 */
export function SiteLayout() {
  return (
    <div className="pg-site">
      <ToastProvider>
      <Header />
      <main>
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
      <ScrollTopButton />
      <Footer />
      </ToastProvider>
      <ScrollRestoration />
    </div>
  );
}
