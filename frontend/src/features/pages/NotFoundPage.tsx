import { Link } from 'react-router';
import { usePageTitle } from '@/hooks/usePageTitle';
import '@/styles/pages/content/content.css';

export default function NotFoundPage() {
  usePageTitle('Сторінку не знайдено — Coffee Time');
  return (
    <div className="pg-content">
      <div className="content-wrap" style={{ textAlign: 'center' }}>
        <div className="nf-code">404</div>
        <div className="content-hero">
          <h1>Сторінку не знайдено</h1>
          <p>Можливо, її перенесли. Зазирніть у меню — там точно є щось смачне ☕</p>
        </div>
        <Link to="/" className="content-cta">На головну</Link>{' '}
        <Link to="/menu" className="content-cta">До меню</Link>
      </div>
    </div>
  );
}
