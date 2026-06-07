/* ================================================================
   Cart item edit modal — опції товару (без кількості)
================================================================ */
(function () {
  'use strict';

  /* ── DOM refs ── */
  var overlay       = document.getElementById('itemModalOverlay');
  var modalClose    = document.getElementById('itemModalClose');
  var modalCancel   = document.getElementById('imModalCancel');
  var modalImg      = document.getElementById('imModalImg');
  var modalName     = document.getElementById('imModalName');
  var modalDesc     = document.getElementById('imModalDesc');
  var modalPrice    = document.getElementById('imModalPrice');
  var modalAdd      = document.getElementById('imModalAdd');
  var sizeWrap      = document.getElementById('imSizeWrap');
  var sizeSmall     = document.getElementById('imSizeSmall');
  var sizeLarge     = document.getElementById('imSizeLarge');
  var sizePriceS    = document.getElementById('imSizePriceSmall');
  var sizePriceL    = document.getElementById('imSizePriceLarge');
  var crustWrap     = document.getElementById('imCrustWrap');
  var cheeseCrust   = document.getElementById('imCheeseCrust');
  var crustPriceLbl = document.getElementById('crustPriceLabel');
  var scoopsWrap    = document.getElementById('imScoopsWrap');
  var scoopsGrid    = document.getElementById('imScoopsGrid');
  var scoopsLabel   = document.getElementById('imScoopsLabel');
  var ffSizeWrap    = document.getElementById('imFfSizeWrap');
  var ffSizeGrid    = document.getElementById('imFfSizeGrid');

  if (!overlay) return;

  /* ── State ── */
  var currentIndex      = -1;
  var currentCat        = '';
  var currentBasePrice  = 0;
  var currentSize       = 'small';
  var currentPriceSmall = 0;
  var currentPriceLarge = 0;
  var currentPriceDiff  = 0;

  var CRUST_SMALL = 65;
  var CRUST_LARGE = 100;

  function getCrustAdd() { return currentSize === 'large' ? CRUST_LARGE : CRUST_SMALL; }

  /* ── Price display (одиниця товару з опціями) ── */
  function updatePrice() {
    var total;
    if (currentCat === 'pizza_items') {
      total = currentSize === 'large' ? currentPriceLarge : currentPriceSmall;
      if (cheeseCrust && cheeseCrust.checked) total += getCrustAdd();
    } else {
      total = currentBasePrice + currentPriceDiff;
    }
    if (!modalPrice) return;
    modalPrice.textContent     = Math.round(total) + ' \u20b4';
    modalPrice.style.transform = 'scale(1.08)';
    modalPrice.style.color     = '#FFC107';
    setTimeout(function () {
      modalPrice.style.transform = 'scale(1)';
      modalPrice.style.color     = '#8B4513';
    }, 250);
  }

  /* ── Helpers ── */
  function hide(el) { if (el) el.style.display = 'none'; }
  function show(el, flex) { if (el) el.style.display = flex ? 'flex' : 'block'; }

  /* ── Build FF size sub-buttons ── */
  function buildFfSizes(sizes, fillingDiff, preSizeLabel) {
    if (!ffSizeGrid || !ffSizeWrap || !sizes || !sizes.length) return;
    ffSizeGrid.innerHTML = '';
    sizes.forEach(function (sz, si) {
      var btn = document.createElement('button');
      var isPreSelected = preSizeLabel ? (sz.label === preSizeLabel) : (si === 0);
      btn.className = 'im-size-btn' + (isPreSelected ? ' active' : '');
      btn.dataset.priceDiff = sz.price_diff || 0;
      btn.dataset.sizeLabel = sz.label;
      var total = currentBasePrice + fillingDiff + (parseFloat(sz.price_diff) || 0);
      btn.innerHTML = sz.label + '<br><span class="im-size-price">' + Math.round(total) + ' \u20b4</span>';
      btn.addEventListener('click', function () {
        ffSizeGrid.querySelectorAll('.im-size-btn').forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        currentPriceDiff = fillingDiff + (parseFloat(this.dataset.priceDiff) || 0);
        updatePrice();
      });
      if (isPreSelected) {
        currentPriceDiff = fillingDiff + (parseFloat(sz.price_diff) || 0);
      }
      ffSizeGrid.appendChild(btn);
    });
    ffSizeWrap.style.animation = 'none';
    ffSizeWrap.offsetHeight;
    ffSizeWrap.style.animation = '';
    show(ffSizeWrap);
  }

  /* ── Open modal ── */
  function openEditModal(data) {
    currentIndex     = data.cart_index;
    currentCat       = data.category;
    currentPriceDiff = 0;

    if (modalImg) {
      modalImg.src           = data.image || '';
      modalImg.alt           = data.name  || '';
      modalImg.style.display = data.image ? '' : 'none';
    }
    if (modalName) modalName.textContent = data.name || '';
    if (modalDesc) modalDesc.textContent = data.desc || '';

    hide(sizeWrap); hide(crustWrap); hide(scoopsWrap); hide(ffSizeWrap);

    /* ── Pizza ── */
    if (data.category === 'pizza_items' && data.has_size_choice) {
      currentPriceSmall = data.price       || 0;
      currentPriceLarge = data.price_large || 0;
      currentSize       = data.selected_size === 'large' ? 'large' : 'small';

      show(sizeWrap);
      show(crustWrap);

      if (sizeSmall)  sizeSmall.classList.toggle('active', currentSize === 'small');
      if (sizeLarge)  sizeLarge.classList.toggle('active', currentSize === 'large');
      if (sizePriceS) sizePriceS.textContent = Math.round(currentPriceSmall) + ' \u20b4';
      if (sizePriceL) sizePriceL.textContent = currentPriceLarge > 0 ? Math.round(currentPriceLarge) + ' \u20b4' : '';

      var hasCrust = data.cheese_crust === 1 || data.cheese_crust === '1';
      if (cheeseCrust) cheeseCrust.checked = hasCrust;
      var cbBox = document.getElementById('crustCbBox');
      if (cbBox)     cbBox.classList.toggle('active', hasCrust);
      if (crustWrap) crustWrap.classList.toggle('active', hasCrust);
      updateCrustLabel();
      updatePrice();

    /* ── Fast food ── */
    } else if (data.category === 'fast_food_items' && data.variant_options) {
      currentBasePrice = data.price || 0;

      var vo = null;
      try { vo = JSON.parse(data.variant_options); } catch (e) {}

      var sv = null;
      if (data.selected_variant) {
        try { sv = JSON.parse(data.selected_variant); } catch (e) {}
      }

      if (vo && (vo.type === 'filling' || vo.type === 'size') && Array.isArray(vo.options)) {
        if (scoopsLabel) scoopsLabel.textContent = (vo.label || 'Начинка') + ':';
        scoopsGrid.innerHTML = '';
        if (ffSizeGrid) ffSizeGrid.innerHTML = '';

        var preFillingId = sv ? (sv.filling_id || sv.scoop_id || null) : null;
        var preSizeLabel = sv ? (sv.size_label || null) : null;

        vo.options.forEach(function (opt, i) {
          var fillingDiff   = parseFloat(opt.price_diff) || 0;
          var isPreSelected = preFillingId ? (opt.id === preFillingId) : (i === 0);

          var btn = document.createElement('button');
          btn.className          = 'im-scoop-btn' + (isPreSelected ? ' selected' : '');
          btn.dataset.priceDiff  = opt.price_diff || 0;
          btn.dataset.scoopId    = opt.id;
          btn.dataset.scoopLabel = opt.label;
          btn.dataset.hasSizes   = (opt.sizes && opt.sizes.length > 0) ? '1' : '0';
          btn.dataset.sizes      = opt.sizes ? JSON.stringify(opt.sizes) : '';

          var displayPrice = currentBasePrice + fillingDiff;
          btn.innerHTML = '<span class="isb-label">' + opt.label + '</span>' +
                          '<span class="isb-price">' + Math.round(displayPrice) + ' \u20b4</span>';

          btn.addEventListener('click', function () {
            scoopsGrid.querySelectorAll('.im-scoop-btn').forEach(function (b) { b.classList.remove('selected'); });
            this.classList.add('selected');
            var fd = parseFloat(this.dataset.priceDiff) || 0;
            if (this.dataset.hasSizes === '1') {
              var szArr = [];
              try { szArr = JSON.parse(this.dataset.sizes); } catch (_) {}
              buildFfSizes(szArr, fd, null);
            } else {
              hide(ffSizeWrap);
              currentPriceDiff = fd;
            }
            updatePrice();
          });

          if (isPreSelected) {
            if (opt.sizes && opt.sizes.length > 0) {
              buildFfSizes(opt.sizes, fillingDiff, preSizeLabel);
            } else {
              currentPriceDiff = fillingDiff;
            }
          }
          scoopsGrid.appendChild(btn);
        });
        show(scoopsWrap);
        updatePrice();
      }

    /* ── Ice cream ── */
    } else if (data.category === 'ice_cream_items' && data.variant_options) {
      currentBasePrice = data.price || 0;

      var voIce = null;
      try { voIce = JSON.parse(data.variant_options); } catch (e) {}

      var svIce = null;
      if (data.selected_variant) {
        try { svIce = JSON.parse(data.selected_variant); } catch (e) {}
      }

      if (voIce && voIce.type === 'scoops' && Array.isArray(voIce.options)) {
        if (scoopsLabel) scoopsLabel.textContent = '\u041a\u0456\u043b\u044c\u043a\u0456\u0441\u0442\u044c \u043a\u0443\u043b\u044c\u043e\u043a:';
        scoopsGrid.innerHTML = '';
        var preScoopId = svIce ? (svIce.scoop_id || null) : null;

        voIce.options.forEach(function (opt, i) {
          var diff          = parseFloat(opt.price_diff) || 0;
          var isPreSelected = preScoopId ? (opt.id === preScoopId) : (i === 0);
          var totalP        = currentBasePrice + diff;

          var btn = document.createElement('button');
          btn.className          = 'im-scoop-btn' + (isPreSelected ? ' selected' : '');
          btn.dataset.priceDiff  = diff;
          btn.dataset.scoopId    = opt.id;
          btn.dataset.scoopLabel = opt.label;
          btn.innerHTML = '<span class="isb-label">' + opt.label + '</span>' +
                          '<span class="isb-price">' + totalP + ' \u20b4</span>';
          btn.addEventListener('click', function () {
            scoopsGrid.querySelectorAll('.im-scoop-btn').forEach(function (b) { b.classList.remove('selected'); });
            this.classList.add('selected');
            currentPriceDiff = parseFloat(this.dataset.priceDiff) || 0;
            updatePrice();
          });
          if (isPreSelected) currentPriceDiff = diff;
          scoopsGrid.appendChild(btn);
        });
        show(scoopsWrap);
        updatePrice();
      }

    /* ── Без опцій ── */
    } else {
      currentBasePrice = (data.price_override !== null && data.price_override !== undefined)
        ? data.price_override
        : (data.price || 0);
      updatePrice();
    }

    if (modalAdd) {
      modalAdd.textContent = '\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0437\u043c\u0456\u043d\u0438';
      modalAdd.classList.remove('saving');
    }
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function updateCrustLabel() {
    if (crustPriceLbl) crustPriceLbl.textContent = '+' + getCrustAdd() + ' \u20b4';
  }

  /* ── Close modal ── */
  function closeModal() {
    if (!overlay.classList.contains('open')) return;
    overlay.classList.add('closing');
    setTimeout(function () {
      overlay.classList.remove('open', 'closing');
      document.body.style.overflow = '';
    }, 360);
  }

  /* ── Size buttons ── */
  if (sizeSmall) sizeSmall.addEventListener('click', function () {
    currentSize = 'small';
    sizeSmall.classList.add('active');
    if (sizeLarge) sizeLarge.classList.remove('active');
    updateCrustLabel(); updatePrice();
  });
  if (sizeLarge) sizeLarge.addEventListener('click', function () {
    if (!currentPriceLarge) return;
    currentSize = 'large';
    sizeLarge.classList.add('active');
    if (sizeSmall) sizeSmall.classList.remove('active');
    updateCrustLabel(); updatePrice();
  });

  /* ── Crust toggle ── */
  if (cheeseCrust) cheeseCrust.addEventListener('change', function () {
    var cbBox = document.getElementById('crustCbBox');
    if (cbBox)     cbBox.classList.toggle('active', this.checked);
    if (crustWrap) crustWrap.classList.toggle('active', this.checked);
    updatePrice();
  });

  /* ── Save ── */
  if (modalAdd) modalAdd.addEventListener('click', function () {
    if (currentIndex < 0) return;
    if (modalAdd.classList.contains('saving')) return;

    var fd = new FormData();
    fd.append('index', currentIndex);

    if (currentCat === 'pizza_items') {
      fd.append('selected_size', currentSize);
      fd.append('cheese_crust', (cheeseCrust && cheeseCrust.checked) ? '1' : '0');
    } else if (currentCat === 'fast_food_items' || currentCat === 'ice_cream_items') {
      var selBtn = scoopsGrid ? scoopsGrid.querySelector('.im-scoop-btn.selected') : null;
      if (selBtn) {
        var svObj = {};
        if (currentCat === 'fast_food_items') {
          svObj = {
            type:          'filling',
            filling_id:    selBtn.dataset.scoopId,
            filling_label: selBtn.dataset.scoopLabel,
            price_diff:    currentPriceDiff,
          };
          if (selBtn.dataset.hasSizes === '1' && ffSizeGrid) {
            var activeSize = ffSizeGrid.querySelector('.im-size-btn.active');
            if (activeSize) {
              svObj.size_label = activeSize.dataset.sizeLabel || '';
              svObj.size_diff  = parseFloat(activeSize.dataset.priceDiff) || 0;
            }
          }
        } else {
          svObj = {
            type:        'scoops',
            scoop_id:    selBtn.dataset.scoopId,
            scoop_label: selBtn.dataset.scoopLabel,
            price_diff:  parseFloat(selBtn.dataset.priceDiff) || 0,
          };
        }
        fd.append('selected_variant', JSON.stringify(svObj));
      }
    }

    modalAdd.classList.add('saving');
    modalAdd.textContent = '\u0417\u0431\u0435\u0440\u0435\u0436\u0435\u043d\u043d\u044f...';

    fetch('../forms/update_cart_item.php', { method: 'POST', body: fd })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      })
      .then(function (text) {
        var resp;
        try { resp = JSON.parse(text); }
        catch (e) { console.error('[cart-edit] Bad JSON from server:', text); throw e; }
        if (!resp.ok) {
          console.error('[cart-edit] Server error:', resp.error || resp);
          modalAdd.textContent = '\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0437\u043c\u0456\u043d\u0438';
          modalAdd.classList.remove('saving');
          return;
        }

        /* ── Оновити рядок у DOM ── */
        var row   = document.querySelector('.cart-item[data-session-index="' + currentIndex + '"]');
        var subEl = row ? row.querySelector('.item-subtotal') : null;

        if (subEl) {
          subEl.textContent = Math.round(resp.new_subtotal).toLocaleString('uk-UA') + ' \u20b4';
          subEl.classList.remove('flash'); void subEl.offsetWidth; subEl.classList.add('flash');
        }
        if (row) {
          row.dataset.price = resp.new_price;
          /* Оновити option-теги */
          refreshOptTags(row, resp);
        }

        /* ── Перерахувати загальну суму ── */
        var totalEl = document.getElementById('cartTotal');
        if (totalEl) {
          var newTotal = Array.from(document.querySelectorAll('.cart-item')).reduce(function (sum, r) {
            var price = parseFloat(r.dataset.price) || 0;
            var qty   = parseInt((r.querySelector('.qty-value') || {}).value || '1', 10);
            return sum + price * qty;
          }, 0);
          totalEl.textContent = Math.round(newTotal).toLocaleString('uk-UA') + ' \u20b4';
          totalEl.classList.remove('flash'); void totalEl.offsetWidth; totalEl.classList.add('flash');
        }

        modalAdd.classList.remove('saving');
        modalAdd.textContent = '\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0437\u043c\u0456\u043d\u0438';
        closeModal();
        if (window.showToast) window.showToast('\u0422\u043e\u0432\u0430\u0440 \u043e\u043d\u043e\u0432\u043b\u0435\u043d\u043e');
      })
      .catch(function (err) {
        console.error('[cart-edit] Save failed:', err);
        modalAdd.textContent = '\u0417\u0431\u0435\u0440\u0435\u0433\u0442\u0438 \u0437\u043c\u0456\u043d\u0438';
        modalAdd.classList.remove('saving');
      });
  });

  /* ── Оновити option-теги в рядку кошика після збереження ── */
  function refreshOptTags(row, resp) {
    var optsEl = row.querySelector('.cart-item-opts');
    if (!optsEl) return;
    var tags = [];

    if (resp.selected_size) {
      tags.push(resp.selected_size === 'large' ? '40 \u0441\u043c' : '30 \u0441\u043c');
    }
    if (resp.cheese_crust) {
      tags.push('\u0421\u0438\u0440\u043d\u0438\u0439 \u0431\u043e\u0440\u0442\u0438\u043a');
    }
    if (resp.selected_variant) {
      try {
        var sv = JSON.parse(resp.selected_variant);
        if (sv.filling_label) {
          tags.push(sv.filling_label + (sv.size_label ? ' \u00b7 ' + sv.size_label : ''));
        } else if (sv.scoop_label) {
          tags.push(sv.scoop_label);
        }
      } catch (_) {}
    }

    if (tags.length) {
      optsEl.innerHTML = tags.map(function (t) {
        return '<span class="cart-opt-tag">' + t.replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</span>';
      }).join('');
      optsEl.style.display = '';
    }
  }

  /* ── Edit button click ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.edit-cart-item');
    if (!btn) return;
    fetch('../forms/get_cart_item.php?index=' + btn.dataset.sessionIndex)
      .then(function (r) { return r.text(); })
      .then(function (text) {
        var data;
        try { data = JSON.parse(text); }
        catch (e) { console.error('[cart-edit] Bad JSON from get_cart_item:', text); return; }
        if (data.ok) openEditModal(data);
        else console.error('[cart-edit] get_cart_item error:', data.error || data);
      })
      .catch(function (err) { console.error('[cart-edit] Fetch error:', err); });
  });

  /* ── Close triggers ── */
  if (modalClose)  modalClose.addEventListener('click', closeModal);
  if (modalCancel) modalCancel.addEventListener('click', closeModal);
  overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal();
  });

})();
