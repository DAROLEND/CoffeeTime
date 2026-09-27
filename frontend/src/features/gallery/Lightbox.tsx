import { useCallback, useEffect, useState } from 'react';
import type { GalleryPage } from '@/api/types';
import { useScrollLock } from '@/hooks/useScrollLock';

type Photo = GalleryPage['photos'][number];

/** Full-screen photo viewer: arrows, keyboard (←/→/Esc), swipe, counter. */
export function Lightbox({ photos, index, onClose, onIndex }: { photos: Photo[]; index: number | null; onClose: () => void; onIndex: (i: number) => void }) {
  const open = index !== null;
  const [loaded, setLoaded] = useState(false);
  const [touchX, setTouchX] = useState(0);
  useScrollLock(open);

  const step = useCallback(
    (d: number) => {
      if (index === null || !photos.length) return;
      setLoaded(false);
      onIndex((index + d + photos.length) % photos.length);
    },
    [index, onIndex, photos.length],
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') step(-1);
      if (e.key === 'ArrowRight') step(1);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose, step]);

  const photo = index !== null ? photos[index] : null;

  return (
    <div
      className={`lb-overlay${open ? ' open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-hidden={!open}
      aria-label="Перегляд фото"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onTouchStart={(e) => setTouchX(e.touches[0].clientX)}
      onTouchEnd={(e) => {
        const diff = touchX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) step(diff > 0 ? 1 : -1);
      }}
    >
      <button className="lb-close" aria-label="Закрити" onClick={onClose}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
      </button>
      <button className="lb-nav lb-prev" aria-label="Попереднє" onClick={() => step(-1)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
      <div className="lb-img-wrap">
        {photo && <img key={photo.id} src={photo.url} alt={photo.alt} className={`lb-img${loaded ? ' loaded' : ''}`} onLoad={() => setLoaded(true)} />}
        <div className="lb-spinner" />
      </div>
      <button className="lb-nav lb-next" aria-label="Наступне" onClick={() => step(1)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="9 18 15 12 9 6" /></svg>
      </button>
      <div className="lb-footer">
        <span className="lb-counter">{index !== null ? `${index + 1} / ${photos.length}` : ''}</span>
        <span className="lb-caption">{photo?.alt}</span>
      </div>
    </div>
  );
}
