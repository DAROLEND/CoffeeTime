import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { json, mockApi, renderRoute } from '@/test/utils';
import LoginPage from './LoginPage';

const anon = { user: null, admin: false, cart: { count: 0, keys: [] } };
const info = { is_locked: false, lock_minutes: 15, remembered_email: '' };

describe('LoginPage', () => {
  it('validates before calling the API', async () => {
    const { calls } = mockApi({ 'GET /api/session': anon, 'GET /api/auth/login-info': info });
    renderRoute(<LoginPage />, { path: '/login', route: '/login' });
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(calls.some((c) => c.path === '/api/auth/login')).toBe(false);
    expect(screen.getByText('Заповніть це поле')).toBeInTheDocument();
  });

  it('logs in and follows a safe ?next= redirect', async () => {
    const { calls } = mockApi({
      'GET /api/session': anon,
      'GET /api/auth/login-info': info,
      'GET /api/csrf-token': { csrf_token: 't' },
      'POST /api/auth/login': { kind: 'user', redirect: '/' },
    });
    renderRoute(<LoginPage />, { path: '/login?next=/checkout', route: '/login', extra: { '/checkout': <p>checkout page</p> } });
    await userEvent.type(screen.getByLabelText('Електронна пошта або логін'), 'olena@example.com');
    await userEvent.type(screen.getByLabelText('Пароль'), 'secret12');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));

    expect(await screen.findByText('checkout page')).toBeInTheDocument();
    const login = calls.find((c) => c.path === '/api/auth/login')!;
    expect(login.body).toEqual({ login: 'olena@example.com', password: 'secret12', remember: false });
    expect(login.headers.get('X-CSRF-Token')).toBe('t');
  });

  it('ignores an off-site ?next= redirect', async () => {
    mockApi({
      'GET /api/session': anon,
      'GET /api/auth/login-info': info,
      'GET /api/csrf-token': { csrf_token: 't' },
      'POST /api/auth/login': { kind: 'user', redirect: '/profile' },
    });
    renderRoute(<LoginPage />, { path: '/login?next=//evil.example', route: '/login', extra: { '/profile': <p>profile page</p> } });
    await userEvent.type(screen.getByLabelText('Електронна пошта або логін'), 'olena');
    await userEvent.type(screen.getByLabelText('Пароль'), 'secret12');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByText('profile page')).toBeInTheDocument();
  });

  it('shows the server error message', async () => {
    mockApi({
      'GET /api/session': anon,
      'GET /api/auth/login-info': info,
      'GET /api/csrf-token': { csrf_token: 't' },
      'POST /api/auth/login': json({ detail: 'Невірний логін або пароль.', code: 'invalid_credentials', errors: [] }, 400),
    });
    renderRoute(<LoginPage />, { path: '/login', route: '/login' });
    await userEvent.type(screen.getByLabelText('Електронна пошта або логін'), 'olena');
    await userEvent.type(screen.getByLabelText('Пароль'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Невірний логін або пароль.');
  });

  it('shows the lockout notice', async () => {
    mockApi({ 'GET /api/session': anon, 'GET /api/auth/login-info': { ...info, is_locked: true, lock_minutes: 12 } });
    renderRoute(<LoginPage />, { path: '/login', route: '/login' });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('через 12 хвилин'));
  });
});
