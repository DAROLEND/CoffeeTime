import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';

export const adminKeys = {
  layout: ['admin', 'layout'] as const,
  newCount: ['admin', 'new-orders-count'] as const,
  dashboard: ['admin', 'dashboard'] as const,
  orders: (params: Record<string, string>) => ['admin', 'orders', params] as const,
  order: (id: number) => ['admin', 'order', id] as const,
  products: (category: string) => ['admin', 'products', category] as const,
  sauces: ['admin', 'sauces'] as const,
  gallery: (cat: string) => ['admin', 'gallery', cat] as const,
  reviews: (params: Record<string, string | number>) => ['admin', 'reviews', params] as const,
  orderRatings: (page: number) => ['admin', 'order-ratings', page] as const,
  slides: ['admin', 'hero-slides'] as const,
  about: ['admin', 'about'] as const,
  banner: ['admin', 'dessert-banner'] as const,
  users: ['admin', 'users'] as const,
};

/** Sidebar badges, notifications and the admin's effective permissions. */
export function useAdminLayout() {
  return useQuery({ queryKey: adminKeys.layout, queryFn: () => unwrap(api.GET('/api/admin/layout')), staleTime: 15_000 });
}
