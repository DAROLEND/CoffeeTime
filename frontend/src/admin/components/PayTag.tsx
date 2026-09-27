import type { components } from '@/api/schema';
import { Icon, type IconName } from '@/components/Icon';

type PayBadge = components['schemas']['AdminPayBadge'];

const COLORS: Record<string, string> = { 'pay-paid': '#2e7d32', 'pay-cash': '#f57f17' };

/** Payment tag: paid / cash / unpaid (server decides the class, icon and label). */
export function PayTag({ badge }: { badge: PayBadge }) {
  return (
    <span className={`pay-tag ${badge.cls}`}>
      <Icon name={badge.icon as IconName} size={13} color={COLORS[badge.cls] ?? '#9e9e9e'} /> {badge.label}
    </span>
  );
}
