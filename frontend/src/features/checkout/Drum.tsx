import { useCallback, useEffect, useRef } from 'react';

export const ITEM_H = 44;

type Props = {
  items: string[];
  selected: number;
  onChange: (index: number) => void;
  label: string;
  /** Faded while its items are being rebuilt (ASAP animation). */
  fading?: boolean;
  /** Animation length when `selected` changes from outside. */
  duration?: number;
};

const ease = (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t);

/**
 * One wheel of the drum-style time picker: a scroll-snapped column.
 * - native scrolling / touch with CSS scroll-snap
 * - mouse wheel: one row per notch, smooth for trackpads
 * - mouse drag with snap on release
 * - keyboard: ArrowUp/ArrowDown
 * - an external change of `selected` animates the wheel to it
 */
export function Drum({ items, selected, onChange, label, fading, duration = 260 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const raf = useRef(0);
  const programmatic = useRef(false);
  const settleTimer = useRef<number | undefined>(undefined);
  const wheelAcc = useRef(0);
  const drag = useRef<{ startY: number; startScroll: number } | null>(null);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;

  const clampIdx = useCallback((i: number) => Math.max(0, Math.min(i, items.length - 1)), [items.length]);

  const animateTo = useCallback(
    (idx: number, ms = duration, onDone?: () => void) => {
      const el = ref.current;
      if (!el) return;
      cancelAnimationFrame(raf.current);
      const start = el.scrollTop;
      const end = Math.max(0, idx) * ITEM_H;
      if (Math.abs(end - start) < 1) {
        onDone?.();
        return;
      }
      programmatic.current = true;
      el.style.scrollSnapType = 'none';
      const t0 = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - t0) / ms, 1);
        el.scrollTop = start + (end - start) * ease(p);
        if (p < 1) raf.current = requestAnimationFrame(step);
        else {
          el.scrollTop = end;
          el.style.scrollSnapType = '';
          programmatic.current = false;
          onDone?.();
        }
      };
      raf.current = requestAnimationFrame(step);
    },
    [duration],
  );

  // Follow `selected` / item changes coming from the parent.
  useEffect(() => {
    const el = ref.current;
    if (!el || drag.current) return;
    const target = clampIdx(selected) * ITEM_H;
    if (Math.abs(el.scrollTop - target) > 1) animateTo(clampIdx(selected));
  }, [selected, items, animateTo, clampIdx]);

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  const settle = useCallback(() => {
    const el = ref.current;
    if (!el || programmatic.current || drag.current || !items.length) return;
    const idx = clampIdx(Math.round(el.scrollTop / ITEM_H));
    if (idx !== selectedRef.current) onChange(idx);
  }, [clampIdx, items.length, onChange]);

  const onScroll = () => {
    if (programmatic.current) return;
    window.clearTimeout(settleTimer.current);
    settleTimer.current = window.setTimeout(settle, 140);
  };

  // Wheel needs a non-passive listener to stop the page from scrolling.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (drag.current) return;
      wheelAcc.current += e.deltaY;
      if (Math.abs(wheelAcc.current) < 40) return;
      const dir = wheelAcc.current > 0 ? 1 : -1;
      wheelAcc.current = 0;
      const next = clampIdx(selectedRef.current + dir);
      if (next !== selectedRef.current) animateTo(next, 180, () => onChange(next));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [animateTo, clampIdx, onChange]);

  // Mouse drag (touch uses native scrolling).
  useEffect(() => {
    const move = (e: MouseEvent) => {
      const el = ref.current;
      if (!drag.current || !el) return;
      el.scrollTop = Math.max(0, Math.min(drag.current.startScroll + (drag.current.startY - e.clientY), (items.length - 1) * ITEM_H));
    };
    const up = () => {
      const el = ref.current;
      if (!drag.current || !el) return;
      drag.current = null;
      el.style.cursor = '';
      const idx = clampIdx(Math.round(el.scrollTop / ITEM_H));
      animateTo(idx, 160, () => idx !== selectedRef.current && onChange(idx));
    };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
    return () => {
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up);
    };
  }, [animateTo, clampIdx, items.length, onChange]);

  return (
    <div className="dt-drum-wrap">
      <div
        ref={ref}
        className={`dt-drum${fading ? ' dt-drum--fading' : ''}`}
        role="listbox"
        aria-label={label}
        aria-activedescendant={items.length ? `${label}-${selected}` : undefined}
        tabIndex={0}
        onScroll={onScroll}
        onMouseDown={(e) => {
          e.preventDefault();
          const el = ref.current!;
          cancelAnimationFrame(raf.current);
          programmatic.current = false;
          el.style.scrollSnapType = 'none';
          el.style.cursor = 'grabbing';
          drag.current = { startY: e.clientY, startScroll: el.scrollTop };
        }}
        onKeyDown={(e) => {
          if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
          e.preventDefault();
          const next = clampIdx(selected + (e.key === 'ArrowDown' ? 1 : -1));
          if (next !== selected) onChange(next);
        }}
      >
        {items.map((item, i) => (
          <div key={`${item}-${i}`} id={`${label}-${i}`} className="dt-drum-item" role="option" aria-selected={i === selected}>
            {item}
          </div>
        ))}
      </div>
      <div className="dt-drum-hl" />
      <div className="dt-drum-fade dt-drum-fade-t" />
      <div className="dt-drum-fade dt-drum-fade-b" />
    </div>
  );
}
