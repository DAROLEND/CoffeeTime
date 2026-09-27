/** Formatting helpers shared by the storefront and admin. */

const NBSP = ' ';

/** 1234.5 -> "1 235 ₴" (whole hryvnias, thin-space thousands). */
export function money(value: number, suffix = '₴'): string {
  return `${Math.round(value).toLocaleString('uk-UA').replace(/\s/g, NBSP)}${NBSP}${suffix}`;
}

/** Menu price: keeps kopecks when there are any ("1 234,50 ₴"). */
export function fmtPrice(value: number): string {
  const whole = Number.isInteger(value);
  const s = value.toLocaleString('uk-UA', {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  });
  return `${s.replace(/\s/g, NBSP)}${NBSP}₴`;
}

/** Ukrainian plural: plural(5, ['товар', 'товари', 'товарів']) -> 'товарів'. */
export function plural(n: number, forms: [string, string, string]): string {
  const n100 = Math.abs(n) % 100;
  const n10 = n100 % 10;
  if (n100 >= 11 && n100 <= 19) return forms[2];
  if (n10 === 1) return forms[0];
  if (n10 >= 2 && n10 <= 4) return forms[1];
  return forms[2];
}

/**
 * The API sends naive ISO timestamps (café-local wall-clock time).
 * `new Date("2026-09-08T10:00:00")` parses those as local time, which
 * keeps the numbers the server stored instead of shifting them.
 */
export function parseNaive(iso: string): Date {
  return new Date(iso);
}

const pad = (n: number) => String(n).padStart(2, '0');

/** "08.09.2026" */
export function fmtDate(iso: string): string {
  if (!iso) return '';
  const d = parseNaive(iso);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

/** "08.09 14:05" */
export function fmtShortDateTime(iso: string): string {
  if (!iso) return '';
  const d = parseNaive(iso);
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "08.09.2026 · 14:05" */
export function fmtDateTime(iso: string, sep = ' · '): string {
  if (!iso) return '';
  const d = parseNaive(iso);
  return `${fmtDate(iso)}${sep}${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}
