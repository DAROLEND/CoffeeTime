import { useCallback, useEffect, useRef, useState, type MouseEvent, type TouchEvent } from 'react';
import { Link } from 'react-router';
import type { HomePage } from '@/api/types';

const INTERVAL = 5000;

/**
 * Full-width hero slider: autoplay (paused on hover), arrows, dots,
 * click on the left/right half, touch swipe, and a slight parallax on the
 * background while scrolling past it.
 */
export function HeroSlider({ slides }: { slides: HomePage['hero_slides'] }) {
  const [idx, setIdx] = useState(0);
  const timer = useRef<number | undefined>(undefined);
  const rootRef = useRef<HTMLDivElement>(null);
  const touchX = useRef(0);
  const [shift, setShift] = useState(0);
  const count = slides.length;

  const show = useCallback((n: number) => setIdx(((n % count) + count) % count), [count]);

  const start = useCallback(() => {
    window.clearInterval(timer.current);
    timer.current = window.setInterval(() => setIdx((i) => (i + 1) % count), INTERVAL);
  }, [count]);
  const stop = () => window.clearInterval(timer.current);

  useEffect(() => {
    start();
    return stop;
  }, [start]);

  useEffect(() => {
    const onScroll = () => {
      const h = rootRef.current?.offsetHeight ?? 0;
      if (window.scrollY <= h) setShift(window.scrollY * 0.28);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const go = (n: number) => {
    show(n);
    start();
  };

  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest('a, button')) return;
    const rect = e.currentTarget.getBoundingClientRect();
    go(idx + (e.clientX - rect.left >= rect.width / 2 ? 1 : -1));
  };
  const onTouchEnd = (e: TouchEvent<HTMLDivElement>) => {
    const diff = touchX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 40) go(idx + (diff > 0 ? 1 : -1));
  };

  return (
    <section className="hero">
      <div
        className="slider"
        ref={rootRef}
        onMouseEnter={stop}
        onMouseLeave={start}
        onClick={onClick}
        onTouchStart={(e) => {
          touchX.current = e.touches[0].clientX;
        }}
        onTouchEnd={onTouchEnd}
      >
        {slides.map((s, i) => (
          <div
            key={`${s.image}-${i}`}
            className={`slide${i === idx ? ' active' : ''}`}
            style={{ backgroundImage: `url('${s.image}')`, backgroundPositionY: `calc(50% + ${shift.toFixed(1)}px)` }}
            aria-hidden={i !== idx}
          >
            <div className="hero-text">
              {s.label && <span className="hero-label">{s.label}</span>}
              <h1>{s.text}</h1>
              <p className="hero-subtitle">{s.sub}</p>
              <Link to="/menu" className="hero-cta" tabIndex={i === idx ? 0 : -1}>
                Переглянути меню →
              </Link>
            </div>
          </div>
        ))}
        <button className="arrow left" aria-label="Попередній слайд" onClick={() => go(idx - 1)} />
        <button className="arrow right" aria-label="Наступний слайд" onClick={() => go(idx + 1)} />
        <div className="slider-controls">
          {slides.map((_, i) => (
            <span
              key={i}
              className={`dot${i === idx ? ' active' : ''}`}
              role="button"
              tabIndex={0}
              aria-label={`Слайд ${i + 1}`}
              onClick={() => go(i)}
              onKeyDown={(e) => e.key === 'Enter' && go(i)}
            />
          ))}
        </div>
        <div className="hero-wave">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 72" preserveAspectRatio="none">
            <path d="M0,0 C480,72 960,0 1440,0 L1440,72 L0,72 Z" fill="#fdf6ee" />
          </svg>
        </div>
      </div>
    </section>
  );
}
