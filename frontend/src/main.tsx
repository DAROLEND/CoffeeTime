import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { ApiError } from './api/errors';
import { PageLoader } from './components/Spinner';
import { ToastProvider } from './components/Toast';
import { router } from './router';
import './styles/global/style.css';
import './styles/global/footer.css';
import './styles/global/animations.css';
import './styles/global/layout.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: false,
      // 4xx answers are final (validation, auth, not found); retry only
      // network failures and 5xx.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Suspense fallback={<PageLoader />}>
          <RouterProvider router={router} />
        </Suspense>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
