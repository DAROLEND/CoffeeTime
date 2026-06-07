document.addEventListener('DOMContentLoaded', function () {

  /* ── STAT BARS ANIMATE-IN ─────────────────────── */
  document.querySelectorAll('.rv-bar-fill').forEach(function (bar) {
    var target = bar.dataset.width;
    if (target) {
      requestAnimationFrame(function () {
        setTimeout(function () {
          bar.style.width = target + '%';
        }, 120);
      });
    }
  });

  /* ── AVG NUMBER COUNT-UP ─────────────────────── */
  var avgEl = document.querySelector('.rv-avg-num[data-value]');
  if (avgEl) {
    var target = parseFloat(avgEl.dataset.value);
    if (!isNaN(target) && target > 0) {
      var start     = 0;
      var duration  = 900;
      var startTime = null;
      function animateAvg(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased    = 1 - Math.pow(1 - progress, 3);
        avgEl.textContent = (start + (target - start) * eased).toFixed(1);
        if (progress < 1) requestAnimationFrame(animateAvg);
      }
      requestAnimationFrame(animateAvg);
    }
  }

  /* ── STAR PICKER ──────────────────────────────── */
  var picker      = document.getElementById('starPicker');
  var ratingInput = document.getElementById('ratingInput');
  var starHint    = document.getElementById('starHint');
  var ratingError = document.getElementById('ratingError');

  var hintMap = { 1: 'Жахливо', 2: 'Погано', 3: 'Нормально', 4: 'Добре', 5: 'Відмінно' };

  if (picker) {
    var stars = picker.querySelectorAll('.rv-star');

    function highlight(upTo) {
      stars.forEach(function (s) {
        var v = parseInt(s.dataset.value);
        s.classList.toggle('hovered', v <= upTo);
        s.classList.remove('selected');
      });
    }

    function select(value) {
      ratingInput.value = value;
      stars.forEach(function (s) {
        var v = parseInt(s.dataset.value);
        s.classList.toggle('selected', v <= value);
        s.classList.remove('hovered');
      });
      starHint.textContent = hintMap[value] || '';
      if (ratingError) ratingError.hidden = true;
      picker.classList.remove('rv-star-picker--error');
    }

    stars.forEach(function (star) {
      star.addEventListener('mouseover', function () { highlight(parseInt(star.dataset.value)); });
      star.addEventListener('mouseout', function () {
        var cur = parseInt(ratingInput.value);
        if (cur > 0) {
          stars.forEach(function (s) { s.classList.toggle('selected', parseInt(s.dataset.value) <= cur); });
          stars.forEach(function (s) { s.classList.remove('hovered'); });
        } else {
          stars.forEach(function (s) { s.classList.remove('hovered', 'selected'); });
        }
      });
      star.addEventListener('click', function () { select(parseInt(star.dataset.value)); });
    });
  }

  /* ── FORM VALIDATION ──────────────────────────── */
  var form = document.getElementById('reviewForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      var valid = true;

      var rating = parseInt(ratingInput ? ratingInput.value : '0');
      if (rating < 1) {
        valid = false;
        if (ratingError) ratingError.hidden = false;
        if (picker)      picker.classList.add('rv-star-picker--error');
      }

      var nameEl  = document.getElementById('reviewName');
      var nameErr = document.getElementById('nameError');
      if (nameEl && nameEl.value.trim().length < 2) {
        valid = false;
        nameEl.classList.add('rv-input--error');
        if (nameErr) nameErr.hidden = false;
      } else if (nameEl) {
        nameEl.classList.remove('rv-input--error');
        if (nameErr) nameErr.hidden = true;
      }

      var textEl  = document.getElementById('reviewText');
      var textErr = document.getElementById('textError');
      if (textEl && textEl.value.trim().length < 10) {
        valid = false;
        textEl.classList.add('rv-input--error');
        if (textErr) textErr.hidden = false;
      } else if (textEl) {
        textEl.classList.remove('rv-input--error');
        if (textErr) textErr.hidden = true;
      }

      if (!valid) e.preventDefault();
    });

    ['reviewName', 'reviewText'].forEach(function (id) {
      var el  = document.getElementById(id);
      var err = document.getElementById(id === 'reviewName' ? 'nameError' : 'textError');
      if (el) {
        el.addEventListener('input', function () {
          el.classList.remove('rv-input--error');
          if (err) err.hidden = true;
        });
      }
    });
  }

  /* ── SUCCESS MESSAGE AUTO-HIDE ───────────────── */
  var successMsg = document.getElementById('successMsg');
  if (successMsg) {
    setTimeout(function () {
      successMsg.style.transition = 'opacity 0.5s ease';
      successMsg.style.opacity = '0';
      setTimeout(function () { successMsg.remove(); }, 520);
    }, 4000);
  }

  /* ── READ MORE TOGGLE ─────────────────────────── */
  function initReadMore() {
    document.querySelectorAll('.rv-read-more').forEach(function (btn) {
      // Avoid double-binding after AJAX reinit
      if (btn._readMoreBound) return;
      btn._readMoreBound = true;

      var textEl   = btn.previousElementSibling;
      if (!textEl) return;
      var expanded = false;

      btn.addEventListener('click', function () {
        expanded = !expanded;
        textEl.textContent = expanded
          ? (textEl.dataset.full  || textEl.textContent)
          : (textEl.dataset.short || textEl.textContent);
        btn.textContent = expanded ? 'згорнути' : 'читати далі';
      });
    });
  }

  initReadMore();

  /* ═══════════════════════════════════════════════
     AJAX FILTER / SORT
  ════════════════════════════════════════════════ */
  var gridWrap  = document.getElementById('rvGridWrap');
  var controls  = document.getElementById('rvControls');

  if (!gridWrap) return; // page may not have the grid

  /* Build a query-string from current state + overrides */
  function buildParams(overrides) {
    var base = {
      sort:   gridWrap.dataset.sort   || 'newest',
      filter: gridWrap.dataset.filter || '0',
      p:      gridWrap.dataset.page   || '1',
    };
    var merged = Object.assign({}, base, overrides);

    var qs = [];
    // Always include ajax flag for fetch calls (stripped for pushState)
    if (merged.sort   && merged.sort   !== 'newest') qs.push('sort='   + encodeURIComponent(merged.sort));
    if (merged.filter && merged.filter !== '0')       qs.push('filter=' + encodeURIComponent(merged.filter));
    if (merged.p      && merged.p      !== '1')       qs.push('p='      + encodeURIComponent(merged.p));
    return qs.join('&');
  }

  var currentRequest = null; // track in-flight XHR to cancel if needed

  function fetchGrid(overrides, pushState) {
    var qs      = buildParams(overrides);
    var ajaxUrl = 'reviews.php?ajax=1' + (qs ? '&' + qs : '');
    var pageUrl = 'reviews.php'        + (qs ? '?' + qs : '');

    // Update state on wrapper
    if (overrides.sort   !== undefined) gridWrap.dataset.sort   = overrides.sort;
    if (overrides.filter !== undefined) gridWrap.dataset.filter = overrides.filter;
    if (overrides.p      !== undefined) gridWrap.dataset.page   = overrides.p;

    // Show loading
    gridWrap.classList.add('loading');

    // Cancel previous request
    if (currentRequest) { currentRequest.abort(); }
    var xhr = new XMLHttpRequest();
    currentRequest = xhr;

    xhr.open('GET', ajaxUrl, true);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.onload = function () {
      currentRequest = null;
      gridWrap.classList.remove('loading');

      if (xhr.status !== 200) return;
      var data;
      try { data = JSON.parse(xhr.responseText); } catch (e) { return; }
      if (!data.ok) return;

      gridWrap.innerHTML = data.html;
      initReadMore();

      if (pushState !== false) {
        history.pushState({ sort: gridWrap.dataset.sort, filter: gridWrap.dataset.filter, p: gridWrap.dataset.page }, '', pageUrl);
      }

      // Scroll to controls if grid is below viewport
      if (controls) {
        var rect = controls.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) {
          controls.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    };

    xhr.onerror = function () {
      currentRequest = null;
      gridWrap.classList.remove('loading');
    };

    xhr.send();
  }

  /* ── Sort tab clicks ─────────────────────────── */
  var sortTabs = document.getElementById('rvSortTabs');
  if (sortTabs) {
    sortTabs.addEventListener('click', function (e) {
      var btn = e.target.closest('.rv-tab[data-sort]');
      if (!btn) return;
      e.preventDefault();

      // Update active state immediately
      sortTabs.querySelectorAll('.rv-tab').forEach(function (b) { b.classList.remove('rv-tab--active'); });
      btn.classList.add('rv-tab--active');

      fetchGrid({ sort: btn.dataset.sort, p: '1' });
    });
  }

  /* ── Filter tab clicks ───────────────────────── */
  var filterTabs = document.getElementById('rvFilterTabs');
  if (filterTabs) {
    filterTabs.addEventListener('click', function (e) {
      var btn = e.target.closest('.rv-tab[data-filter]');
      if (!btn) return;
      e.preventDefault();

      filterTabs.querySelectorAll('.rv-tab').forEach(function (b) { b.classList.remove('rv-tab--active'); });
      btn.classList.add('rv-tab--active');

      fetchGrid({ filter: btn.dataset.filter, p: '1' });
    });
  }

  /* ── Pagination link clicks inside grid ──────── */
  gridWrap.addEventListener('click', function (e) {
    var link = e.target.closest('.rv-page-btn[href]');
    if (!link) return;
    e.preventDefault();

    // Parse page from href query string
    var href   = link.getAttribute('href');
    var params = new URLSearchParams(href.split('?')[1] || '');
    var p      = params.get('p') || '1';
    var s      = params.get('sort')   || gridWrap.dataset.sort   || 'newest';
    var f      = params.get('filter') || gridWrap.dataset.filter || '0';

    fetchGrid({ sort: s, filter: f, p: p });
  });

  /* ── Browser back/forward ────────────────────── */
  window.addEventListener('popstate', function (e) {
    if (e.state && (e.state.sort !== undefined || e.state.filter !== undefined)) {
      var s = e.state.sort   || 'newest';
      var f = e.state.filter || '0';
      var p = e.state.p      || '1';

      // Sync active tabs
      if (sortTabs) {
        sortTabs.querySelectorAll('.rv-tab').forEach(function (b) {
          b.classList.toggle('rv-tab--active', b.dataset.sort === s);
        });
      }
      if (filterTabs) {
        filterTabs.querySelectorAll('.rv-tab').forEach(function (b) {
          b.classList.toggle('rv-tab--active', b.dataset.filter === f);
        });
      }

      fetchGrid({ sort: s, filter: f, p: p }, false /* don't pushState again */);
    }
  });

});
