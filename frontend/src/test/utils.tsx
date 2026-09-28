import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { vi } from 'vitest';
import { resetCsrfToken } from '@/api/client';
import { ToastProvider } from '@/components/Toast';

type Handler = ((req: Request) => unknown) | Response | object;

/**
 * Stubs `fetch` with a tiny router: keys are "METHOD /path" (query string
 * ignored). Handlers return a Response or a JSON-able value (200).
 * Returns the mock so tests can inspect calls.
 */
export function mockApi(routes: Record<string, Handler>) {
  resetCsrfToken();
  const calls: { method: string; path: string; body: unknown; headers: Headers }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const req = input instanceof Request ? input : new Request(new URL(String(input), 'http://localhost'), init);
    const url = new URL(req.url);
    const key = `${req.method} ${url.pathname}`;
    const text = req.method === 'GET' ? '' : await req.clone().text();
    let body: unknown = text;
    try {
      body = text ? JSON.parse(text) : undefined;
    } catch {
      /* not JSON */
    }
    calls.push({ method: req.method, path: url.pathname + url.search, body, headers: req.headers });
    const handler = routes[key];
    if (!handler) return new Response(JSON.stringify({ detail: `unmocked ${key}`, code: 'not_found', errors: [] }), { status: 404 });
    const out = typeof handler === 'function' ? await (handler as (r: Request) => unknown)(req) : handler;
    if (out instanceof Response) return out.clone();
    return new Response(JSON.stringify(out), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock, calls };
}

export const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

/** Renders `ui` at `path` inside the app's providers (fresh QueryClient, no retries). */
export function renderRoute(ui: ReactElement, { path = '/', route = '/', extra = {} as Record<string, ReactElement> } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route path={route} element={ui} />
              {Object.entries(extra).map(([p, el]) => (
                <Route key={p} path={p} element={el} />
              ))}
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    ),
  };
}
