import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { createPortal } from 'react-dom';
import { useSearchParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useEscape } from '@/hooks/useScrollLock';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { readAsDataUrl } from '../components/ImageCrop';
import { adminKeys } from '../useAdmin';

type Photo = components['schemas']['AdminGalleryImage'];
type Cat = Photo['category'];
const CAT_LABEL: Record<Cat, string> = { food: 'Їжа', interior: "Інтер'єр" };

export default function GalleryPage() {
  useAdminTitle('Галерея');
  const toast = useAdminToast();
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const cat = params.get('cat') ?? '';
  const q = useQuery({ queryKey: adminKeys.gallery(cat), queryFn: () => unwrap(api.GET('/api/admin/gallery', { params: { query: { cat } } })) });

  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [category, setCategory] = useState<Cat>('food');
  const [alt, setAlt] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [removing, setRemoving] = useState<Set<number>>(new Set());
  const [lightbox, setLightbox] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  useEscape(!!lightbox, () => setLightbox(null));

  useEffect(() => {
    let alive = true;
    Promise.all(files.slice(0, 8).map(readAsDataUrl)).then((urls) => alive && setPreviews(urls));
    return () => {
      alive = false;
    };
  }, [files]);

  const refresh = () => {
    client.invalidateQueries({ queryKey: ['admin', 'gallery'] });
    client.invalidateQueries({ queryKey: adminKeys.dashboard });
    client.invalidateQueries({ queryKey: ['gallery'] });
  };

  const upload = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      files.forEach((f) => fd.append('photos', f));
      fd.append('category', category);
      fd.append('alt', alt);
      return unwrap(api.POST('/api/admin/gallery', { body: {} as never, bodySerializer: () => fd }));
    },
    onSuccess: (res) => {
      setErrors(res.errors);
      if (res.uploaded) toast(`Завантажено ${res.uploaded} фото!`, 'success');
      setFiles([]);
      setAlt('');
      if (inputRef.current) inputRef.current.value = '';
      refresh();
    },
    onError: (err) => setErrors([errorMessage(err)]),
  });

  const patch = useMutation({
    mutationFn: ({ id, category: c }: { id: number; category: Cat }) => unwrap(api.PATCH('/api/admin/gallery/{photo_id}', { params: { path: { photo_id: id } }, body: { category: c } })),
    onSuccess: (_, { category: c }) => {
      toast(`Категорію змінено на: ${CAT_LABEL[c]}`, 'success');
      refresh();
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const remove = useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/api/admin/gallery/{photo_id}', { params: { path: { photo_id: id } } })),
    onMutate: (id) => setRemoving((s) => new Set(s).add(id)),
    onSuccess: () => {
      toast('Фото видалено', 'success');
      window.setTimeout(refresh, 350);
    },
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
    if (files.length) upload.mutate();
  };

  const pickFiles = (list: FileList | null) => {
    if (!list?.length) return;
    setErrors([]);
    setFiles(Array.from(list));
  };

  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const { images, counts } = q.data;

  return (
    <>
      {errors.map((e) => (
        <div key={e} className="alert alert-error" style={{ marginBottom: 8 }}>
          {e}
        </div>
      ))}

      <div className="section-head" style={{ marginBottom: 18 }}>
        <h2 className="section-title">Фото галереї</h2>
        <span style={{ color: '#999', fontSize: 13 }}>{counts.all} фото</span>
      </div>

      <form onSubmit={submit}>
        <div
          className={`gallery-upload-zone${dragOver ? ' drag-over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            pickFiles(e.dataTransfer.files);
          }}
        >
          <input ref={inputRef} type="file" accept="image/*" multiple aria-label="Обрати фото" onChange={(e) => pickFiles(e.target.files)} />
          <div className="gallery-upload-icon">
            <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#d4a96a" strokeWidth="1.5" strokeLinecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
          </div>
          <p className="gallery-upload-title">Перетягніть фото сюди</p>
          <p className="gallery-upload-sub">або натисніть для вибору · PNG, JPG, WebP до 5 МБ</p>
          <div className="gallery-upload-previews">
            {files.length > 0 &&
              previews.map((src, i) => <img key={i} src={src} alt="" className="upload-preview-thumb" />)}
          </div>
        </div>

        {files.length > 0 && (
          <div className="gallery-upload-options" style={{ display: 'flex' }}>
            <div className="guo-field">
              <label className="im-label">Категорія</label>
              <div className="guo-cat-btns">
                {(['food', 'interior'] as const).map((c) => (
                  <label key={c} className="guo-cat-btn">
                    <input type="radio" name="category" value={c} checked={category === c} onChange={() => setCategory(c)} />
                    <span>{CAT_LABEL[c]}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="guo-field">
              <label className="im-label" htmlFor="altInput">
                Підпис (необов'язково)
              </label>
              <input type="text" id="altInput" className="im-control" placeholder="напр. Піца маргарита" value={alt} onChange={(e) => setAlt(e.target.value)} />
            </div>
            <button type="submit" className="im-btn-save" style={{ alignSelf: 'flex-end' }} disabled={upload.isPending}>
              {upload.isPending ? 'Завантаження…' : 'Завантажити'}
            </button>
          </div>
        )}
      </form>

      <div className="cat-tabs" style={{ margin: '20px 0 16px' }}>
        {(
          [
            ['', 'Всі', counts.all],
            ['food', 'Їжа', counts.food],
            ['interior', "Інтер'єр", counts.interior],
          ] as const
        ).map(([val, label, count]) => (
          <button key={val} type="button" className={`cat-tab${cat === val ? ' active' : ''}`} onClick={() => setParams(val ? { cat: val } : {})}>
            {label}
            <span className="cat-tab-count">{count}</span>
          </button>
        ))}
      </div>

      {!images.length ? (
        <p style={{ color: '#bbb', textAlign: 'center', padding: 48, fontSize: 14 }}>Галерея порожня</p>
      ) : (
        <div className="gallery-grid">
          {images.map((img) => (
            <div key={img.id} className={`gallery-cell${removing.has(img.id) ? ' deleting' : ''}`} onClick={() => setLightbox(img.url)}>
              <img src={img.url} alt={img.alt} loading="lazy" />
              <div className={`gc-badge gc-badge--${img.category}`}>{CAT_LABEL[img.category]}</div>
              <div className="photo-overlay">
                <button
                  className="gc-action-btn gc-cat-toggle"
                  title="Змінити категорію"
                  aria-label="Змінити категорію"
                  onClick={(e) => {
                    e.stopPropagation();
                    patch.mutate({ id: img.id, category: img.category === 'food' ? 'interior' : 'food' });
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="17 1 21 5 17 9" /><path d="M3 11V9a4 4 0 0 1 4-4h14" /><polyline points="7 23 3 19 7 15" /><path d="M21 13v2a4 4 0 0 1-4 4H3" /></svg>
                </button>
                <button
                  className="delete-photo-btn"
                  title="Видалити"
                  aria-label="Видалити фото"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Видалити це фото?')) remove.mutate(img.id);
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /></svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {lightbox &&
        createPortal(
          <div
            role="dialog"
            aria-label="Перегляд фото"
            onClick={() => setLightbox(null)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.9)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out', backdropFilter: 'blur(4px)' }}
          >
            <img src={lightbox} alt="" style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 10, boxShadow: '0 8px 48px rgba(0,0,0,.7)' }} />
          </div>,
          document.body,
        )}
    </>
  );
}
