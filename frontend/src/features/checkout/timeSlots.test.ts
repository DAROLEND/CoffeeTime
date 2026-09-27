import { describe, expect, it } from 'vitest';
import {
  asapSlot,
  availableDays,
  availableHours,
  availableMinutes,
  cafeClock,
  earliestReadyTime,
  findFirstOpenSlot,
  fmtDate,
  fmtTime,
  isAdvanceOrder,
  isCafeOpenAt,
  needsReminderEmail,
  type Schedule,
} from './timeSlots';

// Mon–Fri 08:00–20:00, Sat 10:00–18:00, closed on Sunday (ISO weekdays).
const schedule: Schedule = {
  '1': { open: '08:00', close: '20:00' },
  '2': { open: '08:00', close: '20:00' },
  '3': { open: '08:00', close: '20:00' },
  '4': { open: '08:00', close: '20:00' },
  '5': { open: '08:00', close: '20:00' },
  '6': { open: '10:00', close: '18:00' },
};

// 2026-09-09 is a Wednesday.
const at = (s: string) => new Date(s);
const ctx = (now: string, prep = 15, travel = 0) => ({ now: at(now), schedule, prepMinutes: prep, travelMinutes: travel });

describe('opening hours', () => {
  it('is open inside the window and closed at closing time', () => {
    expect(isCafeOpenAt(at('2026-09-09T08:00:00'), schedule)).toBe(true);
    expect(isCafeOpenAt(at('2026-09-09T19:59:00'), schedule)).toBe(true);
    expect(isCafeOpenAt(at('2026-09-09T20:00:00'), schedule)).toBe(false);
    expect(isCafeOpenAt(at('2026-09-13T12:00:00'), schedule)).toBe(false); // Sunday
  });

  it('finds the next open slot, skipping closed days', () => {
    expect(fmtTime(findFirstOpenSlot(at('2026-09-09T07:10:00'), schedule)!)).toBe('08:00');
    const afterSat = findFirstOpenSlot(at('2026-09-12T18:30:00'), schedule)!;
    expect(fmtDate(afterSat)).toBe('2026-09-14'); // Saturday evening -> Monday
    expect(fmtTime(afterSat)).toBe('08:00');
  });

  it('rounds up to the next quarter hour', () => {
    expect(fmtTime(findFirstOpenSlot(at('2026-09-09T09:01:00'), schedule)!)).toBe('09:15');
  });
});

describe('earliest ready time', () => {
  it('adds prep and travel time from now while open', () => {
    expect(fmtTime(earliestReadyTime(at('2026-09-09T10:00:00'), schedule, 15, 10))).toBe('10:25');
  });
  it('starts from the next opening when closed', () => {
    expect(fmtTime(earliestReadyTime(at('2026-09-09T06:00:00'), schedule, 15, 0))).toBe('08:15');
  });
});

describe('drum options', () => {
  it('hides today\'s minutes that are too soon', () => {
    expect(availableMinutes('2026-09-09', 10, ctx('2026-09-09T10:05:00'))).toEqual([30, 45]);
    // Later days are unrestricted.
    expect(availableMinutes('2026-09-10', 10, ctx('2026-09-09T10:05:00'))).toEqual([0, 15, 30, 45]);
  });

  it('lists only hours with a free slot', () => {
    const hours = availableHours('2026-09-09', ctx('2026-09-09T18:50:00'));
    expect(hours).toEqual([19]);
    expect(availableHours('2026-09-13', ctx('2026-09-09T10:00:00'))).toEqual([]); // Sunday
  });

  it('drops today once it is too late and skips Sunday', () => {
    const days = availableDays(ctx('2026-09-09T19:55:00'), 5);
    expect(days).toEqual(['2026-09-10', '2026-09-11', '2026-09-12']);
  });

  it('ASAP lands on the first open quarter hour', () => {
    expect(fmtTime(asapSlot(ctx('2026-09-09T10:02:00'))!)).toBe('10:30');
    const nextDay = asapSlot(ctx('2026-09-09T19:55:00'))!;
    expect(fmtDate(nextDay)).toBe('2026-09-10');
    expect(fmtTime(nextDay)).toBe('08:00');
  });
});

describe('order rules', () => {
  const now = at('2026-09-09T10:00:00');
  it('treats a later day as an advance (prepaid) order', () => {
    expect(isAdvanceOrder('2026-09-10 09:00', now)).toBe(true);
    expect(isAdvanceOrder('2026-09-09 18:00', now)).toBe(false);
    expect(isAdvanceOrder('', now)).toBe(false);
  });
  it('asks for a reminder email only 3+ hours ahead', () => {
    expect(needsReminderEmail('2026-09-09 13:00', now)).toBe(true);
    expect(needsReminderEmail('2026-09-09 12:45', now)).toBe(false);
    expect(needsReminderEmail('garbage', now)).toBe(false);
  });
});

it('cafeClock follows the server clock, not the device', () => {
  const deviceNow = Date.now();
  const serverNow = new Date(deviceNow + 3_600_000).toISOString();
  const now = cafeClock(serverNow, deviceNow)();
  expect(Math.round((now.getTime() - Date.now()) / 60_000)).toBe(60);
});
