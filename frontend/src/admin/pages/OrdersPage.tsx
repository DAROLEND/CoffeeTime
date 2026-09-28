import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fragment, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { PageError, PageLoader } from '@/components/Spinner';
import { fmtDateTime } from '@/lib/format';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { ConfirmPopup } from '../components/ConfirmPopup';
import { OrderDetails } from '../components/OrderDetails';
import { Pagination } from '../components/Pagination';
import { PayTag } from '../components/PayTag';
import { adminKeys } from '../useAdmin';

const FILTER_KEYS = ['status', 'payment', 'method', 'type', 'search', 'date_from', 'date_to', 'time_from', 'time_to'] as const;
type FilterKey = (typeof FILTER_KEYS)[number];
type Filters = Record<FilterKey, string>;

const grn = (v: number) => Math.round(v).toLocaleString('uk-UA');
const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const daysAgo = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return isoDay(d);
};

const RANGES = [
  ['today', 'Сьогодні'],
  ['yesterday', 'Вчора'],
  ['week', 'Тиждень'],
  ['month', 'Місяць'],
  ['all', 'Весь час'],
] as const;

function rangeDates(range: (typeof RANGES)[number][0]): [string, string] {
  const today = isoDay(new Date());
  switch (range) {
    case 'today':
      return [today, today];
    case 'yesterday':
      return [daysAgo(1), daysAgo(1)];
    case 'week':
      return [daysAgo(6), today];
    case 'month':
      return [daysAgo(29), today];
    default:
      return ['', ''];
  }
}

function activeRange(from: string, to: string) {
  return RANGES.find(([key]) => {
    const [f, t] = rangeDates(key);
    return f === from && t === to;
  })?.[0];
}

const BULK_LABELS: Record<string, string> = { processing: 'В обробку', done: 'Виконано', cancelled: 'Скасовано' };

export default function OrdersPage() {
  useAdminTitle('Замовлення');
  const toast = useAdminToast();
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ''])) as Filters;
  const page = Math.max(1, Number(params.get('page')) || 1);
  const queryParams = useMemo(() => {
    const q: Record<string, string> = {};
    FILTER_KEYS.forEach((k) => filters[k] && (q[k] = filters[k]));
    if (page > 1) q.page = String(page);
    return q;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  // The search form is a draft until "Знайти" is pressed.
  const [draft, setDraft] = useState(filters);
  useEffect(() => setDraft(filters), [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const q = useQuery({
    queryKey: adminKeys.orders(queryParams),
    queryFn: () => unwrap(api.GET('/api/admin/orders', { params: { query: { ...queryParams, page } } })),
    placeholderData: keepPreviousData,
  });

  const [expanded, setExpanded] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [overrides, setOverrides] = useState<Record<number, { status: string; next: string[] }>>({});
  const [deleting, setDeleting] = useState<{ id: number; anchor: HTMLElement } | null>(null);
  const [removed, setRemoved] = useState<Set<number>>(new Set());

  // A new result set resets the per-row UI state.
  useEffect(() => {
    setSelected(new Set());
    setOverrides({});
    setRemoved(new Set());
  }, [q.data]);

  const refreshCounts = (newCount?: number) => {
    if (newCount !== undefined) client.setQueryData(adminKeys.newCount, { count: newCount });
    client.invalidateQueries({ queryKey: adminKeys.layout });
    client.invalidateQueries({ queryKey: adminKeys.dashboard });
  };

  const apply = (updates: Partial<Filters>, keepPage = false) => {
    const next = new URLSearchParams();
    const merged = { ...filters, ...updates };
    FILTER_KEYS.forEach((k) => merged[k] && next.set(k, merged[k]));
    if (keepPage && page > 1) next.set('page', String(page));
    setParams(next);
  };

  const setPage = (p: number) => {
    const next = new URLSearchParams(params);
    if (p > 1) next.set('page', String(p));
    else next.delete('page');
    setParams(next);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      unwrap(api.POST('/api/admin/orders/{order_id}/status', { params: { path: { order_id: id } }, body: { status } })),
  });

  const changeStatus = (id: number, status: string) => {
    const label = q.data?.status_labels[status] ?? status;
    if (!window.confirm(`Змінити статус на «${label}»?`)) return;
    statusMut.mutate(
      { id, status },
      {
        onSuccess: (res) => {
          if (!res.success) return toast(res.error || 'Помилка оновлення', 'error');
          setOverrides((o) => ({ ...o, [id]: { status: res.new_status ?? status, next: res.next_allowed } }));
          toast(`Статус: ${label}`, 'success');
          refreshCounts(res.new_count);
          client.invalidateQueries({ queryKey: adminKeys.order(id) });
        },
        onError: (err) => toast(errorMessage(err), 'error'),
      },
    );
  };

  const deleteMut = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/orders/{order_id}', { params: { path: { order_id: id } } })),
  });

  const confirmDelete = () => {
    if (!deleting) return;
    const id = deleting.id;
    deleteMut.mutate(id, {
      onSuccess: (res) => {
        setDeleting(null);
        if (!res.success) return toast('Помилка видалення', 'error');
        setRemoved((s) => new Set(s).add(id));
        toast(`Замовлення #${id} видалено`, 'success');
        refreshCounts();
        window.setTimeout(() => client.invalidateQueries({ queryKey: ['admin', 'orders'] }), 380);
      },
      onError: (err) => {
        setDeleting(null);
        toast(errorMessage(err), 'error');
      },
    });
  };

  const bulkStatus = async (status: string) => {
    const ids = [...selected];
    if (!ids.length) return;
    if (!window.confirm(`Змінити статус ${ids.length} замовлень → «${BULK_LABELS[status] ?? status}»?`)) return;
    try {
      const res = await unwrap(api.POST('/api/admin/orders/bulk-status', { body: { order_ids: ids, status } }));
      if (res.updated > 0) toast(`Оновлено: ${res.updated}${res.skipped ? `, пропущено: ${res.skipped}` : ''}`, 'success');
      else toast('Жодне замовлення не оновлено (недозволені переходи)', 'error');
      refreshCounts(res.new_count);
      client.invalidateQueries({ queryKey: ['admin', 'orders'] });
    } catch (err) {
      toast(errorMessage(err), 'error');
    }
  };

  const bulkDelete = async () => {
    const ids = [...selected];
    if (!ids.length || !window.confirm(`Видалити ${ids.length} замовлень назавжди?`)) return;
    const results = await Promise.allSettled(ids.map((id) => unwrap(api.DELETE('/api/admin/orders/{order_id}', { params: { path: { order_id: id } } }))));
    const ok = results.filter((r) => r.status === 'fulfilled' && r.value.success).length;
    toast(`Видалено: ${ok} з ${ids.length}`, ok > 0 ? 'success' : 'error');
    refreshCounts();
    client.invalidateQueries({ queryKey: ['admin', 'orders'] });
  };

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    apply({ search: draft.search, status: draft.status, date_from: draft.date_from, date_to: draft.date_to, time_from: draft.time_from, time_to: draft.time_to });
  };

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;

  const data = q.data;
  const counts = data.counts;
  const orders = data.orders;
  const anyFilter = FILTER_KEYS.some((k) => filters[k]);
  const range = activeRange(filters.date_from, filters.date_to);
  const allChecked = orders.length > 0 && orders.every((o) => selected.has(o.order_id));
  const someChecked = selected.size > 0 && !allChecked;
  const statusCount = (st: string) => (counts as Record<string, number>)[st] ?? 0;
  const hasTime = !!(filters.time_from || filters.time_to);

  return (
    <>
      <div className="orders-toolbar">
        <div className="toolbar-chips">
          <div className="chip-group">
            {(
              [
                ['', 'Всі', counts.all],
                ['paid', 'Оплачені', counts.paid],
                ['unpaid', 'Не оплачені', counts.unpaid],
                ['cash', 'Готівка', counts.cash],
              ] as const
            ).map(([val, lbl, cnt]) => (
              <button key={val} type="button" className={`fchip${filters.payment === val ? ' fchip--on' : ''}`} onClick={() => apply({ payment: val })}>
                {lbl}
                {cnt > 0 && <span className="fchip-cnt">{cnt}</span>}
              </button>
            ))}
          </div>
          <span className="chip-sep" />
          <div className="chip-group">
            {(
              [
                ['cash', 'Готівка'],
                ['liqpay', 'Картка онлайн'],
              ] as const
            ).map(([val, lbl]) => (
              <button key={val} type="button" className={`fchip${filters.method === val ? ' fchip--on' : ''}`} onClick={() => apply({ method: filters.method === val ? '' : val })}>
                {lbl}
              </button>
            ))}
          </div>
          <span className="chip-sep" />
          <div className="chip-group">
            {(
              [
                ['takeout', 'З собою'],
                ['hall', 'В залі'],
              ] as const
            ).map(([val, lbl]) => (
              <button key={val} type="button" className={`fchip${filters.type === val ? ' fchip--on' : ''}`} onClick={() => apply({ type: filters.type === val ? '' : val })}>
                {lbl}
              </button>
            ))}
          </div>
          {anyFilter && (
            <button type="button" className="fchip fchip--reset" onClick={() => setParams(new URLSearchParams())}>
              ✕ Скинути
            </button>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#bbb', whiteSpace: 'nowrap', alignSelf: 'center' }}>{data.total} замовлень</span>
        </div>

        <form className="toolbar-search" onSubmit={onSearch}>
          <div className="ts-search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#bbb" strokeWidth="2.2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            <input type="text" placeholder="Ім'я, телефон або #ID" value={draft.search} onChange={(e) => setDraft((d) => ({ ...d, search: e.target.value }))} aria-label="Пошук" />
          </div>
          <select className="ts-select" value={draft.status} onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value }))} aria-label="Статус">
            <option value="">Всі статуси</option>
            {Object.entries(data.status_labels).map(([st, lbl]) => (
              <option key={st} value={st}>
                {lbl}
                {statusCount(st) > 0 ? ` (${statusCount(st)})` : ''}
              </option>
            ))}
          </select>
          <div className={`ts-date-group${filters.date_from || filters.date_to ? ' ts-date-group--active' : ''}`}>
            {RANGES.map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`fchip fchip--sm${range === key ? ' fchip--on' : ''}`}
                onClick={() => {
                  const [from, to] = rangeDates(key);
                  apply({ date_from: from, date_to: to });
                }}
              >
                {label}
              </button>
            ))}
            <input type="date" className="ts-date-input" aria-label="Від" value={draft.date_from} max={draft.date_to || undefined} onChange={(e) => setDraft((d) => ({ ...d, date_from: e.target.value }))} />
            <span className="ts-sep">—</span>
            <input type="date" className="ts-date-input" aria-label="До" value={draft.date_to} min={draft.date_from || undefined} onChange={(e) => setDraft((d) => ({ ...d, date_to: e.target.value }))} />
            {(filters.date_from || filters.date_to) && (
              <button type="button" className="ts-time-clear" title="Скинути фільтр дат" onClick={() => apply({ date_from: '', date_to: '' })}>
                ✕
              </button>
            )}
          </div>
          <div className={`ts-time-group${hasTime ? ' ts-time-group--active' : ''}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={hasTime ? '#FFC107' : '#bbb'} strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
            <select className="ts-time-select" aria-label="З години" value={draft.time_from} onChange={(e) => setDraft((d) => ({ ...d, time_from: e.target.value }))}>
              <option value="">00</option>
              {Array.from({ length: 23 }, (_, i) => i + 1).map((h) => (
                <option key={h} value={String(h)}>
                  {String(h).padStart(2, '0')}
                </option>
              ))}
            </select>
            <span className="ts-sep">—</span>
            <select className="ts-time-select" aria-label="До години" value={draft.time_to} onChange={(e) => setDraft((d) => ({ ...d, time_to: e.target.value }))}>
              <option value="">23</option>
              {Array.from({ length: 23 }, (_, h) => h).map((h) => (
                <option key={h} value={String(h)}>
                  {String(h).padStart(2, '0')}
                </option>
              ))}
            </select>
            {hasTime && (
              <button type="button" className="ts-time-clear" title="Скинути фільтр годин" onClick={() => apply({ time_from: '', time_to: '' })}>
                ✕
              </button>
            )}
          </div>
          <button type="submit" className="ts-submit">
            Знайти
          </button>
        </form>
      </div>

      <div style={{ opacity: q.isPlaceholderData ? 0.45 : 1, pointerEvents: q.isPlaceholderData ? 'none' : undefined }}>
        <div className={`bulk-bar${selected.size > 0 ? ' bulk-bar--visible' : ''}`}>
          <span className="bulk-bar__count">
            Обрано: <strong>{selected.size}</strong>
          </span>
          <div className="bulk-bar__actions">
            <button className="bulk-btn bulk-btn--process" onClick={() => bulkStatus('processing')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 .49-4.47" /></svg>
              В обробку
            </button>
            <button className="bulk-btn bulk-btn--done" onClick={() => bulkStatus('done')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
              Виконано
            </button>
            <button className="bulk-btn bulk-btn--cancel" onClick={() => bulkStatus('cancelled')}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              Скасувати
            </button>
            <button className="bulk-btn bulk-btn--delete" onClick={bulkDelete}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /></svg>
              Видалити
            </button>
          </div>
        </div>

        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th style={{ width: 32, paddingLeft: 16 }}>
                  <input
                    type="checkbox"
                    className="order-checkbox"
                    title="Виділити всі"
                    checked={allChecked}
                    ref={(el) => {
                      if (el) el.indeterminate = someChecked;
                    }}
                    onChange={(e) => setSelected(e.target.checked ? new Set(orders.map((o) => o.order_id)) : new Set())}
                  />
                </th>
                <th style={{ width: 28 }} />
                <th>#</th>
                <th>Клієнт</th>
                <th>Телефон</th>
                <th>К-ть</th>
                <th>Сума</th>
                <th>Оплата</th>
                <th style={{ minWidth: 230 }}>Статус</th>
                <th>Дата</th>
                <th style={{ width: 48 }}>Дії</th>
              </tr>
            </thead>
            <tbody>
              {orders.length ? (
                orders.map((o) => {
                  const status = overrides[o.order_id]?.status ?? o.status;
                  const next = overrides[o.order_id]?.next ?? o.next_allowed;
                  const open = expanded === o.order_id;
                  return (
                    <Fragment key={o.order_id}>
                      <tr className="order-row" data-status={status} style={removed.has(o.order_id) ? { animation: 'rowDelete .35s ease forwards' } : undefined}>
                        <td style={{ paddingLeft: 16 }}>
                          <input
                            type="checkbox"
                            className="order-checkbox row-checkbox"
                            aria-label={`Обрати замовлення #${o.order_id}`}
                            checked={selected.has(o.order_id)}
                            onChange={(e) =>
                              setSelected((s) => {
                                const n = new Set(s);
                                if (e.target.checked) n.add(o.order_id);
                                else n.delete(o.order_id);
                                return n;
                              })
                            }
                          />
                        </td>
                        <td>
                          <button className={`expand-btn${open ? ' rotated' : ''}`} title="Деталі" onClick={() => setExpanded(open ? null : o.order_id)}>
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="6 9 12 15 18 9" /></svg>
                          </button>
                        </td>
                        <td>
                          <Link to={`/admin/orders/${o.order_id}`} style={{ fontWeight: 700, color: '#8B4513', textDecoration: 'none' }}>
                            #{o.order_id}
                          </Link>
                        </td>
                        <td>{o.full_name}</td>
                        <td style={{ fontSize: 12, color: '#666' }}>{o.phone}</td>
                        <td style={{ color: '#888' }}>{o.items_count}</td>
                        <td>
                          <strong>{grn(o.total)} ₴</strong>
                        </td>
                        <td>
                          <PayTag badge={o.pay_badge} />
                        </td>
                        <td>
                          <div className="status-cell">
                            <span className={`order-status-badge badge-${status}`}>{data.status_labels[status] ?? status}</span>
                            {next.map((ns) => (
                              <button key={ns} className={`status-pill-btn pill-${ns}`} disabled={statusMut.isPending} onClick={() => changeStatus(o.order_id, ns)}>
                                {data.next_labels[ns] ?? `→ ${data.status_labels[ns] ?? ns}`}
                              </button>
                            ))}
                          </div>
                        </td>
                        <td style={{ fontSize: 12, color: '#999', whiteSpace: 'nowrap' }}>{fmtDateTime(o.created_at, ' ')}</td>
                        <td>
                          <button className="btn-delete-order" title="Видалити замовлення" onClick={(e) => setDeleting({ id: o.order_id, anchor: e.currentTarget })}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /></svg>
                          </button>
                        </td>
                      </tr>
                      <tr className={`order-details-row${open ? ' open' : ''}`}>
                        <td colSpan={11}>
                          <div className="order-details-inner">{open && <OrderDetails order={o} />}</div>
                        </td>
                      </tr>
                    </Fragment>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', color: '#bbb', padding: 36 }}>
                    Замовлень не знайдено
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination page={data.page} totalPages={data.total_pages} onPage={setPage} />
      </div>

      <ConfirmPopup
        anchor={deleting?.anchor ?? null}
        text="Видалити замовлення назавжди?"
        confirmLabel="Видалити"
        danger
        busy={deleteMut.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />
    </>
  );
}
