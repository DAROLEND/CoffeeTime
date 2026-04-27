document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.slider').forEach(initSlider);
});

function initSlider(root) {
  const isCategory = root.classList.contains('category-slider');
  const slides = Array.from(root.querySelectorAll('.slide'));
  const prev   = root.querySelector('.arrow.left');
  const next   = root.querySelector('.arrow.right');
  const dots   = isCategory ? [] : Array.from(root.querySelectorAll('.dot'));
  const track  = isCategory ? root.querySelector('.slider-track') : null;

  if (!slides.length) return;

  let idx   = 0;
  let timer = null;

  setTimeout(() => {
    const gap       = parseFloat(getComputedStyle(slides[0]).marginRight) || 0;
    const cardWidth = slides[0].getBoundingClientRect().width + gap;
    const visible   = 3;

    // Reveal cards entering the category slider view
    function revealVisible(startIdx) {
      for (let i = startIdx; i < Math.min(startIdx + visible + 1, slides.length); i++) {
        const item = slides[i]?.querySelector('.drink-item, .food-item, .dessert-item');
        if (!item || item.classList.contains('visible')) continue;
        const delay = (i - startIdx) * 90;
        setTimeout(() => item.classList.add('visible'), delay);
      }
    }

    function show(n) {
      if (isCategory) {
        const max = slides.length - visible;
        if (slides.length <= visible) {
          idx = 0;
        } else {
          idx = n > max ? 0 : n < 0 ? max : n;
        }
        track.style.transform = `translateX(${-idx * cardWidth}px)`;
        revealVisible(idx);
      } else {
        idx = ((n % slides.length) + slides.length) % slides.length;
        slides.forEach((s, i) => s.classList.toggle('active', i === idx));
        dots.forEach((d, i)   => d.classList.toggle('active', i === idx));
      }
    }

    // Arrows
    if (prev) prev.addEventListener('click', () => { show(idx - 1); if (isCategory) resetCatProgress(); else startHeroTimer(); });
    if (next) next.addEventListener('click', () => { show(idx + 1); if (isCategory) resetCatProgress(); else startHeroTimer(); });

    /* ── HERO SLIDER ─────────────────────────────── */
    if (!isCategory) {
      const INTERVAL = 5000;

      const startHeroTimer = () => {
        clearInterval(timer);
        timer = setInterval(() => show(idx + 1), INTERVAL);
      };

      // Pause on hover, resume on leave
      root.addEventListener('mouseenter', () => clearInterval(timer));
      root.addEventListener('mouseleave', () => startHeroTimer());

      // Dot clicks
      dots.forEach((d, i) => d.addEventListener('click', () => { show(i); startHeroTimer(); }));

      // Click left half = prev, click right half = next
      root.addEventListener('click', e => {
        if (e.target.closest('a, button')) return;
        const half = root.getBoundingClientRect().width / 2;
        show(idx + ((e.clientX - root.getBoundingClientRect().left) >= half ? 1 : -1));
        startHeroTimer();
      });

      // Touch swipe
      let touchX = 0;
      root.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
      root.addEventListener('touchend', e => {
        const diff = touchX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 40) { show(idx + (diff > 0 ? 1 : -1)); startHeroTimer(); }
      }, { passive: true });

      show(0);
      startHeroTimer();

      // expose so arrow listeners can call it
      window._startHeroTimer = startHeroTimer;

    /* ── CATEGORY SLIDER ─────────────────────────── */
    } else {
      const CAT_INTERVAL = 4000;
      let catTimer       = null;
      let paused         = false;

      // Progress bar element
      const progressBar = document.createElement('div');
      progressBar.className = 'cat-progress-bar';
      root.appendChild(progressBar);

      function resetCatProgress() {
        if (paused) return;
        progressBar.style.transition = 'none';
        progressBar.style.width      = '0%';
        // Double rAF to let the style flush before starting transition
        requestAnimationFrame(() => requestAnimationFrame(() => {
          progressBar.style.transition = `width ${CAT_INTERVAL}ms linear`;
          progressBar.style.width      = '100%';
        }));
      }

      function startCatTimer() {
        clearInterval(catTimer);
        catTimer = setInterval(() => {
          show(idx + 1);
          resetCatProgress();
        }, CAT_INTERVAL);
      }

      // Pause on hover
      root.addEventListener('mouseenter', () => {
        paused = true;
        clearInterval(catTimer);
        // Freeze progress bar in place
        const computed = getComputedStyle(progressBar).width;
        progressBar.style.transition = 'none';
        progressBar.style.width      = computed;
      });
      root.addEventListener('mouseleave', () => {
        paused = false;
        // Restart: reset bar and timer
        resetCatProgress();
        startCatTimer();
      });

      // Dot clicks (category has none by default, but safe)
      dots.forEach((d, i) => d.addEventListener('click', () => {
        show(i);
        resetCatProgress();
        startCatTimer();
      }));

      show(0);
      startCatTimer();
      resetCatProgress();
    }
  }, 50);
}
