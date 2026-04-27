document.addEventListener('DOMContentLoaded', function () {

  /* ── STAR PICKER ──────────────────────────────── */
  const picker      = document.getElementById('starPicker');
  const ratingInput = document.getElementById('ratingInput');
  const starHint    = document.getElementById('starHint');
  const ratingError = document.getElementById('ratingError');

  const hintMap = { 1: 'Жахливо', 2: 'Погано', 3: 'Нормально', 4: 'Добре', 5: 'Відмінно' };

  if (picker) {
    const stars = picker.querySelectorAll('.rv-star');

    function highlight(upTo) {
      stars.forEach(s => {
        const v = parseInt(s.dataset.value);
        s.classList.toggle('hovered', v <= upTo);
        s.classList.remove('selected');
      });
    }

    function select(value) {
      ratingInput.value = value;
      stars.forEach(s => {
        const v = parseInt(s.dataset.value);
        s.classList.toggle('selected', v <= value);
        s.classList.remove('hovered');
      });
      starHint.textContent = hintMap[value] || '';
      if (ratingError) ratingError.hidden = true;
      picker.classList.remove('rv-star-picker--error');
    }

    stars.forEach(star => {
      star.addEventListener('mouseover', () => highlight(parseInt(star.dataset.value)));
      star.addEventListener('mouseout',  () => {
        const cur = parseInt(ratingInput.value);
        if (cur > 0) {
          stars.forEach(s => s.classList.toggle('selected', parseInt(s.dataset.value) <= cur));
          stars.forEach(s => s.classList.remove('hovered'));
        } else {
          stars.forEach(s => s.classList.remove('hovered', 'selected'));
        }
      });
      star.addEventListener('click', () => select(parseInt(star.dataset.value)));
    });
  }

  /* ── FORM VALIDATION ──────────────────────────── */
  const form = document.getElementById('reviewForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      let valid = true;

      // rating
      const rating = parseInt(ratingInput?.value ?? '0');
      if (rating < 1) {
        valid = false;
        if (ratingError)  ratingError.hidden = false;
        if (picker)       picker.classList.add('rv-star-picker--error');
      }

      // name
      const nameEl  = document.getElementById('reviewName');
      const nameErr = document.getElementById('nameError');
      if (nameEl && nameEl.value.trim().length < 2) {
        valid = false;
        nameEl.classList.add('rv-input--error');
        if (nameErr) nameErr.hidden = false;
      } else if (nameEl) {
        nameEl.classList.remove('rv-input--error');
        if (nameErr) nameErr.hidden = true;
      }

      // text
      const textEl  = document.getElementById('reviewText');
      const textErr = document.getElementById('textError');
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

    // Clear errors on input
    ['reviewName', 'reviewText'].forEach(id => {
      const el  = document.getElementById(id);
      const err = document.getElementById(id === 'reviewName' ? 'nameError' : 'textError');
      el?.addEventListener('input', () => {
        el.classList.remove('rv-input--error');
        if (err) err.hidden = true;
      });
    });
  }

  /* ── SUCCESS MESSAGE AUTO-HIDE ───────────────── */
  const successMsg = document.getElementById('successMsg');
  if (successMsg) {
    setTimeout(() => {
      successMsg.style.transition = 'opacity 0.5s ease';
      successMsg.style.opacity = '0';
      setTimeout(() => successMsg.remove(), 520);
    }, 4000);
  }

  /* ── READ MORE TOGGLE ─────────────────────────── */
  document.querySelectorAll('.rv-read-more').forEach(btn => {
    const textEl = btn.previousElementSibling;
    if (!textEl) return;

    let expanded = false;
    btn.addEventListener('click', () => {
      expanded = !expanded;
      textEl.textContent = expanded
        ? (textEl.dataset.full  || textEl.textContent)
        : (textEl.dataset.short || textEl.textContent);
      btn.textContent = expanded ? 'згорнути' : 'читати далі';
    });
  });

});
