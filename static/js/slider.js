document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.slider').forEach(initSlider);
});

function initSlider(root) {
  const isCategory = root.classList.contains('category-slider');
  const slides = Array.from(root.querySelectorAll('.slide'));
  const prev = root.querySelector('.arrow.left');
  const next = root.querySelector('.arrow.right');
  const dots = isCategory ? [] : Array.from(root.querySelectorAll('.dot'));
  const track = isCategory ? root.querySelector('.slider-track') : null;

  let idx = 0;
  let timer;

  setTimeout(() => {
    const style = getComputedStyle(slides[0]);
    const gap = parseFloat(style.marginRight) || 0;
    const cardWidth = slides[0].getBoundingClientRect().width + gap;

    const visibleCount = 3;

    function show(n) {
      if (isCategory) {
        const maxIndex = slides.length - visibleCount;
        if (slides.length <= visibleCount) {
          idx = 0;
        } else {
          if (n > maxIndex) {
            idx = 0;
          } else if (n < 0) {
            idx = maxIndex;
          } else {
            idx = n;
          }
        }
        track.style.transform = `translateX(${-idx * cardWidth}px)`;
      } else {
        idx = ((n % slides.length) + slides.length) % slides.length;
        slides.forEach((s, i) => s.classList.toggle('active', i === idx));
        dots.forEach((d, i) => d.classList.toggle('active', i === idx));
      }
    }

    prev.addEventListener('click', () => show(idx - 1));
    next.addEventListener('click', () => show(idx + 1));

    if (isCategory) {
      show(0);
    } else {
      root.addEventListener('mouseenter', () => clearInterval(timer));
      root.addEventListener('mouseleave', () => {
        timer = setInterval(() => show(idx + 1), 5000);
      });
      show(0);
      timer = setInterval(() => show(idx + 1), 5000);
    }
  }, 50);
}
