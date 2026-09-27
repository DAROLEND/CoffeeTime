import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router';
import { useSession } from '@/api/queries';
import { PageLoader } from '@/components/Spinner';
import '@/styles/pages/admin/admin.css';
import '@/styles/pages/admin/admin-pages.css';
import { AdminLayout } from './AdminLayout';
import { AdminToastProvider } from './AdminToast';

const Dashboard = lazy(() => import('./pages/DashboardPage'));
const Orders = lazy(() => import('./pages/OrdersPage'));
const OrderView = lazy(() => import('./pages/OrderViewPage'));
const Products = lazy(() => import('./pages/ProductsPage'));
const Sauces = lazy(() => import('./pages/SaucesPage'));
const Users = lazy(() => import('./pages/UsersPage'));
const Reviews = lazy(() => import('./pages/ReviewsPage'));
const Gallery = lazy(() => import('./pages/GalleryPage'));
const HeroSlides = lazy(() => import('./pages/HeroSlidesPage'));
const AboutSection = lazy(() => import('./pages/AboutSectionPage'));
const DessertBanner = lazy(() => import('./pages/DessertBannerPage'));

/**
 * The admin panel (its own lazy chunk). Only renders for an admin
 * session; every screen and endpoint still checks permissions on the
 * server, the client just hides what the admin can't use.
 */
export default function AdminApp() {
  const { data: session, isPending } = useSession();
  const location = useLocation();

  if (isPending) return <PageLoader />;
  if (!session?.admin) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;

  return (
    <div className="pg-admin">
      <AdminToastProvider>
        <AdminLayout>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="login" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="orders" element={<Orders />} />
              <Route path="orders/:orderId" element={<OrderView />} />
              <Route path="manage-items" element={<Products />} />
              <Route path="sauces" element={<Sauces />} />
              <Route path="users" element={<Users />} />
              <Route path="reviews" element={<Reviews />} />
              <Route path="gallery" element={<Gallery />} />
              <Route path="hero-slides" element={<HeroSlides />} />
              <Route path="about-section" element={<AboutSection />} />
              <Route path="dessert-banner" element={<DessertBanner />} />
              <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
            </Routes>
          </Suspense>
        </AdminLayout>
      </AdminToastProvider>
    </div>
  );
}
