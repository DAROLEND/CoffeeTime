import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { qk } from '@/api/queries';
import type { HomePage as HomeData } from '@/api/types';
import { Icon, type IconName } from '@/components/Icon';
import { Reveal } from '@/components/Reveal';
import { PageError, PageLoader } from '@/components/Spinner';
import { useCountUp } from '@/hooks/useCountUp';
import { usePageTitle } from '@/hooks/usePageTitle';
import { plural } from '@/lib/format';
import '@/styles/pages/home/slider.css';
import '@/styles/pages/home/slider_food.css';
import '@/styles/pages/home/homepage.css';
import { DrinkSlider } from './DrinkSlider';
import { HeroSlider } from './HeroSlider';
import { ProductCard } from './ProductCard';

const BENEFITS: { icon: IconName; title: string; sub: string }[] = [
  { icon: 'coffee-cup', title: 'Свіжозварена кава', sub: 'Щоранку нова обсмажка' },
  { icon: 'cake', title: 'Десерти щодня', sub: 'Мусові, еклери, макарони' },
  { icon: 'leaf', title: 'Свіжі інгредієнти', sub: 'Без консервантів' },
  { icon: 'clock', title: 'Графік роботи', sub: 'Пн–Пт 8:00–20:00' },
];

function Stat({ value, suffix = '', decimals = 0, label }: { value: number; suffix?: string; decimals?: number; label: string }) {
  const [ref, current] = useCountUp<HTMLSpanElement>(value, { duration: 1000 });
  return (
    <div className="stat-item">
      <span className="stat-number" ref={ref}>
        {current.toFixed(decimals)}
        {suffix}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function DessertBanner({ banner }: { banner: HomeData['dessert_banner'] }) {
  const photoRef = useRef<HTMLDivElement>(null);
  const [shift, setShift] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const el = photoRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) return;
      const pct = 1 - (rect.top + rect.height) / (window.innerHeight + rect.height);
      setShift((pct - 0.5) * 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <section className="dessert-banner">
      <Reveal className="dessert-banner__text">
        {banner.label && <p className="banner-label">{banner.label}</p>}
        <h2>{banner.title}</h2>
        <p className="dessert-banner__desc">
          {banner.desc.split('\n').map((line, i) => (
            <span key={i}>
              {i > 0 && <br />}
              {line}
            </span>
          ))}
        </p>
        <Link to="/menu?category=dessert_items" className="banner-btn">
          {banner.btn}
        </Link>
      </Reveal>
      <div className={`dessert-banner__photo${banner.image ? ' has-photo' : ''}`} ref={photoRef}>
        {banner.image && <img src={banner.image} alt="Десерт дня" style={{ transform: `translateY(${shift.toFixed(1)}px) scale(1.06)` }} />}
      </div>
    </section>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <>
      <Reveal as="h2">{title}</Reveal>
      {subtitle && (
        <Reveal as="p" className="section-subtitle">
          {subtitle}
        </Reveal>
      )}
    </>
  );
}

export default function HomePage() {
  usePageTitle('Головна | Coffee Time');
  const { data, error, isPending, refetch } = useQuery({
    queryKey: qk.home,
    queryFn: () => unwrap(api.GET('/api/home')),
  });

  if (isPending) return <PageLoader />;
  if (error) return <PageError message={errorMessage(error)} onRetry={() => refetch()} />;

  const { about } = data;

  return (
    <div className="pg-home">
      <HeroSlider slides={data.hero_slides} />

      <section className="benefits-strip">
        <div className="container">
          {BENEFITS.map((b) => (
            <Reveal key={b.title} className="benefit-block">
              <Icon name={b.icon} size={36} color="#8B4513" className="benefit-icon" />
              <div>
                <p className="benefit-title">{b.title}</p>
                <p className="benefit-sub">{b.sub}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="container">
          <SectionTitle title="Краща їжа" />
          <div className="product-grid">
            {data.food_items.map((item, i) => (
              <ProductCard key={`${item.table}-${item.id}`} item={item} kind="food" index={i} badge />
            ))}
          </div>
        </div>
      </section>

      <DessertBanner banner={data.dessert_banner} />

      <section className="home-section">
        <div className="container">
          <SectionTitle title="Обирають найчастіше" subtitle="Найпопулярніші напої та кава" />
          {data.drink_items.length < 4 ? (
            <div className="product-grid">
              {data.drink_items.map((item, i) => (
                <ProductCard key={`${item.table}-${item.id}`} item={item} kind="drink" index={i} />
              ))}
            </div>
          ) : (
            <DrinkSlider items={data.drink_items} />
          )}
        </div>
      </section>

      <section className="home-section about-section">
        <div className="container">
          <Reveal className="about-content" base="reveal-left">
            <p className="about-label">Про нас</p>
            <h2>{about.title}</h2>
            <p className="about-text">{about.text}</p>
            <div className="about-stats">
              <Stat value={about.years_open} label={`${plural(about.years_open, ['рік', 'роки', 'років'])} на ринку`} />
              <Stat value={Number(about.menu_count) || 0} suffix="+" label="позицій меню" />
              <Stat value={Number(about.rating) || 0} suffix="★" decimals={1} label="Google рейтинг" />
            </div>
          </Reveal>
          <Reveal className="about-photo" base="reveal-right">
            <img src={about.photo} alt="Coffee Time кафе" />
          </Reveal>
        </div>
      </section>

      <section className="home-section dessert-featured">
        <div className="container">
          <SectionTitle title="Наші десерти" subtitle="Готуємо щоранку — мусові торти, еклери, макарони, тарти" />
          <div className="product-grid">
            {data.dessert_items.map((item, i) => (
              <ProductCard key={`${item.table}-${item.id}`} item={item} kind="dessert" index={i} />
            ))}
          </div>
        </div>
      </section>

      <section className="home-section reviews-section">
        <div className="container">
          <SectionTitle
            title="Що кажуть наші гості"
            subtitle={data.total_reviews >= 10 ? `На основі ${data.total_reviews} відгуків` : 'Реальні відгуки наших відвідувачів'}
          />
          <div className="reviews-grid">
            {data.reviews.map((r, i) => (
              <Reveal key={`${r.name}-${i}`} className="review-card">
                <div className="review-avatar" style={{ background: r.avatar_color }}>
                  {r.name.slice(0, 1).toUpperCase()}
                </div>
                <div className="review-stars">{'★'.repeat(r.rating) + '☆'.repeat(5 - r.rating)}</div>
                <p className="review-text">"{r.text}"</p>
                <div className="review-author">
                  <span className="review-name">{r.name}</span>
                </div>
              </Reveal>
            ))}
          </div>
          <div className="reviews-cta">
            <Link to="/reviews" className="btn-outline">
              Переглянути всі відгуки{data.total_reviews > 0 ? ` (${data.total_reviews})` : ''} →
            </Link>
          </div>
          <div className="reviews-leave-cta">
            <Link to="/reviews#leave-review" className="btn-leave-review">
              Залишити відгук
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
