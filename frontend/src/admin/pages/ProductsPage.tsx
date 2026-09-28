import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { truncate } from '@/lib/format';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { PickCropper, useImagePick } from '../components/ImageCrop';
import { AdminModal } from '../components/Modal';
import { adminKeys } from '../useAdmin';

type Product = components['schemas']['AdminProduct'];
type Category = components['schemas']['CategoryCount'];

const NoPhoto = () => (
  <div style={{ width: 52, height: 52, background: '#f0e8df', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c9b49a" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
  </div>
);

function Thumb({ src }: { src: string }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) return <NoPhoto />;
  return <img src={src} alt="" loading="lazy" style={{ width: 52, height: 52, objectFit: 'cover', borderRadius: 8, border: '1px solid #ede5dd' }} onError={() => setBroken(true)} />;
}

type FormState = {
  category: string;
  name: string;
  price: string;
  description: string;
  min_weight: string;
  pieces_count: string;
  scoop_diff_2: string;
  scoop_diff_3: string;
};

const emptyForm = (category: string): FormState => ({ category, name: '', price: '', description: '', min_weight: '', pieces_count: '', scoop_diff_2: '', scoop_diff_3: '' });
const num = (v: number | null | undefined) => (v == null ? '' : String(v));

function ProductModal({
  open,
  editing,
  categories,
  defaultCategory,
  onClose,
}: {
  open: boolean;
  editing: Product | null;
  categories: Category[];
  defaultCategory: string;
  onClose: () => void;
}) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const photo = useImagePick();
  const [form, setForm] = useState<FormState>(emptyForm(defaultCategory));
  const [existing, setExisting] = useState<string>('');
  const [removeImage, setRemoveImage] = useState(false);
  const [error, setError] = useState('');
  const [pressing, setPressing] = useState(false);
  const descRef = useRef<HTMLTextAreaElement>(null);
  const resetPhoto = photo.reset;

  useEffect(() => {
    if (!open) return;
    resetPhoto();
    setRemoveImage(false);
    setError('');
    if (editing) {
      setForm({
        category: editing.category,
        name: editing.name,
        price: num(editing.price_per_kg ?? editing.price),
        description: editing.description,
        min_weight: num(editing.min_weight),
        pieces_count: num(editing.pieces_count),
        scoop_diff_2: num(editing.scoop_diff_2),
        scoop_diff_3: num(editing.scoop_diff_3),
      });
      setExisting(editing.has_photo ? editing.image : '');
    } else {
      setForm(emptyForm(defaultCategory === 'all' ? '' : defaultCategory));
      setExisting('');
    }
  }, [open, editing, defaultCategory, resetPhoto]);

  // Auto-grow the description.
  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(80, el.scrollHeight)}px`;
  }, [form.description, open]);

  const save = useMutation({
    mutationFn: async () => {
      const isCake = form.category === 'cake_items';
      const body = {
        name: form.name,
        description: form.description,
        price: form.price,
        ...(isCake ? { price_per_kg: form.price, min_weight: form.min_weight } : {}),
        ...(form.category === 'ice_cream_items' ? { scoop_diff_2: form.scoop_diff_2, scoop_diff_3: form.scoop_diff_3 } : {}),
        ...(form.category === 'sushi_set_items' ? { pieces_count: form.pieces_count } : {}),
      };
      const fd = new FormData();
      Object.entries(body).forEach(([k, v]) => fd.append(k, v));
      photo.append(fd, 'image', 'image_b64');
      if (editing && removeImage && !photo.picked) fd.append('remove_image', '1');
      // Multipart body: the typed client can't express a File field, so
      // the serializer hands over the prepared FormData as-is.
      const opts = { body: {}, bodySerializer: () => fd };
      return editing
        ? unwrap(api.POST('/api/admin/products/{category}/{item_id}', { params: { path: { category: editing.category, item_id: editing.id } }, ...opts }))
        : unwrap(api.POST('/api/admin/products/{category}', { params: { path: { category: form.category } }, ...opts }));
    },
    onSuccess: () => {
      toast('Товар збережено!', 'success');
      client.invalidateQueries({ queryKey: ['admin', 'products'] });
      client.invalidateQueries({ queryKey: adminKeys.dashboard });
      client.invalidateQueries({ queryKey: ['menu'] });
      onClose();
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.category) return setError('Оберіть категорію.');
    save.mutate();
  };

  const set = (key: keyof FormState) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const preview = photo.preview ?? (removeImage ? '' : existing);
  const isCake = form.category === 'cake_items';
  const isIceCream = form.category === 'ice_cream_items';

  return (
    <AdminModal open={open} onClose={onClose} className="modal item-modal" label={editing ? 'Редагувати товар' : 'Додати товар'}>
      <button className="modal-close-btn" type="button" onClick={onClose} aria-label="Закрити">
        ✕
      </button>
      <h3 className="item-modal-title">{editing ? 'Редагувати товар' : 'Додати товар'}</h3>

      <form onSubmit={submit}>
        {error && (
          <div className="alert alert-error" role="alert" style={{ margin: '0 0 14px' }}>
            {error}
          </div>
        )}

        {!editing && defaultCategory === 'all' && (
          <div className="form-group" style={{ marginBottom: 18 }}>
            <label className="im-label" htmlFor="imCategory">
              Категорія *
            </label>
            <select id="imCategory" className="im-control" value={form.category} onChange={set('category')} required>
              <option value="">— Оберіть —</option>
              {categories.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="item-modal-grid">
          <div className="form-group">
            <label className="im-label" htmlFor="imName">
              Назва *
            </label>
            <input className="im-control" type="text" id="imName" value={form.name} onChange={set('name')} required />
          </div>
          <div className="form-group">
            <label className="im-label" htmlFor="imPrice">
              {isCake ? 'Ціна за кг (₴) *' : 'Ціна (₴) *'}
            </label>
            <input className="im-control" type="number" id="imPrice" step="0.01" min="0" value={form.price} onChange={set('price')} required />
          </div>
        </div>

        {isCake && (
          <div className="form-group" style={{ marginTop: 18 }}>
            <label className="im-label" htmlFor="imMinWeight">
              Мінімальна вага (кг)
            </label>
            <input className="im-control" type="number" id="imMinWeight" step="0.1" min="0.1" placeholder="1" value={form.min_weight} onChange={set('min_weight')} />
          </div>
        )}
        {form.category === 'sushi_set_items' && (
          <div className="form-group" style={{ marginTop: 18 }}>
            <label className="im-label" htmlFor="imPieces">
              Кількість шматочків
            </label>
            <input className="im-control" type="number" id="imPieces" step="1" min="0" value={form.pieces_count} onChange={set('pieces_count')} />
          </div>
        )}

        <div className="form-group" style={{ marginTop: 18 }}>
          <label className="im-label" htmlFor="imDesc">
            Опис
          </label>
          <textarea ref={descRef} className="im-control im-textarea" id="imDesc" value={form.description} onChange={set('description')} />
        </div>

        <div className="form-group im-photo-group" style={{ marginTop: 18 }}>
          <label className="im-label">Фото{editing ? '' : ' *'}</label>
          <div className="im-photo-section">
            <div className={`im-photo-preview-wrap${preview ? '' : ' no-photo'}`}>
              {preview ? (
                <img src={preview} alt="" style={{ display: 'block' }} onError={() => setExisting('')} />
              ) : (
                <div className="im-photo-empty" style={{ display: 'flex' }}>
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#d4c4b8" strokeWidth="1.2" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
                  <span>Немає фото</span>
                </div>
              )}
            </div>
            <div className="im-photo-actions">
              <label
                className={`im-pick-btn${pressing ? ' pressing' : ''}`}
                htmlFor="imImage"
                onMouseDown={() => setPressing(true)}
                onMouseUp={() => setPressing(false)}
                onMouseLeave={() => setPressing(false)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
                <span>{preview ? 'Замінити фото' : 'Обрати фото'}</span>
              </label>
              <input
                type="file"
                id="imImage"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => {
                  photo.pick(e.target.files?.[0]);
                  e.target.value = '';
                }}
              />
              {photo.picked && (
                <button type="button" className="im-edit-btn" style={{ display: 'inline-flex' }} onClick={photo.openCropper}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  Редагувати
                </button>
              )}
              {editing && preview && (
                <button
                  type="button"
                  className="im-remove-btn"
                  style={{ display: 'inline-flex' }}
                  onClick={() => {
                    photo.reset();
                    setRemoveImage(true);
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
                  Видалити фото
                </button>
              )}
            </div>
          </div>
        </div>

        {isIceCream && (
          <div style={{ marginTop: 20, padding: 16, background: '#faf7f2', borderRadius: 10, border: '1px solid #e8e0d8' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#8B4513', marginBottom: 14 }}>Налаштування кульок</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="im-label">1 кулька (базова ціна)</label>
                <input className="im-control" type="number" placeholder="45" value={form.price} readOnly style={{ background: '#f0ebe4', color: '#999', cursor: 'not-allowed' }} title="Базова ціна — поле «Ціна» вище" />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="im-label" htmlFor="imScoopDiff2">
                  Надбавка за 2 кульки (₴)
                </label>
                <input className="im-control" type="number" id="imScoopDiff2" placeholder="20" step="0.01" min="0" value={form.scoop_diff_2} onChange={set('scoop_diff_2')} />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="im-label" htmlFor="imScoopDiff3">
                  Надбавка за 3 кульки (₴)
                </label>
                <input className="im-control" type="number" id="imScoopDiff3" placeholder="40" step="0.01" min="0" value={form.scoop_diff_3} onChange={set('scoop_diff_3')} />
              </div>
            </div>
          </div>
        )}

        <div className="im-modal-footer">
          <button type="button" className="im-btn-cancel" onClick={onClose}>
            Скасувати
          </button>
          <button type="submit" className="im-btn-save" disabled={save.isPending}>
            {save.isPending ? 'Збереження…' : 'Зберегти'}
          </button>
        </div>
      </form>
      <PickCropper pick={photo} />
    </AdminModal>
  );
}

export default function ProductsPage() {
  const [params, setParams] = useSearchParams();
  const category = params.get('category') || 'all';
  const toast = useAdminToast();
  const client = useQueryClient();
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<{ open: boolean; editing: Product | null }>({ open: false, editing: null });
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Set<string>>(new Set());

  const q = useQuery({
    queryKey: adminKeys.products(category),
    queryFn: () => unwrap(api.GET('/api/admin/products', { params: { query: { category } } })),
  });
  useAdminTitle(q.data?.title ?? 'Товари');

  const del = useMutation({
    mutationFn: (p: Product) => unwrap(api.DELETE('/api/admin/products/{category}/{item_id}', { params: { path: { category: p.category, item_id: p.id } } })),
    onSuccess: (res, p) => {
      if (!res.success) return toast('Помилка видалення', 'error');
      toast('Товар видалено', 'success');
      window.setTimeout(() => {
        client.invalidateQueries({ queryKey: ['admin', 'products'] });
        client.invalidateQueries({ queryKey: adminKeys.dashboard });
      }, 350);
      setConfirming(null);
      void p;
    },
    onError: (err, p) => {
      setDeleting((s) => {
        const n = new Set(s);
        n.delete(`${p.category}:${p.id}`);
        return n;
      });
      setConfirming(null);
      toast(errorMessage(err), 'error');
    },
  });

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const data = q.data;
  const needle = search.trim().toLowerCase();
  const visible = data.products.filter((p) => !needle || p.name.toLowerCase().includes(needle));
  const cols = data.is_all ? 7 : 6;

  return (
    <>
      <div className="cat-tabs">
        <button type="button" className={`cat-tab${data.is_all ? ' active' : ''}`} onClick={() => setParams({ category: 'all' })}>
          Всі
          <span className="cat-tab-count">{data.total_count}</span>
        </button>
        {data.categories.map((c) => (
          <button key={c.key} type="button" className={`cat-tab${!data.is_all && data.category === c.key ? ' active' : ''}`} onClick={() => setParams({ category: c.key })}>
            {c.label}
            <span className="cat-tab-count">{c.count}</span>
          </button>
        ))}
      </div>

      <div className="section-head">
        <h2 className="section-title">{data.title}</h2>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <svg style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#aaa" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
            <input type="search" className="admin-search-input" placeholder="Пошук по назві…" aria-label="Пошук по назві" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button className="btn-add-item" onClick={() => setModal({ open: true, editing: null })}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            Додати товар
          </button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Фото</th>
              <th>Назва</th>
              {data.is_all && <th>Категорія</th>}
              <th className="col-hide-mobile">Опис</th>
              <th>Ціна</th>
              <th className="col-hide-mobile">Продажі</th>
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((p) => {
              const key = `${p.category}:${p.id}`;
              return (
                <tr key={key} style={deleting.has(key) ? { animation: 'rowDelete .35s ease forwards' } : undefined}>
                  <td>
                    <Thumb src={p.has_photo ? p.image : ''} />
                  </td>
                  <td>
                    <strong>{p.name || '—'}</strong>
                  </td>
                  {data.is_all && (
                    <td>
                      <Link to={`/admin/manage-items?category=${p.category}`} style={{ fontSize: 12, color: '#8B4513', textDecoration: 'none', background: '#fdf3e8', padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap' }}>
                        {p.category_label}
                      </Link>
                    </td>
                  )}
                  <td className="td-desc col-hide-mobile">{truncate(p.description, 70)}</td>
                  <td>
                    {p.price.toFixed(2)} ₴{p.category === 'cake_items' ? '/кг' : ''}
                  </td>
                  <td className="col-hide-mobile">{p.sold > 0 ? <span className="sold-badge">{p.sold} шт</span> : <span style={{ color: '#ccc' }}>—</span>}</td>
                  <td>
                    {confirming === key ? (
                      <div className="delete-confirm" style={{ display: 'flex' }}>
                        <span>Видалити товар?</span>
                        <button
                          className="confirm-yes"
                          onClick={() => {
                            setDeleting((s) => new Set(s).add(key));
                            del.mutate(p);
                          }}
                        >
                          Так
                        </button>
                        <button className="confirm-no" onClick={() => setConfirming(null)}>
                          Ні
                        </button>
                      </div>
                    ) : (
                      <div className="item-actions">
                        <button className="item-btn-edit" onClick={() => setModal({ open: true, editing: p })}>
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                          Редагувати
                        </button>
                        <button className="item-btn-delete" onClick={() => setConfirming(key)}>
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
                          Видалити
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
            {!data.products.length && (
              <tr>
                <td colSpan={cols} style={{ textAlign: 'center', color: '#bbb', padding: 32 }}>
                  Товарів у цій категорії немає
                </td>
              </tr>
            )}
            {data.products.length > 0 && !visible.length && (
              <tr>
                <td colSpan={cols} style={{ textAlign: 'center', color: '#bbb', padding: 32 }}>
                  Нічого не знайдено
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <ProductModal open={modal.open} editing={modal.editing} categories={data.categories} defaultCategory={data.category} onClose={() => setModal((m) => ({ ...m, open: false }))} />
    </>
  );
}
