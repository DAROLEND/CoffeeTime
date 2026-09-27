import { describe, expect, it } from 'vitest';
import { fmtDate, fmtDateTime, fmtPrice, fmtShortDateTime, money, plural, truncate } from './format';

const NBSP = ' ';

describe('money / fmtPrice', () => {
  it('rounds to whole hryvnias with non-breaking spaces', () => {
    expect(money(1234.5)).toBe(`1${NBSP}235${NBSP}₴`);
    expect(money(0)).toBe(`0${NBSP}₴`);
  });
  it('keeps kopecks only when there are any', () => {
    expect(fmtPrice(65)).toBe(`65${NBSP}₴`);
    expect(fmtPrice(65.5)).toBe(`65,50${NBSP}₴`);
  });
});

describe('plural', () => {
  const forms: [string, string, string] = ['товар', 'товари', 'товарів'];
  it.each([
    [1, 'товар'],
    [2, 'товари'],
    [4, 'товари'],
    [5, 'товарів'],
    [11, 'товарів'],
    [12, 'товарів'],
    [21, 'товар'],
    [22, 'товари'],
    [111, 'товарів'],
  ])('%i -> %s', (n, word) => expect(plural(n, forms)).toBe(word));
});

describe('dates (naive café-local ISO)', () => {
  const iso = '2026-09-08T14:05:00';
  it('formats without shifting the wall-clock time', () => {
    expect(fmtDate(iso)).toBe('08.09.2026');
    expect(fmtShortDateTime(iso)).toBe('08.09 14:05');
    expect(fmtDateTime(iso)).toBe('08.09.2026 · 14:05');
    expect(fmtDateTime(iso, ' ')).toBe('08.09.2026 14:05');
  });
  it('returns an empty string for missing values', () => {
    expect(fmtDate('')).toBe('');
  });
});

it('truncate adds an ellipsis only past the limit', () => {
  expect(truncate('abc', 5)).toBe('abc');
  expect(truncate('abcdef', 3)).toBe('abc…');
});
