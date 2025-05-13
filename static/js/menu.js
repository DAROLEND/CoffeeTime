// отримуємо елементи
const searchInput = document.getElementById('menu-search');
const catSection  = document.querySelector('.category');
const resultsBox  = document.getElementById('search-results');
const allItems    = document.getElementById('all-items').children;

// обробник вводу в поле пошуку
searchInput.addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();

  if (q.length === 0) {
    // якщо порожньо — показуємо лише поточну категорію
    catSection.style.display = '';
    resultsBox.style.display = 'none';
    resultsBox.innerHTML = '';
    return;
  }

  // інакше — сховаємо категорію й відобразимо результати
  catSection.style.display = 'none';
  resultsBox.innerHTML = '';

  Array.from(allItems).forEach(card => {
    const name = card.querySelector('h3').textContent.toLowerCase();
    if (name.includes(q)) {
      resultsBox.appendChild(card.cloneNode(true));
    }
  });
  

  resultsBox.style.display = 'flex';
});

// Делегуємо клік по кнопці "Додати в корзину" для анімації
document.body.addEventListener('click', e => {
  if (e.target.classList.contains('add-to-cart')) {
    e.target.classList.add('added');
    setTimeout(() => e.target.classList.remove('added'), 300);
  }
});
