const searchInput = document.getElementById('menu-search');
const catSection  = document.querySelector('.category');
const resultsBox  = document.getElementById('search-results');
const allItems    = document.getElementById('all-items').children;

searchInput.addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();

  if (q.length === 0) {
    catSection.style.display = '';
    resultsBox.style.display = 'none';
    resultsBox.innerHTML = '';
    return;
  }

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

document.body.addEventListener('click', e => {
  if (e.target.classList.contains('add-to-cart')) {
    e.target.classList.add('added');
    setTimeout(() => e.target.classList.remove('added'), 300);
  }
});
