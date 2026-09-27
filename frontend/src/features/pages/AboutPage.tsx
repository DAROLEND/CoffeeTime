import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { api } from '@/api/client';
import { unwrap } from '@/api/errors';
import { qk } from '@/api/queries';
import { PageLoader } from '@/components/Spinner';
import { Reveal } from '@/components/Reveal';
import { usePageTitle } from '@/hooks/usePageTitle';
import { plural } from '@/lib/format';
import '@/styles/pages/content/content.css';

/**
 * /about and /contact. These were empty placeholder pages in the old
 * site; now they show the "About us" content editable in the admin panel
 * (site_settings) plus the café's hours and contacts.
 */
export default function AboutPage({ variant }: { variant: 'about' | 'contact' }) {
  usePageTitle(variant === 'about' ? 'Про нас — Coffee Time' : 'Контакти — Coffee Time');
  const about = useQuery({ queryKey: qk.about, queryFn: () => unwrap(api.GET('/api/about')) });
  if (about.isPending) return <PageLoader />;
  const a = about.data;

  return (
    <div className="pg-content">
      <div className="content-wrap">
        <div className="content-hero">
          <h1>{variant === 'about' ? 'Про Coffee Time' : 'Контакти'}</h1>
          <p>{variant === 'about' ? 'Затишне кафе у серці Гусятина' : 'Завжди раді бачити вас у Coffee Time'}</p>
        </div>

        {a && variant === 'about' && (
          <div className="about-grid">
            <Reveal base="reveal-left">
              <h2>{a.title}</h2>
              <p className="about-text">{a.text}</p>
              <div className="about-facts">
                <div className="about-fact"><strong>{a.years_open}</strong><span>{plural(a.years_open, ['рік', 'роки', 'років'])} на ринку</span></div>
                <div className="about-fact"><strong>{a.menu_count}+</strong><span>позицій меню</span></div>
                <div className="about-fact"><strong>{a.rating}★</strong><span>Google рейтинг</span></div>
              </div>
            </Reveal>
            <Reveal base="reveal-right">
              <img src={a.photo} alt="Coffee Time кафе" />
            </Reveal>
          </div>
        )}

        <div className="contact-grid">
          <Reveal className="contact-card">
            <h3>Години роботи</h3>
            <ul>
              <li>Пн–Пт: 8:00 – 20:00</li>
              <li>Субота: 10:00 – 20:00</li>
              <li>Неділя: 12:00 – 20:00</li>
            </ul>
          </Reveal>
          <Reveal className="contact-card">
            <h3>Звʼязок</h3>
            <p><a href="tel:+380989357337">+38 (098) 935-73-37</a></p>
            <p><a href="https://www.instagram.com/coffeetime_husiatyn/" target="_blank" rel="noopener noreferrer">Instagram</a></p>
          </Reveal>
          <Reveal className="contact-card">
            <h3>Як нас знайти</h3>
            <p>м. Гусятин</p>
            <p>
              <a href="https://www.google.com/maps/place/Coffee+Time/@49.0703593,26.2004433,17z" target="_blank" rel="noopener noreferrer">
                Ми на Google Maps →
              </a>
            </p>
          </Reveal>
        </div>

        <div style={{ textAlign: 'center', marginTop: 48 }}>
          <Link to="/menu" className="content-cta">Переглянути меню →</Link>
        </div>
      </div>
    </div>
  );
}
