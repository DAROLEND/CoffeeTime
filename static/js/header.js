// static/js/header.js
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.querySelector('.menu-toggle');
    const header      = document.querySelector('.site-header');
  
    if (!menuToggle || !header) return;
  
    menuToggle.addEventListener('click', () => {
      header.classList.toggle('open');
    });
  });
  