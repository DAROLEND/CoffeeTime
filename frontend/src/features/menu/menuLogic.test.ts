import { describe, expect, it } from 'vitest';
import type { MenuCard, VariantOptions } from '@/api/types';
import {
  DEFAULT_FILTERS,
  defaultSelection,
  fmtWeight,
  hasActiveFilters,
  matchesFilters,
  pizzaUnitPrice,
  searchSections,
  selectionFromVariant,
  sortCards,
  stepWeight,
  variantDiff,
  variantPayload,
} from './menuLogic';

const card = (over: Partial<MenuCard>): MenuCard => ({ ...({} as MenuCard), name: 'X', price: 100, price_large: 150, popularity: 0, order: 0, tags: [], ...over });

const filling: VariantOptions = {
  type: 'filling',
  label: 'Начинка',
  options: [
    { id: 'chicken', label: 'Курка', price_diff: 0, sizes: [{ label: 'M', price_diff: 0 }, { label: 'L', price_diff: 30 }] },
    { id: 'beef', label: 'Яловичина', price_diff: 20, sizes: [] },
  ],
} as VariantOptions;
const scoops: VariantOptions = {
  type: 'scoops',
  label: 'Кульки',
  options: [
    { id: '1', label: '1 кулька', price_diff: 0, sizes: [] },
    { id: '2', label: '2 кульки', price_diff: 20, sizes: [] },
  ],
} as VariantOptions;
const sauce: VariantOptions = { type: 'sauce', label: 'Соус', options: [] } as unknown as VariantOptions;

describe('filters', () => {
  it('detects active filters', () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, spicy: true })).toBe(true);
  });

  it('filters coffee by temperature', () => {
    const cold = card({ is_cold_coffee: true });
    const hot = card({ is_cold_coffee: false });
    const f = { ...DEFAULT_FILTERS, coffeeType: 'cold' as const };
    expect(matchesFilters(cold, 'coffee_items', f)).toBe(true);
    expect(matchesFilters(hot, 'coffee_items', f)).toBe(false);
    // Other sections ignore the coffee filter.
    expect(matchesFilters(hot, 'dessert_items', f)).toBe(true);
  });

  it('filters pizzas by sauce, spiciness and every chosen ingredient', () => {
    const pizza = card({ is_pizza_type: true, sauce_type: 'cream', is_spicy: true, tags: ['Бекон', 'Гриби'] });
    expect(matchesFilters(pizza, 'pizza_items', { ...DEFAULT_FILTERS, sauce: 'cream' })).toBe(true);
    expect(matchesFilters(pizza, 'pizza_items', { ...DEFAULT_FILTERS, sauce: 'tomato' })).toBe(false);
    expect(matchesFilters(pizza, 'pizza_items', { ...DEFAULT_FILTERS, ingredients: ['бекон', 'гриби'] })).toBe(true);
    expect(matchesFilters(pizza, 'pizza_items', { ...DEFAULT_FILTERS, ingredients: ['бекон', 'шинка'] })).toBe(false);
    // A pizza without a sauce type counts as tomato.
    expect(matchesFilters(card({ is_pizza_type: true }), 'pizza_items', { ...DEFAULT_FILTERS, sauce: 'tomato' })).toBe(true);
  });
});

describe('sortCards', () => {
  const cards = [card({ name: 'a', price: 50, popularity: 1, order: 2 }), card({ name: 'b', price: 20, popularity: 9, order: 1 }), card({ name: 'c', price: 90, popularity: 5, order: 0 })];
  it.each([
    ['default', ['c', 'b', 'a']],
    ['price_asc', ['b', 'a', 'c']],
    ['price_desc', ['c', 'a', 'b']],
    ['popular', ['b', 'c', 'a']],
  ] as const)('%s', (sort, names) => expect(sortCards(cards, sort).map((c) => c.name)).toEqual(names));

  it('does not mutate the input', () => {
    sortCards(cards, 'price_asc');
    expect(cards.map((c) => c.name)).toEqual(['a', 'b', 'c']);
  });
});

it('searchSections matches names case-insensitively and drops empty sections', () => {
  const res = searchSections({ coffee: [card({ name: 'Лате' }), card({ name: 'Раф' })], pizza: [card({ name: 'Маргарита' })] }, '  ЛАТ ');
  expect(Object.keys(res)).toEqual(['coffee']);
  expect(res.coffee.map((c) => c.name)).toEqual(['Лате']);
});

describe('variants', () => {
  it('defaults to the first option and its first size', () => {
    expect(defaultSelection(filling)).toEqual({ optionId: 'chicken', sizeLabel: 'M' });
    expect(defaultSelection(sauce)).toEqual({ optionId: null, sizeLabel: null });
    expect(defaultSelection(null)).toEqual({ optionId: null, sizeLabel: null });
  });

  it('adds option and nested size surcharges', () => {
    expect(variantDiff(filling, { optionId: 'chicken', sizeLabel: 'L' })).toBe(30);
    expect(variantDiff(filling, { optionId: 'beef', sizeLabel: null })).toBe(20);
    expect(variantDiff(scoops, { optionId: '2', sizeLabel: null })).toBe(20);
    expect(variantDiff(filling, { optionId: 'nope', sizeLabel: null })).toBe(0);
  });

  it('sends only option identity, never a price', () => {
    const p = JSON.parse(variantPayload(filling, { optionId: 'chicken', sizeLabel: 'L' })!);
    expect(p).toEqual({ type: 'filling', filling_id: 'chicken', size_label: 'L' });
    expect(JSON.parse(variantPayload(scoops, { optionId: '2', sizeLabel: null })!)).toEqual({ type: 'scoops', scoop_id: '2' });
    expect(JSON.parse(variantPayload(sauce, { optionId: null, sizeLabel: null }, 'Кетчуп')!)).toEqual({ type: 'sauce', label: 'Кетчуп' });
    expect(variantPayload(sauce, { optionId: null, sizeLabel: null })).toBeNull();
    expect(variantPayload(null, { optionId: 'x', sizeLabel: null })).toBeNull();
  });

  it('round-trips a stored variant back into a selection', () => {
    expect(selectionFromVariant('{"type":"filling","filling_id":"beef","size_label":"L"}')).toEqual({ optionId: 'beef', sizeLabel: 'L', sauceLabel: null });
    expect(selectionFromVariant('{"type":"scoops","scoop_id":"2"}')).toMatchObject({ optionId: '2' });
    expect(selectionFromVariant('{"type":"sauce","label":"BBQ"}')).toMatchObject({ sauceLabel: 'BBQ' });
    expect(selectionFromVariant(null)).toEqual({ optionId: null, sizeLabel: null, sauceLabel: null });
    // Legacy plain-text sauce values.
    expect(selectionFromVariant('Кетчуп')).toMatchObject({ sauceLabel: 'Кетчуп' });
  });
});

describe('pizza and cake helpers', () => {
  it('prices a pizza by size with the cheese crust surcharge', () => {
    const p = { price: 180, price_large: 260 };
    expect(pizzaUnitPrice(p, 'small', false)).toBe(180);
    expect(pizzaUnitPrice(p, 'small', true)).toBe(245);
    expect(pizzaUnitPrice(p, 'large', true)).toBe(360);
  });

  it('steps cake weight but never below the minimum', () => {
    expect(stepWeight(1.5, 0.5, 1.5)).toBe(2);
    expect(stepWeight(1.5, -0.5, 1.5)).toBe(1.5);
    expect(stepWeight(2, -0.5, 1)).toBe(1.5);
    expect(fmtWeight(2)).toBe('2');
    expect(fmtWeight(1.5)).toBe('1.5');
  });
});
