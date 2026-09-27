import { Suspense, useEffect, useState } from 'react';
import { Outlet, ScrollRestoration } from 'react-router';
import { PageLoader } from '../Spinner';
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

/** Storefront shell: header, page, scroll-to-top button, footer. */
export function SiteLayout() {
  return (
    <>
      <Header />
      <main>
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
      <ScrollTopButton />
      <Footer />
      <ScrollRestoration />
    </>
  );
}
