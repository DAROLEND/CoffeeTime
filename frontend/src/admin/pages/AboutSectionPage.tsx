import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api } from '@/api/client';
import { errorMessage, unwrap } from '@/api/errors';
import type { components } from '@/api/schema';
import { PageError, PageLoader } from '@/components/Spinner';
import { useAdminTitle } from '../AdminLayout';
import { useAdminToast } from '../AdminToast';
import { UploadZone, useImagePick } from '../components/ImageCrop';
import { adminKeys } from '../useAdmin';

type Settings = components['schemas']['AboutSettings'];
type Fields = Pick<Settings, 'about_title' | 'about_text' | 'about_founded_year' | 'about_menu_count' | 'about_rating'>;

const MAX_TEXT = 600;

function AboutForm({ settings }: { settings: Settings }) {
  const toast = useAdminToast();
  const client = useQueryClient();
  const photo = useImagePick();
  const [f, setF] = useState<Fields>(() => ({
    about_title: settings.about_title,
    about_text: settings.about_text,
    about_founded_year: settings.about_founded_year,
    about_menu_count: settings.about_menu_count,
    about_rating: settings.about_rating,
  }));
  const textRef = useRef<HTMLTextAreaElement>(null);
  const currentYear = new Date().getFullYear();

  useEffect(() => {
    const el = textRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [f.about_text]);

  const save = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      Object.entries(f).forEach(([k, v]) => fd.append(k, v));
      photo.append(fd, 'about_photo', 'about_photo_b64');
      return unwrap(api.POST('/api/admin/about-section', { body: {}, bodySerializer: () => fd }));
    },
    onSuccess: (data) => {
      toast('Зміни збережено', 'success');
      client.setQueryData(adminKeys.about, data);
      photo.reset();
      client.invalidateQueries({ queryKey: ['about'] });
      client.invalidateQueries({ queryKey: ['home'] });
      client.invalidateQueries({ queryKey: adminKeys.dashboard });
    },
    onError: (err) => toast(errorMessage(err), 'error'),
  });

  const set = (k: keyof Fields) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  const len = f.about_text.length;
  const previewYears = currentYear - (parseInt(f.about_founded_year, 10) || 2016);

  return (
    <div className="ab-grid">
      <div className="panel">
        <div className="panel-head">
          <h2 className="panel-title">Редагування</h2>
        </div>
        <form className="ab-form" onSubmit={submit}>
          <div className="ab-field">
            <label htmlFor="abTitle">Заголовок секції</label>
            <input type="text" id="abTitle" value={f.about_title} maxLength={120} required onChange={set('about_title')} />
          </div>
          <div className="ab-field">
            <label htmlFor="aboutText">Текст</label>
            <textarea ref={textRef} id="aboutText" maxLength={MAX_TEXT} value={f.about_text} onChange={set('about_text')} />
            <div className={`ab-char-counter${len >= 480 && len < 580 ? ' near' : ''}${len >= 580 ? ' full' : ''}`}>
              <span>{len}</span> / {MAX_TEXT}
            </div>
          </div>
          <div className="ab-row3">
            <div className="ab-field">
              <label htmlFor="abYear">Рік заснування</label>
              <input type="number" id="abYear" value={f.about_founded_year} min={1900} max={currentYear} onChange={set('about_founded_year')} />
              <small>
                Зараз відображається: <b>{settings.years_open} р.</b>
              </small>
            </div>
            <div className="ab-field">
              <label htmlFor="abMenu">Позицій меню</label>
              <input type="number" id="abMenu" value={f.about_menu_count} min={1} max={999} onChange={set('about_menu_count')} />
              <small>Показується як «{settings.about_menu_count}+»</small>
            </div>
            <div className="ab-field">
              <label htmlFor="abRating">Google рейтинг</label>
              <input type="number" id="abRating" value={f.about_rating} min={1} max={5} step={0.1} onChange={set('about_rating')} />
              <small>Показується як «{settings.about_rating}★»</small>
            </div>
          </div>
          <div className="ab-field">
            <label>
              Фото <small>(залиш порожнім щоб не міняти · JPG, PNG, WEBP · до 4 MB)</small>
            </label>
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
              💾 Зберегти зміни
            </button>
          </div>
        </form>
      </div>

      <div className="panel ab-preview-panel">
        <div className="panel-head">
          <h2 className="panel-title">Прев'ю</h2>
        </div>
        <div className="ab-preview">
          <p className="prev-label">Про нас</p>
          <h3 className="prev-title">{f.about_title}</h3>
          <p className="prev-text">{f.about_text}</p>
          <div className="prev-stats">
            <div className="prev-stat">
              <span className="prev-num">{previewYears}</span>
              <span className="prev-lbl">років на ринку</span>
            </div>
            <div className="prev-stat">
              <span className="prev-num">{f.about_menu_count || '0'}+</span>
              <span className="prev-lbl">позицій меню</span>
            </div>
            <div className="prev-stat">
              <span className="prev-num">{f.about_rating || '0'}★</span>
              <span className="prev-lbl">Google рейтинг</span>
            </div>
          </div>
          <div className="prev-photo">
            <img src={photo.preview ?? settings.about_photo} alt="" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AboutSectionPage() {
  useAdminTitle('Про нас');
  const q = useQuery({ queryKey: adminKeys.about, queryFn: () => unwrap(api.GET('/api/admin/about-section')) });
  if (q.isPending) return <PageLoader />;
  if (q.error) return <PageError message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  // The form keeps its own draft; a background refetch doesn't reset it.
  return <AboutForm settings={q.data} />;
}
