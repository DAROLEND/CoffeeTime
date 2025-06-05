document.addEventListener("DOMContentLoaded", function () {
  // ЗІРКИ
  const stars = document.querySelectorAll("#starRating span");
  const ratingInput = document.getElementById("ratingInput");

  stars.forEach((star) => {
    star.addEventListener("mouseover", () => {
      const val = parseInt(star.dataset.value);
      highlightStars(val);
    });

    star.addEventListener("mouseout", () => {
      highlightStars(parseInt(ratingInput.value));
    });

    star.addEventListener("click", () => {
      ratingInput.value = star.dataset.value;
      highlightStars(parseInt(star.dataset.value));
    });
  });

  function highlightStars(rating) {
    stars.forEach((s) => {
      s.classList.toggle("active", parseInt(s.dataset.value) <= rating);
    });
  }

  // ВИПАДАЮЧЕ СОРТУВАННЯ
  const sortWrapper = document.querySelector(".sort-wrapper");
  const sortButton = document.querySelector(".sort-button");

  sortButton.addEventListener("click", function (e) {
    e.stopPropagation(); // щоб не закрилося миттєво
    sortWrapper.classList.toggle("open");
  });

  window.addEventListener("click", function (e) {
    if (!sortWrapper.contains(e.target)) {
      sortWrapper.classList.remove("open");
    }
  });
});

// ВАЛІДАЦІЯ ПЕРЕД ВІДПРАВКОЮ
function validateReviewForm() {
  const name = document.getElementById('name').value.trim();
  const rating = parseInt(document.getElementById('ratingInput').value);
  if (!name || rating === 0) {
    alert('Будь ласка, введіть ім’я та оберіть оцінку.');
    return false;
  }
  return true;
}
