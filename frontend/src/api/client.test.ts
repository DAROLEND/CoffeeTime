import { describe, expect, it } from 'vitest';
import { json, mockApi } from '@/test/utils';
import { api } from './client';
import { ApiError, errorMessage, unwrap } from './errors';

describe('CSRF handling', () => {
  it('fetches the token once and sends it on mutating requests only', async () => {
    const { calls } = mockApi({
      'GET /api/csrf-token': { csrf_token: 'tok-1' },
      'GET /api/session': { user: null, admin: false, cart: { count: 0, keys: [] } },
      'DELETE /api/cart': { ok: true },
      'POST /api/cart/items': { ok: true, count: 1, index: 0 },
    });
    await api.GET('/api/session');
    await api.DELETE('/api/cart');
    await api.POST('/api/cart/items', { body: { id: 1, category: 'coffee_items' } });

    expect(calls.filter((c) => c.path === '/api/csrf-token')).toHaveLength(1);
    expect(calls.find((c) => c.path === '/api/session')!.headers.get('X-CSRF-Token')).toBeNull();
    expect(calls.find((c) => c.method === 'DELETE')!.headers.get('X-CSRF-Token')).toBe('tok-1');
    expect(calls.find((c) => c.method === 'POST')!.headers.get('X-CSRF-Token')).toBe('tok-1');
  });

  it('refreshes the token and retries once after a csrf_* 403', async () => {
    let token = 0;
    let attempts = 0;
    const { calls } = mockApi({
      'GET /api/csrf-token': () => ({ csrf_token: `tok-${++token}` }),
      'DELETE /api/cart': (req) => {
        attempts++;
        return req.headers.get('X-CSRF-Token') === 'tok-2' ? { ok: true } : json({ detail: 'expired', code: 'csrf_expired', errors: [] }, 403);
      },
    });
    const res = await unwrap(api.DELETE('/api/cart'));
    expect(res).toEqual({ ok: true });
    expect(attempts).toBe(2);
    expect(calls.filter((c) => c.path === '/api/csrf-token')).toHaveLength(2);
  });

  it('does not retry other 403s', async () => {
    let attempts = 0;
    mockApi({
      'GET /api/csrf-token': { csrf_token: 't' },
      'DELETE /api/cart': () => {
        attempts++;
        return json({ detail: 'Недостатньо прав.', code: 'forbidden', errors: [] }, 403);
      },
    });
    await expect(unwrap(api.DELETE('/api/cart'))).rejects.toMatchObject({ status: 403, code: 'forbidden' });
    expect(attempts).toBe(1);
  });
});

describe('errors', () => {
  it('unwrap turns the error envelope into an ApiError', async () => {
    mockApi({ 'GET /api/cart': json({ detail: 'Кошик недоступний', code: 'invalid_request', errors: ['a', 'b'] }, 400) });
    const err = await unwrap(api.GET('/api/cart')).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe('Кошик недоступний');
    expect(err.errors).toEqual(['a', 'b']);
    expect(errorMessage(err)).toBe('Кошик недоступний');
  });

  it('maps network failures to a friendly message', () => {
    expect(errorMessage(new TypeError('Failed to fetch'))).toMatch(/зʼєднання/);
  });
});
