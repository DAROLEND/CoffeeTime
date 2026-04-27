/* =====================================================
   Coffee Time — Menu Page JS
   - Category tabs (no reload)
   - Live search with 300 ms debounce
   - AJAX add-to-cart + cart badge bounce
   - Item detail modal with quantity / weight selector
   - Cake items: weight-based ordering
   - Sticky tab shadow on scroll
   - IntersectionObserver stagger reveal
   - Toast notifications
===================================================== */
(function () {
  'use strict';

  /* ── State ── */
  var cartKeys = window._cartKeys ? window._cartKeys.slice() : [];

  /* ── DOM refs ── */
  var tabsWrap    = document.getElementById('menuTabsWrap');
  var tabs        = Array.from(document.querySelectorAll('.menu-tab'));
  var sections    = Array.from(document.querySelectorAll('.menu-cat-section'));
  var searchInput = document.getElementById('menuSearch');
  var clearBtn    = document.getElementById('menuSearchClear');
  var toast       = document.getElementById('menuToast');
  var toastTimer  = null;

  /* ── Helpers ── */
  function cartKey(cat, id) { return cat + '_' + id; }
  function inCart(cat, id)  { return cartKeys.indexOf(cartKey(cat, id)) !== -1; }
  function addCartKey(cat, id) {
    var k = cartKey(cat, id);
    if (cartKeys.indexOf(k) === -1) cartKeys.push(k);
  }

  function showToast(msg) {
    toast.innerHTML =
      '<span>' + msg + '</span>' +
      '<a href="cart.php" class="toast-cart-link">Перейти до кошику \u2192</a>';
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 3500);
  }

  /* ── Category switch ── */
  function switchToCategory(cat) {
    tabs.forEach(function (t) {
      var active = t.dataset.cat === cat;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    sections.forEach(function (s) {
      s.classList.toggle('active', s.dataset.cat === cat);
    });
    try {
      var u = new URL(window.location.href);
      u.searchParams.set('category', cat);
      history.replaceState(null, '', u.toString());
    } catch (e) { /* ignore */ }
    if (searchInput && searchInput.value.trim()) {
      runSearch(searchInput.value.trim().toLowerCase());
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      switchToCategory(this.dataset.cat);
      this.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      if (searchInput && searchInput.value) {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        clearSearch();
      }
    });
  });

  /* ── Sticky shadow + tab scroll fade ── */
  var tabsNav = document.getElementById('menuTabs');
  function updateTabFade() {
    if (!tabsWrap || !tabsNav) return;
    var atEnd = tabsNav.scrollLeft + tabsNav.clientWidth >= tabsNav.scrollWidth - 4;
    tabsWrap.classList.toggle('at-end', atEnd);
  }
  if (tabsNav) {
    tabsNav.addEventListener('scroll', updateTabFade, { passive: true });
    updateTabFade();
  }
  if (tabsWrap) {
    window.addEventListener('scroll', function () {
      tabsWrap.classList.toggle('stuck', window.scrollY > 10);
    }, { passive: true });
  }

  /* ── Search ── */
  var searchTimer = null;

  function runSearch(q) {
    var activeSection = sections.find(function (s) { return s.classList.contains('active'); });
    if (!activeSection) return;
    var cards = Array.from(activeSection.querySelectorAll('.menu-card'));
    var visibleCount = 0;
    cards.forEach(function (card) {
      var match = (card.dataset.name || '').indexOf(q) !== -1 ||
                  (card.dataset.desc || '').indexOf(q) !== -1;
      card.classList.toggle('search-hidden', !match);
      if (match) visibleCount++;
    });
    var sem = activeSection.querySelector('.menu-search-empty');
    if (sem) {
      if (visibleCount === 0) {
        var txt = sem.querySelector('.mse-text');
        if (txt) txt.textContent = '\u041d\u0456\u0447\u043e\u0433\u043e \u043d\u0435 \u0437\u043d\u0430\u0439\u0434\u0435\u043d\u043e \u0437\u0430 \u0437\u0430\u043f\u0438\u0442\u043e\u043c \u00ab' + q + '\u00bb';
        sem.style.display = 'block';
      } else {
        sem.style.display = 'none';
      }
    }
  }

  function clearSearch() {
    sections.forEach(function (section) {
      section.querySelectorAll('.menu-card').forEach(function (c) {
        c.classList.remove('search-hidden');
      });
      var sem = section.querySelector('.menu-search-empty');
      if (sem) sem.style.display = 'none';
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var q = this.value.trim().toLowerCase();
      clearBtn.style.display = q ? 'flex' : 'none';
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        if (q) { runSearch(q); } else { clearSearch(); }
      }, 300);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      searchInput.value = '';
      clearBtn.style.display = 'none';
      clearSearch();
      searchInput.focus();
    });
  }

  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('mse-reset')) {
      searchInput.value = '';
      clearBtn.style.display = 'none';
      clearSearch();
    }
  });

  /* ── IntersectionObserver stagger reveal ── */
  if (typeof IntersectionObserver !== 'undefined') {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('io-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    sections.forEach(function (section) {
      Array.from(section.querySelectorAll('.menu-card')).forEach(function (card, i) {
        if (i >= 12) {
          card.classList.add('io-hidden');
          card.style.transitionDelay = ((i - 12) * 0.06) + 's';
          io.observe(card);
        }
      });
    });
  }

  /* ── Cart badge update ── */
  function updateCartBadge(count) {
    var cartWrap = document.querySelector('.cart-wrapper');
    var badge    = document.querySelector('.cart-count');
    if (!badge && cartWrap) {
      badge = document.createElement('span');
      badge.className = 'cart-count';
      var anchor = cartWrap.querySelector('a');
      if (anchor) anchor.appendChild(badge);
    }
    if (badge) {
      badge.textContent = count;
      badge.classList.remove('cart-badge-bounce');
      void badge.offsetWidth;
      badge.classList.add('cart-badge-bounce');
      setTimeout(function () { badge.classList.remove('cart-badge-bounce'); }, 500);
    }
  }

  /* ── AJAX add-to-cart (regular) ── */
  function addItemToCart(cat, id, name, qty, cb) {
    var fd = new FormData();
    fd.append('category', cat);
    fd.append('id', id);
    fd.append('quantity', qty || 1);
    fetch('../forms/add_to_cart.php', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { cb(false, 0); return; }
        addCartKey(cat, id);
        updateCartBadge(data.count);
        showToast('\u2713 \u00ab' + name + '\u00bb \u0434\u043e\u0434\u0430\u043d\u043e \u0432 \u043a\u043e\u0448\u0438\u043a!');
        cb(true, data.count);
      })
      .catch(function () { cb(false, 0); });
  }

  /* ── AJAX add-to-cart (cake — weight-based) ── */
  function addCakeToCart(cat, id, name, weight, cb) {
    var fd = new FormData();
    fd.append('category', cat);
    fd.append('id', id);
    fd.append('weight', weight);
    fetch('../forms/add_to_cart.php', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { cb(false, 0); return; }
        addCartKey(cat, id);
        updateCartBadge(data.count);
        showToast('\u2713 \u00ab' + name + '\u00bb (' + weight + ' \u043a\u0433) \u0434\u043e\u0434\u0430\u043d\u043e!');
        cb(true, data.count);
      })
      .catch(function () { cb(false, 0); });
  }

  /* ── Item detail modal ── */
  var modalOverlay  = document.getElementById('itemModalOverlay');
  var modalClose    = document.getElementById('itemModalClose');
  var modalImg      = document.getElementById('imModalImg');
  var modalName     = document.getElementById('imModalName');
  var modalDesc     = document.getElementById('imModalDesc');
  var modalPrice    = document.getElementById('imModalPrice');
  var modalCatBadge = document.getElementById('imModalCatBadge');
  var modalAdd      = document.getElementById('imModalAdd');
  var qtyVal        = document.getElementById('imQtyVal');
  var qtyMinus      = document.getElementById('imQtyMinus');
  var qtyPlus       = document.getElementById('imQtyPlus');
  var qtyWrap       = document.getElementById('imQtyWrap');
  var weightWrap    = document.getElementById('imWeightWrap');
  var weightVal     = document.getElementById('imWeightVal');
  var weightMinus   = document.getElementById('imWeightMinus');
  var weightPlus    = document.getElementById('imWeightPlus');
  var weightTotal   = document.getElementById('imWeightTotal');

  var currentModalCat  = '';
  var currentModalId   = 0;
  var currentModalName = '';
  var currentQty       = 1;
  var currentBasePrice = 0;
  var currentIsCake    = false;
  var currentPricePerKg = 0;
  var currentMinWeight  = 1;
  var currentWeight     = 1;

  function parsePrice(str) {
    return parseFloat(String(str).replace(/[^\d,\.]/g, '').replace(',', '.')) || 0;
  }

  function updateModalPrice() {
    if (!modalPrice) return;
    var total = currentIsCake
      ? (currentPricePerKg * currentWeight).toFixed(0)
      : (currentBasePrice  * currentQty).toFixed(0);
    modalPrice.textContent    = total + ' \u20b4';
    modalPrice.style.transform = 'scale(1.08)';
    modalPrice.style.color     = '#FFC107';
    setTimeout(function () {
      modalPrice.style.transform = 'scale(1)';
      modalPrice.style.color     = '#8B4513';
    }, 250);
    if (currentIsCake && weightTotal) {
      weightTotal.textContent = currentWeight + ' \u043a\u0433 \u00d7 ' + currentPricePerKg + ' \u0433\u0440\u043d/\u043a\u0433 = ' + total + ' \u0433\u0440\u043d';
    }
  }

  function openModal(data) {
    currentModalCat  = data.cat;
    currentModalId   = data.id;
    currentModalName = data.name;
    currentIsCake    = (data.cat === 'cake_items');

    modalImg.src          = data.img || '';
    modalImg.alt          = data.name;
    modalImg.style.display = data.img ? '' : 'none';
    modalName.textContent = data.name;
    modalDesc.textContent = data.desc || '';
    if (modalCatBadge) modalCatBadge.textContent = data.catLabel || '';

    if (currentIsCake) {
      currentPricePerKg = parseFloat(data.pricePerKg) || 1000;
      currentMinWeight  = parseFloat(data.minWeight)  || 1;
      currentWeight     = currentMinWeight;

      if (qtyWrap)    qtyWrap.style.display    = 'none';
      if (weightWrap) weightWrap.style.display  = 'flex';
      if (weightVal)  weightVal.textContent     = currentWeight.toFixed(1).replace('.0', '');

      var totalCake = (currentPricePerKg * currentWeight).toFixed(0);
      modalPrice.textContent = totalCake + ' \u20b4';
      if (weightTotal) weightTotal.textContent = currentWeight + ' \u043a\u0433 \u00d7 ' + currentPricePerKg + ' \u0433\u0440\u043d/\u043a\u0433 = ' + totalCake + ' \u0433\u0440\u043d';
      modalAdd.textContent = '\u0417\u0430\u043c\u043e\u0432\u0438\u0442\u0438';
      modalAdd.classList.remove('in-cart', 'just-added-modal');
    } else {
      currentQty       = 1;
      currentBasePrice = parsePrice(data.price);

      if (qtyWrap)    qtyWrap.style.display    = 'flex';
      if (weightWrap) weightWrap.style.display  = 'none';
      qtyVal.textContent = '1';

      modalPrice.textContent     = currentBasePrice.toFixed(0) + ' \u20b4';
      modalPrice.style.transform = '';
      modalPrice.style.color     = '';

      if (inCart(currentModalCat, currentModalId)) {
        modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713';
        modalAdd.classList.add('in-cart');
        modalAdd.classList.remove('just-added-modal');
      } else {
        modalAdd.textContent = '\u0414\u043e\u0434\u0430\u0442\u0438 \u0432 \u043a\u043e\u0448\u0438\u043a';
        modalAdd.classList.remove('in-cart', 'just-added-modal');
      }
    }

    modalOverlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modalOverlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  /* Open on overlay click */
  document.addEventListener('click', function (e) {
    var overlay = e.target.closest('.mc-img-overlay');
    if (!overlay) return;
    openModal({
      id:         parseInt(overlay.dataset.id, 10),
      cat:        overlay.dataset.cat,
      catLabel:   overlay.dataset.catLabel || '',
      name:       overlay.dataset.name,
      desc:       overlay.dataset.desc,
      price:      overlay.dataset.price,
      pricePerKg: overlay.dataset.pricePerKg || '0',
      minWeight:  overlay.dataset.minWeight  || '1',
      img:        overlay.dataset.img,
    });
  });

  if (modalClose)   modalClose.addEventListener('click', closeModal);
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('open')) closeModal();
  });

  /* Regular qty buttons */
  if (qtyMinus) {
    qtyMinus.addEventListener('click', function () {
      if (currentQty > 1) { currentQty--; qtyVal.textContent = currentQty; updateModalPrice(); }
    });
  }
  if (qtyPlus) {
    qtyPlus.addEventListener('click', function () {
      if (currentQty < 99) { currentQty++; qtyVal.textContent = currentQty; updateModalPrice(); }
    });
  }

  /* Cake weight buttons (step 0.5 kg) */
  if (weightMinus) {
    weightMinus.addEventListener('click', function () {
      var step = 0.5;
      var next = Math.round((currentWeight - step) * 10) / 10;
      if (next >= currentMinWeight) {
        currentWeight = next;
        weightVal.textContent = currentWeight.toFixed(1).replace('.0', '');
        updateModalPrice();
      }
    });
  }
  if (weightPlus) {
    weightPlus.addEventListener('click', function () {
      var step = 0.5;
      currentWeight = Math.round((currentWeight + step) * 10) / 10;
      weightVal.textContent = currentWeight.toFixed(1).replace('.0', '');
      updateModalPrice();
    });
  }

  /* Modal add button */
  if (modalAdd) {
    modalAdd.addEventListener('click', function () {
      if (currentIsCake) {
        if (modalAdd.classList.contains('just-added-modal')) return;
        addCakeToCart(currentModalCat, currentModalId, currentModalName, currentWeight, function (ok) {
          if (!ok) return;
          modalAdd.textContent = '\u0414\u043e\u0434\u0430\u043d\u043e!';
          modalAdd.classList.add('just-added-modal');
          setTimeout(function () {
            modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713';
            modalAdd.classList.remove('just-added-modal');
            modalAdd.classList.add('in-cart');
          }, 1500);
        });
        return;
      }

      if (modalAdd.classList.contains('in-cart')) {
        window.location.href = 'cart.php';
        return;
      }
      if (modalAdd.classList.contains('just-added-modal')) return;

      addItemToCart(currentModalCat, currentModalId, currentModalName, currentQty, function (ok) {
        if (!ok) return;
        modalAdd.textContent = '\u2713 \u0414\u043e\u0434\u0430\u043d\u043e!';
        modalAdd.classList.add('just-added-modal');
        setTimeout(function () {
          modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713';
          modalAdd.classList.remove('just-added-modal');
          modalAdd.classList.add('in-cart');
        }, 1500);
      });
    });
  }

  /* ── Card buttons ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.mc-add-btn');
    if (!btn) return;

    /* Cake "Замовити" — open modal */
    if (btn.classList.contains('mc-order-btn')) {
      openModal({
        id:         parseInt(btn.dataset.id, 10),
        cat:        btn.dataset.cat,
        catLabel:   '\u0422\u043e\u0440\u0442\u0438 \u043d\u0430 \u0437\u0430\u043c\u043e\u0432\u043b\u0435\u043d\u043d\u044f',
        name:       btn.dataset.name,
        desc:       '',
        price:      '',
        pricePerKg: btn.dataset.pricePerKg || '0',
        minWeight:  btn.dataset.minWeight  || '1',
        img:        '',
      });
      return;
    }

    if (btn.classList.contains('in-cart')) {
      window.location.href = 'cart.php';
      return;
    }

    var id   = parseInt(btn.dataset.id, 10);
    var cat  = btn.dataset.cat;
    var name = btn.dataset.name;

    addItemToCart(cat, id, name, 1, function (ok) {
      if (!ok) return;
      btn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713';
      btn.classList.add('in-cart', 'just-added');
      setTimeout(function () { btn.classList.remove('just-added'); }, 600);
      if (modalOverlay && modalOverlay.classList.contains('open') &&
          currentModalCat === cat && currentModalId === id) {
        modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713';
        modalAdd.classList.add('in-cart');
        modalAdd.classList.remove('just-added-modal');
      }
    });
  });

})();
