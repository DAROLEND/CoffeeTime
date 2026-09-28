import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { qk } from '@/api/queries';
import { PageError, PageLoader } from '@/components/Spinner';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/gallery/gallery.css';
import '@/styles/pages/gallery/gallery-layout.css';
import { Lightbox } from './Lightbox';

type Filter = 'all' | 'food' | 'interior';

export default function GalleryPage() {
  usePageTitle('Галерея — Coffee Time');
  const gallery = useQuery({ queryKey: qk.gallery, queryFn: () => unwrap(api.GET('/api/gallery')) });
  const [filter, setFilter] = useState<Filter>('all');
  const [shown, setShown] = useState(0);
  const [lightbox, setLightbox] = useState<number | null>(null);

  const photos = (gallery.data?.photos ?? []).filter((p) => filter === 'all' || p.category === filter);

  // Staggered fade-in, replayed when the filter changes.
  useEffect(() => {
    setShown(0);
    let i = 0;
    const t = window.setInterval(() => {
      i += 1;
      setShown(i);
      if (i >= photos.length) window.clearInterval(t);
    }, 50);
    return () => window.clearInterval(t);
  }, [filter, photos.length]);

  if (gallery.isPending) return <PageLoader />;
  if (gallery.error) return <PageError message={errorMessage(gallery.error)} onRetry={() => gallery.refetch()} />;
  const data = gallery.data;

  const filters: [Filter, string, number][] = [
    ['all', 'Всі', data.photos.length],
    ['food', 'Їжа', data.food_count],
    ['interior', "Інтер'єр", data.interior_count],
  ];

  return (
    <div className="pg-gallery">
      <main className="gallery-page">
        <section className="gallery-hero">
          <h1 className="gallery-hero-title">Наша галерея</h1>
          <p className="gallery-hero-sub">Страви, атмосфера та затишок Coffee Time</p>
        </section>

        <div className="gallery-filters" role="tablist">
          {filters.map(([key, label, count]) => (
            <button key={key} role="tab" aria-selected={filter === key} className={`gf-btn${filter === key ? ' active' : ''}`} onClick={() => setFilter(key)}>
              {label} <span className="gf-count">{count}</span>
            </button>
          ))}
        </div>

        <div className="gallery-masonry">
          {photos.map((photo, i) => (
            <div
              key={photo.id}
              className={`g-item${i < shown ? ' visible' : ''}`}
              role="button"
              tabIndex={0}
              aria-label={photo.alt || 'Відкрити фото'}
              onClick={() => setLightbox(i)}
              onKeyDown={(e) => e.key === 'Enter' && setLightbox(i)}
            >
              <div className="g-inner">
                <img src={photo.url} alt={photo.alt} loading="lazy" />
                <div className="g-overlay">
                  <svg className="g-zoom-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="22" y2="22" /><line x1="11" y1="8" x2="11" y2="14" /><line x1="8" y1="11" x2="14" y2="11" /></svg>
                </div>
              </div>
            </div>
          ))}
        </div>
        {photos.length === 0 && <p className="gallery-empty">Немає фото у цій категорії</p>}
      </main>
      <Lightbox photos={photos} index={lightbox} onClose={() => setLightbox(null)} onIndex={setLightbox} />
    </div>
  );
}
