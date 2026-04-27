/* Scroll-reveal для .food-item, .drink-item, .dessert-item
   Stagger-ефект: кожна наступна картка в ряду з'являється на 100ms пізніше */

const revealItems = document.querySelectorAll('.food-item, .drink-item, .dessert-item');

const io = new IntersectionObserver((entries) => {
  entries.forEach(({ isIntersecting, target }) => {
    if (!isIntersecting) return;

    // Знаходимо позицію картки серед братів у батьківському контейнері
    const siblings = Array.from(target.parentElement.children);
    const idx = siblings.indexOf(target);

    // Додаємо delay тільки на час появи — потім прибираємо щоб hover не лагав
    target.style.transitionDelay = `${idx * 0.1}s`;
    target.classList.add('visible');
    setTimeout(() => { target.style.transitionDelay = '0s'; }, 600 + idx * 100);

    io.unobserve(target);
  });
}, { threshold: 0.12 });

revealItems.forEach(el => io.observe(el));
