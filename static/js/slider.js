// static/js/slider.js
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.slider').forEach(initSlider);
});

function initSlider(root) {
  let idx = 0, timer;
  const isCategory = root.classList.contains('category-slider');
  const slides     = Array.from(root.querySelectorAll('.slide'));
  const prev       = root.querySelector('.arrow.left');
  const next       = root.querySelector('.arrow.right');
  const dots       = isCategory ? [] : Array.from(root.querySelectorAll('.dot'));
  const track      = isCategory ? root.querySelector('.slider-track') : null;

  // Дамо браузеру мить, щоб елементи відрендерились і ми змогли вичислити їхню ширину
  setTimeout(() => {
    const style      = getComputedStyle(slides[0]);
    const gap        = parseFloat(style.marginRight) || 0;
    const cardWidth  = slides[0].getBoundingClientRect().width + gap;

    function show(n) {
      // wrap-around індексу
      idx = ((n % slides.length) + slides.length) % slides.length;

      if (isCategory) {
        // нескінченне гортання track
        track.style.transform = `translateX(${-idx * cardWidth}px)`;
      } else {
        // hero-слайдер класичний
        slides.forEach((s,i) => s.classList.toggle('active', i === idx));
        dots.forEach  ((d,i) => d.classList.toggle('active', i === idx));
      }
    }

    // ручні кнопки завжди
    prev.addEventListener('click', () => show(idx - 1));
    next.addEventListener('click', () => show(idx + 1));

    if (isCategory) {
      // тільки ручне гортання, без автоплею
      show(0);
    } else {
      // автоплей для hero
      root.addEventListener('mouseenter', () => clearInterval(timer));
      root.addEventListener('mouseleave', () => {
        timer = setInterval(() => show(idx + 1), 5000);
      });
      show(0);
      timer = setInterval(() => show(idx + 1), 5000);
    }
  }, 50);
}
