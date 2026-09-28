/**
 * Pickup-time slot logic for the checkout drum picker.
 *
 * Every Date here holds *café-local* (Europe/Kyiv) wall-clock time in its
 * local fields. `cafeClock()` builds "now" from the server's clock, so a
 * customer whose device is in another timezone (or has a wrong clock)
 * still sees the café's real opening hours. The server re-validates the
 * chosen time anyway.
 */
export type DaySchedule = { open: string; close: string };
export type Schedule = Record<string, DaySchedule>;

export const SLOT_MINUTES = [0, 15, 30, 45];

/** Returns a function giving café-local "now", anchored to the server time. */
export function cafeClock(serverNow: string, deviceNowMs = Date.now()): () => Date {
  const offset = new Date(serverNow).getTime() - deviceNowMs;
  return () => new Date(Date.now() + offset);
}

const pad = (n: number) => String(n).padStart(2, '0');
export const fmtDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const fmtTime = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

function isoWeekday(d: Date): number {
  return d.getDay() === 0 ? 7 : d.getDay();
}

function parseDateStr(ds: string): Date {
  const [y, m, d] = ds.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function isCafeOpenAt(date: Date, schedule: Schedule): boolean {
  const day = schedule[String(isoWeekday(date))];
  if (!day) return false;
  const [oh, om] = day.open.split(':').map(Number);
  const [ch, cm] = day.close.split(':').map(Number);
  const open = new Date(date);
  open.setHours(oh, om, 0, 0);
  const close = new Date(date);
  close.setHours(ch, cm, 0, 0);
  return date >= open && date < close;
}

/** First 15-minute slot at or after `from` when the café is open. */
export function findFirstOpenSlot(from: Date, schedule: Schedule): Date | null {
  const d = new Date(from);
  const rem = d.getMinutes() % 15;
  if (rem) d.setMinutes(d.getMinutes() + (15 - rem));
  d.setSeconds(0, 0);
  for (let i = 0; i < 14 * 24 * 4; i++) {
    if (isCafeOpenAt(d, schedule)) return new Date(d);
    d.setMinutes(d.getMinutes() + 15);
  }
  return null;
}

/**
 * Earliest time the order can be ready: kitchen starts now (or at the
 * next opening), plus prep time, plus the customer's travel time.
 */
export function earliestReadyTime(now: Date, schedule: Schedule, prepMinutes: number, travelMinutes: number): Date {
  const start = isCafeOpenAt(now, schedule) ? now : findFirstOpenSlot(now, schedule);
  if (!start) return new Date(9999, 0, 1);
  return new Date(start.getTime() + (prepMinutes + travelMinutes) * 60_000);
}

type Ctx = { now: Date; schedule: Schedule; prepMinutes: number; travelMinutes: number };

function minTimeFor(dateStr: string, ctx: Ctx): Date | null {
  if (dateStr !== fmtDate(ctx.now)) return null;
  const t = earliestReadyTime(ctx.now, ctx.schedule, ctx.prepMinutes, ctx.travelMinutes);
  t.setSeconds(0, 0);
  return t;
}

export function availableMinutes(dateStr: string, hour: number, ctx: Ctx): number[] {
  const min = minTimeFor(dateStr, ctx);
  const day = parseDateStr(dateStr);
  return SLOT_MINUTES.filter((m) => {
    if (!min) return true;
    const slot = new Date(day);
    slot.setHours(hour, m, 0, 0);
    return slot >= min;
  });
}

export function availableHours(dateStr: string, ctx: Ctx): number[] {
  const conf = ctx.schedule[String(isoWeekday(parseDateStr(dateStr)))];
  if (!conf) return [];
  const [oh] = conf.open.split(':').map(Number);
  const [ch] = conf.close.split(':').map(Number);
  const hours: number[] = [];
  for (let h = oh; h < ch; h++) if (availableMinutes(dateStr, h, ctx).length) hours.push(h);
  return hours;
}

/** Days (today + up to `maxDaysAhead - 1`) that still have a free slot. */
export function availableDays(ctx: Ctx, maxDaysAhead = 14): string[] {
  const days: string[] = [];
  for (let i = 0; i < maxDaysAhead; i++) {
    const d = new Date(ctx.now);
    d.setDate(ctx.now.getDate() + i);
    const ds = fmtDate(d);
    if (availableHours(ds, ctx).length) days.push(ds);
  }
  return days;
}

/** "Якнайшвидше": earliest ready time rounded up to a slot the café is open. */
export function asapSlot(ctx: Ctx): Date | null {
  const ready = earliestReadyTime(ctx.now, ctx.schedule, ctx.prepMinutes, ctx.travelMinutes);
  const rem = ready.getMinutes() % 15;
  if (rem) ready.setMinutes(ready.getMinutes() + (15 - rem));
  ready.setSeconds(0, 0);
  return isCafeOpenAt(ready, ctx.schedule) ? ready : findFirstOpenSlot(ready, ctx.schedule);
}

function isToday(ds: string, now: Date) {
  return ds === fmtDate(now);
}
function isTomorrow(ds: string, now: Date) {
  const t = new Date(now);
  t.setDate(now.getDate() + 1);
  return ds === fmtDate(t);
}

/** Short label in the day drum: "Сьогодні", "Завтра", "Пт 12". */
export function dayDrumLabel(ds: string, now: Date): string {
  if (isToday(ds, now)) return 'Сьогодні';
  if (isTomorrow(ds, now)) return 'Завтра';
  const d = parseDateStr(ds);
  const wd = d.toLocaleDateString('uk-UA', { weekday: 'short' });
  return `${wd.charAt(0).toUpperCase()}${wd.slice(1)} ${d.getDate()}`;
}

/** Long label in the summary: "Сьогодні", "Завтра", "пʼятниця, 12 вересня". */
export function dayLabel(ds: string, now: Date): string {
  if (isToday(ds, now)) return 'Сьогодні';
  if (isTomorrow(ds, now)) return 'Завтра';
  return parseDateStr(ds).toLocaleDateString('uk-UA', { weekday: 'long', day: 'numeric', month: 'long' });
}

/** Orders for a later day must be prepaid online. */
export function isAdvanceOrder(readyTime: string, now: Date): boolean {
  return !!readyTime && readyTime.slice(0, 10) > fmtDate(now);
}

/** The reminder email field only makes sense for pickups 3+ hours away. */
export function needsReminderEmail(readyTime: string, now: Date): boolean {
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(readyTime)) return false;
  const [ds, ts] = readyTime.split(' ');
  const [h, m] = ts.split(':').map(Number);
  const at = parseDateStr(ds);
  at.setHours(h, m, 0, 0);
  return (at.getTime() - now.getTime()) / 3_600_000 >= 3;
}
