const observers = document.querySelectorAll('.food-item, .drink-item, .dessert-item');
const io = new IntersectionObserver(
  (entries) => {
    entries.forEach(({isIntersecting, target}) => {
      if (isIntersecting) {
        target.classList.add('visible');
        io.unobserve(target);
      }
    });
  },
  { threshold: 0.2 }
);
observers.forEach(el => io.observe(el));
