import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { UploadZone, useImagePick } from '../components/ImageCrop';
import { adminKeys } from '../useAdmin';

type Banner = components['schemas']['DessertBannerSettings'];
type Fields = Pick<Banner, 'dessert_banner_label' | 'dessert_banner_title' | 'dessert_banner_desc' | 'dessert_banner_btn'>;

const MAX_DESC = 300;

function BannerForm({ banner }: { banner: Banner }) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const photo = useImagePick();
  const [f, setF] = useState<Fields>(() => ({
    dessert_banner_label: banner.dessert_banner_label,
    dessert_banner_title: banner.dessert_banner_title,
    dessert_banner_desc: banner.dessert_banner_desc,
    dessert_banner_btn: banner.dessert_banner_btn,
  }));
  const descRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [f.dessert_banner_desc]);

  const save = useMutation({
    mutationFn: (clearImage: boolean) => {
      const fd = new FormData();
      Object.entries(f).forEach(([k, v]) => fd.append(k, v));
      if (clearImage) fd.append('clear_image', 'true');
      else photo.append(fd, 'dessert_banner_image', 'dessert_banner_image_b64');
      return unwrap(api.POST('/api/admin/dessert-banner', { body: {}, bodySerializer: () => fd }));
    },
    onSuccess: (data, clearImage) => {
      toast(clearImage ? 'Фото видалено — показується рандомний десерт' : 'Зміни збережено', 'success');
      client.setQueryData(adminKeys.banner, data);
      photo.reset();
      client.invalidateQueries({ queryKey: ['home'] });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const set = (k: keyof Fields) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate(false);
  };
  const len = f.dessert_banner_desc.length;
  const previewPhoto = photo.preview ?? (banner.has_custom_image ? banner.image : banner.random_image);
  const descLines = f.dessert_banner_desc.split('\n');

  return (
    <>
      <div className="db-grid">
        <div className="panel">
          <div className="panel-head">
            <h2 className="panel-title">Редагування банера</h2>
          </div>
          <form className="db-form" onSubmit={submit}>
            <div className="db-fields-row">
              <div className="db-field">
                <label htmlFor="dbLabel">Мітка над заголовком</label>
                <input type="text" id="dbLabel" value={f.dessert_banner_label} maxLength={60} onChange={set('dessert_banner_label')} />
              </div>
              <div className="db-field">
                <label htmlFor="dbTitle">Заголовок</label>
                <input type="text" id="dbTitle" value={f.dessert_banner_title} maxLength={80} required onChange={set('dessert_banner_title')} />
              </div>
              <div className="db-field">
                <label htmlFor="dbBtn">Текст кнопки</label>
                <input type="text" id="dbBtn" value={f.dessert_banner_btn} maxLength={60} onChange={set('dessert_banner_btn')} />
              </div>
            </div>
            <div className="db-field">
              <label htmlFor="dbDesc">Опис</label>
              <textarea ref={descRef} id="dbDesc" maxLength={MAX_DESC} value={f.dessert_banner_desc} onChange={set('dessert_banner_desc')} />
              <div className={`db-char-counter${len >= 220 && len < 270 ? ' near' : ''}${len >= 270 ? ' full' : ''}`}>
                <span>{len}</span> / {MAX_DESC}
              </div>
            </div>
            <div className="db-field">
              <label>
                Фото банера <small>(залиш порожнім щоб не міняти · JPG, PNG, WEBP · до 4 MB)</small>
              </label>
              {banner.has_custom_image && banner.image ? (
                <div className="db-current-img">
                  <img src={banner.image} alt="" />
                  <div className="db-current-img-meta">
                    <span>Поточне фото</span>
                    <button
                      type="button"
                      className="db-btn-clear"
                      disabled={save.isPending}
                      onClick={() => window.confirm('Видалити фото? Буде показуватись рандомний десерт.') && save.mutate(true)}
                    >
                      ✕ Видалити (показувати рандомний)
                    </button>
                  </div>
                </div>
              ) : (
                <div className="db-hint-random">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B4513" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
                  <span>
                    Зараз відображається <strong>рандомний десерт із меню</strong>. Завантаж фото щоб зафіксувати конкретне.
                  </span>
                </div>
              )}
              <UploadZone
                pick={photo}
                placeholder={
                  <>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#aaa" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
                    <span>Оберіть або перетягніть фото</span>
                  </>
                }
              />
            </div>
            <div style={{ padding: '0 0 4px' }}>
              <button type="submit" className="btn btn-primary" disabled={save.isPending}>
                Зберегти зміни
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="panel db-preview-panel">
        <div className="panel-head">
          <h2 className="panel-title">Прев'ю — як виглядає на сайті</h2>
          {!banner.has_custom_image && <p className="db-preview-note">* Фото — рандомний десерт, міняється при кожному завантаженні</p>}
        </div>
        <div className="db-preview-wrap">
          <div className="db-preview">
            <div className="db-prev-text">
              <p className="db-prev-label">{f.dessert_banner_label}</p>
              <h3 className="db-prev-title">{f.dessert_banner_title}</h3>
              <p className="db-prev-desc">
                {descLines.map((line, i) => (
                  <Fragment key={i}>
                    {i > 0 && <br />}
                    {line}
                  </Fragment>
                ))}
              </p>
              <span className="db-prev-btn">{f.dessert_banner_btn}</span>
            </div>
            <div className="db-prev-photo">{previewPhoto && <img src={previewPhoto} alt="" />}</div>
          </div>
        </div>
      </div>
    </>
  );
}

export default function DessertBannerPage() {
  useAdminTitle('Десерт дня');
  const q = useQuery({ queryKey: adminKeys.banner, queryFn: () => unwrap(api.GET('/api/admin/dessert-banner')) });
  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  return <BannerForm banner={q.data} />;
}
