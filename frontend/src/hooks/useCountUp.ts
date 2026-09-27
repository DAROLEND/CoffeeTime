import { useEffect, useRef, useState } from 'react';

/**
 * Animates 0 -> target once the element becomes visible (or immediately
 * when `startOnView` is false). Returns [ref, currentValue].
 */
export function useCountUp<T extends HTMLElement>(target: number, { duration = 900, startOnView = true } = {}) {
  const ref = useRef<T>(null);
  const [value, setValue] = useState(startOnView ? 0 : 0);

  useEffect(() => {
    let raf = 0;
    const run = () => {
      const t0 = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - t0) / duration, 1);
        setValue(target * p);
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    };
    const el = ref.current;
    if (!startOnView || !el || typeof IntersectionObserver === 'undefined') {
      run();
      return () => cancelAnimationFrame(raf);
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        run();
      },
      { threshold: 0.5 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [target, duration, startOnView]);

  return [ref, value] as const;
}
