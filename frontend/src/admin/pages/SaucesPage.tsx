import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { PickCropper, useImagePick } from '../components/ImageCrop';
import { adminKeys } from '../useAdmin';

type Sauce = components['schemas']['AdminSauce'];

const NoImage = () => (
  <div style={{ width: 40, height: 40, borderRadius: 8, background: '#f5f0eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c8b9a8" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
  </div>
);

export default function SaucesPage() {
  useAdminTitle('Соуси');
  const toast = useAdminToast();
  const client = useQueryClient();
  const q = useQuery({ queryKey: adminKeys.sauces, queryFn: () => unwrap(api.GET('/api/admin/sauces')) });

  const [panel, setPanel] = useState<{ open: boolean; editing: Sauce | null }>({ open: false, editing: null });
  const [form, setForm] = useState({ name: '', price: '', active: true });
  const [removing, setRemoving] = useState<Set<number>>(new Set());
  const photo = useImagePick();
  const nameRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const invalidate = () => {
    client.invalidateQueries({ queryKey: adminKeys.sauces });
    client.invalidateQueries({ queryKey: adminKeys.dashboard });
    client.invalidateQueries({ queryKey: ['menu'] });
  };

  const openForm = (editing: Sauce | null) => {
    photo.reset();
    if (fileRef.current) fileRef.current.value = '';
    setForm(editing ? { name: editing.name, price: String(editing.price), active: editing.active } : { name: '', price: '', active: true });
    setPanel({ open: true, editing });
  };

  useEffect(() => {
    if (!panel.open) return;
    if (panel.editing) panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    else window.setTimeout(() => nameRef.current?.focus(), 50);
  }, [panel]);

  const save = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append('name', form.name);
      fd.append('price', form.price);
      fd.append('active', form.active ? 'true' : 'false');
      photo.append(fd, 'image', 'image_b64');
      const opts = { body: {}, bodySerializer: () => fd };
      return panel.editing
        ? unwrap(api.POST('/api/admin/sauces/{sauce_id}', { params: { path: { sauce_id: panel.editing.id } }, ...opts }))
        : unwrap(api.POST('/api/admin/sauces', opts));
    },
    onSuccess: () => {
      toast('Соус збережено', 'success');
      setPanel({ open: false, editing: null });
      invalidate();
    },
    onError: (err) => toast(errorMessage(err) || 'Помилка збереження', 'error'),
  });

  const toggle = useMutation({
    mutationFn: (s: Sauce) => unwrap(api.PATCH('/api/admin/sauces/{sauce_id}/active', { params: { path: { sauce_id: s.id } }, body: { active: !s.active } })),
    onMutate: (s) => client.setQueryData<Sauce[]>(adminKeys.sauces, (list) => list?.map((x) => (x.id === s.id ? { ...x, active: !s.active } : x))),
    onError: (err) => {
      toast(errorMessage(err), 'error');
      invalidate();
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ['menu'] }),
  });

  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/sauces/{sauce_id}', { params: { path: { sauce_id: id } } })),
    onMutate: (id) => setRemoving((s) => new Set(s).add(id)),
    onSuccess: () => window.setTimeout(invalidate, 250),
    onError: (err, id) => {
      setRemoving((s) => {
        const n = new Set(s);
        n.delete(id);
        return n;
      });
      toast(errorMessage(err), 'error');
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const sauces = q.data;
  const preview = photo.preview ?? (panel.editing?.has_photo ? panel.editing.image : null);

  return (
    <>
      <div className="admin-page-header">
        <div>
          <div className="aph-title">Соуси</div>
          <div className="aph-sub">Управління соусами до страв</div>
        </div>
        <button className="btn-primary" onClick={() => openForm(null)}>
          + Додати соус
        </button>
      </div>

      <div ref={panelRef} className={`admin-card sauce-panel${panel.open ? ' visible' : ''}`}>
        <div className="sauce-panel__title">{panel.editing ? `Редагування: ${panel.editing.name}` : 'Новий соус'}</div>
        <form onSubmit={submit}>
          <div className="sauce-panel__row">
            <div className="sauce-panel__field sauce-panel__field--grow">
              <label htmlFor="sfName">Назва</label>
              <input ref={nameRef} type="text" id="sfName" placeholder="Кетчуп" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="sauce-panel__field">
              <label htmlFor="sfPrice">Ціна (₴)</label>
              <input type="number" id="sfPrice" placeholder="15" step="1" min="0" required value={form.price} onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))} />
            </div>
            <div className="sauce-panel__field sauce-panel__field--check">
              <label className="sauce-check">
                <input type="checkbox" checked={form.active} onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))} />
                <span>Активний</span>
              </label>
            </div>
          </div>
          <div className="sauce-panel__row" style={{ marginTop: 10, alignItems: 'center' }}>
            <div className="sauce-panel__field" style={{ flex: 1 }}>
              <label htmlFor="sfImage">
                Фото <small style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(JPG/PNG/WEBP · до 2 MB · залиш порожнім щоб не міняти)</small>
              </label>
              <input ref={fileRef} type="file" id="sfImage" accept="image/jpeg,image/png,image/webp" style={{ padding: '6px 10px' }} onChange={(e) => photo.pick(e.target.files?.[0])} />
            </div>
            {preview && (
              <div style={{ width: 52, height: 52, borderRadius: 8, overflow: 'hidden', flexShrink: 0, background: '#f5f0eb' }}>
                <img src={preview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            )}
            {photo.picked && (
              <button type="button" className="upload-recrop" style={{ marginTop: 0 }} onClick={photo.openCropper}>
                Редагувати
              </button>
            )}
          </div>
          <div className="sauce-panel__actions">
            <button type="submit" className="btn-primary" disabled={save.isPending}>
              Зберегти
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setPanel((p) => ({ ...p, open: false }))}>
              Скасувати
            </button>
          </div>
        </form>
        <PickCropper pick={photo} aspect={1} />
      </div>

      <div className="admin-card" style={{ overflow: 'hidden' }}>
        {!sauces.length ? (
          <div style={{ padding: 48, textAlign: 'center', color: '#bbb', fontSize: 14 }}>Соусів ще немає. Додайте перший!</div>
        ) : (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th style={{ width: 52 }}>#</th>
                  <th style={{ width: 60 }}>Фото</th>
                  <th>Назва</th>
                  <th style={{ width: 130 }}>Ціна</th>
                  <th style={{ width: 130 }}>Статус</th>
                  <th style={{ width: 180 }} />
                </tr>
              </thead>
              <tbody>
                {sauces.map((s, i) => (
                  <tr key={s.id} style={removing.has(s.id) ? { transition: 'opacity .25s', opacity: 0 } : undefined}>
                    <td style={{ color: '#bbb', fontSize: 13 }}>{i + 1}</td>
                    <td>{s.has_photo ? <img src={s.image} alt="" style={{ width: 40, height: 40, borderRadius: 8, objectFit: 'cover', display: 'block' }} /> : <NoImage />}</td>
                    <td style={{ fontWeight: 600, color: '#2c2c2a' }}>{s.name}</td>
                    <td>
                      <strong style={{ color: '#5a2d0c' }}>{Math.round(s.price)} ₴</strong>
                    </td>
                    <td>
                      <button className={`sauce-toggle ${s.active ? 'sauce-toggle--on' : 'sauce-toggle--off'}`} onClick={() => toggle.mutate(s)}>
                        {s.active ? 'Активний' : 'Вимкнено'}
                      </button>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn-ghost btn-sm" onClick={() => openForm(s)}>
                          Редагувати
                        </button>
                        <button className="sauce-del-btn btn-sm" onClick={() => window.confirm('Видалити цей соус?') && remove.mutate(s.id)}>
                          Видалити
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
