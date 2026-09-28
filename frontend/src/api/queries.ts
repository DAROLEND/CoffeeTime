/**
 * TanStack Query hooks for server state that several screens share.
 * Page-specific queries live next to their page.
 *
 * The cart is the interesting part: it lives in the server session, so
 * after any cart mutation we invalidate everything derived from it —
 * the session (header badge + "in cart" keys), the mini-cart preview and
 * the full cart view — and TanStack refetches whatever is on screen.
 */
import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api } from './client';
import { unwrap } from './errors';
import type { AddToCartRequest } from './types';

export const qk = {
  session: ['session'] as const,
  cart: ['cart'] as const,
  cartPreview: ['cart', 'preview'] as const,
  cartItem: (index: number) => ['cart', 'item', index] as const,
  menu: ['menu'] as const,
  home: ['home'] as const,
  checkout: ['checkout'] as const,
  profile: ['profile'] as const,
  reviews: (sort: string, filter: number, page: number) => ['reviews', sort, filter, page] as const,
  gallery: ['gallery'] as const,
  about: ['about'] as const,
};

export function useSession() {
  return useQuery({
    queryKey: qk.session,
    queryFn: () => unwrap(api.GET('/api/session')),
    staleTime: 30_000,
  });
}

export function invalidateCart(client: QueryClient) {
  // ['cart'] prefix covers the view, the preview and single items.
  return Promise.all([
    client.invalidateQueries({ queryKey: qk.cart }),
    client.invalidateQueries({ queryKey: qk.session }),
    client.invalidateQueries({ queryKey: qk.checkout }),
  ]);
}

export function useCartPreview(enabled: boolean) {
  return useQuery({
    queryKey: qk.cartPreview,
    queryFn: () => unwrap(api.GET('/api/cart/preview')),
    enabled,
  });
}

export function useAddToCart() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: AddToCartRequest) => unwrap(api.POST('/api/cart/items', { body })),
    onSuccess: () => invalidateCart(client),
  });
}

export function useRemoveCartItem() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (index: number) => unwrap(api.DELETE('/api/cart/items/{index}', { params: { path: { index } } })),
    onSuccess: () => invalidateCart(client),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.POST('/api/auth/logout')),
    onSuccess: () => client.invalidateQueries(),
  });
}
