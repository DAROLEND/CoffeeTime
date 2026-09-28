import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { ApiError, errorMessage, unwrap } from '@/api/errors';
import { qk, useSession } from '@/api/queries';
import type { ReviewsPage as ReviewsData } from '@/api/types';
import { PageError, PageLoader } from '@/components/Spinner';
import { Reveal } from '@/components/Reveal';
import { useCountUp } from '@/hooks/useCountUp';
import { usePageTitle } from '@/hooks/usePageTitle';
import { useInView } from '@/hooks/useReveal';
import { fmtDate } from '@/lib/format';
import '@/styles/pages/reviews/reviews.css';

const SORTS: [string, string][] = [['newest', 'Нові'], ['oldest', 'Старі'], ['best', 'Висока оцінка'], ['worst', 'Низька оцінка']];
const HINTS: Record<number, string> = { 1: 'Жахливо', 2: 'Погано', 3: 'Нормально', 4: 'Добре', 5: 'Відмінно' };
const SHORT_LEN = 140;

function StatsCard({ data }: { data: ReviewsData }) {
  const [numRef, avg] = useCountUp<HTMLSpanElement>(data.avg_rating, { duration: 1100 });
  const [barsRef, barsShown] = useInView<HTMLDivElement>(0.3);
  const full = Math.floor(data.avg_rating);
  const n = data.total_count;
  return (
    <div className="rv-stats-card">
      <div className="rv-avg">
        <span className="rv-avg-num" ref={numRef}>{avg.toFixed(1)}</span>
        <div className="rv-avg-stars">{'★'.repeat(full) + '★'.repeat(5 - full)}</div>
        <span className="rv-avg-label">
          на основі {n} {n % 10 === 1 && n % 100 !== 11 ? 'відгуку' : 'відгуків'}
        </span>
      </div>
      <div className="rv-stats-divider" />
      <div className="rv-bars" ref={barsRef}>
        {data.distribution.map((b) => (
          <div className="rv-bar-row" key={b.stars}>
            <span className="rv-bar-label">{b.stars}★</span>
            <div className="rv-bar-track">
              <div className="rv-bar-fill" style={{ width: barsShown ? `${b.pct}%` : 0 }} />
            </div>
            <span className="rv-bar-pct">{b.pct}%</span>
          </div>
        ))}
      </div>
      <div className="rv-stats-divider" />
      <div className="rv-stats-badge">
        <div className="rv-stats-badge-icon">★</div>
        <span className="rv-stats-badge-text">
          Рекомендують
          <br />
          наші клієнти
        </span>
      </div>
    </div>
  );
}

function ReviewCard({ review }: { review: ReviewsData['reviews'][number] }) {
  const [expanded, setExpanded] = useState(false);
  const long = review.text.length > SHORT_LEN;
  return (
    <Reveal className="rv-card">
      <span className="rv-card-quote">❝</span>
      <div className="rv-card-head">
        <div className="rv-avatar" style={{ background: review.avatar_color }}>{review.initial}</div>
        <div className="rv-card-meta">
          <span className="rv-name">{review.name}</span>
          <span className="rv-date">{fmtDate(review.created_at)}</span>
        </div>
        <div className="rv-stars" aria-label={`${review.rating} з 5`}>
          {[1, 2, 3, 4, 5].map((i) => <span key={i} className={i <= review.rating ? 'star-full' : 'star-empty'}>★</span>)}
        </div>
      </div>
      <p className="rv-text">{long && !expanded ? `${review.text.slice(0, SHORT_LEN)}...` : review.text}</p>
      {long && (
        <button className="rv-read-more" type="button" onClick={() => setExpanded((e) => !e)}>
          {expanded ? 'згорнути' : 'читати далі'}
        </button>
      )}
    </Reveal>
  );
}

function Pagination({ page, total, onPage }: { page: number; total: number; onPage: (p: number) => void }) {
  if (total <= 1) return null;
  const start = Math.max(1, page - 2);
  const end = Math.min(total, page + 2);
  const btn = (p: number, label: string | number, active = false) => (
    <button key={`${label}-${p}`} type="button" className={`rv-page-btn${active ? ' rv-page-btn--active' : ''}`} onClick={() => onPage(p)} aria-current={active ? 'page' : undefined}>
      {label}
    </button>
  );
  return (
    <nav className="rv-pagination" aria-label="Pagination">
      {page > 1 ? btn(page - 1, '← Попередня') : <span className="rv-page-btn rv-page-btn--disabled">← Попередня</span>}
      {start > 1 && (
        <>
          {btn(1, 1)}
          {start > 2 && <span className="rv-page-ellipsis">…</span>}
        </>
      )}
      {Array.from({ length: end - start + 1 }, (_, i) => start + i).map((p) => btn(p, p, p === page))}
      {end < total && (
        <>
          {end < total - 1 && <span className="rv-page-ellipsis">…</span>}
          {btn(total, total)}
        </>
      )}
      {page < total ? btn(page + 1, 'Наступна →') : <span className="rv-page-btn rv-page-btn--disabled">Наступна →</span>}
    </nav>
  );
}

function ReviewForm({ onDone }: { onDone: () => void }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [errors, setErrors] = useState({ rating: false, name: false, text: false });
  const [pop, setPop] = useState(0);
  const submit = useMutation({
    mutationFn: () => unwrap(api.POST('/api/reviews', { body: { name, text, rating } })),
    onSuccess: onDone,
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const next = { rating: rating < 1, name: name.trim().length < 2, text: text.trim().length < 10 };
    setErrors(next);
    if (!Object.values(next).some(Boolean)) submit.mutate();
  };
  const shown = hover || rating;

  return (
    <Reveal className="rv-form-wrap">
      <h2>Залишити свій відгук</h2>
      {submit.error && <p className="rv-field-error">{submit.error instanceof ApiError ? submit.error.message : errorMessage(submit.error)}</p>}
      <form className="rv-form" noValidate onSubmit={onSubmit}>
        <div className="rv-field">
          <label className="rv-label">Оцінка:</label>
          <div className={`rv-star-picker${errors.rating ? ' rv-star-picker--error' : ''}`} onMouseLeave={() => setHover(0)} role="radiogroup" aria-label="Оцінка">
            {[1, 2, 3, 4, 5].map((i) => (
              <span
                key={i}
                role="radio"
                tabIndex={0}
                aria-checked={rating === i}
                aria-label={HINTS[i]}
                className={`rv-star${hover && i <= hover ? ' hovered' : ''}${!hover && i <= rating ? ' selected' : ''}${pop === i ? ' just-selected' : ''}`}
                onMouseOver={() => setHover(i)}
                onClick={() => {
                  setRating(i);
                  setPop(i);
                  window.setTimeout(() => setPop(0), 320);
                  setErrors((er) => ({ ...er, rating: false }));
                }}
                onKeyDown={(e) => e.key === 'Enter' && setRating(i)}
              >
                ★
              </span>
            ))}
          </div>
          <p className="rv-star-hint">{shown ? HINTS[shown] : ' '}</p>
          <p className="rv-field-error" hidden={!errors.rating}>Оберіть оцінку</p>
        </div>
        <div className="rv-field">
          <label className="rv-label" htmlFor="reviewName">Ваше ім'я:</label>
          <input id="reviewName" type="text" className={`rv-input${errors.name ? ' rv-input--error' : ''}`} placeholder="Ваше ім'я (мінімум 2 символи)" autoComplete="name"
            value={name} onChange={(e) => { setName(e.target.value); setErrors((er) => ({ ...er, name: false })); }} />
          <p className="rv-field-error" hidden={!errors.name}>Ім'я занадто коротке</p>
        </div>
        <div className="rv-field">
          <label className="rv-label" htmlFor="reviewText">Відгук:</label>
          <textarea id="reviewText" className={`rv-input rv-textarea${errors.text ? ' rv-input--error' : ''}`} placeholder="Розкажіть що вам сподобалось або що можна покращити... (мінімум 10 символів)"
            value={text} onChange={(e) => { setText(e.target.value); setErrors((er) => ({ ...er, text: false })); }} />
          <p className="rv-field-error" hidden={!errors.text}>Відгук занадто короткий</p>
        </div>
        <button type="submit" className={`rv-submit${submit.isPending ? ' loading' : ''}`} disabled={submit.isPending}>
          Надіслати
        </button>
      </form>
    </Reveal>
  );
}

export default function ReviewsPage() {
  usePageTitle('Відгуки — Coffee Time');
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const client = useQueryClient();
  const { data: session } = useSession();
  const controlsRef = useRef<HTMLElement>(null);
  const [success, setSuccess] = useState(false);

  const sort = params.get('sort') ?? 'newest';
  const filter = Number(params.get('filter') ?? 0);
  const page = Number(params.get('p') ?? 1);

  const reviews = useQuery({
    queryKey: qk.reviews(sort, filter, page),
    queryFn: () => unwrap(api.GET('/api/reviews', { params: { query: { sort, filter, page } } })),
    placeholderData: keepPreviousData,
  });

  // "Залишити відгук" link from the homepage.
  useEffect(() => {
    if (location.hash === '#leave-review' && reviews.data) {
      document.getElementById('leave-review')?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [location.hash, reviews.data]);

  useEffect(() => {
    if (!success) return;
    const t = window.setTimeout(() => setSuccess(false), 4500);
    return () => window.clearTimeout(t);
  }, [success]);

  const update = (patch: Record<string, string | number>) => {
    const next = { sort, filter: String(filter), p: String(page), ...Object.fromEntries(Object.entries(patch).map(([k, v]) => [k, String(v)])) };
    const clean: Record<string, string> = {};
    if (next.sort !== 'newest') clean.sort = next.sort;
    if (next.filter !== '0') clean.filter = next.filter;
    if (next.p !== '1') clean.p = next.p;
    setParams(clean);
    const rect = controlsRef.current?.getBoundingClientRect();
    if (rect && (rect.bottom < 0 || rect.top > window.innerHeight)) controlsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (reviews.isPending) return <PageLoader />;
  if (reviews.error) return <PageError message={errorMessage(reviews.error)} onRetry={() => reviews.refetch()} />;
  const data = reviews.data;

  return (
    <div className="pg-reviews">
      <main className="reviews-page">
        <section className="rv-hero">
          <div className="rv-hero-inner container">
            <h1 className="rv-title">Відгуки наших клієнтів</h1>
            <p className="rv-subtitle">Думки людей, які вже скуштували смак Coffee Time</p>
          </div>
          {data.total_count > 0 && <StatsCard data={data} />}
        </section>

        <section className="rv-controls" ref={controlsRef}>
          <div className="container">
            <div className="rv-controls-inner">
              <div className="rv-ctrl-group">
                <span className="rv-ctrl-label">Сортування</span>
                <div className="rv-tabs">
                  {SORTS.map(([val, label]) => (
                    <button key={val} type="button" className={`rv-tab${sort === val ? ' rv-tab--active' : ''}`} onClick={() => update({ sort: val, p: 1 })}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="rv-ctrl-group">
                <span className="rv-ctrl-label">Рейтинг</span>
                <div className="rv-filter-tabs">
                  <button type="button" className={`rv-tab${filter === 0 ? ' rv-tab--active' : ''}`} onClick={() => update({ filter: 0, p: 1 })}>
                    Всі
                  </button>
                  {[5, 4, 3, 2, 1].map((i) => (
                    <button key={i} type="button" className={`rv-tab${filter === i ? ' rv-tab--active' : ''}`} onClick={() => update({ filter: i, p: 1 })} aria-label={`${i} зірок`}>
                      {'★'.repeat(i)}
                    </button>
                  ))}
                </div>
              </div>
              <a href="https://www.google.com/maps/search/Coffee+Time" target="_blank" rel="noopener noreferrer" className="rv-google-link">
                Google Maps →
              </a>
            </div>
          </div>
        </section>

        <section className="rv-grid-section">
          <div className="container">
            <div className={reviews.isPlaceholderData ? 'loading' : ''} id="rvGridWrap">
              {data.reviews.length === 0 ? (
                <div className="rv-empty">
                  <div className="rv-empty-icon">☕</div>
                  <p>Відгуків не знайдено.</p>
                </div>
              ) : (
                <div className="rv-grid">
                  {data.reviews.map((r, i) => <ReviewCard key={`${data.page}-${i}-${r.name}`} review={r} />)}
                </div>
              )}
              <Pagination page={data.page} total={data.total_pages} onPage={(p) => update({ p })} />
            </div>
          </div>
        </section>

        <section className="rv-form-section" id="leave-review">
          <div className="container">
            {success && <div className="rv-success">✓ Дякуємо! Ваш відгук успішно додано.</div>}
            {!session?.user ? (
              <Reveal className="rv-auth-prompt">
                <div className="rv-auth-icon">☕</div>
                <p className="rv-auth-text">Увійдіть, щоб залишити відгук</p>
                <Link to="/login?next=%2Freviews%23leave-review" className="rv-auth-btn">Увійти</Link>
              </Reveal>
            ) : data.reviewed_already ? (
              !success && (
                <div className="rv-already">
                  <span className="rv-already-icon">✓</span>
                  <p>Ви вже залишили відгук. Дякуємо за вашу думку!</p>
                </div>
              )
            ) : (
              <ReviewForm
                onDone={() => {
                  setSuccess(true);
                  void client.invalidateQueries({ queryKey: ['reviews'] });
                }}
              />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
