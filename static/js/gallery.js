document.addEventListener("DOMContentLoaded", function () {
  var grid = document.querySelector('#gallery');
  imagesLoaded(grid, function () {
    new Masonry(grid, {
      itemSelector: '.gallery-item',
      columnWidth: '.grid-sizer',
      gutter: 20,
      percentPosition: true
    });
  });
});
