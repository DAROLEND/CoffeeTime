/** Live mask for Ukrainian phone numbers: "+38 (0XX) XXX-XX-XX". */
export function formatPhone(raw: string): string {
  let d = raw.replace(/\D/g, '');
  if (d.startsWith('380')) d = d.slice(2);
  else if (d.startsWith('38')) d = d.slice(2);
  if (d.length > 0 && !d.startsWith('0')) d = `0${d}`;
  d = d.slice(0, 10);
  let out = '';
  if (d.length > 0) out = `+38 (${d.slice(0, Math.min(3, d.length))}`;
  if (d.length > 3) out += `) ${d.slice(3, Math.min(6, d.length))}`;
  if (d.length > 6) out += `-${d.slice(6, Math.min(8, d.length))}`;
  if (d.length > 8) out += `-${d.slice(8, 10)}`;
  return out;
}

export const PHONE_RE = /^\+38 \(0\d{2}\) \d{3}-\d{2}-\d{2}$/;
