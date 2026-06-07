/* global Masonry, imagesLoaded */
(function () {
  'use strict';

  /* ── Masonry init ── */
  const grid = document.getElementById('galleryGrid');
  let msnry;

  var isMobile = window.innerWidth <= 560;

  function revealItems() {
    document.querySelectorAll('.g-item').forEach(function (el, i) {
      setTimeout(function () { el.classList.add('visible'); }, 50 + i * 50);
    });
  }

  if (isMobile) {
    /* Mobile: flexbox handles layout, just reveal items */
    revealItems();
  } else if (typeof imagesLoaded !== 'undefined') {
    imagesLoaded(grid, function () {
      msnry = new Masonry(grid, {
        itemSelector: '.g-item:not(.hiding)',
        columnWidth: '.g-sizer',
        gutter: 18,
        percentPosition: true,
        transitionDuration: 0,
      });
      revealItems();
    });
  } else {
    msnry = new Masonry(grid, {
      itemSelector: '.g-item:not(.hiding)',
      columnWidth: '.g-sizer',
      gutter: 18,
      percentPosition: true,
      transitionDuration: 0,
    });
    revealItems();
  }

  /* ── Filter ── */
  const filterBtns = document.querySelectorAll('.gf-btn');
  const allItems   = document.querySelectorAll('.g-item');
  const emptyMsg   = document.getElementById('galleryEmpty');
  let currentFilter = 'all';

  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const filter = this.dataset.filter;
      if (filter === currentFilter) return;
      currentFilter = filter;

      filterBtns.forEach(function (b) { b.classList.remove('active'); });
      this.classList.add('active');

      let visibleCount = 0;
      allItems.forEach(function (item) {
        const match = filter === 'all' || item.dataset.cat === filter;
        if (match) {
          item.classList.remove('hiding');
          item.style.display = '';
          visibleCount++;
        } else {
          item.classList.add('hiding');
          item.classList.remove('visible');
          item.style.display = 'none';
        }
      });

      emptyMsg.style.display = visibleCount === 0 ? 'block' : 'none';

      /* Re-layout, then fade in visible items */
      if (msnry) { msnry.reloadItems(); msnry.layout(); }
      var idx = 0;
      allItems.forEach(function (item) {
        if (!item.classList.contains('hiding')) {
          item.classList.remove('visible');
          (function (el, delay) {
            setTimeout(function () { el.classList.add('visible'); }, delay);
          })(item, 30 + idx * 40);
          idx++;
        }
      });
    });
  });

  /* ── Build visible items list for lightbox ── */
  function getVisibleItems() {
    return Array.from(document.querySelectorAll('.g-item:not(.hiding)'));
  }

  /* ── Lightbox ── */
  const overlay  = document.getElementById('lbOverlay');
  const lbImg    = document.getElementById('lbImg');
  const lbSpinner = document.getElementById('lbSpinner');
  const lbCounter = document.getElementById('lbCounter');
  const lbCaption = document.getElementById('lbCaption');
  const lbClose  = document.getElementById('lbClose');
  const lbPrev   = document.getElementById('lbPrev');
  const lbNext   = document.getElementById('lbNext');

  let currentIndex = 0;

  function openLightbox(index) {
    const items = getVisibleItems();
    currentIndex = index;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    showSlide(currentIndex, items);
  }

  function closeLightbox() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
    lbImg.classList.remove('loaded');
    lbImg.src = '';
  }

  function showSlide(index, items) {
    items = items || getVisibleItems();
    if (!items.length) return;

    currentIndex = (index + items.length) % items.length;
    const item   = items[currentIndex];
    const img    = item.querySelector('img');
    const src    = img ? img.src : '';
    const alt    = img ? img.alt : '';

    lbImg.classList.remove('loaded');
    lbSpinner.style.display = 'block';
    lbImg.src = src;
    lbImg.alt = alt;
    lbImg.onload = function () {
      lbImg.classList.add('loaded');
      lbSpinner.style.display = 'none';
    };

    lbCounter.textContent = (currentIndex + 1) + ' / ' + items.length;
    lbCaption.textContent = alt;
    lbPrev.disabled = currentIndex === 0;
    lbNext.disabled = currentIndex === items.length - 1;
  }

  /* Click items to open */
  allItems.forEach(function (item) {
    item.addEventListener('click', function () {
      if (this.classList.contains('hiding')) return;
      const visible = getVisibleItems();
      const idx     = visible.indexOf(this);
      openLightbox(idx);
    });
  });

  lbClose.addEventListener('click', closeLightbox);
  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeLightbox();
  });

  lbPrev.addEventListener('click', function () {
    showSlide(currentIndex - 1);
  });
  lbNext.addEventListener('click', function () {
    showSlide(currentIndex + 1);
  });

  /* Keyboard */
  document.addEventListener('keydown', function (e) {
    if (!overlay.classList.contains('open')) return;
    if (e.key === 'Escape')      closeLightbox();
    if (e.key === 'ArrowLeft')   showSlide(currentIndex - 1);
    if (e.key === 'ArrowRight')  showSlide(currentIndex + 1);
  });

  /* Touch swipe */
  let touchStartX = 0;
  overlay.addEventListener('touchstart', function (e) {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });
  overlay.addEventListener('touchend', function (e) {
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      if (dx < 0) showSlide(currentIndex + 1);
      else         showSlide(currentIndex - 1);
    }
  });

})();
