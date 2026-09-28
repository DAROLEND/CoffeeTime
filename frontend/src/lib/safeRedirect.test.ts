import { expect, it } from 'vitest';
import { safeRedirect } from './safeRedirect';

it('allows same-site paths only', () => {
  expect(safeRedirect('/profile?tab=orders')).toBe('/profile?tab=orders');
  expect(safeRedirect(null)).toBe('/');
  expect(safeRedirect('https://evil.example')).toBe('/');
  expect(safeRedirect('//evil.example')).toBe('/');
  expect(safeRedirect('/\\evil.example')).toBe('/');
  expect(safeRedirect('javascript:alert(1)', '/menu')).toBe('/menu');
});
