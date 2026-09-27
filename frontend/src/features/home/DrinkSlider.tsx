import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { HomeProduct } from '@/api/types';
import { ProductCard } from './ProductCard';

const INTERVAL = 4000;
const VISIBLE = 3;

/**
 * Carousel for the "most ordered drinks" row: 3 cards visible, autoplay
 * with a progress bar, paused (and the bar frozen) on hover.
 */
export function DrinkSlider({ items }: { items: HomeProduct[] }) {
  const [idx, setIdx] = useState(0);
  const [cardWidth, setCardWidth] = useState(0);
  const [revealedUpTo, setRevealedUpTo] = useState(-1);
  const [paused, setPaused] = useState(false);
  const [cycle, setCycle] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const max = Math.max(0, items.length - VISIBLE);

  useLayoutEffect(() => {
    const measure = () => {
      const first = trackRef.current?.firstElementChild as HTMLElement | null;
      if (!first) return;
      const gap = parseFloat(getComputedStyle(first).marginRight) || 0;
      setCardWidth(first.getBoundingClientRect().width + gap);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [items.length]);

  // Reveal the cards that scroll into view, staggered.
  useEffect(() => {
    const last = Math.min(idx + VISIBLE, items.length - 1);
    if (last <= revealedUpTo) return;
    const t = window.setTimeout(() => setRevealedUpTo(last), 90);
    return () => window.clearTimeout(t);
  }, [idx, items.length, revealedUpTo]);

  useEffect(() => {
    if (paused) return;
    const t = window.setInterval(() => {
      setIdx((i) => (i >= max ? 0 : i + 1));
      setCycle((c) => c + 1);
    }, INTERVAL);
    return () => window.clearInterval(t);
  }, [paused, max, cycle]);

  // Progress bar: reset to 0, then animate to 100% over one interval.
  useEffect(() => {
    const bar = barRef.current;
    if (!bar || paused) return;
    bar.style.transition = 'none';
    bar.style.width = '0%';
    const raf = requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        bar.style.transition = `width ${INTERVAL}ms linear`;
        bar.style.width = '100%';
      }),
    );
    return () => cancelAnimationFrame(raf);
  }, [cycle, paused]);

  const go = (n: number) => {
    setIdx(n > max ? 0 : n < 0 ? max : n);
    setCycle((c) => c + 1);
  };

  const onEnter = () => {
    setPaused(true);
    const bar = barRef.current;
    if (bar) {
      const w = getComputedStyle(bar).width;
      bar.style.transition = 'none';
      bar.style.width = w;
    }
  };

  return (
    <div className="slider category-slider" onMouseEnter={onEnter} onMouseLeave={() => { setPaused(false); setCycle((c) => c + 1); }}>
      <button className="arrow left" aria-label="Попередній" onClick={() => go(idx - 1)}>
        &#10094;
      </button>
      <button className="arrow right" aria-label="Наступний" onClick={() => go(idx + 1)}>
        &#10095;
      </button>
      <div className="slider-track" ref={trackRef} style={{ transform: `translateX(${-idx * cardWidth}px)` }}>
        {items.map((item, i) => (
          <div className="slide" key={`${item.table}-${item.id}`}>
            <ProductCard item={item} kind="drink" index={i} revealed={i <= revealedUpTo} />
          </div>
        ))}
      </div>
      <div className="cat-progress-bar" ref={barRef} />
    </div>
  );
}
