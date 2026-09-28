import { useQuery } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { fmtShortDateTime, truncate } from '@/lib/format';
import { useAdminTitle } from '../AdminLayout';
import { BarChart } from '../components/BarChart';
import { PayTag } from '../components/PayTag';
import { adminKeys, useAdminLayout } from '../useAdmin';

type S = components['schemas'];
type StaffStats = S['StaffStats'];
type Category = S['CategoryCount'];
type TopProduct = S['TopProduct'];

const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
const RANK_COLORS = ['#FFC107', '#aaaaaa', '#cd7f32'];
const grn = (v: number) => Math.round(v).toLocaleString('uk-UA');
const todayIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const dateInputStyle = {
  border: '1px solid #e0d6cd',
  borderRadius: 8,
  padding: '5px 10px',
  fontSize: 12,
  color: '#3a2a1a',
  background: '#fff',
  cursor: 'pointer',
  fontFamily: 'inherit',
  outline: 'none',
};

function StatCard({ bg, icon, label, value, compare }: { bg: string; icon: ReactNode; label: string; value: ReactNode; compare: S['StatCompare'] }) {
  return (
    <div className="stat-card">
      <div className="stat-icon-box" style={{ background: bg }}>
        {icon}
      </div>
      <div className="stat-text">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        <span className={`stat-compare stat-compare--${compare.direction}`}>{compare.text}</span>
      </div>
    </div>
  );
}

const statIcon = (stroke: string, children: ReactNode) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round">
    {children}
  </svg>
);

function CategoriesCard({ stats, categories }: { stats: StaffStats; categories: Category[] }) {
  return (
    <div className="shc-cat-card" style={{ gridColumn: '1/-1' }}>
      <div className="shc-cat-header">
        <div className="shc-cat-header__left">
          <div className="shc-icon" style={{ background: '#fff8e6', width: 40, height: 40, borderRadius: 10 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFC107" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
          </div>
          <div>
            <div className="shc-title">Товари по категоріях</div>
            <div className="shc-sub">Всього {stats.products_total ?? 0} позицій</div>
          </div>
        </div>
        <Link to="/admin/manage-items" className="shc-cat-btn">
          Управляти →
        </Link>
      </div>
      <div className="shc-cat-grid">
        {categories.map((c) => (
          <Link key={c.key} to={`/admin/manage-items?category=${c.key}`} className="shc-cat-item">
            <span className="shc-cat-name">{c.label}</span>
            <span className="shc-cat-count">{c.count}</span>
          </Link>
        ))}
        <Link to="/admin/sauces" className="shc-cat-item shc-cat-item--sauces">
          <span className="shc-cat-name">🫙 Соуси</span>
          <span className="shc-cat-count shc-cat-count--sauces">{stats.sauces_total ?? 0}</span>
        </Link>
      </div>
    </div>
  );
}

function ContentCard({ stats }: { stats: StaffStats }) {
  const gt = Math.max(1, stats.gallery_total ?? 1);
  const sTotal = stats.slides_total ?? 0;
  const sActive = stats.slides_active ?? 0;
  const sPct = Math.round((sActive / Math.max(1, sTotal)) * 100);
  const pct = (n: number | null | undefined) => `${Math.round(((n ?? 0) / gt) * 100)}%`;
  return (
    <div className="shc-cat-card">
      <div className="shc-cat-header">
        <div className="shc-cat-header__left">
          <div className="shc-icon" style={{ background: '#e3f2fd', width: 40, height: 40, borderRadius: 10 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2196F3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>
          </div>
          <div>
            <div className="shc-title">Контент сайту</div>
            <div className="shc-sub">Галерея, слайдер та сторінка «Про нас»</div>
          </div>
        </div>
      </div>
      <div className="shc-content-grid">
        <Link to="/admin/gallery" className="shc-content-block">
          <div className="shc-cb-header">
            <div className="shc-icon" style={{ background: '#e3f2fd', width: 36, height: 36, borderRadius: 9, flexShrink: 0 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2196F3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
            </div>
            <div>
              <div className="shc-cb-title">Галерея</div>
              <div className="shc-cb-sub">Фото сайту</div>
            </div>
            <div className="shc-cb-count">{stats.gallery_total ?? 0}</div>
          </div>
          <div className="shc-cb-cats">
            <div className="shc-cb-cat-row">
              <span className="shc-cb-cat-lbl">Їжа</span>
              <div className="shc-cb-bar"><div className="shc-cb-bar-fill" style={{ width: pct(stats.gallery_food), background: '#2196F3' }} /></div>
              <span className="shc-cb-cat-val">{stats.gallery_food ?? 0}</span>
            </div>
            <div className="shc-cb-cat-row">
              <span className="shc-cb-cat-lbl">Інтер'єр</span>
              <div className="shc-cb-bar"><div className="shc-cb-bar-fill" style={{ width: pct(stats.gallery_interior), background: '#90CAF9' }} /></div>
              <span className="shc-cb-cat-val">{stats.gallery_interior ?? 0}</span>
            </div>
          </div>
        </Link>
        <Link to="/admin/hero-slides" className="shc-content-block">
          <div className="shc-cb-header">
            <div className="shc-icon" style={{ background: '#e8f5e9', width: 36, height: 36, borderRadius: 9, flexShrink: 0 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4CAF50" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="10" rx="2" /><path d="M17 7V5a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v2" /><polyline points="9 12 12 15 15 12" /></svg>
            </div>
            <div>
              <div className="shc-cb-title">Хіро слайдер</div>
              <div className="shc-cb-sub">Головний банер</div>
            </div>
            <div className="shc-cb-count">{sTotal}</div>
          </div>
          <div className="shc-cb-cats">
            <div className="shc-cb-cat-row">
              <span className="shc-cb-cat-lbl">Активних</span>
              <div className="shc-cb-bar"><div className="shc-cb-bar-fill" style={{ width: `${sPct}%`, background: '#4CAF50' }} /></div>
              <span className="shc-cb-cat-val">
                {sActive} / {sTotal}
              </span>
            </div>
            <div style={{ marginTop: 10 }}>
              {Array.from({ length: sTotal }, (_, i) => (
                <span key={i} className={`shc-slide-dot${i < sActive ? ' shc-slide-dot--on' : ''}`} />
              ))}
              {!sTotal && <span style={{ fontSize: 12, color: '#bbb' }}>Слайди відсутні</span>}
            </div>
          </div>
        </Link>
        <Link to="/admin/about-section" className="shc-content-block">
          <div className="shc-cb-header">
            <div className="shc-icon" style={{ background: '#f3e5f5', width: 36, height: 36, borderRadius: 9, flexShrink: 0 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9C27B0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
            </div>
            <div>
              <div className="shc-cb-title">Про нас</div>
              <div className="shc-cb-sub">Секція на сайті</div>
            </div>
            <div className={`shc-cb-status ${stats.about_title ? 'shc-cb-status--ok' : 'shc-cb-status--warn'}`}>{stats.about_title ? '✓ Налаштовано' : '! Не заповнено'}</div>
          </div>
          {stats.about_title && (
            <div className="shc-cb-about-preview">
              <div className="shc-cb-about-title">{stats.about_title}</div>
              {stats.about_text && <div className="shc-cb-about-text">{truncate(stats.about_text, 90)}</div>}
            </div>
          )}
        </Link>
      </div>
    </div>
  );
}

function TopList({ products, empty, animate }: { products: TopProduct[]; empty: string; animate: boolean }) {
  if (!products.length) return <li style={{ color: '#bbb', fontSize: 13, padding: '16px 0', listStyle: 'none' }}>{empty}</li>;
  return (
    <>
      {products.map((p, i) => (
        <li
          key={`${p.name}-${i}`}
          className="top-item"
          style={{ ...(animate ? { animation: `rowFadeIn .25s ease ${i * 0.05}s both` } : {}), ...(p.deleted ? { opacity: 0.55 } : {}) }}
        >
          <span className="top-rank" style={{ color: RANK_COLORS[i] ?? '#ccc' }}>
            {i + 1}
          </span>
          {p.image ? (
            <img src={p.image} className="top-thumb" alt="" style={{ objectFit: 'cover', borderRadius: 8 }} />
          ) : (
            <div className="top-thumb top-thumb--letter">{(p.name || '?').charAt(0).toUpperCase()}</div>
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="top-name" style={p.deleted ? { color: '#aaa', fontStyle: 'italic' } : undefined}>
              {p.name}
            </div>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 1 }}>
              {p.orders_count} замовлень · {p.unit_price} грн/шт
            </div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div className="top-sold">{p.sold} шт</div>
            <div style={{ fontSize: 11, color: '#aaa' }}>{grn(p.total_revenue)} грн</div>
          </div>
        </li>
      ))}
    </>
  );
}

type Period = 'all' | 'month' | 'week' | 'custom';

function TopProducts({ initial }: { initial: TopProduct[] }) {
  const [period, setPeriod] = useState<Period>('all');
  const [range, setRange] = useState({ from: '', to: '' });
  const [applied, setApplied] = useState<{ from: string; to: string } | null>(null);
  const today = todayIso();

  const params = period === 'custom' ? (applied ? { period, date_from: applied.from, date_to: applied.to } : null) : period === 'all' ? null : { period };
  const q = useQuery({
    queryKey: ['admin', 'top-products', params],
    queryFn: () => unwrap(api.GET('/api/admin/dashboard/top-products', { params: { query: params! } })),
    enabled: params !== null,
    placeholderData: (prev) => prev,
  });
  const products = params === null ? initial : (q.data?.products ?? initial);
  const loading = params !== null && q.isFetching;

  return (
    <div className="dash-section dash-section--narrow">
      <div className="section-head" style={{ alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
        <h2 className="section-title">Топ товарів</h2>
        <div className="top-filter-tabs">
          {(
            [
              ['all', 'Весь час'],
              ['month', 'Місяць'],
              ['week', 'Тиждень'],
              ['custom', 'Власний'],
            ] as const
          ).map(([key, label]) => (
            <button key={key} className={`top-ftab${period === key ? ' active' : ''}`} onClick={() => setPeriod(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {period === 'custom' && (
        <div style={{ display: 'flex', padding: '10px 0 4px', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="date" aria-label="Від" value={range.from} max={range.to || today} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} style={{ ...dateInputStyle, fontSize: 13, width: 140 }} />
          <span style={{ color: '#aaa', fontSize: 13 }}>—</span>
          <input type="date" aria-label="До" value={range.to} min={range.from || undefined} max={today} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} style={{ ...dateInputStyle, fontSize: 13, width: 140 }} />
          <button
            onClick={() => range.from && range.to && setApplied({ ...range })}
            style={{ padding: '6px 14px', background: '#6b3a1f', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
          >
            Застосувати
          </button>
        </div>
      )}
      <ul className="top-list" style={{ opacity: loading ? 0.45 : 1, pointerEvents: loading ? 'none' : 'auto' }}>
        <TopList products={products} empty={params === null ? 'Даних поки немає' : 'Даних за цей період немає'} animate={params !== null} />
      </ul>
    </div>
  );
}

type ChartMode = 'today' | 'week' | 'month' | 'day';

function OrdersChart({ full }: { full: S['FullDashboard'] }) {
  const [mode, setMode] = useState<ChartMode>('today');
  const [day, setDay] = useState(full.today_iso);
  const dayQ = useQuery({
    queryKey: ['admin', 'chart-data', day],
    queryFn: () => unwrap(api.GET('/api/admin/dashboard/chart-data', { params: { query: { date: day } } })),
    enabled: mode === 'day' && !!day,
    staleTime: 60_000,
  });

  let labels = HOUR_LABELS;
  let values = full.hours_data;
  if (mode === 'week') [labels, values] = [full.week_labels, full.week_data];
  else if (mode === 'month') [labels, values] = [full.month_labels, full.month_data];
  else if (mode === 'day' && dayQ.data?.success) values = dayQ.data.data;

  return (
    <div className="dash-section">
      <div className="section-head">
        <h2 className="section-title">Графік замовлень</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <div className="chart-tabs">
            {(
              [
                ['today', 'Сьогодні'],
                ['week', 'Тиждень'],
                ['month', 'Місяць'],
                ['day', 'День'],
              ] as const
            ).map(([key, label]) => (
              <button key={key} className={`chart-tab${mode === key ? ' active' : ''}`} onClick={() => setMode(key)}>
                {label}
              </button>
            ))}
          </div>
          {mode === 'day' && (
            <input type="date" aria-label="День" value={day} max={full.today_iso} onChange={(e) => e.target.value && setDay(e.target.value)} style={{ ...dateInputStyle, width: 140 }} />
          )}
        </div>
      </div>
      <BarChart labels={labels} values={values} />
    </div>
  );
}

function FullDashboard({ data }: { data: S['DashboardResponse'] & { full: S['FullDashboard'] } }) {
  const f = data.full;
  const stats = data.staff_stats;
  return (
    <>
      <div className={`stats-grid ${f.show_reviews_stat ? 'stats-grid--five' : 'stats-grid--four'}`}>
        <StatCard bg="#fff8e6" icon={statIcon('#FFC107', <><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></>)} label="Замовлення сьогодні" value={f.today_orders} compare={f.compare.orders} />
        <StatCard bg="#e8f5e9" icon={statIcon('#4CAF50', <><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>)} label="Виручка сьогодні" value={`${grn(f.today_revenue)} ₴`} compare={f.compare.revenue} />
        <StatCard bg="#f3e5f5" icon={statIcon('#9C27B0', <><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>)} label="Середній чек" value={f.avg_check > 0 ? `${f.avg_check} ₴` : '—'} compare={f.compare.avg_check} />
        <StatCard bg="#e3f2fd" icon={statIcon('#2196F3', <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>)} label="Клієнтів усього" value={f.total_clients} compare={f.compare.clients} />
        {f.show_reviews_stat && (
          <StatCard bg="#fce4ec" icon={statIcon('#E91E63', <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />)} label="Відгуки за тиждень" value={f.week_reviews} compare={f.compare.reviews} />
        )}
      </div>

      <div className="dashboard-grid">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <OrdersChart full={f} />

          <div className="dash-section">
            <div className="section-head">
              <h2 className="section-title">Останні замовлення</h2>
              <Link to="/admin/orders" className="btn-ghost btn-sm">
                Всі →
              </Link>
            </div>
            <div className="table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Клієнт</th>
                    <th>Телефон</th>
                    <th>Оплата</th>
                    <th>Сума</th>
                    <th>Статус</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {f.recent_orders.length ? (
                    f.recent_orders.map((o) => (
                      <tr key={o.order_id}>
                        <td>
                          <Link to={`/admin/orders/${o.order_id}`} style={{ fontWeight: 700, color: '#8B4513', textDecoration: 'none' }}>
                            #{o.order_id}
                          </Link>
                        </td>
                        <td>{o.full_name}</td>
                        <td style={{ color: '#666', fontSize: 12 }}>{o.phone}</td>
                        <td>
                          <PayTag badge={o.pay_badge} />
                        </td>
                        <td>
                          <strong>{grn(o.total)} ₴</strong>
                        </td>
                        <td>
                          <span className={`order-status-badge ${o.status_class}`}>{o.status_label}</span>
                        </td>
                        <td style={{ color: '#999', fontSize: 12 }}>{fmtShortDateTime(o.created_at)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', color: '#bbb', padding: 32 }}>
                        Замовлень ще немає
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <TopProducts initial={f.top_products} />
      </div>

      {data.categories.length > 0 && (
        <div style={{ marginTop: 18 }}>
          <CategoriesCard stats={stats} categories={data.categories} />
        </div>
      )}
      {stats.gallery_total != null && (
        <div style={{ marginTop: 14 }}>
          <ContentCard stats={stats} />
        </div>
      )}
    </>
  );
}

function StaffDashboard({ data }: { data: S['DashboardResponse'] }) {
  const layout = useAdminLayout().data;
  const s = data.staff_stats;
  const cats = data.categories;
  return (
    <>
      <div className="sh-welcome">
        <div className="sh-welcome__left">
          <div className="sh-welcome__avatar">{layout?.initial}</div>
          <div>
            <div className="sh-welcome__name">Вітаємо, {layout?.display_name}!</div>
            <div className="sh-welcome__role">{data.role_label}</div>
          </div>
        </div>
        <div className="sh-welcome__date">
          {data.today_str}, {data.weekday}
        </div>
      </div>

      <div className="sh-stats-row">
        {s.products_total != null && (
          <>
            <div className="sh-stat"><div className="sh-stat__val">{s.products_total}</div><div className="sh-stat__lbl">Товарів всього</div><div className="sh-stat__sub">у всіх категоріях</div></div>
            <div className="sh-stat"><div className="sh-stat__val">{cats.length}</div><div className="sh-stat__lbl">Категорій</div><div className="sh-stat__sub">в меню</div></div>
            <div className="sh-stat"><div className="sh-stat__val">{s.sauces_total ?? 0}</div><div className="sh-stat__lbl">Соусів</div><div className="sh-stat__sub">додаткові інгредієнти</div></div>
          </>
        )}
        {s.reviews_total != null && (
          <div className="sh-stat"><div className="sh-stat__val">{s.reviews_total}</div><div className="sh-stat__lbl">Відгуків всього</div><div className="sh-stat__sub">{s.reviews_week ?? 0} за тиждень</div></div>
        )}
        {s.gallery_total != null && (
          <div className="sh-stat"><div className="sh-stat__val">{s.gallery_total}</div><div className="sh-stat__lbl">Фото в галереї</div><div className="sh-stat__sub">{s.gallery_food ?? 0} їжа · {s.gallery_interior ?? 0} інтер'єр</div></div>
        )}
        {s.slides_total != null && (
          <div className="sh-stat">
            <div className="sh-stat__val">
              {s.slides_active}
              <span style={{ fontSize: 14, fontWeight: 500, color: '#aaa' }}> / {s.slides_total}</span>
            </div>
            <div className="sh-stat__lbl">Слайдів активних</div>
            <div className="sh-stat__sub">з {s.slides_total} всього</div>
          </div>
        )}
      </div>

      <div className="sh-section-title">Швидкий перехід</div>
      <div className="staff-home-grid">
        {cats.length > 0 && (
          <>
            <CategoriesCard stats={s} categories={cats} />
            <Link to="/admin/sauces" className="staff-home-card">
              <div className="shc-icon" style={{ background: '#fef3e2' }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#e6851a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" /><path d="M8 12s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></svg>
              </div>
              <div>
                <div className="shc-title">Соуси</div>
                <div className="shc-sub">Додаткові інгредієнти до страв</div>
              </div>
              <div className="shc-badge">{s.sauces_total ?? 0} шт</div>
            </Link>
          </>
        )}
        {s.reviews_total != null && (
          <Link to="/admin/reviews" className="staff-home-card">
            <div className="shc-icon" style={{ background: '#fce4ec' }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#E91E63" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
            </div>
            <div>
              <div className="shc-title">Відгуки</div>
              <div className="shc-sub">Модерація відгуків клієнтів</div>
            </div>
            {(s.reviews_week ?? 0) > 0 && <div className="shc-badge shc-badge--new">{s.reviews_week} нових</div>}
          </Link>
        )}
        {s.gallery_total != null && <ContentCard stats={s} />}
      </div>
    </>
  );
}

export default function DashboardPage() {
  useAdminTitle('Головна');
  const q = useQuery({ queryKey: adminKeys.dashboard, queryFn: () => unwrap(api.GET('/api/admin/dashboard')) });
  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const data = q.data;
  if (data.mode === 'full' && data.full) return <FullDashboard data={{ ...data, full: data.full }} />;
  return <StaffDashboard data={data} />;
}
