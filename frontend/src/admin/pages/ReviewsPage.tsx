import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type CSSProperties, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { fmtDate, fmtDateTime, truncate } from '@/lib/format';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { Pagination } from '../components/Pagination';
import { adminKeys } from '../useAdmin';

type Review = components['schemas']['AdminReview'];
type Status = Review['status'];

const tabStyle = (active: boolean): CSSProperties => ({
  padding: '9px 20px',
  borderRadius: 10,
  fontSize: 13,
  fontWeight: 700,
  textDecoration: 'none',
  transition: 'all .2s',
  border: 'none',
  cursor: 'pointer',
  fontFamily: 'inherit',
  ...(active ? { background: '#8B4513', color: '#fff', boxShadow: '0 2px 8px rgba(139,69,19,.25)' } : { background: '#f5f0ea', color: '#8B6040' }),
});

function Stat({ bg, icon, label, value }: { bg: string; icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="stat-card">
      <div className="stat-icon-box" style={{ background: bg }}>
        {icon}
      </div>
      <div className="stat-text">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
      </div>
    </div>
  );
}

const StarIcon = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#E91E63" strokeWidth="2" strokeLinecap="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
);
const CheckIcon = (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" strokeWidth="2" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
);

const Stars = ({ n, size }: { n: number; size?: number }) => (
  <span style={{ letterSpacing: 1, fontSize: size }}>
    <span style={{ color: '#FFC107' }}>{'★'.repeat(n)}</span>
    <span style={{ color: '#ddd' }}>{'★'.repeat(5 - n)}</span>
  </span>
);

function OrderRatings({ page, setPage }: { page: number; setPage: (p: number) => void }) {
  const q = useQuery({
    queryKey: adminKeys.orderRatings(page),
    queryFn: () => unwrap(api.GET('/api/admin/reviews/order-ratings', { params: { query: { page } } })),
    placeholderData: keepPreviousData,
  });
  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const d = q.data;
  return (
    <>
      <div className="stats-grid stats-grid--three" style={{ marginBottom: 20 }}>
        <Stat bg="#fce4ec" icon={StarIcon} label="Середній рейтинг" value={d.avg.toFixed(1)} />
        <Stat
          bg="#e3f2fd"
          icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2196F3" strokeWidth="2" strokeLinecap="round"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="1" /></svg>}
          label="Оцінок всього"
          value={d.total}
        />
        <Stat bg="#e8f5e9" icon={CheckIcon} label="За цей тиждень" value={d.week} />
      </div>
      <div className="table-wrap" style={{ opacity: q.isPlaceholderData ? 0.5 : 1 }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Замовлення</th>
              <th>Клієнт</th>
              <th>Оцінка</th>
              <th className="col-hide-mobile">Дата</th>
            </tr>
          </thead>
          <tbody>
            {d.order_ratings.map((r) => (
              <tr key={`${r.order_id}-${r.created_at}`}>
                <td>
                  <Link to={`/admin/orders/${r.order_id}`} style={{ color: '#8B4513', fontWeight: 700, textDecoration: 'none' }}>
                    #{r.order_id}
                  </Link>
                </td>
                <td style={{ fontSize: 13 }}>
                  {r.uname}
                  {r.email && <div style={{ fontSize: 11, color: '#aaa' }}>{r.email}</div>}
                </td>
                <td>
                  <Stars n={r.rating} size={15} />
                </td>
                <td className="col-hide-mobile" style={{ fontSize: 12, color: '#999', whiteSpace: 'nowrap' }}>
                  {fmtDateTime(r.created_at, ' ')}
                </td>
              </tr>
            ))}
            {!d.order_ratings.length && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#bbb', padding: 32 }}>
                  Оцінок ще немає
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Pagination page={d.page} totalPages={d.total_pages} onPage={setPage} />
    </>
  );
}

const STATUS_BADGE: Record<Status, [string, string]> = {
  approved: ['badge-ready', 'Схвалено'],
  declined: ['badge-cancelled', 'Відхилено'],
  pending: ['badge-new', 'На модерації'],
};

function SiteReviews({ rating, status, page, update }: { rating: number; status: string; page: number; update: (u: Record<string, string>) => void }) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const params = { rating, status, page };
  const [removing, setRemoving] = useState<Set<number>>(new Set());
  const q = useQuery({
    queryKey: adminKeys.reviews(params),
    queryFn: () => unwrap(api.GET('/api/admin/reviews', { params: { query: params } })),
    placeholderData: keepPreviousData,
  });

  const refresh = () => {
    client.invalidateQueries({ queryKey: ['admin', 'reviews'] });
    client.invalidateQueries({ queryKey: adminKeys.layout });
    client.invalidateQueries({ queryKey: adminKeys.dashboard });
    client.invalidateQueries({ queryKey: ['reviews'] });
  };

  const setStatus = useMutation({
    mutationFn: ({ id, status: s }: { id: number; status: Status }) => unwrap(api.PATCH('/api/admin/reviews/{review_id}', { params: { path: { review_id: id } }, body: { status: s } })),
    onSuccess: (_, { status: s }) => {
      toast(s === 'approved' ? 'Відгук схвалено' : 'Відгук відхилено', 'success');
      refresh();
    },
    onError: (err) => toast(errorMessage(err) || 'Помилка запиту', 'error'),
  });

  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/reviews/{review_id}', { params: { path: { review_id: id } } })),
    onMutate: (id) => setRemoving((s) => new Set(s).add(id)),
    onSuccess: () => {
      toast('Відгук видалено', 'success');
      window.setTimeout(refresh, 350);
    },
    onError: (err, id) => {
      setRemoving((s) => {
        const n = new Set(s);
        n.delete(id);
        return n;
      });
      toast(errorMessage(err) || 'Помилка запиту', 'error');
    },
  });

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const d = q.data;
  const dist = Object.fromEntries(d.rating_dist.map((r) => [r.stars, r.count]));

  return (
    <>
      <div className="stats-grid stats-grid--three">
        <Stat bg="#fce4ec" icon={StarIcon} label="Середній рейтинг" value={d.avg_rating.toFixed(1)} />
        <Stat
          bg="#e3f2fd"
          icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2196F3" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>}
          label="Всього відгуків"
          value={d.total_count}
        />
        <Stat bg="#e8f5e9" icon={CheckIcon} label="За цей тиждень" value={d.this_week} />
      </div>

      <div className="dash-section" style={{ marginBottom: 20 }}>
        <h3 className="section-title" style={{ marginBottom: 14 }}>
          Розподіл оцінок
        </h3>
        <div className="rating-dist">
          {[5, 4, 3, 2, 1].map((s) => {
            const cnt = dist[s] ?? 0;
            const pct = d.total_count > 0 ? Math.round((cnt / d.total_count) * 100) : 0;
            return (
              <div key={s} className="rating-dist-row">
                <span className="rating-star-label">{s}★</span>
                <div className="rating-bar-bg">
                  <div className="rating-bar-fill" style={{ width: `${pct}%` }} />
                </div>
                <span className="rating-bar-count">{cnt}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="orders-toolbar">
        <div className="toolbar-chips">
          <div className="chip-group">
            {(
              [
                [0, 'Всі оцінки'],
                [5, '★★★★★'],
                [4, '★★★★'],
                [3, '★★★'],
                [2, '★★'],
                [1, '★'],
              ] as const
            ).map(([val, lbl]) => (
              <button key={val} type="button" className={`fchip${rating === val ? ' fchip--on' : ''}`} onClick={() => update({ rating: val ? String(val) : '', page: '' })}>
                {lbl}
              </button>
            ))}
          </div>
          <span className="chip-sep" />
          <div className="chip-group">
            {(
              [
                ['', 'Всі статуси'],
                ['approved', 'Схвалені'],
                ['pending', 'Очікують'],
                ['declined', 'Відхилені'],
              ] as const
            ).map(([val, lbl]) => (
              <button key={val} type="button" className={`fchip${status === val ? ' fchip--on' : ''}`} onClick={() => update({ status: val, page: '' })}>
                {lbl}
              </button>
            ))}
          </div>
          {(rating > 0 || status) && (
            <button type="button" className="fchip fchip--reset" onClick={() => update({ rating: '', status: '', page: '' })}>
              ✕ Скинути
            </button>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#bbb', whiteSpace: 'nowrap', alignSelf: 'center' }}>
            Знайдено: <strong>{d.total_rows}</strong>
          </span>
        </div>
      </div>

      <div className="table-wrap" style={{ opacity: q.isPlaceholderData ? 0.5 : 1 }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Автор</th>
              <th>Оцінка</th>
              <th>Текст</th>
              <th>Дата</th>
              <th>Статус</th>
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            {d.reviews.map((rv) => {
              const [badge, label] = STATUS_BADGE[rv.status];
              return (
                <tr key={rv.id} style={removing.has(rv.id) ? { animation: 'rowDelete .35s ease forwards' } : undefined}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="review-avatar" style={{ background: rv.color, width: 34, height: 34, fontSize: 13, flexShrink: 0 }}>
                        {rv.initial}
                      </div>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{rv.author}</span>
                    </div>
                  </td>
                  <td>
                    <Stars n={rv.rating} />
                  </td>
                  <td style={{ maxWidth: 280, fontSize: 13, color: '#555' }} title={rv.text}>
                    {truncate(rv.text, 100)}
                  </td>
                  <td style={{ fontSize: 12, color: '#999' }}>{fmtDate(rv.created_at)}</td>
                  <td>
                    <span className={`order-badge ${badge}`}>{label}</span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {rv.status !== 'approved' && (
                        <button className="rv-btn-approve" disabled={setStatus.isPending} onClick={() => setStatus.mutate({ id: rv.id, status: 'approved' })}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                          Схвалити
                        </button>
                      )}
                      {rv.status !== 'declined' && (
                        <button className="rv-btn-decline" disabled={setStatus.isPending} onClick={() => setStatus.mutate({ id: rv.id, status: 'declined' })}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                          Відхилити
                        </button>
                      )}
                      <button className="rv-btn-delete" onClick={() => window.confirm('Видалити цей відгук?') && remove.mutate(rv.id)}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
                        Видалити
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {!d.reviews.length && (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: '#bbb', padding: 32 }}>
                  Відгуків не знайдено
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={d.page} totalPages={d.total_pages} onPage={(p) => update({ page: p > 1 ? String(p) : '' })} />
    </>
  );
}

export default function ReviewsPage() {
  useAdminTitle('Відгуки');
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'order_ratings' ? 'order_ratings' : 'site_reviews';
  const page = Math.max(1, Number(params.get('page')) || 1);

  const update = (u: Record<string, string>) => {
    const next = new URLSearchParams(params);
    Object.entries(u).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    setParams(next);
  };

  return (
    <>
      <div style={{ display: 'flex', gap: 6, marginBottom: 22 }}>
        <button type="button" style={tabStyle(tab === 'site_reviews')} onClick={() => setParams({})}>
          Відгуки сайту
        </button>
        <button type="button" style={tabStyle(tab === 'order_ratings')} onClick={() => setParams({ tab: 'order_ratings' })}>
          Оцінки замовлень
        </button>
      </div>
      {tab === 'order_ratings' ? (
        <OrderRatings page={page} setPage={(p) => update({ page: p > 1 ? String(p) : '' })} />
      ) : (
        <SiteReviews rating={Number(params.get('rating')) || 0} status={params.get('status') ?? ''} page={page} update={update} />
      )}
    </>
  );
}
