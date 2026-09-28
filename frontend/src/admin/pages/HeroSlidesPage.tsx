import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState, type FormEvent } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { UploadZone, useImagePick } from '../components/ImageCrop';
import { AdminModal } from '../components/Modal';
import { adminKeys } from '../useAdmin';

type Slide = components['schemas']['AdminHeroSlide'];
type Texts = { label: string; title: string; subtitle: string };

const ASPECT = 16 / 9;
const MOVE_MS = 280;
const emptyTexts: Texts = { label: '', title: '', subtitle: '' };

const PhotoIcon = ({ size }: { size: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#aaa" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
);

function TextFields({ value, onChange, idPrefix }: { value: Texts; onChange: (v: Texts) => void; idPrefix: string }) {
  const set = (k: keyof Texts) => (e: { target: { value: string } }) => onChange({ ...value, [k]: e.target.value });
  return (
    <>
      <div className="form-field">
        <label htmlFor={`${idPrefix}Label`}>
          Мітка <small style={{ color: '#bbb', fontWeight: 400 }}>(над заголовком, необов'язково)</small>
        </label>
        <input type="text" id={`${idPrefix}Label`} placeholder="Спробуй зараз" maxLength={60} value={value.label} onChange={set('label')} />
      </div>
      <div className="form-field" style={{ marginTop: 14 }}>
        <label htmlFor={`${idPrefix}Title`}>
          Заголовок <span className="req">*</span>
        </label>
        <input type="text" id={`${idPrefix}Title`} placeholder="Кожен ковток — тепла історія" maxLength={100} required value={value.title} onChange={set('title')} />
      </div>
      <div className="form-field" style={{ marginTop: 14 }}>
        <label htmlFor={`${idPrefix}Subtitle`}>Підзаголовок</label>
        <input type="text" id={`${idPrefix}Subtitle`} placeholder="Свіжозварена кава щоранку з любов'ю" maxLength={160} value={value.subtitle} onChange={set('subtitle')} />
      </div>
    </>
  );
}

function slideForm(texts: Texts, pick: ReturnType<typeof useImagePick>) {
  const fd = new FormData();
  fd.append('label', texts.label);
  fd.append('title', texts.title);
  fd.append('subtitle', texts.subtitle);
  pick.append(fd, 'image', 'image_b64');
  return fd;
}

export default function HeroSlidesPage() {
  useAdminTitle('Хіро слайдер');
  const toast = useAdminToast();
  const client = useQueryClient();
  const q = useQuery({ queryKey: adminKeys.slides, queryFn: () => unwrap(api.GET('/api/admin/hero-slides')) });

  const addPhoto = useImagePick();
  const [addTexts, setAddTexts] = useState<Texts>(emptyTexts);
  const editPhoto = useImagePick();
  const [editing, setEditing] = useState<Slide | null>(null);
  const [editTexts, setEditTexts] = useState<Texts>(emptyTexts);
  const [moving, setMoving] = useState<Record<number, number>>({});
  const rowRefs = useRef(new Map<number, HTMLDivElement>());

  const refresh = () => {
    client.invalidateQueries({ queryKey: adminKeys.slides });
    client.invalidateQueries({ queryKey: adminKeys.dashboard });
    client.invalidateQueries({ queryKey: ['home'] });
  };

  const add = useMutation({
    mutationFn: () => unwrap(api.POST('/api/admin/hero-slides', { body: {}, bodySerializer: () => slideForm(addTexts, addPhoto) })),
    onSuccess: () => {
      toast('Слайд додано', 'success');
      setAddTexts(emptyTexts);
      addPhoto.reset();
      refresh();
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const save = useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/api/admin/hero-slides/{slide_id}', { params: { path: { slide_id: id } }, body: {}, bodySerializer: () => slideForm(editTexts, editPhoto) })),
    onSuccess: () => {
      toast('Слайд збережено', 'success');
      setEditing(null);
      refresh();
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const toggle = useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/api/admin/hero-slides/{slide_id}/toggle', { params: { path: { slide_id: id } } })),
    onSuccess: (res, id) => {
      client.setQueryData<Slide[]>(adminKeys.slides, (list) => list?.map((s) => (s.id === id ? { ...s, active: res.active } : s)));
      client.invalidateQueries({ queryKey: adminKeys.dashboard });
      client.invalidateQueries({ queryKey: ['home'] });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/hero-slides/{slide_id}', { params: { path: { slide_id: id } } })),
    onSuccess: () => {
      toast('Слайд видалено', 'success');
      refresh();
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const move = (slides: Slide[], index: number, dir: 'up' | 'down') => {
    const other = dir === 'up' ? index - 1 : index + 1;
    if (other < 0 || other >= slides.length || Object.keys(moving).length) return;
    const a = slides[index];
    const b = slides[other];
    const aTop = rowRefs.current.get(a.id)?.offsetTop ?? 0;
    const bTop = rowRefs.current.get(b.id)?.offsetTop ?? 0;
    // Slide the two rows past each other, then swap them in the cache.
    setMoving({ [a.id]: bTop - aTop, [b.id]: aTop - bTop });
    api.POST('/api/admin/hero-slides/{slide_id}/move', { params: { path: { slide_id: a.id } }, body: { dir } }).then(({ error }) => {
      if (error) {
        toast(errorMessage(error), 'error');
        refresh();
      }
    });
    window.setTimeout(() => {
      client.setQueryData<Slide[]>(adminKeys.slides, (list) => {
        if (!list) return list;
        const next = [...list];
        [next[index], next[other]] = [next[other], next[index]];
        return next;
      });
      setMoving({});
      client.invalidateQueries({ queryKey: ['home'] });
    }, MOVE_MS);
  };

  const openEdit = (s: Slide) => {
    editPhoto.reset();
    setEditTexts({ label: s.label, title: s.title, subtitle: s.subtitle });
    setEditing(s);
  };

  const submitAdd = (e: FormEvent) => {
    e.preventDefault();
    if (!addPhoto.picked) return toast('Оберіть зображення', 'error');
    add.mutate();
  };

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const slides = q.data;
  const busy = Object.keys(moving).length > 0;

  return (
    <div className="ap-hero">
      <div className="panel" style={{ marginBottom: 28 }}>
        <div className="panel-head">
          <h2 className="panel-title">Додати слайд</h2>
        </div>
        <form className="slide-form" onSubmit={submitAdd}>
          <div className="sf-row">
            <div className="sf-field sf-field--upload">
              <label>
                Зображення <span className="req">*</span>
              </label>
              <UploadZone
                pick={addPhoto}
                aspect={ASPECT}
                placeholder={
                  <>
                    <PhotoIcon size={28} />
                    <span>Оберіть або перетягніть фото</span>
                    <small>JPG, PNG, WEBP · до 4 MB</small>
                  </>
                }
              />
            </div>
            <div className="sf-field sf-field--text">
              <TextFields value={addTexts} onChange={setAddTexts} idPrefix="add" />
              <button type="submit" className="btn btn-primary" style={{ marginTop: 18 }} disabled={add.isPending}>
                + Додати слайд
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2 className="panel-title">Поточні слайди ({slides.length})</h2>
        </div>
        {!slides.length ? (
          <p style={{ padding: 24, color: '#999', textAlign: 'center' }}>Слайдів ще немає.</p>
        ) : (
          <div className="slides-list">
            {slides.map((sl, i) => (
              <div
                key={sl.id}
                ref={(el) => {
                  if (el) rowRefs.current.set(sl.id, el);
                  else rowRefs.current.delete(sl.id);
                }}
                className={`slide-row${sl.active ? '' : ' slide-row--inactive'}`}
                style={moving[sl.id] !== undefined ? { transition: `transform ${MOVE_MS}ms cubic-bezier(0.4,0,0.2,1)`, transform: `translateY(${moving[sl.id]}px)` } : undefined}
              >
                <div className="slide-order">
                  <button type="button" className="move-btn" title="Вгору" aria-label="Вгору" disabled={busy || i === 0} onClick={() => move(slides, i, 'up')}>
                    ▲
                  </button>
                  <button type="button" className="move-btn" title="Вниз" aria-label="Вниз" disabled={busy || i === slides.length - 1} onClick={() => move(slides, i, 'down')}>
                    ▼
                  </button>
                  <span className="slide-num">{i + 1}</span>
                </div>
                <div className="slide-thumb">
                  <img src={sl.image} alt="" />
                </div>
                <div className="slide-texts">
                  <div className="slide-title">{sl.title}</div>
                  <div className="slide-sub">{sl.subtitle}</div>
                </div>
                <div className="slide-toggle-form">
                  <button
                    type="button"
                    className={`toggle-btn ${sl.active ? 'toggle-btn--on' : 'toggle-btn--off'}`}
                    title={sl.active ? 'Активний — натисни щоб вимкнути' : 'Вимкнений — натисни щоб увімкнути'}
                    onClick={() => toggle.mutate(sl.id)}
                  >
                    {sl.active ? 'Активний' : 'Вимкнений'}
                  </button>
                </div>
                <div className="slide-actions">
                  <button className="btn btn-sm btn-outline" onClick={() => openEdit(sl)}>
                    ✏️ Редагувати
                  </button>
                  <button className="btn btn-sm btn-danger" onClick={() => window.confirm('Видалити цей слайд?') && remove.mutate(sl.id)}>
                    🗑 Видалити
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <AdminModal open={!!editing} onClose={() => setEditing(null)} className="modal-box" style={{ width: 'min(500px, 92vw)' }} label="Редагувати слайд">
        <button className="modal-close" type="button" onClick={() => setEditing(null)} aria-label="Закрити">
          ✕
        </button>
        <h3 className="modal-title">Редагувати слайд</h3>
        <form
          className="slide-form"
          style={{ marginTop: 20 }}
          onSubmit={(e) => {
            e.preventDefault();
            if (editing) save.mutate(editing.id);
          }}
        >
          <div className="form-field">
            <label>
              Нове зображення <small>(залиш порожнім щоб не міняти)</small>
            </label>
            <UploadZone
              pick={editPhoto}
              aspect={ASPECT}
              placeholder={
                <>
                  <PhotoIcon size={22} />
                  <span>Оберіть фото</span>
                </>
              }
            />
          </div>
          <div style={{ marginTop: 14 }}>
            <TextFields value={editTexts} onChange={setEditTexts} idPrefix="edit" />
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
            <button type="submit" className="btn btn-primary" disabled={save.isPending}>
              Зберегти
            </button>
            <button type="button" className="btn btn-outline" onClick={() => setEditing(null)}>
              Скасувати
            </button>
          </div>
        </form>
      </AdminModal>
    </div>
  );
}
