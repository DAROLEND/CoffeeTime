import { useEffect, useRef, useState } from 'react';

/**
 * Adds `className` (default "visible") to the element the first time it
 * scrolls into view (IntersectionObserver-based scroll reveal).
 * `delay` staggers cards in a row.
 */
export function useReveal<T extends HTMLElement>(options: { threshold?: number; delay?: number; className?: string } = {}) {
  const ref = useRef<T>(null);
  const { threshold = 0.12, delay = 0, className = 'visible' } = options;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add(className);
      return;
    }
    let timer: number | undefined;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        if (delay > 0) {
          el.style.transitionDelay = `${delay}s`;
          // Drop the delay once shown, so hover transitions aren't sluggish.
          timer = window.setTimeout(() => {
            el.style.transitionDelay = '0s';
          }, 600 + delay * 1000);
        }
        el.classList.add(className);
        io.disconnect();
      },
      { threshold },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      window.clearTimeout(timer);
    };
  }, [threshold, delay, className]);

  return ref;
}

/** [ref, inView]: flips to true (once) when the element scrolls into view. */
export function useInView<T extends HTMLElement>(threshold = 0.3) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      setInView(true);
      io.disconnect();
    }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return [ref, inView] as const;
}
