/**
 * Typed API client. Paths, params, bodies and responses all come from
 * `schema.d.ts`, generated from the backend's /openapi.json
 * (`npm run gen:api`), so a backend change that breaks the contract
 * fails `tsc` instead of failing at runtime.
 *
 * Auth is the backend's session cookie, so every request goes out with
 * `credentials: 'include'` to the same origin (Vite proxy in dev, Render
 * rewrites in production).
 *
 * CSRF: mutating requests carry `X-CSRF-Token`. The token is fetched
 * once from /api/csrf-token and cached. If the server answers 403 with a
 * `csrf_*` code (session expired or rotated), the token is refetched and
 * the request retried once — the user never sees it.
 */
import createClient from 'openapi-fetch';
import type { paths } from './schema';

const MUTATING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

let csrfToken: string | null = null;
let csrfInflight: Promise<string> | null = null;

export function refreshCsrfToken(): Promise<string> {
  csrfInflight ??= fetch('/api/csrf-token', { credentials: 'include' })
    .then((r) => r.json() as Promise<{ csrf_token: string }>)
    .then((j) => {
      csrfToken = j.csrf_token;
      return csrfToken;
    })
    .finally(() => {
      csrfInflight = null;
    });
  return csrfInflight;
}

export function resetCsrfToken(): void {
  csrfToken = null;
}

async function isCsrfFailure(res: Response): Promise<boolean> {
  if (res.status !== 403) return false;
  const body = (await res.clone().json().catch(() => null)) as { code?: string } | null;
  return typeof body?.code === 'string' && body.code.startsWith('csrf_');
}

/** `fetch` with the CSRF header and a single transparent retry. */
export async function csrfFetch(input: Request): Promise<Response> {
  if (!MUTATING.has(input.method)) return fetch(input);
  const retry = input.clone();
  input.headers.set('X-CSRF-Token', csrfToken ?? (await refreshCsrfToken()));
  const res = await fetch(input);
  if (!(await isCsrfFailure(res))) return res;
  retry.headers.set('X-CSRF-Token', await refreshCsrfToken());
  return fetch(retry);
}

export const api = createClient<paths>({
  baseUrl: '',
  credentials: 'include',
  fetch: csrfFetch,
});

/**
 * multipart/form-data body serializer for the admin upload endpoints.
 * Blobs/Files are appended as files, booleans as "true"/"false", and
 * null/undefined fields are skipped.
 */
export function formData(body: object): FormData {
  const fd = new FormData();
  for (const [key, value] of Object.entries(body)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) value.forEach((v) => fd.append(key, v instanceof Blob ? v : String(v)));
    else if (value instanceof Blob) fd.append(key, value);
    else fd.append(key, String(value));
  }
  return fd;
}
