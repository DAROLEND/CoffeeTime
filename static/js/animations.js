/* =====================================================
   Coffee Time — Animations & Interactions
===================================================== */

(function () {
  'use strict';

  /* ── 1. SCROLL REVEAL ──────────────────────────── */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.12 });

  // Додаємо .reveal до елементів що ще не мають власного scroll-reveal
  const revealTargets = [
    '.gallery-item',
    '.rv-card',
    '.review-card',
    '.benefit-block',
    '.rv-form-wrap',
    '.rv-auth-prompt',
    '.home-section h2',
    '.home-section .section-subtitle',
    '.dessert-banner__text',
    '.desserts-cta',
  ];
  document.querySelectorAll(revealTargets.join(',')).forEach(el => {
    // Не дублюємо з існуючим scroll-reveal.js
    if (!el.classList.contains('food-item') &&
        !el.classList.contains('drink-item') &&
        !el.classList.contains('dessert-item')) {
      el.classList.add('reveal');
      revealObserver.observe(el);
    }
  });

  // About section — slide in from sides
  const aboutContent = document.querySelector('.about-content');
  const aboutPhoto   = document.querySelector('.about-photo');
  if (aboutContent) { aboutContent.classList.add('reveal-left');  revealObserver.observe(aboutContent); }
  if (aboutPhoto)   { aboutPhoto.classList.add('reveal-right');   revealObserver.observe(aboutPhoto); }

  /* ── 2. HERO PARALLAX ──────────────────────────── */
  const heroSlider = document.querySelector('.hero .slider');
  if (heroSlider) {
    const heroH = heroSlider.offsetHeight;
    window.addEventListener('scroll', () => {
      const scrolled = window.scrollY;
      if (scrolled > heroH) return;
      const shift = (scrolled * 0.28).toFixed(1);
      heroSlider.querySelectorAll('.slide').forEach(s => {
        s.style.backgroundPositionY = `calc(50% + ${shift}px)`;
      });
    }, { passive: true });
  }

  /* ── 4. SCROLL TO TOP ──────────────────────────── */
  const scrollBtn = document.querySelector('.scroll-top-btn');
  if (scrollBtn) {
    window.addEventListener('scroll', () => {
      scrollBtn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ── 5. TOAST NOTIFICATION ──────────────────────── */
  let toastEl = null;
  let toastTimer = null;
  window.showToast = function (msg) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'ct-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2200);
  };

  /* ── 6. NAVBAR SHADOW ON SCROLL ─────────────────── */
  const header = document.querySelector('.site-header');
  if (header) {
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll(); // Initial check
  }

  /* ── 3. CART BOUNCE + BADGE POP ─────────────────── */
  function animateCart() {
    const wrapper = document.querySelector('.cart-wrapper');
    const badge   = document.querySelector('.cart-count');
    if (wrapper) {
      wrapper.classList.remove('bounce');
      void wrapper.offsetWidth; // reflow to restart animation
      wrapper.classList.add('bounce');
      setTimeout(() => wrapper.classList.remove('bounce'), 420);
    }
    if (badge) {
      badge.classList.remove('pop');
      void badge.offsetWidth;
      badge.classList.add('pop');
      setTimeout(() => badge.classList.remove('pop'), 320);
    }
  }

  // Перехоплюємо кліки на кнопках "Додати в кошик" (homepage)
  document.addEventListener('click', e => {
    if (e.target.matches('.btn-add-cart') || e.target.closest('.btn-add-cart')) {
      setTimeout(animateCart, 300); // Чекаємо поки badge оновиться
    }
  });

  /* ── 4. ВИДАЛЕННЯ ТОВАРУ З КОШИКА ───────────────── */
  document.querySelectorAll('.remove-item').forEach(link => {
    link.addEventListener('click', function (e) {
      const row = this.closest('.cart-item');
      if (row) {
        e.preventDefault();
        row.classList.add('removing');
        const href = this.href;
        setTimeout(() => { window.location = href; }, 320);
      }
    });
  });

  /* ── 5. COUNT-UP ДЛЯ СТАТИСТИКИ ─────────────────── */
  const aboutStats = document.querySelector('.about-stats');
  if (aboutStats) {
    const statsObserver = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      entries[0].target.querySelectorAll('.stat-number[data-count]').forEach(el => {
        const target   = parseFloat(el.dataset.count);
        const suffix   = el.dataset.suffix   ?? '';
        const decimals = parseInt(el.dataset.decimals ?? '0');
        let current = 0;
        const step = target / 55;
        const interval = setInterval(() => {
          current = Math.min(current + step, target);
          el.textContent = current.toFixed(decimals) + suffix;
          if (current >= target) clearInterval(interval);
        }, 18);
      });
      statsObserver.disconnect();
    }, { threshold: 0.5 });
    statsObserver.observe(aboutStats);
  }

  /* ── 6. РЕЙТИНГ-БАРИ АНІМАЦІЯ ───────────────────── */
  const barsSection = document.querySelector('.rv-bars');
  if (barsSection) {
    const barObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.querySelectorAll('.rv-bar-fill').forEach(bar => {
          const target = bar.getAttribute('data-width');
          if (target !== null) bar.style.width = target + '%';
        });
        barObserver.unobserve(entry.target);
      });
    }, { threshold: 0.3 });
    barObserver.observe(barsSection);
  }

  /* ── 7. COUNT-UP ДЛЯ СЕРЕДНЬОГО РЕЙТИНГУ ────────── */
  const ratingNum = document.querySelector('.rv-avg-number');
  if (ratingNum) {
    const target = parseFloat(ratingNum.dataset.value || ratingNum.textContent) || 0;
    ratingNum.textContent = '0.0';
    let current = 0;
    const numObserver = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      const step = target / 60;
      const interval = setInterval(() => {
        current = Math.min(current + step, target);
        ratingNum.textContent = current.toFixed(1);
        if (current >= target) clearInterval(interval);
      }, 20);
      numObserver.disconnect();
    }, { threshold: 0.5 });
    numObserver.observe(ratingNum);
  }

  /* ── 7. GALLERY OVERLAY + LIGHTBOX ──────────────── */
  const galleryItems = document.querySelectorAll('.gallery-item');
  if (galleryItems.length) {
    // Додаємо overlay з іконкою лупи
    galleryItems.forEach((item, i, all) => {
      if (!item.querySelector('.gallery-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'gallery-overlay';
        overlay.innerHTML = '<span class="gallery-zoom">🔍</span>';
        item.appendChild(overlay);
      }

      const img = item.querySelector('img');
      if (!img) return;

      item.addEventListener('click', () => {
        openLightbox(Array.from(all).map(el => el.querySelector('img')), i);
      });
    });

    function openLightbox(imgs, startIdx) {
      let cur = startIdx;

      const lb = document.createElement('div');
      lb.className = 'lightbox';
      lb.innerHTML = `
        <button class="lb-close" style="position:absolute;top:20px;right:28px;
          font-size:32px;padding:8px 14px;z-index:1">✕</button>
        <button class="lb-prev" style="position:absolute;left:20px;
          font-size:28px;padding:10px 16px">‹</button>
        <img src="${imgs[cur].src}" alt="">
        <button class="lb-next" style="position:absolute;right:20px;
          font-size:28px;padding:10px 16px">›</button>
      `;
      document.body.appendChild(lb);
      document.body.style.overflow = 'hidden';

      const lbImg = lb.querySelector('img');
      const update = () => { lbImg.src = imgs[cur].src; };

      lb.querySelector('.lb-close').addEventListener('click', close);
      lb.querySelector('.lb-prev').addEventListener('click', (e) => {
        e.stopPropagation();
        cur = (cur - 1 + imgs.length) % imgs.length;
        update();
      });
      lb.querySelector('.lb-next').addEventListener('click', (e) => {
        e.stopPropagation();
        cur = (cur + 1) % imgs.length;
        update();
      });
      lb.addEventListener('click', e => { if (e.target === lb) close(); });

      function onKey(e) {
        if (e.key === 'Escape')      { close(); }
        if (e.key === 'ArrowLeft')   { cur = (cur - 1 + imgs.length) % imgs.length; update(); }
        if (e.key === 'ArrowRight')  { cur = (cur + 1) % imgs.length; update(); }
      }
      document.addEventListener('keydown', onKey);

      function close() {
        lb.remove();
        document.body.style.overflow = '';
        document.removeEventListener('keydown', onKey);
      }
    }
  }

  /* ── 8. SHAKE ФОРМИ ПРИ ПОМИЛЦІ ─────────────────── */
  const authError = document.querySelector('.auth-error, .auth-message.error');
  if (authError) {
    const form = authError.closest('form') || authError.closest('.auth-card')?.querySelector('form');
    if (form) {
      form.classList.add('shake');
      setTimeout(() => form.classList.remove('shake'), 500);
    }
  }

  /* ── 9. LOADING НА SUBMIT ───────────────────────── */
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function () {
      const btn = this.querySelector('.auth-btn, .form-btn, [type="submit"]');
      if (btn) {
        btn.classList.add('loading');
        // Знімаємо після редиректу якщо щось пішло не так
        setTimeout(() => btn.classList.remove('loading'), 8000);
      }
    });
  });

  /* ── 10. ЗІРКИ У ФОРМІ ВІДГУКУ ──────────────────── */
  const starPicker = document.getElementById('starPicker');
  if (starPicker) {
    // Sync із reviews.js — додаємо тільки .just-selected анімацію
    starPicker.addEventListener('click', e => {
      const star = e.target.closest('.rv-star');
      if (star) {
        star.classList.add('just-selected');
        setTimeout(() => star.classList.remove('just-selected'), 320);
      }
    });
  }


})();
