import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { CSSProperties } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import { PageError, PageLoader } from '@/components/Spinner';
import { fmtDateTime } from '@/lib/format';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { payMethodLabel } from '../components/OrderDetails';
import { adminKeys, useAdminLayout } from '../useAdmin';

// Same wording as the server's STATUS_LABELS / NEXT_LABELS (orders_admin.py).
const STATUS_LABELS: Record<string, string> = { new: 'Нове', processing: 'В обробці', ready: 'Готово', done: 'Виконано', cancelled: 'Скасовано' };
const NEXT_LABELS: Record<string, string> = { processing: '→ В обробці', ready: '→ Готово', done: '✓ Виконано', cancelled: '✕ Скасувати' };

const grn = (v: number) => Math.round(v).toLocaleString('uk-UA');
const caption: CSSProperties = { fontSize: 10, fontWeight: 700, color: '#b09070', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 16 };
const row: CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 8, borderBottom: '1px solid #f0e8df' };

export default function OrderViewPage() {
  const orderId = Number(useParams().orderId);
  useAdminTitle(`Замовлення #${orderId}`);
  const toast = useAdminToast();
  const client = useQueryClient();
  const canEdit = !!useAdminLayout().data?.perms.orders_edit;
  const q = useQuery({
    queryKey: adminKeys.order(orderId),
    queryFn: () => unwrap(api.GET('/api/admin/orders/{order_id}', { params: { path: { order_id: orderId } } })),
    enabled: Number.isFinite(orderId),
  });

  const statusMut = useMutation({
    mutationFn: (status: string) => unwrap(api.POST('/api/admin/orders/{order_id}/status', { params: { path: { order_id: orderId } }, body: { status } })),
    onSuccess: (res, status) => {
      if (!res.success) return toast(res.error || 'Помилка оновлення', 'error');
      toast(`Статус: ${STATUS_LABELS[status] ?? status}`, 'success');
      client.setQueryData(adminKeys.newCount, { count: res.new_count });
      client.invalidateQueries({ queryKey: adminKeys.order(orderId) });
      client.invalidateQueries({ queryKey: ['admin', 'orders'] });
      client.invalidateQueries({ queryKey: adminKeys.layout });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const order = q.data;
  const pm = order.payment_method;
  const ps = order.payment_status;
  const pay = ps === 'paid' ? { label: 'Оплачено', cls: 'badge-ready' } : !ps || ps === 'pending' ? { label: 'Не оплачено', cls: 'badge-new' } : { label: ps, cls: 'badge-new' };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#b09070' }}>
          <Link to="/admin/orders" style={{ color: '#8B4513', textDecoration: 'none', fontWeight: 600 }}>
            Замовлення
          </Link>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="9 18 15 12 9 6" /></svg>
          <span>#{order.order_id}</span>
        </div>
        <Link to="/admin/orders" className="action-btn action-btn--ghost" style={{ fontSize: 12, padding: '6px 14px' }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
          Назад до списку
        </Link>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#2c1810', margin: 0 }}>Замовлення #{order.order_id}</h1>
        <span className={`order-status-badge badge-${order.status}`} style={{ fontSize: 13, padding: '5px 14px' }}>
          {STATUS_LABELS[order.status] ?? order.status}
        </span>
        {canEdit && order.next_allowed.length > 0 && (
          <div className="status-cell" style={{ marginLeft: 'auto' }}>
            {order.next_allowed.map((ns) => (
              <button
                key={ns}
                className={`status-pill-btn pill-${ns}`}
                disabled={statusMut.isPending}
                onClick={() => window.confirm(`Змінити статус на «${STATUS_LABELS[ns] ?? ns}»?`) && statusMut.mutate(ns)}
              >
                {NEXT_LABELS[ns] ?? `→ ${STATUS_LABELS[ns] ?? ns}`}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="order-view-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 20 }}>
        <div className="dash-section" style={{ padding: '22px 24px' }}>
          <div style={caption}>Клієнт</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <div style={{ width: 42, height: 42, borderRadius: '50%', background: 'linear-gradient(135deg,#8B4513,#d4a96a)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 16, flexShrink: 0 }}>
              {order.client_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div style={{ fontWeight: 700, color: '#2c1810', fontSize: 15 }}>{order.client_name}</div>
              {(order.client_email || order.customer_email) && <div style={{ fontSize: 12, color: '#aaa' }}>{order.client_email || order.customer_email}</div>}
            </div>
          </div>
          {order.phone && order.phone !== '—' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#555', padding: '8px 0', borderTop: '1px solid #f0e8df' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8B4513" strokeWidth="2" strokeLinecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.58 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" /></svg>
              <a href={`tel:${order.phone.replace(/[^\d+]/g, '')}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                {order.phone}
              </a>
            </div>
          )}
        </div>

        <div className="dash-section" style={{ padding: '22px 24px' }}>
          <div style={caption}>Деталі замовлення</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
            <div style={row}>
              <span style={{ color: '#aaa' }}>Дата</span>
              <span style={{ fontWeight: 600, color: '#2c1810' }}>{fmtDateTime(order.created_at)}</span>
            </div>
            <div style={row}>
              <span style={{ color: '#aaa' }}>Сума</span>
              <span style={{ fontWeight: 700, color: '#8B4513', fontSize: 16 }}>{grn(order.total)} ₴</span>
            </div>
            <div style={row}>
              <span style={{ color: '#aaa' }}>Оплата</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: '#555' }}>{order.payment_method_label || payMethodLabel(pm)}</span>
                {pm === 'card_online' && (
                  <span className={`order-badge ${pay.cls}`} style={{ fontSize: 10, padding: '2px 8px' }}>
                    {pay.label}
                  </span>
                )}
              </div>
            </div>
            {order.paid_at && (
              <div style={row}>
                <span style={{ color: '#aaa' }}>Оплачено</span>
                <span style={{ fontWeight: 600, color: '#2e7d32' }}>{fmtDateTime(order.paid_at)}</span>
              </div>
            )}
            <div style={row}>
              <span style={{ color: '#aaa' }}>Тип</span>
              <span style={{ fontWeight: 600, color: '#2c1810' }}>{order.order_type === 'takeaway' ? 'З собою' : 'В залі'}</span>
            </div>
            {order.ready_time && (
              <div style={row}>
                <span style={{ color: '#aaa' }}>Час готовності</span>
                <span style={{ fontWeight: 600, color: '#2c1810' }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ verticalAlign: 'middle', marginRight: 3 }}><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg> {order.ready_time}
                </span>
              </div>
            )}
            {order.comment && (
              <div style={{ paddingTop: 2 }}>
                <div style={{ color: '#aaa', marginBottom: 4 }}>Коментар</div>
                <div style={{ background: '#fdf6ee', borderRadius: 8, padding: '10px 12px', fontSize: 12, color: '#555', fontStyle: 'italic', lineHeight: 1.5 }}>💬 {order.comment}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="dash-section" style={{ padding: '22px 24px', marginBottom: 20 }}>
        <div style={caption}>
          Позиції замовлення <span style={{ background: '#f0e8df', color: '#8B6040', padding: '2px 8px', borderRadius: 10, marginLeft: 8, fontSize: 10 }}>{order.line_items.length}</span>
        </div>
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Назва</th>
                <th style={{ textAlign: 'center' }}>Кількість</th>
                <th style={{ textAlign: 'right' }}>Ціна</th>
                <th style={{ textAlign: 'right' }}>Сума</th>
              </tr>
            </thead>
            <tbody>
              {order.line_items.map((item, i) => (
                <tr key={i}>
                  <td>
                    <div style={{ fontWeight: 600, color: '#2c1810' }}>{item.product_name}</div>
                    {item.opts.length > 0 && <div style={{ fontSize: 11, color: '#8B6040', marginTop: 2 }}>{item.opts.join(' · ')}</div>}
                  </td>
                  <td style={{ textAlign: 'center' }}>×{item.quantity}</td>
                  <td style={{ textAlign: 'right', color: '#555' }}>{grn(item.price)} ₴</td>
                  <td style={{ textAlign: 'right', fontWeight: 700, color: '#8B4513' }}>{grn(item.price * item.quantity)} ₴</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3} style={{ textAlign: 'right', fontWeight: 700, color: '#555', borderTop: '2px solid #f0e8df', paddingTop: 12 }}>
                  Разом:
                </td>
                <td style={{ textAlign: 'right', fontWeight: 700, fontSize: 16, color: '#8B4513', borderTop: '2px solid #f0e8df', paddingTop: 12 }}>{grn(order.total)} ₴</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {order.rating != null && (
        <div className="dash-section" style={{ padding: '22px 24px', marginBottom: 20 }}>
          <div style={{ ...caption, marginBottom: 14 }}>Оцінка клієнта</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 22, letterSpacing: 2, fontFamily: 'serif', lineHeight: 1 }}>
              <span style={{ color: '#FFC107' }}>{'★'.repeat(order.rating)}</span>
              <span style={{ color: '#e0d5c9' }}>{'★'.repeat(5 - order.rating)}</span>
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#8B4513' }}>{order.rating}/5</div>
          </div>
        </div>
      )}
    </>
  );
}
