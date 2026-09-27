import { lazy } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import { SiteLayout } from './components/layout/SiteLayout';
import { RequireUser } from './components/RequireUser';
import HomePage from './features/home/HomePage';

// Every page but the homepage is its own chunk (and its own CSS).
const MenuPage = lazy(() => import('./features/menu/MenuPage'));
const CartPage = lazy(() => import('./features/cart/CartPage'));
const CheckoutPage = lazy(() => import('./features/checkout/CheckoutPage'));
const LiqpayCheckoutPage = lazy(() => import('./features/payment/LiqpayCheckoutPage'));
const PaymentSuccessPage = lazy(() => import('./features/payment/PaymentSuccessPage'));
const PaymentPendingPage = lazy(() => import('./features/payment/PaymentPendingPage'));
const PaymentFailurePage = lazy(() => import('./features/payment/PaymentFailurePage'));
const LoginPage = lazy(() => import('./features/auth/LoginPage'));
const RegisterPage = lazy(() => import('./features/auth/RegisterPage'));
const ForgotPage = lazy(() => import('./features/auth/ForgotPage'));
const ResetPage = lazy(() => import('./features/auth/ResetPage'));
const ChangePasswordPage = lazy(() => import('./features/auth/ChangePasswordPage'));
const ProfilePage = lazy(() => import('./features/profile/ProfilePage'));
const ReviewsPage = lazy(() => import('./features/reviews/ReviewsPage'));
const GalleryPage = lazy(() => import('./features/gallery/GalleryPage'));
const AboutPage = lazy(() => import('./features/pages/AboutPage'));
const NotFoundPage = lazy(() => import('./features/pages/NotFoundPage'));
const AdminApp = lazy(() => import('./admin/AdminApp'));

export const routes: RouteObject[] = [
  {
    element: <SiteLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'menu', element: <MenuPage /> },
      { path: 'cart', element: <CartPage /> },
      { path: 'checkout', element: <CheckoutPage /> },
      { path: 'payment-success', element: <PaymentSuccessPage /> },
      { path: 'payment-pending', element: <PaymentPendingPage /> },
      { path: 'payment-failure', element: <PaymentFailurePage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'forgot', element: <ForgotPage /> },
      { path: 'reset', element: <ResetPage /> },
      { path: 'change-password', element: <RequireUser><ChangePasswordPage /></RequireUser> },
      { path: 'profile', element: <RequireUser><ProfilePage /></RequireUser> },
      { path: 'reviews', element: <ReviewsPage /> },
      { path: 'gallery', element: <GalleryPage /> },
      { path: 'about', element: <AboutPage variant="about" /> },
      { path: 'contact', element: <AboutPage variant="contact" /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  // Standalone: no site chrome while handing off to LiqPay.
  { path: 'liqpay-checkout', element: <LiqpayCheckoutPage /> },
  { path: 'admin/*', element: <AdminApp /> },
];

export const router = createBrowserRouter(routes);
