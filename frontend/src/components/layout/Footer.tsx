import { Link } from 'react-router';
import { Icon } from '../Icon';

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer__inner">
        <div className="footer__col footer__brand">
          <Link to="/" className="footer-logo-link">
            <img src="/static/images/main/logo-cup.svg" alt="Coffee Time" className="footer-logo-img" />
          </Link>
          <p className="footer-tagline">Затишне кафе у серці міста</p>
          <div className="footer-socials">
            <a href="https://www.instagram.com/coffeetime_husiatyn/" target="_blank" rel="noopener noreferrer" aria-label="Instagram" className="social-btn">
              <img src="/static/images/icons/instagram.svg" alt="Instagram" />
            </a>
            <a href="#" target="_blank" rel="noopener noreferrer" aria-label="Facebook" className="social-btn">
              <img src="/static/images/icons/facebook.svg" alt="Facebook" />
            </a>
          </div>
        </div>

        <div className="footer__col">
          <h4>Години роботи</h4>
          <ul>
            <li><span className="footer-day">Пн–Пт</span> 8:00 – 20:00</li>
            <li><span className="footer-day">Субота</span> 10:00 – 20:00</li>
            <li><span className="footer-day">Неділя</span> 12:00 – 20:00</li>
          </ul>
        </div>

        <div className="footer__col">
          <h4>Контакти</h4>
          <ul>
            <li><a href="tel:+380989357337">+38 (098) 935-73-37</a></li>
            <li>
              <a
                href="https://www.google.com/maps/place/Coffee+Time/@49.0703593,26.2004433,17z/data=!4m6!3m5!1s0x47318487eb2721a5:0x989e59f6404162e4!8m2!3d49.0703593!4d26.2004433!16s%2Fg%2F11d_8c3725"
                target="_blank"
                rel="noopener noreferrer"
              >
                Ми на Google Maps
              </a>
            </li>
            <li><Link to="/about">Про нас</Link></li>
          </ul>
        </div>

        <div className="footer__col">
          <h4>Навігація</h4>
          <ul>
            <li><Link to="/">Головна</Link></li>
            <li><Link to="/menu">Меню</Link></li>
            <li><Link to="/gallery">Галерея</Link></li>
            <li><Link to="/reviews">Відгуки</Link></li>
          </ul>
        </div>
      </div>

      <div className="footer__bottom">
        <span>© {new Date().getFullYear()} Coffee Time. All Rights Reserved.</span>
        <span>
          Розроблено з <Icon name="heart" size={14} color="#e53935" /> у Гусятині
        </span>
      </div>
    </footer>
  );
}
