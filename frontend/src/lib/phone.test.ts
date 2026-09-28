import { describe, expect, it } from 'vitest';
import { formatPhone, PHONE_RE } from './phone';

describe('formatPhone', () => {
  it.each([
    ['0671234567', '+38 (067) 123-45-67'],
    ['380671234567', '+38 (067) 123-45-67'],
    ['+38 (067) 123-45-67', '+38 (067) 123-45-67'],
    ['671234567', '+38 (067) 123-45-67'],
    ['067', '+38 (067'],
    ['06712', '+38 (067) 12'],
    ['0671234', '+38 (067) 123-4'],
    ['', ''],
  ])('%s -> %s', (raw, out) => expect(formatPhone(raw)).toBe(out));

  it('ignores digits past a full number', () => {
    expect(formatPhone('06712345678999')).toBe('+38 (067) 123-45-67');
  });

  it('produces exactly what PHONE_RE accepts', () => {
    expect(PHONE_RE.test(formatPhone('0671234567'))).toBe(true);
    expect(PHONE_RE.test(formatPhone('067123'))).toBe(false);
  });
});
