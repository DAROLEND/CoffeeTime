/* =====================================================
   Coffee Time — Menu Page JS
   - Category tabs (no reload)
   - Live search with 300 ms debounce
   - AJAX add-to-cart + cart badge bounce
   - Item detail modal (qty / weight / size / options)
   - Cake items: weight-based ordering
   - Pizza: size (30/40cm), cheese crust, takeaway
   - Fast food: sauce popup + modal add-on sauces
   - Filter bar: dropdowns for sauce/ingredients/spicy/sort
   - Sort applies to ALL categories
   - Active filter badges
   - Toast notifications
===================================================== */
(function () {
  'use strict';

  /* ── State ── */
  var cartKeys  = window._cartKeys ? window._cartKeys.slice() : [];
  var activeSauce       = 'all';
  var activeSpecials    = new Set();
  var activeIngredients = new Set();
  var activeSort        = 'default';
  var activeCoffeeType  = 'all'; // 'all' | 'hot' | 'cold'

  /* ── DOM refs ── */
  var tabsWrap    = document.getElementById('menuTabsWrap');
  var tabs        = Array.from(document.querySelectorAll('.menu-tab'));
  var sections    = Array.from(document.querySelectorAll('.menu-cat-section'));
  var searchInput = document.getElementById('menuSearch');
  var clearBtn    = document.getElementById('menuSearchClear');
  var toast       = document.getElementById('menuToast');
  var toastTimer  = null;
  var filterBar   = document.getElementById('menu-filter-bar');

  /* ── Helpers ── */
  function cartKey(cat, id)  { return cat + '_' + id; }
  function inCart(cat, id)   { return cartKeys.indexOf(cartKey(cat, id)) !== -1; }
  function addCartKey(cat, id) {
    var k = cartKey(cat, id);
    if (cartKeys.indexOf(k) === -1) cartKeys.push(k);
  }

  /* ── Scroll lock: блокуємо wheel/touchmove, не чіпаємо body/sticky ── */
  function _preventScroll(e) { e.preventDefault(); }
  function lockScroll() {
    window.addEventListener('wheel',      _preventScroll, { passive: false });
    window.addEventListener('touchmove',  _preventScroll, { passive: false });
  }
  function unlockScroll() {
    window.removeEventListener('wheel',     _preventScroll);
    window.removeEventListener('touchmove', _preventScroll);
  }

  function truncName(n) { return n.length > 16 ? n.slice(0, 16) + '…' : n; }
  function showToast(msg) {
    toast.innerHTML =
      '<span>' + msg + '</span>' +
      '<a href="cart.php" class="toast-cart-link">До кошику →</a>';
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 3500);
  }

  /* ═══════════════════════════════════════
     FILTER BAR
  ═══════════════════════════════════════ */

  /* Show/hide pizza-specific filter controls */
  function onCategoryChange(cat) {
    var isPizza  = (cat === 'pizza_items');
    var isCoffee = (cat === 'coffee_items');

    var pizzaEls = ['sauce-filter-wrap', 'ingredients-filter-wrap', 'spicy-toggle', 'pizza-sep'];
    pizzaEls.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = isPizza ? 'flex' : 'none';
    });

    var coffeeEls = ['coffee-temp-wrap', 'coffee-sep'];
    coffeeEls.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = isCoffee ? 'flex' : 'none';
    });

    if (filterBar) filterBar.style.display = 'block';
  }

  /* ── Dropdown open/close ── */
  function closeAllDropdowns() {
    document.querySelectorAll('.filter-dropdown-menu').forEach(function (m) {
      m.style.display = 'none';
    });
    document.querySelectorAll('.filter-btn .fd-arrow').forEach(function (s) {
      s.style.transform = 'rotate(0deg)';
    });
  }

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.filter-dropdown')) closeAllDropdowns();
  });

  document.querySelectorAll('.filter-btn[data-filter]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var menu   = this.nextElementSibling;
      var isOpen = menu && menu.style.display === 'block';
      closeAllDropdowns();
      if (!isOpen && menu) {
        menu.style.display = 'block';
        menu.style.animation = 'none';
        menu.offsetHeight; // reflow to restart animation
        menu.style.animation = 'dropIn 0.18s ease both';
        var arrow = this.querySelector('.fd-arrow');
        if (arrow) arrow.style.transform = 'rotate(180deg)';
      }
    });
  });

  /* ── Sauce dropdown ── */
  var sauceMenu = document.getElementById('sauceMenu');
  if (sauceMenu) {
    sauceMenu.querySelectorAll('.filter-option').forEach(function (opt) {
      opt.addEventListener('click', function () {
        sauceMenu.querySelectorAll('.filter-option').forEach(function (o) { o.classList.remove('active'); });
        this.classList.add('active');
        activeSauce = this.dataset.value;
        closeAllDropdowns();
        // Update button label
        var lbl = document.getElementById('sauceBtnLabel');
        if (lbl) lbl.textContent = activeSauce === 'all' ? 'Соус' : this.textContent.trim();
        var btn = document.getElementById('sauceFilterBtn');
        if (btn) btn.classList.toggle('has-value', activeSauce !== 'all');
        applyFilters();
        updateActiveFiltersBadges();
      });
    });
  }

  /* ── Coffee temp dropdown ── */
  var coffeeTempMenu = document.getElementById('coffeeTempMenu');
  if (coffeeTempMenu) {
    coffeeTempMenu.querySelectorAll('.filter-option').forEach(function (opt) {
      opt.addEventListener('click', function () {
        coffeeTempMenu.querySelectorAll('.filter-option').forEach(function (o) { o.classList.remove('active'); });
        this.classList.add('active');
        activeCoffeeType = this.dataset.value;
        closeAllDropdowns();
        var lbl = document.getElementById('coffeeTempLabel');
        if (lbl) lbl.textContent = activeCoffeeType === 'all' ? 'Тип'
          : activeCoffeeType === 'hot' ? 'Тепла' : 'Холодна';
        var btn = document.getElementById('coffeeTempBtn');
        if (btn) btn.classList.toggle('has-value', activeCoffeeType !== 'all');
        applyCoffeeFilter();
        updateActiveFiltersBadges();
      });
    });
  }

  /* ── Ingredient chips ── */
  document.querySelectorAll('.ingredient-chip').forEach(function (chip) {
    chip.addEventListener('click', function (e) {
      e.stopPropagation();
      var tag = this.dataset.tag;
      this.classList.toggle('active');
      if (this.classList.contains('active')) activeIngredients.add(tag);
      else activeIngredients.delete(tag);
      var btn = document.getElementById('ingFilterBtn');
      if (btn) btn.classList.toggle('has-value', activeIngredients.size > 0);
      var lbl = document.getElementById('ingBtnLabel');
      if (lbl) lbl.textContent = activeIngredients.size > 0
        ? 'Склад (' + activeIngredients.size + ')' : 'Склад';
      applyFilters();
      updateActiveFiltersBadges();
    });
  });

  /* ── Spicy toggle ── */
  var spicyBtn = document.getElementById('spicy-toggle');
  if (spicyBtn) {
    spicyBtn.addEventListener('click', function () {
      if (activeSpecials.has('spicy')) {
        activeSpecials.delete('spicy');
        this.classList.remove('active');
      } else {
        activeSpecials.add('spicy');
        this.classList.add('active');
      }
      applyFilters();
      updateActiveFiltersBadges();
    });
  }

  /* ── Sort dropdown ── */
  var sortMenu = document.getElementById('sortMenu');
  if (sortMenu) {
    sortMenu.querySelectorAll('.sort-option').forEach(function (opt) {
      opt.addEventListener('click', function () {
        sortMenu.querySelectorAll('.sort-option').forEach(function (o) { o.classList.remove('active'); });
        this.classList.add('active');
        activeSort = this.dataset.sort;
        closeAllDropdowns();
        var lbl = document.getElementById('sortBtnLabel');
        if (lbl) lbl.textContent = activeSort === 'default' ? 'Сортування' : this.textContent.trim();
        var btn = document.getElementById('sortFilterBtn');
        if (btn) btn.classList.toggle('has-value', activeSort !== 'default');
        applySort();
      });
    });
  }

  /* ── Reset buttons ── */
  var pfResetEl = document.getElementById('pfReset');
  if (pfResetEl) pfResetEl.addEventListener('click', resetAllFilters);
  document.addEventListener('click', function (e) {
    if (e.target.id === 'noResultsReset') resetAllFilters();
  });

  /* ═══════════════════════════════════════
     FILTER LOGIC (pizza)
  ═══════════════════════════════════════ */
  var pizzaSection = document.getElementById('cat-pizza_items');

  function applyFilters() {
    if (!pizzaSection) return;
    var hasActiveFilter = activeSauce !== 'all' || activeSpecials.size > 0 || activeIngredients.size > 0;
    if (hasActiveFilter) revealAllLazy(pizzaSection);
    var cards = Array.from(pizzaSection.querySelectorAll('.pizza-card'));
    var visibleCount = 0;

    cards.forEach(function (card) {
      var sauce  = card.dataset.sauce  || 'tomato';
      var spicy  = card.dataset.spicy  === '1';
      var tags   = [];
      try { tags = JSON.parse(card.dataset.tags || '[]').map(function (t) { return t.toLowerCase(); }); } catch (e) {}

      var sauceOk   = activeSauce === 'all' || sauce === activeSauce;
      var specialOk = activeSpecials.size === 0 || (activeSpecials.has('spicy') ? spicy : true);
      var ingOk     = activeIngredients.size === 0;
      if (!ingOk) {
        ingOk = true;
        // tags are already lowercased; compare each selected ingredient case-insensitively
        activeIngredients.forEach(function (ing) {
          var ingLower = ing.toLowerCase();
          if (!tags.some(function (t) { return t === ingLower; })) ingOk = false;
        });
      }

      var hidden = !(sauceOk && specialOk && ingOk);
      card.classList.toggle('filter-hidden', hidden);
      if (!hidden) visibleCount++;
    });

    var noRes = document.getElementById('no-pizza-results');
    if (noRes) noRes.style.display = visibleCount === 0 ? 'flex' : 'none';
  }

  /* ═══════════════════════════════════════
     COFFEE TEMP FILTER
  ═══════════════════════════════════════ */
  var coffeeSection = document.getElementById('cat-coffee_items');

  function applyCoffeeFilter() {
    if (!coffeeSection) return;
    if (activeCoffeeType !== 'all') revealAllLazy(coffeeSection);
    var cards = Array.from(coffeeSection.querySelectorAll('.menu-card'));
    var toReveal = [];

    cards.forEach(function (card) {
      var isCold = card.dataset.isCold === '1';
      var hidden = activeCoffeeType === 'hot'  ? isCold
                 : activeCoffeeType === 'cold' ? !isCold
                 : false;
      var wasHidden = card.classList.contains('filter-hidden');
      card.classList.toggle('filter-hidden', hidden);
      if (wasHidden && !hidden) toReveal.push(card);
    });

    // Replay entrance animation for newly revealed cards with stagger
    toReveal.forEach(function (card, i) {
      card.style.opacity = '0';
      card.style.transform = 'translateY(26px)';
      card.style.animation = 'none';
      void card.offsetWidth; // force reflow
      card.style.animation = 'menuCardIn .42s ease ' + (i * 0.07).toFixed(2) + 's forwards';
    });
  }

  /* ═══════════════════════════════════════
     SORT LOGIC (all categories)
  ═══════════════════════════════════════ */
  function applySort() {
    var activeSection = sections.find(function (s) { return s.classList.contains('active'); });
    if (!activeSection) return;
    // Reveal lazy cards only when non-default sort needs to see all items
    if (activeSort !== 'default') revealAllLazy(activeSection);
    var grid = activeSection.querySelector('.menu-grid');
    if (!grid) return;

    var cards = Array.from(grid.querySelectorAll('.menu-card'));
    if (activeSort === 'default') {
      // Restore original render order using data-order set server-side
      cards.sort(function (a, b) {
        return (parseInt(a.dataset.order) || 0) - (parseInt(b.dataset.order) || 0);
      });
    } else {
      cards.sort(function (a, b) {
        var pa = parseFloat(a.dataset.price) || 0;
        var pb = parseFloat(b.dataset.price) || 0;
        var oa = parseInt(a.dataset.ordered) || 0;
        var ob = parseInt(b.dataset.ordered) || 0;
        if (activeSort === 'price_asc')  return pa - pb;
        if (activeSort === 'price_desc') return pb - pa;
        if (activeSort === 'popular')    return ob - oa;
        return 0;
      });
    }
    cards.forEach(function (c, i) {
      c.style.transition = 'transform 0.25s ease ' + (i * 0.02) + 's, opacity 0.25s ease';
      grid.appendChild(c);
    });
  }

  function resetAllFilters() {
    activeSauce       = 'all';
    activeSpecials    = new Set();
    activeIngredients = new Set();
    activeSort        = 'default';

    // Reset sauce UI
    if (sauceMenu) {
      sauceMenu.querySelectorAll('.filter-option').forEach(function (o) {
        o.classList.toggle('active', o.dataset.value === 'all');
      });
    }
    var sl = document.getElementById('sauceBtnLabel');
    if (sl) sl.textContent = 'Соус';
    var sb = document.getElementById('sauceFilterBtn');
    if (sb) sb.classList.remove('has-value');

    // Reset ingredients UI
    document.querySelectorAll('.ingredient-chip').forEach(function (c) { c.classList.remove('active'); });
    var il = document.getElementById('ingBtnLabel');
    if (il) il.textContent = 'Склад';
    var ib = document.getElementById('ingFilterBtn');
    if (ib) ib.classList.remove('has-value');

    // Reset spicy
    if (spicyBtn) spicyBtn.classList.remove('active');

    // Reset sort UI
    if (sortMenu) {
      sortMenu.querySelectorAll('.sort-option').forEach(function (o) {
        o.classList.toggle('active', o.dataset.sort === 'default');
      });
    }
    var stl = document.getElementById('sortBtnLabel');
    if (stl) stl.textContent = 'Сортування';
    var stb = document.getElementById('sortFilterBtn');
    if (stb) stb.classList.remove('has-value');

    // Reset coffee temp UI
    activeCoffeeType = 'all';
    if (coffeeTempMenu) {
      coffeeTempMenu.querySelectorAll('.filter-option').forEach(function (o) {
        o.classList.toggle('active', o.dataset.value === 'all');
      });
    }
    var ctl = document.getElementById('coffeeTempLabel');
    if (ctl) ctl.textContent = 'Тип';
    var ctb = document.getElementById('coffeeTempBtn');
    if (ctb) ctb.classList.remove('has-value');
    applyCoffeeFilter();

    applyFilters();
    applySort();
    updateActiveFiltersBadges();
  }

  /* ═══════════════════════════════════════
     ACTIVE FILTER BADGES
  ═══════════════════════════════════════ */
  function h(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function updateActiveFiltersBadges() {
    var bar = document.getElementById('active-filters-bar');
    if (!bar) return;

    var badges = [];
    if (activeCoffeeType !== 'all') {
      (function (t) {
        badges.push({
          label: t === 'hot' ? 'Тепла' : 'Холодна',
          clear: function () {
            activeCoffeeType = 'all';
            if (coffeeTempMenu) coffeeTempMenu.querySelectorAll('.filter-option').forEach(function(o){ o.classList.toggle('active', o.dataset.value==='all'); });
            var ctl2 = document.getElementById('coffeeTempLabel'); if (ctl2) ctl2.textContent='Тип';
            var ctb2 = document.getElementById('coffeeTempBtn'); if (ctb2) ctb2.classList.remove('has-value');
            applyCoffeeFilter();
          }
        });
      })(activeCoffeeType);
    }
    if (activeSauce !== 'all') {
      var sauceLabels = {tomato:'Томатний', cream:'Вершковий', bbq:'BBQ'};
      (function (s) {
        badges.push({ label: sauceLabels[s] || s, clear: function () { activeSauce = 'all'; } });
      })(activeSauce);
    }
    if (activeSpecials.has('spicy')) {
      badges.push({ label: 'Гострі', clear: function () { activeSpecials.delete('spicy'); } });
    }
    activeIngredients.forEach(function (ing) {
      (function (i) {
        badges.push({ label: i, clear: function () { activeIngredients.delete(i); } });
      })(ing);
    });

    bar.innerHTML = '';
    if (badges.length === 0) { bar.style.display = 'none'; return; }

    bar.style.display = 'flex';
    badges.forEach(function (badge) {
      var el = document.createElement('span');
      el.className = 'afb-badge';
      el.innerHTML = h(badge.label) + ' <span class="afb-x">\u2715</span>';
      el.addEventListener('click', function () {
        badge.clear();
        applyFilters();
        applySort();
        updateActiveFiltersBadges();
        // Sync spicy button state
        if (spicyBtn) spicyBtn.classList.toggle('active', activeSpecials.has('spicy'));
        // Sync ingredient chips
        document.querySelectorAll('.ingredient-chip').forEach(function (c) {
          c.classList.toggle('active', activeIngredients.has(c.dataset.tag));
        });
        // Sync sauce options
        if (sauceMenu) {
          sauceMenu.querySelectorAll('.filter-option').forEach(function (o) {
            o.classList.toggle('active', o.dataset.value === activeSauce);
          });
        }
        var sl2 = document.getElementById('sauceBtnLabel');
        if (sl2) sl2.textContent = activeSauce === 'all' ? 'Соус' : (sauceMenu ? sauceMenu.querySelector('[data-value="'+activeSauce+'"]')?.textContent?.trim() || 'Соус' : 'Соус');
        var sb2 = document.getElementById('sauceFilterBtn');
        if (sb2) sb2.classList.toggle('has-value', activeSauce !== 'all');
        var il2 = document.getElementById('ingBtnLabel');
        if (il2) il2.textContent = activeIngredients.size > 0 ? 'Склад (' + activeIngredients.size + ')' : 'Склад';
        var ib2 = document.getElementById('ingFilterBtn');
        if (ib2) ib2.classList.toggle('has-value', activeIngredients.size > 0);
      });
      bar.appendChild(el);
    });

    // Reset all button
    var resetSpan = document.createElement('button');
    resetSpan.className = 'afb-reset';
    resetSpan.textContent = '\u2715 Скинути';
    resetSpan.addEventListener('click', resetAllFilters);
    bar.appendChild(resetSpan);
  }

  /* ═══════════════════════════════════════
     CATEGORY SWITCH
  ═══════════════════════════════════════ */
  function switchToCategory(cat) {
    if (typeof catToGroup === 'function') {
      var grp = catToGroup(cat);
      if (grp) switchToGroup(grp, false);
    }
    tabs.forEach(function (t) {
      var active = t.dataset.cat === cat;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    sections.forEach(function (s) {
      s.classList.toggle('active', s.dataset.cat === cat);
    });

    // Анімуємо перші видимі картки при переключенні категорії
    var newSection = sections.find(function (s) { return s.dataset.cat === cat; });
    if (newSection) {
      var visCards = Array.from(newSection.querySelectorAll('.menu-card:not(.lazy-hidden):not(.filter-hidden)'));
      observeCards(visCards);
    }

    try {
      var u = new URL(window.location.href);
      u.searchParams.set('category', cat);
      history.replaceState(null, '', u.toString());
    } catch (e) {}

    onCategoryChange(cat);

    // Reset pizza filters when leaving pizza
    if (cat !== 'pizza_items') {
      activeSauce = 'all'; activeSpecials = new Set(); activeIngredients = new Set();
      if (sauceMenu) sauceMenu.querySelectorAll('.filter-option').forEach(function(o){ o.classList.toggle('active', o.dataset.value==='all'); });
      document.querySelectorAll('.ingredient-chip').forEach(function(c){ c.classList.remove('active'); });
      if (spicyBtn) spicyBtn.classList.remove('active');
      var sl3 = document.getElementById('sauceBtnLabel'); if (sl3) sl3.textContent='Соус';
      var ib3 = document.getElementById('ingBtnLabel'); if (ib3) ib3.textContent='Склад';
    } else {
      // Returning to pizza — re-apply filters to clear any stale filter-hidden classes
      applyFilters();
    }

    // Reset coffee filter when leaving coffee
    if (cat !== 'coffee_items') {
      activeCoffeeType = 'all';
      if (coffeeTempMenu) coffeeTempMenu.querySelectorAll('.filter-option').forEach(function(o){ o.classList.toggle('active', o.dataset.value==='all'); });
      var ctl = document.getElementById('coffeeTempLabel'); if (ctl) ctl.textContent='Тип';
      var ctb = document.getElementById('coffeeTempBtn'); if (ctb) ctb.classList.remove('has-value');
      // Show all coffee cards again
      if (coffeeSection) coffeeSection.querySelectorAll('.menu-card').forEach(function(c){ c.classList.remove('filter-hidden'); });
    }

    updateActiveFiltersBadges();

    // Re-apply sort for new category
    applySort();

    if (searchInput && searchInput.value.trim()) {
      runSearch(searchInput.value.trim().toLowerCase());
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      switchToCategory(this.dataset.cat);
      this.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      if (searchInput && searchInput.value) {
        searchInput.value = ''; clearBtn.style.display = 'none'; clearSearch();
      }
    });
  });

  /* ── Group map ── */
  var groupCats = {
    drinks:   ['coffee_items', 'cold_drink_items'],
    food:     ['pizza_items', 'salad_items', 'dessert_items', 'cake_items'],
    fastfood: ['fast_food_items'],
    sushi:    ['sushi_items', 'sushi_sets'],
  };

  function catToGroup(cat) {
    for (var gid in groupCats) {
      if (groupCats[gid].indexOf(cat) !== -1) return gid;
    }
    return null;
  }

  function switchToGroup(gid, withAnimation) {
    document.querySelectorAll('.mmt-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.group === gid);
    });
    document.querySelectorAll('.menu-sub-tabs').forEach(function (st) {
      var isActive = st.dataset.group === gid;
      var wasActive = st.classList.contains('active');
      st.classList.toggle('active', isActive);
      if (isActive && withAnimation && !wasActive) {
        st.style.animation = 'none';
        st.offsetHeight; // reflow
        st.style.animation = '';
        bindSubTabsFade();
      }
    });
  }

  /* Main group button clicks */
  document.querySelectorAll('.mmt-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var gid = this.dataset.group;
      switchToGroup(gid, true);
      var firstCat = (groupCats[gid] || [])[0];
      if (firstCat) {
        switchToCategory(firstCat);
        if (searchInput && searchInput.value) {
          searchInput.value = ''; clearBtn.style.display = 'none'; clearSearch();
        }
      }
    });
  });

  /* Filter bar залишається в menu-body (не sticky) */

  /* ═══════════════════════════════════════
     CARD SCROLL ANIMATIONS (IntersectionObserver)
  ═══════════════════════════════════════ */
  var cardIO = typeof IntersectionObserver !== 'undefined'
    ? new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var card = entry.target;
          cardIO.unobserve(card);
          var delay = parseFloat(card.dataset.ioDelay || 0);
          card.style.animation = 'none';
          void card.offsetWidth;
          card.style.animation = 'menuCardIn .44s ease ' + delay.toFixed(3) + 's forwards';
        });
      }, { threshold: 0.06, rootMargin: '40px' })
    : null;

  function observeCards(cards) {
    if (!cardIO) {
      /* IO not supported — reveal cards immediately */
      cards.forEach(function (card) {
        card.style.opacity = '1';
        card.style.transform = '';
        card.style.animation = '';
      });
      return;
    }
    cards.forEach(function (card, i) {
      var rowDelay = Math.floor(i / 3) * 0.08 + (i % 3) * 0.05;
      card.dataset.ioDelay = rowDelay.toFixed(3);
      /* Don't cancel CSS animation here — let IO restart it with stagger.
         CSS animation serves as a fallback if IO never fires. */
      cardIO.observe(card);
    });
  }

  /* ═══════════════════════════════════════
     LAZY REVEAL (infinite-scroll style)
  ═══════════════════════════════════════ */
  var LAZY_BATCH = 9;

  function revealBatch(cards) {
    cards.forEach(function (card) { card.classList.remove('lazy-hidden'); });
    observeCards(cards);
  }

  function initLazySection(section) {
    var grid = section.querySelector('.menu-grid');
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll('.menu-card'));
    if (cards.length <= LAZY_BATCH) return;
    cards.forEach(function (card, i) {
      if (i >= LAZY_BATCH) card.classList.add('lazy-hidden');
    });
    var sent = document.createElement('div');
    sent.className = 'lazy-sentinel';
    sent.innerHTML = '<div class="lazy-loader"></div>';
    grid.insertAdjacentElement('afterend', sent);
    var obs = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      var hidden = Array.from(grid.querySelectorAll('.menu-card.lazy-hidden')).filter(function (c) {
        return !c.classList.contains('filter-hidden');
      });
      if (!hidden.length) { obs.disconnect(); sent.remove(); return; }
      revealBatch(hidden.slice(0, LAZY_BATCH));
      if (hidden.length <= LAZY_BATCH) { obs.disconnect(); sent.remove(); }
    }, { rootMargin: '200px' });
    obs.observe(sent);
    section._lazyObs = obs;
    section._lazySentinel = sent;
  }

  function revealAllLazy(section) {
    section.querySelectorAll('.menu-card.lazy-hidden').forEach(function (c) {
      c.classList.remove('lazy-hidden');
      c.style.animation = '';
      c.style.opacity = '';
      c.style.transform = '';
    });
    if (section._lazyObs) { section._lazyObs.disconnect(); delete section._lazyObs; }
    if (section._lazySentinel && section._lazySentinel.parentNode) {
      section._lazySentinel.remove(); delete section._lazySentinel;
    }
  }

  if (typeof IntersectionObserver !== 'undefined') {
    sections.forEach(function (section) { initLazySection(section); });
  }

  /* Init filter bar on page load */
  onCategoryChange(window._currentCat || (tabs.find(function(t){return t.classList.contains('active');}) || {dataset:{cat:'coffee_items'}}).dataset.cat);

  /* Анімуємо перші картки активної секції при завантаженні */
  (function () {
    var initSection = sections.find(function (s) { return s.classList.contains('active'); });
    if (!initSection) return;
    var visCards = Array.from(initSection.querySelectorAll('.menu-card:not(.lazy-hidden):not(.filter-hidden)'));
    observeCards(visCards);
  }());

  /* ── Sticky shadow + tab scroll fade ── */
  // Sub-tabs scroll fade — attach to active sub-tabs row
  function bindSubTabsFade() {
    var nav = document.querySelector('.menu-sub-tabs.active');
    if (!nav) return;
    nav.addEventListener('scroll', function () {
      tabsWrap && tabsWrap.classList.toggle('at-end', nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 4);
    }, { passive: true });
  }
  bindSubTabsFade();
  var tabsOuter = document.getElementById('menuTabsOuter');
  if (tabsOuter) {
    var sentinel = document.createElement('div');
    sentinel.style.cssText = 'height:1px;margin-bottom:-1px;pointer-events:none;';
    tabsOuter.parentNode.insertBefore(sentinel, tabsOuter);
    new IntersectionObserver(function (entries) {
      tabsOuter.classList.toggle('stuck', !entries[0].isIntersecting);
    }, { rootMargin: '-76px 0px 0px 0px', threshold: 0 }).observe(sentinel);
  }

  /* ═══════════════════════════════════════
     SEARCH
  ═══════════════════════════════════════ */
  var searchTimer = null;

  var menuWrap = document.querySelector('.menu-content') || document.querySelector('main');

  var tabsOuter    = document.getElementById('menuTabsOuter');
  var searchBanner = null; // \u0431\u0430\u043d\u0435\u0440 "\u041f\u043e\u0448\u0443\u043a \u043f\u043e \u0432\u0441\u044c\u043e\u043c\u0443 \u043c\u0435\u043d\u044e"

  function getOrCreateSearchBanner() {
    if (searchBanner) return searchBanner;
    searchBanner = document.createElement('div');
    searchBanner.className = 'global-search-banner';
    searchBanner.innerHTML = '<span class="gsb-icon">\ud83d\udd0d</span> <span class="gsb-text"></span>';
    return searchBanner;
  }

  function runSearch(q) {
    var totalFound = 0;
    var tabsWrap = document.getElementById('menuTabsWrap');

    // \u0417\u0430\u0442\u0435\u043c\u043d\u044e\u0454\u043c\u043e \u0432\u0441\u0456 \u0442\u0430\u0431\u0438 \u2014 \u043f\u043e\u0448\u0443\u043a \u0431\u0435\u0440\u0435 \u043a\u0435\u0440\u0443\u0432\u0430\u043d\u043d\u044f
    if (tabsWrap) tabsWrap.classList.add('search-active');
    if (menuWrap) menuWrap.classList.add('global-search-active');

    // \u0420\u043e\u0437\u043a\u0440\u0438\u0432\u0430\u0454\u043c\u043e \u0432\u0441\u0456 lazy-hidden \u043f\u0435\u0440\u0435\u0434 \u043f\u043e\u0448\u0443\u043a\u043e\u043c
    sections.forEach(function (s) { revealAllLazy(s); });

    sections.forEach(function (section) {
      var cards = Array.from(section.querySelectorAll('.menu-card'));
      var sectionFound = 0;
      var wasVisible = section.classList.contains('search-visible');

      cards.forEach(function (card) {
        if (card.classList.contains('filter-hidden')) { card.classList.add('search-hidden'); return; }
        var match = (card.dataset.name || '').indexOf(q) !== -1;
        card.classList.toggle('search-hidden', !match);
        if (match) { sectionFound++; totalFound++; }
      });

      var nowVisible = sectionFound > 0;
      section.classList.toggle('search-visible', nowVisible);

      // \u0410\u043d\u0456\u043c\u0443\u0454\u043c\u043e \u043a\u0430\u0440\u0442\u043a\u0438 \u043f\u0440\u0438 \u043f\u043e\u044f\u0432\u0456 \u0441\u0435\u043a\u0446\u0456\u0457
      if (nowVisible && !wasVisible) {
        var toAnimate = cards.filter(function (c) { return !c.classList.contains('search-hidden'); });
        toAnimate.forEach(function (card, i) {
          card.style.opacity = '0';
          card.style.transform = 'translateY(22px)';
          card.style.animation = 'none';
          void card.offsetWidth;
          card.style.animation = 'menuCardIn .38s ease ' + (i * 0.055).toFixed(3) + 's forwards';
        });
      }
    });

    // \u0411\u0430\u043d\u0435\u0440
    var banner = getOrCreateSearchBanner();
    var bannerText = banner.querySelector('.gsb-text');
    if (bannerText) bannerText.textContent = totalFound > 0
      ? '\u0417\u043d\u0430\u0439\u0434\u0435\u043d\u043e ' + totalFound + ' ' + (totalFound === 1 ? '\u043f\u043e\u0437\u0438\u0446\u0456\u044e' : totalFound < 5 ? '\u043f\u043e\u0437\u0438\u0446\u0456\u0457' : '\u043f\u043e\u0437\u0438\u0446\u0456\u0439') + ' \u0443 \u0432\u0441\u0456\u0445 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0456\u044f\u0445'
      : '\u041d\u0456\u0447\u043e\u0433\u043e \u043d\u0435 \u0437\u043d\u0430\u0439\u0434\u0435\u043d\u043e \u0437\u0430 \u0437\u0430\u043f\u0438\u0442\u043e\u043c \u00ab' + q + '\u00bb';
    if (menuWrap && !menuWrap.contains(banner)) {
      var firstSection = menuWrap.querySelector('.menu-cat-section');
      if (firstSection) menuWrap.insertBefore(banner, firstSection);
      else menuWrap.appendChild(banner);
    }

    if (totalFound === 0) {
      var activeSection = sections.find(function (s) { return s.classList.contains('active'); });
      if (activeSection) activeSection.classList.add('search-visible');
    }
  }

  function clearSearch() {
    var tabsWrap = document.getElementById('menuTabsWrap');
    if (tabsWrap) tabsWrap.classList.remove('search-active');

    sections.forEach(function (section) {
      section.querySelectorAll('.menu-card').forEach(function (c) {
        c.classList.remove('search-hidden');
        c.style.animation = '';
        c.style.opacity = '';
        c.style.transform = '';
      });
      section.classList.remove('search-visible');
      var sem = section.querySelector('.menu-search-empty');
      if (sem) sem.style.display = 'none';
    });
    if (menuWrap) menuWrap.classList.remove('global-search-active');
    if (searchBanner && searchBanner.parentNode) searchBanner.parentNode.removeChild(searchBanner);

    // Re-animate visible cards in the active section (base CSS has opacity:0)
    var activeSection = sections.find(function (s) { return s.classList.contains('active'); });
    if (activeSection) {
      var visCards = Array.from(activeSection.querySelectorAll('.menu-card:not(.filter-hidden):not(.lazy-hidden)'));
      observeCards(visCards);
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var q = this.value.trim().toLowerCase();
      clearBtn.style.display = q ? 'flex' : 'none';
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () { if (q) { runSearch(q); } else { clearSearch(); } }, 300);
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      searchInput.value = ''; clearBtn.style.display = 'none'; clearSearch(); searchInput.focus();
    });
  }
  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('mse-reset')) {
      searchInput.value = ''; clearBtn.style.display = 'none'; clearSearch();
    }
  });


  /* ═══════════════════════════════════════
     CART BADGE
  ═══════════════════════════════════════ */
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

  /* ═══════════════════════════════════════
     AJAX ADD-TO-CART
  ═══════════════════════════════════════ */
  function addItemToCart(cat, id, name, qty, extraData, cb) {
    var fd = new FormData();
    fd.append('category', cat); fd.append('id', id); fd.append('quantity', qty || 1);
    if (extraData) {
      if (extraData.selected_size)    fd.append('selected_size',    extraData.selected_size);
      if (extraData.cheese_crust)     fd.append('cheese_crust',     extraData.cheese_crust);
      if (extraData.takeaway)         fd.append('takeaway',         extraData.takeaway);
      if (extraData.selected_variant) fd.append('selected_variant', extraData.selected_variant);
      if (extraData.price_override)   fd.append('price_override',   extraData.price_override);
    }
    fetch('../forms/add_to_cart.php', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { cb(false, 0); return; }
        addCartKey(cat, id); updateCartBadge(data.count);
        window.dispatchEvent(new CustomEvent('cartUpdated'));
        showToast('\u2713 \u00ab' + truncName(name) + '\u00bb \u0434\u043e\u0434\u0430\u043d\u043e \u0432 \u043a\u043e\u0448\u0438\u043a!');
        cb(true, data.count);
      })
      .catch(function () { cb(false, 0); });
  }

  function addCakeToCart(cat, id, name, weight, cb) {
    var fd = new FormData();
    fd.append('category', cat); fd.append('id', id); fd.append('weight', weight);
    fetch('../forms/add_to_cart.php', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { cb(false, 0); return; }
        addCartKey(cat, id); updateCartBadge(data.count);
        window.dispatchEvent(new CustomEvent('cartUpdated'));
        showToast('\u2713 \u00ab' + truncName(name) + '\u00bb (' + weight + ' \u043a\u0433) \u0434\u043e\u0434\u0430\u043d\u043e!');
        cb(true, data.count);
      })
      .catch(function () { cb(false, 0); });
  }

  /* ═══════════════════════════════════════
     SAUCE PICKER MODAL (add-on sauces)
  ═══════════════════════════════════════ */
  var SAUCE_CATS = { 'fast_food_items': true, 'pizza_items': true, 'mini_pizza_items': true };

  var smOverlay  = document.getElementById('smOverlay');
  var smSubtitle = document.getElementById('smSubtitle');
  var smClose    = document.getElementById('smClose');
  var smSkip     = document.getElementById('smSkip');
  var smConfirm  = document.getElementById('smConfirm');
  var _smCb      = null;

  function openSauceModal(itemName, onDone) {
    if (!smOverlay) { onDone([]); return; }
    smOverlay.querySelectorAll('.sm-row').forEach(function (row) {
      row.classList.remove('sm-row--on');
      row.querySelector('.sm-qty-val').textContent = '1';
    });
    smSubtitle.textContent = 'До: ' + itemName;
    _smCb = onDone;
    smOverlay.classList.add('open');
    lockScroll();
  }

  function closeSauceModal() {
    if (!smOverlay) return;
    smOverlay.classList.remove('open');
    unlockScroll();
    _smCb = null;
  }

  function collectSauces() {
    var result = [];
    smOverlay && smOverlay.querySelectorAll('.sm-row--on').forEach(function (row) {
      result.push({
        id:   parseInt(row.dataset.sauceId, 10),
        name: row.dataset.sauceName,
        price: parseFloat(row.dataset.saucePrice) || 0,
        qty:  parseInt(row.querySelector('.sm-qty-val').textContent, 10) || 1,
      });
    });
    return result;
  }

  function updateSmPrice(row, qty) {
    var price = parseFloat(row.dataset.saucePrice) || 0;
    var el = row.querySelector('.sm-price');
    if (el && price > 0) el.textContent = '+' + Math.round(price * qty) + ' ₴';
  }

  smOverlay && smOverlay.addEventListener('click', function (e) {
    if (e.target === smOverlay) { if (_smCb) _smCb([]); closeSauceModal(); return; }
    var toggle = e.target.closest('.sm-toggle') || e.target.closest('.sm-check');
    if (toggle) { toggle.closest('.sm-row').classList.toggle('sm-row--on'); return; }
    var minus = e.target.closest('.sm-minus');
    if (minus) {
      var row = minus.closest('.sm-row');
      var v = row.querySelector('.sm-qty-val');
      var n = parseInt(v.textContent, 10) || 1;
      if (n > 1) { v.textContent = n - 1; updateSmPrice(row, n - 1); }
      return;
    }
    var plus = e.target.closest('.sm-plus');
    if (plus) {
      var row = plus.closest('.sm-row');
      var v = row.querySelector('.sm-qty-val');
      var n = parseInt(v.textContent, 10) || 1;
      if (n < 10) { v.textContent = n + 1; updateSmPrice(row, n + 1); }
      return;
    }
  });

  smClose  && smClose.addEventListener('click',  function () { if (_smCb) _smCb([]); closeSauceModal(); });
  smSkip   && smSkip.addEventListener('click',   function () { if (_smCb) _smCb([]); closeSauceModal(); });
  smConfirm && smConfirm.addEventListener('click', function () {
    var sauces = collectSauces();
    if (_smCb) _smCb(sauces);
    closeSauceModal();
  });

  /* Helper: add item + sauces; show sauce modal for eligible categories */
  function addWithSauces(cat, id, name, qty, extra, btnDoneCb) {
    var hasSauces = smOverlay && smOverlay.querySelectorAll('.sm-row').length > 0;
    if (!SAUCE_CATS[cat] || !hasSauces) {
      addItemToCart(cat, id, name, qty, extra, btnDoneCb);
      return;
    }
    openSauceModal(name, function (selectedSauces) {
      addItemToCart(cat, id, name, qty, extra, function (ok) {
        if (!ok) return;
        btnDoneCb(ok);
        selectedSauces.forEach(function (s) {
          addItemToCart('sauces', s.id, s.name, s.qty, null, function () {});
        });
      });
    });
  }

  /* ═══════════════════════════════════════
     SAUCE POPUP (fast-food card btn)
  ═══════════════════════════════════════ */
  var saucePopup     = document.getElementById('saucePopup');
  var spOptions      = document.getElementById('spOptions');
  var spTitle        = document.getElementById('spTitle');
  var spClose        = document.getElementById('spClose');
  var sauceCloseTimer = null;

  function showSaucePopup(variantJson, onPick) {
    var vd;
    try { vd = JSON.parse(variantJson); } catch(e) { return; }
    if (!vd || !vd.options || !vd.options.length) return;
    if (spTitle) spTitle.textContent = vd.label || '\u041e\u0431\u0435\u0440\u0456\u0442\u044c \u0441\u043e\u0443\u0441';
    if (spOptions) {
      spOptions.innerHTML = '';
      vd.options.forEach(function (opt) {
        var btn = document.createElement('button');
        btn.className = 'sp-option-btn'; btn.textContent = opt;
        btn.addEventListener('click', function () { onPick(opt); hideSaucePopup(); });
        spOptions.appendChild(btn);
      });
    }
    if (saucePopup) {
      saucePopup.classList.add('show');
      clearTimeout(sauceCloseTimer);
      sauceCloseTimer = setTimeout(function () { hideSaucePopup(); }, 8000);
    }
  }

  function hideSaucePopup() {
    if (saucePopup) saucePopup.classList.remove('show');
    clearTimeout(sauceCloseTimer);
  }
  if (spClose) spClose.addEventListener('click', hideSaucePopup);

  /* ═══════════════════════════════════════
     ITEM DETAIL MODAL
  ═══════════════════════════════════════ */
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
  /* Pizza options */
  var sizeWrap      = document.getElementById('imSizeWrap');
  var sizeSmall     = document.getElementById('imSizeSmall');
  var sizeLarge     = document.getElementById('imSizeLarge');
  var sizePriceS    = document.getElementById('imSizePriceSmall');
  var sizePriceL    = document.getElementById('imSizePriceLarge');
  var crustWrap     = document.getElementById('imCrustWrap');
  var cheeseCrust   = document.getElementById('imCheeseCrust');

  var saucesWrap    = document.getElementById('imSaucesWrap');
  var scoopsWrap    = document.getElementById('imScoopsWrap');
  var scoopsGrid    = document.getElementById('imScoopsGrid');
  var scoopsLabel   = document.getElementById('imScoopsLabel');
  var ffSizeWrap    = document.getElementById('imFfSizeWrap');
  var ffSizeGrid    = document.getElementById('imFfSizeGrid');
  /* Crust */
  var crustWrapEl   = document.getElementById('imCrustWrap');
  var crustPriceLbl = document.getElementById('crustPriceLabel');

  var currentModalCat   = '';
  var currentModalId    = 0;
  var currentModalName  = '';
  var currentQty        = 1;
  var currentBasePrice  = 0;
  var currentIsCake     = false;
  var currentPricePerKg = 0;
  var currentMinWeight  = 1;
  var currentWeight     = 1;
  var currentIsPizza    = false;
  var currentHasSize    = false;
  var currentPriceSmall = 0;
  var currentPriceLarge = 0;
  var currentSize       = 'small';
  var currentIsFastFood     = false;
  var currentIsIceCream     = false;
  var currentHasFastFoodSize = false;
  var currentScoopPriceDiff = 0;

  var CRUST_PRICE_SMALL = 65;
  var CRUST_PRICE_LARGE = 100;

  function getCrustPrice() { return currentSize === 'large' ? CRUST_PRICE_LARGE : CRUST_PRICE_SMALL; }

  function updateCrustLabel() {
    if (crustPriceLbl) crustPriceLbl.textContent = '+' + getCrustPrice() + ' \u20b4';
  }

  function getSaucesTotal() {
    var total = 0;
    document.querySelectorAll('.sauce-checkbox:checked').forEach(function (cb) {
      total += parseFloat(cb.dataset.saucePrice) || 0;
    });
    return total;
  }

  function parsePrice(str) {
    return parseFloat(String(str).replace(/[^\d,\.]/g, '').replace(',', '.')) || 0;
  }

  function fmtN(n) { return Math.round(n) + ' \u20b4'; }

  function calcPizzaTotal() {
    var base = currentSize === 'large' ? currentPriceLarge : currentPriceSmall;
    if (cheeseCrust && cheeseCrust.checked) base += getCrustPrice();
    return base * currentQty;
  }

  function updateModalPrice() {
    if (!modalPrice) return;
    var total;
    if (currentIsCake) {
      total = currentPricePerKg * currentWeight;
    } else if (currentIsPizza) {
      total = calcPizzaTotal();
    } else if (currentIsIceCream || (currentIsFastFood && currentHasFastFoodSize)) {
      total = (currentBasePrice + currentScoopPriceDiff) * currentQty;
    } else {
      total = (currentBasePrice + getSaucesTotal()) * currentQty;
    }
    modalPrice.textContent     = fmtN(total);
    modalPrice.style.transform = 'scale(1.08)';
    modalPrice.style.color     = '#FFC107';
    setTimeout(function () {
      modalPrice.style.transform = 'scale(1)';
      modalPrice.style.color     = '#8B4513';
    }, 250);
    if (currentIsCake && weightTotal)
      weightTotal.textContent = currentWeight + ' \u043a\u0433 \u00d7 ' + currentPricePerKg + ' \u0433\u0440\u043d/\u043a\u0433 = ' + Math.round(total) + ' \u0433\u0440\u043d';
  }

  /* Sauce checkboxes in modal */
  document.addEventListener('change', function (e) {
    if (!e.target.classList.contains('sauce-checkbox')) return;
    var lbl = e.target.closest('label');
    if (lbl) {
      lbl.classList.toggle('im-sauce-chip--active', e.target.checked);
    }
    updateModalPrice();
  });

  /* Crust toggle */
  if (cheeseCrust) {
    cheeseCrust.addEventListener('change', function () {
      var cbBox = document.getElementById('crustCbBox');
      if (cbBox) cbBox.classList.toggle('active', this.checked);
      if (crustWrapEl) crustWrapEl.classList.toggle('active', this.checked);
      updateModalPrice();
    });
  }

  function openModal(data) {
    currentModalCat   = data.cat;
    currentModalId    = data.id;
    currentModalName  = data.name;
    currentIsCake     = (data.cat === 'cake_items');
    currentIsPizza    = (data.cat === 'pizza_items');
    currentIsFastFood      = (data.isFastFood === '1' || data.isFastFood === true);
    currentIsIceCream      = (data.isIceCream === '1' || data.isIceCream === true);
    currentHasFastFoodSize = (data.hasFfSize === '1' || data.hasFfSize === true);
    currentHasSize    = (data.hasSize === '1' || data.hasSize === true);
    currentScoopPriceDiff = 0;

    modalImg.src           = data.img || '';
    modalImg.alt           = data.name;
    modalImg.style.display = data.img ? '' : 'none';
    modalName.textContent  = data.name;
    modalDesc.textContent  = data.desc || '';
    if (modalCatBadge) modalCatBadge.textContent = data.catLabel || '';

    // Hide all option sections
    if (sizeWrap)   sizeWrap.style.display   = 'none';
    if (crustWrap)  crustWrap.style.display  = 'none';
    if (saucesWrap) saucesWrap.style.display = 'none';
    if (scoopsWrap) scoopsWrap.style.display = 'none';
    if (ffSizeWrap) ffSizeWrap.style.display = 'none';
    if (qtyWrap)    qtyWrap.style.display    = 'flex';
    if (weightWrap) weightWrap.style.display = 'none';

    // Reset sauces
    document.querySelectorAll('.sauce-checkbox').forEach(function (cb) {
      cb.checked = false;
      var lbl = cb.closest('label');
      if (lbl) lbl.classList.remove('im-sauce-chip--active');
    });

    if (currentIsCake) {
      currentPricePerKg = parseFloat(data.pricePerKg) || 1000;
      currentMinWeight  = parseFloat(data.minWeight)  || 1;
      currentWeight     = currentMinWeight;
      if (qtyWrap)    qtyWrap.style.display   = 'none';
      if (weightWrap) weightWrap.style.display = 'flex';
      if (weightVal)  weightVal.textContent    = currentWeight.toFixed(1).replace('.0', '');
      var totalCake = (currentPricePerKg * currentWeight).toFixed(0);
      modalPrice.textContent = totalCake + ' \u20b4';
      if (weightTotal) weightTotal.textContent = currentWeight + ' \u043a\u0433 \u00d7 ' + currentPricePerKg + ' \u0433\u0440\u043d/\u043a\u0433 = ' + totalCake + ' \u0433\u0440\u043d';
      modalAdd.textContent = '\u0417\u0430\u043c\u043e\u0432\u0438\u0442\u0438';
      modalAdd.classList.remove('in-cart', 'just-added-modal');

    } else if (currentIsPizza && currentHasSize) {
      currentPriceSmall = parseFloat(data.price)      || parsePrice(data.priceFmt);
      currentPriceLarge = parseFloat(data.priceLarge) || 0;
      currentSize = 'small'; currentQty = 1;
      qtyVal.textContent = '1';

      if (sizeWrap)  sizeWrap.style.display  = 'block';
      if (crustWrap) crustWrap.style.display = 'block';
      if (cheeseCrust) cheeseCrust.checked = false;
      var cbBox = document.getElementById('crustCbBox');
      if (cbBox) cbBox.classList.remove('active');
      if (crustWrapEl) crustWrapEl.classList.remove('active');
      updateCrustLabel();

      if (sizeSmall)  sizeSmall.classList.add('active');
      if (sizeLarge)  sizeLarge.classList.remove('active');
      if (sizePriceS) sizePriceS.textContent = Math.round(currentPriceSmall) + ' \u20b4';
      if (sizePriceL) sizePriceL.textContent = currentPriceLarge > 0 ? Math.round(currentPriceLarge) + ' \u20b4' : '';

      modalPrice.textContent = fmtN(calcPizzaTotal());
      modalPrice.style.transform = ''; modalPrice.style.color = '';

      if (inCart(currentModalCat, currentModalId)) {
        modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; modalAdd.classList.add('in-cart'); modalAdd.classList.remove('just-added-modal');
      } else {
        modalAdd.textContent = '\u0414\u043e\u0434\u0430\u0442\u0438 \u0432 \u043a\u043e\u0448\u0438\u043a'; modalAdd.classList.remove('in-cart', 'just-added-modal');
      }

    } else {
      currentQty = 1; currentBasePrice = parsePrice(data.priceFmt || data.price);
      if (qtyWrap) qtyWrap.style.display = 'flex';
      qtyVal.textContent = '1';
      modalPrice.textContent = currentBasePrice.toFixed(0) + ' \u20b4';
      modalPrice.style.transform = ''; modalPrice.style.color = '';

      // Show sauces for fast food (only when variant_options has type:"sauce")
      if (currentIsFastFood && saucesWrap) {
        var ffVoRaw = data.variantOptions || '';
        var ffVo = null;
        try { ffVo = ffVoRaw ? JSON.parse(ffVoRaw) : null; } catch (e) {}
        if (ffVo && ffVo.type === 'sauce') saucesWrap.style.display = 'block';

        // Show size/variant buttons for fast food with price variants (type:"size")
        if (ffVo && ffVo.type === 'size' && Array.isArray(ffVo.options) && scoopsWrap && scoopsGrid) {
          if (scoopsLabel) scoopsLabel.textContent = (ffVo.label || '\u041d\u0430\u0447\u0438\u043d\u043a\u0430') + ':';
          scoopsGrid.innerHTML = '';
          currentScoopPriceDiff = 0;
          ffVo.options.forEach(function (opt, i) {
            var totalPrice = currentBasePrice + (parseFloat(opt.price_diff) || 0);
            var btn = document.createElement('button');
            btn.className = 'im-scoop-btn' + (i === 0 ? ' selected' : '');
            btn.dataset.priceDiff  = opt.price_diff || 0;
            btn.dataset.scoopId    = opt.id;
            btn.dataset.scoopLabel = opt.label;
            btn.innerHTML = '<span class="isb-label">' + opt.label + '</span>' +
                            '<span class="isb-price">' + totalPrice + ' \u20b4</span>';
            btn.addEventListener('click', function () {
              scoopsGrid.querySelectorAll('.im-scoop-btn').forEach(function (b) { b.classList.remove('selected'); });
              this.classList.add('selected');
              currentScoopPriceDiff = parseFloat(this.dataset.priceDiff) || 0;
              updateModalPrice();
            });
            if (i === 0) currentScoopPriceDiff = parseFloat(opt.price_diff) || 0;
            scoopsGrid.appendChild(btn);
          });
          scoopsWrap.style.display = 'block';
          updateModalPrice();
        }

        // Show filling buttons for fast food (type:"filling") with optional nested size
        if (ffVo && ffVo.type === 'filling' && Array.isArray(ffVo.options) && scoopsWrap && scoopsGrid) {
          if (scoopsLabel) scoopsLabel.textContent = (ffVo.label || '\u041d\u0430\u0447\u0438\u043d\u043a\u0430') + ':';
          scoopsGrid.innerHTML = '';
          if (ffSizeGrid) ffSizeGrid.innerHTML = '';
          currentScoopPriceDiff = 0;

          var buildFfSizes = function (opt, fillingDiff) {
            if (!opt.sizes || !Array.isArray(opt.sizes) || !ffSizeGrid || !ffSizeWrap) return;
            ffSizeGrid.innerHTML = '';
            opt.sizes.forEach(function (sz, si) {
              var sizeBtn = document.createElement('button');
              sizeBtn.className = 'im-size-btn' + (si === 0 ? ' active' : '');
              sizeBtn.dataset.priceDiff = sz.price_diff || 0;
              sizeBtn.dataset.sizeLabel = sz.label;
              var szTotal = currentBasePrice + fillingDiff + (parseFloat(sz.price_diff) || 0);
              sizeBtn.innerHTML = sz.label + '<br><span class="im-size-price">' + Math.round(szTotal) + ' \u20b4</span>';
              sizeBtn.addEventListener('click', function () {
                ffSizeGrid.querySelectorAll('.im-size-btn').forEach(function (b) { b.classList.remove('active'); });
                this.classList.add('active');
                currentScoopPriceDiff = fillingDiff + (parseFloat(this.dataset.priceDiff) || 0);
                updateModalPrice();
              });
              if (si === 0) currentScoopPriceDiff = fillingDiff + (parseFloat(sz.price_diff) || 0);
              ffSizeGrid.appendChild(sizeBtn);
            });
            // Re-trigger CSS animation on each show
            ffSizeWrap.style.animation = 'none';
            ffSizeWrap.offsetHeight; // reflow
            ffSizeWrap.style.animation = '';
            ffSizeWrap.style.display = 'block';
          };

          ffVo.options.forEach(function (opt, i) {
            var fillingDiff = parseFloat(opt.price_diff) || 0;
            var displayPrice = currentBasePrice + fillingDiff;
            var btn = document.createElement('button');
            btn.className = 'im-scoop-btn' + (i === 0 ? ' selected' : '');
            btn.dataset.priceDiff  = opt.price_diff || 0;
            btn.dataset.scoopId    = opt.id;
            btn.dataset.scoopLabel = opt.label;
            btn.dataset.hasSizes   = (opt.sizes && opt.sizes.length > 0) ? '1' : '0';
            btn.dataset.sizes      = opt.sizes ? JSON.stringify(opt.sizes) : '';
            btn.innerHTML = '<span class="isb-label">' + opt.label + '</span>' +
                            '<span class="isb-price">' + Math.round(displayPrice) + ' \u20b4</span>';
            btn.addEventListener('click', function () {
              scoopsGrid.querySelectorAll('.im-scoop-btn').forEach(function (b) { b.classList.remove('selected'); });
              this.classList.add('selected');
              var fd = parseFloat(this.dataset.priceDiff) || 0;
              if (this.dataset.hasSizes === '1') {
                var sizes = [];
                try { sizes = JSON.parse(this.dataset.sizes); } catch (_e) {}
                buildFfSizes({ price_diff: fd, sizes: sizes }, fd);
              } else {
                if (ffSizeWrap) ffSizeWrap.style.display = 'none';
                currentScoopPriceDiff = fd;
              }
              updateModalPrice();
            });
            scoopsGrid.appendChild(btn);
          });

          // Initialize: first option
          var firstOpt = ffVo.options[0];
          if (firstOpt) {
            currentScoopPriceDiff = parseFloat(firstOpt.price_diff) || 0;
            if (firstOpt.sizes && firstOpt.sizes.length > 0) {
              buildFfSizes(firstOpt, parseFloat(firstOpt.price_diff) || 0);
            }
          }
          scoopsWrap.style.display = 'block';
          updateModalPrice();
        }
      }

      // Show scoops selector for ice cream
      if (currentIsIceCream && scoopsWrap && scoopsGrid) {
        var voRaw = data.variantOptions || '';
        var vo = null;
        try { vo = voRaw ? JSON.parse(voRaw) : null; } catch (e) {}
        if (vo && vo.type === 'scoops' && Array.isArray(vo.options)) {
          scoopsGrid.innerHTML = '';
          var scoopSvgs = [
            /* 1 куля */
            '<svg viewBox="0 0 297 297" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M223.288,74.788C223.288,33.55,189.738,0,148.5,0S73.712,33.55,73.712,74.788c0,13.441,3.62,26.637,10.47,38.159c0.228,0.383,54.913,177.106,54.913,177.106c1.27,4.129,5.086,6.947,9.405,6.947s8.135-2.818,9.405-6.947c0,0,54.685-176.722,54.913-177.106C219.668,101.425,223.288,88.23,223.288,74.788z M203.607,74.788c0,8.077-1.773,16.03-5.161,23.29H98.554c-3.388-7.259-5.161-15.212-5.161-23.29c0-3.586,0.356-7.09,1.013-10.487c9.377-1.04,18.583,1.193,29.132,3.753c5.261,1.276,10.702,2.597,16.456,3.556c0.095,0.015,0.191,0.03,0.287,0.043c1.969,0.268,3.916,0.401,5.845,0.401c17.805,0,33.775-11.344,45.103-32.017C198.961,49.526,203.607,61.623,203.607,74.788z M148.5,19.681c9.942,0,19.269,2.66,27.33,7.285c-4.829,9.863-15.895,27.393-32.755,25.205c-4.996-0.841-10.028-2.062-14.896-3.243c-8.265-2.006-16.724-4.052-25.65-4.48C112.401,29.539,129.318,19.681,148.5,19.681z M148.5,253.698l-41.828-135.939h83.655L148.5,253.698z"/></svg>',
            /* 2 кулі */
            '<svg viewBox="0 0 297 297" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M84,143 C84.2,143.5,138,281,138,281 C140,287,144.5,291,148.5,291 C152.5,291,157,287,159,281 C159,281,212.8,143.5,213,143 Z M148.5,253 l-38,-108 h76 Z"/><circle cx="148.5" cy="98" r="52"/><circle cx="148.5" cy="33" r="42"/></svg>',
            /* 3 кулі */
            '<svg viewBox="0 0 297 297" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M57,158 C57.2,158.5,138,281,138,281 C140,287,144.5,291,148.5,291 C152.5,291,157,287,159,281 C159,281,240.8,158.5,241,158 Z M148.5,253 l-50,-93 h100 Z"/><circle cx="96" cy="120" r="40"/><circle cx="201" cy="120" r="40"/><circle cx="148.5" cy="58" r="40"/></svg>'
          ];
          vo.options.forEach(function (opt, i) {
            var totalPrice = currentBasePrice + (parseFloat(opt.price_diff) || 0);
            var btn = document.createElement('button');
            btn.className = 'im-scoop-btn' + (i === 0 ? ' selected' : '');
            btn.dataset.priceDiff = opt.price_diff || 0;
            btn.dataset.scoopId   = opt.id;
            btn.dataset.scoopLabel = opt.label;
            btn.innerHTML =
              '<span class="isb-icon">' + (scoopSvgs[i] || '') + '</span>' +
              '<span class="isb-label">' + opt.label + '</span>' +
              '<span class="isb-price">' + totalPrice + ' ₴</span>';
            btn.addEventListener('click', function () {
              scoopsGrid.querySelectorAll('.im-scoop-btn').forEach(function (b) { b.classList.remove('selected'); });
              this.classList.add('selected');
              currentScoopPriceDiff = parseFloat(this.dataset.priceDiff) || 0;
              updateModalPrice();
            });
            if (i === 0) currentScoopPriceDiff = parseFloat(opt.price_diff) || 0;
            scoopsGrid.appendChild(btn);
          });
          scoopsWrap.style.display = 'block';
          updateModalPrice();
        }
      }

      if (inCart(currentModalCat, currentModalId)) {
        modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; modalAdd.classList.add('in-cart'); modalAdd.classList.remove('just-added-modal');
      } else {
        modalAdd.textContent = '\u0414\u043e\u0434\u0430\u0442\u0438 \u0432 \u043a\u043e\u0448\u0438\u043a'; modalAdd.classList.remove('in-cart', 'just-added-modal');
      }
    }

    modalOverlay.classList.add('open');
    lockScroll();
  }

  function closeModal() {
    if (!modalOverlay.classList.contains('open')) return;
    modalOverlay.classList.add('closing');
    setTimeout(function () {
      modalOverlay.classList.remove('open', 'closing');
      unlockScroll();
    }, 360);
  }

  /* Size buttons */
  if (sizeSmall) {
    sizeSmall.addEventListener('click', function () {
      currentSize = 'small'; sizeSmall.classList.add('active');
      if (sizeLarge) sizeLarge.classList.remove('active');
      updateCrustLabel(); updateModalPrice();
    });
  }
  if (sizeLarge) {
    sizeLarge.addEventListener('click', function () {
      if (!currentPriceLarge) return;
      currentSize = 'large'; sizeLarge.classList.add('active');
      if (sizeSmall) sizeSmall.classList.remove('active');
      updateCrustLabel(); updateModalPrice();
    });
  }

  /* Open modal on overlay click */
  document.addEventListener('click', function (e) {
    var overlay = e.target.closest('.mc-img-overlay');
    if (!overlay) return;
    openModal({
      id:         parseInt(overlay.dataset.id, 10),
      cat:        overlay.dataset.cat,
      catLabel:   overlay.dataset.catLabel || '',
      name:       overlay.dataset.name,
      desc:       overlay.dataset.desc,
      priceFmt:   overlay.dataset.price,
      price:      parsePrice(overlay.dataset.price),
      priceLarge: parseFloat(overlay.dataset.priceLarge) || 0,
      hasSize:        overlay.dataset.hasSize,
      isFastFood:     overlay.dataset.isFastFood,
      hasFfSize:      overlay.dataset.hasFfSize,
      isIceCream:     overlay.dataset.isIceCream,
      variantOptions: overlay.dataset.variantOptions || '',
      pricePerKg:     overlay.dataset.pricePerKg || '0',
      minWeight:      overlay.dataset.minWeight  || '1',
      img:            overlay.dataset.img,
    });
  });

  if (modalClose)   modalClose.addEventListener('click', closeModal);
  if (modalOverlay) modalOverlay.addEventListener('click', function (e) { if (e.target === modalOverlay) closeModal(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('open')) closeModal();
  });

  /* Qty buttons */
  if (qtyMinus) qtyMinus.addEventListener('click', function () {
    if (currentQty > 1) { currentQty--; qtyVal.textContent = currentQty; updateModalPrice(); }
  });
  if (qtyPlus) qtyPlus.addEventListener('click', function () {
    if (currentQty < 99) { currentQty++; qtyVal.textContent = currentQty; updateModalPrice(); }
  });

  /* Weight buttons */
  if (weightMinus) weightMinus.addEventListener('click', function () {
    var next = Math.round((currentWeight - 0.5) * 10) / 10;
    if (next >= currentMinWeight) { currentWeight = next; weightVal.textContent = currentWeight.toFixed(1).replace('.0',''); updateModalPrice(); }
  });
  if (weightPlus) weightPlus.addEventListener('click', function () {
    currentWeight = Math.round((currentWeight + 0.5) * 10) / 10;
    weightVal.textContent = currentWeight.toFixed(1).replace('.0',''); updateModalPrice();
  });

  /* Modal add button */
  if (modalAdd) {
    modalAdd.addEventListener('click', function () {
      if (currentIsCake) {
        if (modalAdd.classList.contains('just-added-modal')) return;
        addCakeToCart(currentModalCat, currentModalId, currentModalName, currentWeight, function (ok) {
          if (!ok) return;
          modalAdd.textContent = '\u0414\u043e\u0434\u0430\u043d\u043e!'; modalAdd.classList.add('just-added-modal');
          setTimeout(function () { modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; modalAdd.classList.remove('just-added-modal'); modalAdd.classList.add('in-cart'); }, 1500);
        });
        return;
      }

      if (currentIsPizza && currentHasSize) {
        if (modalAdd.classList.contains('just-added-modal')) return;
        var sizePrice = currentSize === 'large' ? currentPriceLarge : currentPriceSmall;
        if (cheeseCrust && cheeseCrust.checked) sizePrice += getCrustPrice();
        var extra = {
          selected_size:  currentSize,
          cheese_crust:   (cheeseCrust && cheeseCrust.checked) ? '1' : '0',
          price_override: sizePrice,
        };
        addItemToCart(currentModalCat, currentModalId, currentModalName, currentQty, extra, function (ok) {
          if (!ok) return;
          modalAdd.textContent = '\u2713 \u0414\u043e\u0434\u0430\u043d\u043e!'; modalAdd.classList.add('just-added-modal'); closeModal();
          setTimeout(function () {
            var cardBtn = document.querySelector('.mc-size-btn[data-id="' + currentModalId + '"][data-cat="pizza_items"]');
            if (cardBtn) { cardBtn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; cardBtn.classList.add('in-cart'); }
          }, 100);
        });
        return;
      }

      if (modalAdd.classList.contains('in-cart')) { window.location.href = 'cart.php'; return; }
      if (modalAdd.classList.contains('just-added-modal')) return;

      // Ice cream: collect selected scoop
      var extraFF = null;
      if (currentIsIceCream) {
        var scoopBtn = scoopsGrid ? scoopsGrid.querySelector('.im-scoop-btn.selected') : null;
        if (scoopBtn) {
          extraFF = { selected_variant: JSON.stringify({
            type:        'scoops',
            scoop_id:    scoopBtn.dataset.scoopId,
            scoop_label: scoopBtn.dataset.scoopLabel,
            price_diff:  parseFloat(scoopBtn.dataset.priceDiff) || 0,
          }) };
        }
      }

      // Fast food: collect filling variant, size variant, or sauces
      if (!extraFF && currentIsFastFood) {
        var fillingBtn = scoopsGrid ? scoopsGrid.querySelector('.im-scoop-btn.selected') : null;

        // Filling variant (type:"filling") — may have nested size
        if (fillingBtn && fillingBtn.dataset.hasSizes !== undefined) {
          var svObj = {
            type:          'filling',
            filling_id:    fillingBtn.dataset.scoopId,
            filling_label: fillingBtn.dataset.scoopLabel,
            price_diff:    currentScoopPriceDiff,
          };
          if (fillingBtn.dataset.hasSizes === '1' && ffSizeGrid) {
            var activeSzBtn = ffSizeGrid.querySelector('.im-size-btn.active');
            if (activeSzBtn) {
              svObj.size_label = activeSzBtn.dataset.sizeLabel || '';
              svObj.size_diff  = parseFloat(activeSzBtn.dataset.priceDiff) || 0;
            }
          }
          extraFF = {
            selected_variant: JSON.stringify(svObj),
            price_override:   currentBasePrice + currentScoopPriceDiff,
          };
        }

        // Size variant (type:"size") — includes price_override
        if (!extraFF) {
          var sizeBtn = scoopsGrid ? scoopsGrid.querySelector('.im-scoop-btn.selected') : null;
          if (sizeBtn && sizeBtn.dataset.scoopId) {
            var sizePriceDiff = parseFloat(sizeBtn.dataset.priceDiff) || 0;
            extraFF = {
              selected_variant: JSON.stringify({
                type:        'size',
                scoop_id:    sizeBtn.dataset.scoopId,
                scoop_label: sizeBtn.dataset.scoopLabel,
                price_diff:  sizePriceDiff,
              }),
              price_override: currentBasePrice + sizePriceDiff,
            };
          } else {
            // Sauce selection
            var selectedSauces = [];
            var saucesTotal = 0;
            document.querySelectorAll('.sauce-checkbox:checked').forEach(function (cb) {
              var sp = parseFloat(cb.dataset.saucePrice) || 0;
              selectedSauces.push({ id: parseInt(cb.dataset.sauceId), name: cb.dataset.sauceName, price: sp });
              saucesTotal += sp;
            });
            if (selectedSauces.length > 0) {
              extraFF = { selected_variant: JSON.stringify({ sauces: selectedSauces, sauces_total: saucesTotal }) };
            }
          }
        }
      }

      var _modalCat  = currentModalCat;
      var _modalId   = currentModalId;
      var _modalName = currentModalName;
      var _modalQty  = currentQty;
      var _modalExtra = extraFF;

      function doAddFromModal(selectedSauces) {
        addItemToCart(_modalCat, _modalId, _modalName, _modalQty, _modalExtra, function (ok) {
          if (!ok) return;
          var cardScoopBtn = document.querySelector('.mc-scoop-btn[data-id="' + _modalId + '"][data-cat="' + _modalCat + '"], .mc-ff-size-btn[data-id="' + _modalId + '"][data-cat="' + _modalCat + '"]');
          if (cardScoopBtn) { cardScoopBtn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; cardScoopBtn.classList.add('in-cart'); }
          if (selectedSauces) {
            selectedSauces.forEach(function (s) {
              addItemToCart('sauces', s.id, s.name, s.qty, null, function () {});
            });
          }
        });
      }

      if (SAUCE_CATS[_modalCat] && smOverlay && smOverlay.querySelectorAll('.sm-row').length > 0) {
        modalAdd.textContent = '\u2713 \u0414\u043e\u0434\u0430\u043d\u043e!'; modalAdd.classList.add('just-added-modal');
        closeModal();
        openSauceModal(_modalName, doAddFromModal);
      } else {
        addItemToCart(_modalCat, _modalId, _modalName, _modalQty, _modalExtra, function (ok) {
          if (!ok) return;
          modalAdd.textContent = '\u2713 \u0414\u043e\u0434\u0430\u043d\u043e!'; modalAdd.classList.add('just-added-modal');
          closeModal();
          var cardScoopBtn = document.querySelector('.mc-scoop-btn[data-id="' + _modalId + '"][data-cat="' + _modalCat + '"], .mc-ff-size-btn[data-id="' + _modalId + '"][data-cat="' + _modalCat + '"]');
          if (cardScoopBtn) { cardScoopBtn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; cardScoopBtn.classList.add('in-cart'); }
        });
      }
    });
  }

  /* ═══════════════════════════════════════
     CARD BUTTONS
  ═══════════════════════════════════════ */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.mc-add-btn');
    if (!btn) return;

    if (btn.classList.contains('mc-order-btn')) {
      var _card0 = btn.closest('.menu-card');
      var _ov0   = _card0 ? _card0.querySelector('.mc-img-overlay') : null;
      openModal({
        id: parseInt(btn.dataset.id, 10), cat: btn.dataset.cat,
        catLabel: '\u0422\u043e\u0440\u0442\u0438 \u043d\u0430 \u0437\u0430\u043c\u043e\u0432\u043b\u0435\u043d\u043d\u044f',
        name: btn.dataset.name, desc: '', priceFmt: '', price: 0,
        pricePerKg: btn.dataset.pricePerKg || '0', minWeight: btn.dataset.minWeight || '1',
        img: _ov0 ? (_ov0.dataset.img || '') : '',
      });
      return;
    }

    if (btn.classList.contains('mc-size-btn')) {
      if (btn.classList.contains('in-cart')) { window.location.href = 'cart.php'; return; }
      var _card1 = btn.closest('.menu-card');
      var _ov1   = _card1 ? _card1.querySelector('.mc-img-overlay') : null;
      openModal({
        id: parseInt(btn.dataset.id, 10), cat: btn.dataset.cat, catLabel: 'Піца',
        name: btn.dataset.name, desc: '', priceFmt: '',
        price: parseFloat(btn.dataset.price) || 0, priceLarge: parseFloat(btn.dataset.priceLarge) || 0,
        hasSize: '1', img: _ov1 ? (_ov1.dataset.img || '') : '',
      });
      return;
    }

    if (btn.classList.contains('mc-scoop-btn')) {
      // Find the overlay on the same card to get full data
      var card = btn.closest('.menu-card');
      var overlay = card ? card.querySelector('.mc-img-overlay') : null;
      if (overlay) {
        openModal({
          id:             parseInt(overlay.dataset.id, 10),
          cat:            overlay.dataset.cat,
          catLabel:       overlay.dataset.catLabel || 'Морозиво',
          name:           overlay.dataset.name,
          desc:           overlay.dataset.desc || '',
          priceFmt:       overlay.dataset.price,
          price:          parsePrice(overlay.dataset.price),
          isIceCream:     '1',
          variantOptions: overlay.dataset.variantOptions || '',
          img:            overlay.dataset.img,
        });
      }
      return;
    }

    if (btn.classList.contains('mc-ff-size-btn')) {
      if (btn.classList.contains('in-cart')) { window.location.href = 'cart.php'; return; }
      var card = btn.closest('.menu-card');
      var overlay = card ? card.querySelector('.mc-img-overlay') : null;
      if (overlay) {
        openModal({
          id:             parseInt(overlay.dataset.id, 10),
          cat:            overlay.dataset.cat,
          catLabel:       overlay.dataset.catLabel || 'Фаст-фуд',
          name:           overlay.dataset.name,
          desc:           overlay.dataset.desc || '',
          priceFmt:       overlay.dataset.price,
          price:          parsePrice(overlay.dataset.price),
          isFastFood:     '1',
          hasFfSize:      '1',
          variantOptions: overlay.dataset.variantOptions || '',
          img:            overlay.dataset.img,
        });
      }
      return;
    }

    if (btn.classList.contains('in-cart')) { window.location.href = 'cart.php'; return; }

    var id             = parseInt(btn.dataset.id, 10);
    var cat            = btn.dataset.cat;
    var name           = btn.dataset.name;
    var variantOptions = btn.dataset.variantOptions || '';

    if (variantOptions) {
      addItemToCart(cat, id, name, 1, null, function (ok) {
        if (!ok) return;
        btn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; btn.classList.add('in-cart', 'just-added');
        setTimeout(function () { btn.classList.remove('just-added'); }, 600);
        showSaucePopup(variantOptions, function (sauce) {
          var fd2 = new FormData();
          fd2.append('category', cat); fd2.append('id', id); fd2.append('selected_variant', sauce);
          fetch('../forms/update_cart_variant.php', { method: 'POST', body: fd2 });
        });
      });
      return;
    }

    var _btn = btn, _cat = cat, _id = id, _name = name;
    addWithSauces(_cat, _id, _name, 1, null, function (ok) {
      if (!ok) return;
      _btn.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; _btn.classList.add('in-cart', 'just-added');
      setTimeout(function () { _btn.classList.remove('just-added'); }, 600);
      if (modalOverlay && modalOverlay.classList.contains('open') && currentModalCat === _cat && currentModalId === _id) {
        modalAdd.textContent = '\u0412 \u043a\u043e\u0448\u0438\u043a\u0443 \u2713'; modalAdd.classList.add('in-cart'); modalAdd.classList.remove('just-added-modal');
      }
    });
  });

})();
