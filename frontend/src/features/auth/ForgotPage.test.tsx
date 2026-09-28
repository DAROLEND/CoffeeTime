import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { json, mockApi, renderRoute } from '@/test/utils';
import ForgotPage from './ForgotPage';

async function submit(email: string) {
  renderRoute(<ForgotPage />, { path: '/forgot', route: '/forgot' });
  await userEvent.type(screen.getByLabelText('Електронна пошта'), email);
  await userEvent.click(screen.getByRole('button', { name: /надіслати/i }));
}

it('says so when no account has that e-mail', async () => {
  mockApi({
    'GET /api/csrf-token': { csrf_token: 't' },
    'POST /api/auth/forgot': json({ detail: 'Користувача з такою поштою не знайдено.', code: 'email_not_found', errors: [] }, 404),
  });
  await submit('nobody@example.com');
  expect(await screen.findByRole('alert')).toHaveTextContent('Користувача з такою поштою не знайдено.');
  expect(screen.queryByText('Лист надіслано!')).not.toBeInTheDocument();
});

it('confirms when the letter was sent', async () => {
  mockApi({ 'GET /api/csrf-token': { csrf_token: 't' }, 'POST /api/auth/forgot': { ok: true, message: 'Лист надіслано' } });
  await submit('olena@example.com');
  expect(await screen.findByText('Лист надіслано!')).toBeInTheDocument();
});
