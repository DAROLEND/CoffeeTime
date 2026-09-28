import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { CartLine, CartView } from '@/api/types';
import { mockApi, renderRoute } from '@/test/utils';
import CartPage from './CartPage';

const line = (over: Partial<CartLine>): CartLine => ({
  session_index: 0,
  category: 'coffee_items',
  id: 1,
  name: 'Лате',
  description: '',
  image: '',
  price: 65,
  quantity: 2,
  subtotal: 130,
  opt_tags: [],
  editable: false,
  weight: null,
  ...over,
});

function cartOf(items: CartLine[]): CartView {
  const total = items.reduce((s, i) => s + i.subtotal, 0);
  return {
    items,
    groups: items.length ? [{ key: 'coffee_items', label: 'Кава', items }] : [],
    total,
    total_qty: items.reduce((s, i) => s + i.quantity, 0),
    item_count: items.length,
    item_word: 'товари',
    back_category: 'coffee',
  };
}

describe('CartPage', () => {
  it('shows the empty state', async () => {
    mockApi({ 'GET /api/cart': cartOf([]) });
    renderRoute(<CartPage />, { path: '/cart', route: '/cart' });
    expect(await screen.findByText('Ваша корзина порожня')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Перейти до меню' })).toHaveAttribute('href', '/menu?category=coffee');
  });

  it('renders server-computed lines and totals', async () => {
    mockApi({
      'GET /api/cart': cartOf([
        line({}),
        line({ session_index: 1, id: 7, name: 'Торт Наполеон', category: 'cake_items', quantity: 1, subtotal: 900, opt_tags: ['1.5 кг'] }),
      ]),
    });
    renderRoute(<CartPage />, { path: '/cart', route: '/cart' });
    expect(await screen.findByText('Торт Наполеон')).toBeInTheDocument();
    expect(screen.getByText('1.5 кг')).toBeInTheDocument();
    expect(screen.getByText('3 шт.')).toBeInTheDocument();
    // A cake is sold by weight: no quantity stepper on its row.
    expect(screen.getAllByLabelText('Кількість товару')).toHaveLength(1);
  });

  it('sends only the new quantity — the price comes back from the server', async () => {
    let cart = cartOf([line({})]);
    const { calls } = mockApi({
      'GET /api/csrf-token': { csrf_token: 't' },
      'GET /api/cart': () => cart,
      'GET /api/session': { user: null, admin: false, cart: { count: 1, keys: [] } },
      'GET /api/checkout': {},
      'PATCH /api/cart/items/0': () => {
        cart = cartOf([line({ quantity: 3, subtotal: 195 })]);
        return { ok: true };
      },
    });
    renderRoute(<CartPage />, { path: '/cart', route: '/cart' });
    await userEvent.click(await screen.findByRole('button', { name: 'Збільшити' }));

    await waitFor(() => expect(screen.getByLabelText('Кількість товару')).toHaveValue(3));
    const patch = calls.find((c) => c.method === 'PATCH')!;
    expect(patch.body).toEqual({ quantity: 3 });
    const summary = document.querySelector('.cart-summary-box') as HTMLElement;
    expect(within(summary).getByText(/195/)).toBeInTheDocument();
  });

  it('asks before clearing the cart', async () => {
    const { calls } = mockApi({ 'GET /api/cart': cartOf([line({})]) });
    renderRoute(<CartPage />, { path: '/cart', route: '/cart' });
    await userEvent.click(await screen.findByRole('button', { name: 'Очистити корзину' }));
    expect(screen.getByText('Ви впевнені?')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Скасувати' }));
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false);
  });
});
