let slideIndex = 0;
const slides = document.querySelectorAll('.slide');
const dots = document.querySelectorAll('.dot');
const prev = document.querySelector('.arrow.left');
const next = document.querySelector('.arrow.right');

function showSlide(index) {
    slides.forEach((slide, i) => {
        slide.classList.toggle('active', i === index);
        dots[i].classList.toggle('active', i === index);
    });
    slideIndex = index;
}

prev.addEventListener('click', () => {
    let newIndex = (slideIndex - 1 + slides.length) % slides.length;
    showSlide(newIndex);
});

next.addEventListener('click', () => {
    let newIndex = (slideIndex + 1) % slides.length;
    showSlide(newIndex);
});

dots.forEach((dot, i) => {
    dot.addEventListener('click', () => showSlide(i));
});

setInterval(() => {
    let newIndex = (slideIndex + 1) % slides.length;
    showSlide(newIndex);
}, 5000);

showSlide(0);


