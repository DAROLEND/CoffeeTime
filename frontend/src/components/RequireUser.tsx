import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { useSession } from '@/api/queries';
import { PageLoader } from './Spinner';

/**
 * Client-side guard for customer-only pages. It only decides what to
 * render; the API enforces access on its own (401 without a session).
 */
export function RequireUser({ children }: { children: ReactNode }) {
  const { data, isPending } = useSession();
  const location = useLocation();
  if (isPending) return <PageLoader />;
  if (!data?.user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <>{children}</>;
}
