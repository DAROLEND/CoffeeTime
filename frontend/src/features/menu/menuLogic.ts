/**
 * Pure menu logic: filtering, sorting, global search, and the price shown
 * in the item modal. The modal price is only a preview — the server
 * recomputes every price from the database when the item is added.
 */
import type { MenuCard, VariantOptions } from '@/api/types';

export type SortKey = 'default' | 'price_asc' | 'price_desc' | 'popular';
export type CoffeeType = 'all' | 'hot' | 'cold';
export type SauceFilter = 'all' | 'tomato' | 'cream' | 'bbq';

export type MenuFilters = {
  sort: SortKey;
  coffeeType: CoffeeType;
  sauce: SauceFilter;
  spicy: boolean;
  ingredients: string[]; // lower-cased
};

export const DEFAULT_FILTERS: MenuFilters = { sort: 'default', coffeeType: 'all', sauce: 'all', spicy: false, ingredients: [] };

export const LAZY_BATCH = 9;
export const CHEESE_CRUST = { small: 65, large: 100 } as const;
/** Categories where adding an item offers the paid sauce add-ons. */
export const SAUCE_CATEGORIES = new Set(['fast_food_items', 'pizza_items', 'mini_pizza_items']);

export function hasActiveFilters(f: MenuFilters): boolean {
  return f.sort !== 'default' || f.coffeeType !== 'all' || f.sauce !== 'all' || f.spicy || f.ingredients.length > 0;
}

/** Coffee temperature filter + pizza sauce/spicy/ingredient filters. */
export function matchesFilters(card: MenuCard, section: string, f: MenuFilters): boolean {
  if (section === 'coffee_items' && f.coffeeType !== 'all') {
    const cold = card.is_cold_coffee;
    if (f.coffeeType === 'hot' ? cold : !cold) return false;
  }
  if (section === 'pizza_items' && card.is_pizza_type) {
    if (f.sauce !== 'all' && (card.sauce_type || 'tomato') !== f.sauce) return false;
    if (f.spicy && !card.is_spicy) return false;
    if (f.ingredients.length) {
      const tags = card.tags.map((t) => t.toLowerCase());
      if (!f.ingredients.every((ing) => tags.includes(ing))) return false;
    }
  }
  return true;
}

export function sortCards(cards: MenuCard[], sort: SortKey): MenuCard[] {
  const sorted = [...cards];
  switch (sort) {
    case 'price_asc':
      return sorted.sort((a, b) => a.price - b.price);
    case 'price_desc':
      return sorted.sort((a, b) => b.price - a.price);
    case 'popular':
      return sorted.sort((a, b) => b.popularity - a.popularity);
    default:
      return sorted.sort((a, b) => a.order - b.order);
  }
}

/** Case-insensitive name match across every section. */
export function searchSections(sections: Record<string, MenuCard[]>, query: string): Record<string, MenuCard[]> {
  const q = query.trim().toLowerCase();
  const out: Record<string, MenuCard[]> = {};
  for (const [key, cards] of Object.entries(sections)) {
    const hits = cards.filter((c) => c.name.toLowerCase().includes(q));
    if (hits.length) out[key] = hits;
  }
  return out;
}

export function positionsWord(n: number): string {
  return n === 1 ? 'позицію' : n < 5 ? 'позиції' : 'позицій';
}

/** The selection a modal is currently showing for a variant product. */
export type VariantSelection = { optionId: string | null; sizeLabel: string | null };

export function defaultSelection(vo: VariantOptions | null | undefined): VariantSelection {
  if (!vo || vo.type === 'sauce') return { optionId: null, sizeLabel: null };
  const first = vo.options[0];
  return { optionId: first?.id ?? null, sizeLabel: first?.sizes[0]?.label ?? null };
}

/** Surcharge of the selected option (+ nested size) — mirrors the server. */
export function variantDiff(vo: VariantOptions | null | undefined, sel: VariantSelection): number {
  if (!vo || vo.type === 'sauce' || !sel.optionId) return 0;
  const opt = vo.options.find((o) => o.id === sel.optionId);
  if (!opt) return 0;
  const size = opt.sizes.find((s) => s.label === sel.sizeLabel);
  return opt.price_diff + (size?.price_diff ?? 0);
}

/**
 * The `selected_variant` JSON sent to the API. Only option identity is
 * sent; the server looks up labels and prices itself.
 */
export function variantPayload(vo: VariantOptions | null | undefined, sel: VariantSelection, sauceLabel?: string | null): string | null {
  if (!vo) return null;
  if (vo.type === 'sauce') return sauceLabel ? JSON.stringify({ type: 'sauce', label: sauceLabel }) : null;
  if (!sel.optionId) return null;
  if (vo.type === 'filling') {
    return JSON.stringify({ type: 'filling', filling_id: sel.optionId, ...(sel.sizeLabel ? { size_label: sel.sizeLabel } : {}) });
  }
  return JSON.stringify({ type: vo.type, scoop_id: sel.optionId });
}

export function pizzaUnitPrice(card: Pick<MenuCard, 'price' | 'price_large'>, size: 'small' | 'large', crust: boolean): number {
  return (size === 'large' ? card.price_large : card.price) + (crust ? CHEESE_CRUST[size] : 0);
}

/** Round a cake weight step (0.5 kg), never below the cake's minimum. */
export function stepWeight(current: number, delta: number, min: number): number {
  const next = Math.round((current + delta) * 10) / 10;
  return next < min ? current : next;
}

export function fmtWeight(w: number): string {
  return w.toFixed(1).replace('.0', '');
}

/** Read the option identity back out of a stored `selected_variant`. */
export function selectionFromVariant(raw: string | null | undefined): VariantSelection & { sauceLabel: string | null } {
  const empty = { optionId: null, sizeLabel: null, sauceLabel: null };
  if (!raw) return empty;
  try {
    const v = JSON.parse(raw) as Record<string, unknown>;
    return {
      optionId: (v.filling_id ?? v.scoop_id ?? null) as string | null,
      sizeLabel: (v.size_label ?? null) as string | null,
      sauceLabel: v.type === 'sauce' ? ((v.label as string) ?? null) : null,
    };
  } catch {
    return { ...empty, sauceLabel: raw };
  }
}
