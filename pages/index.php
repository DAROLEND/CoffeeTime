<?php
session_start();
require '../db/db.php';

$heroSlides = [
  ['image' => 'static/images/categories/coffee_category.jpg', 'text' => 'Кожен ковток — тепла історія'],
  ['image' => 'static/images/categories/dessert.jpg',        'text' => 'Неможливо встояти…'],
  ['image' => 'static/images/categories/fast_food.jpg',      'text' => 'Ідеальне комбо'],
];

$sections = [
  'fast_food_items'  => ['title' => 'Їжа, яку найчастіше обирають', 'css' => 'food-item'],
  'cold_drink_items' => ['title' => 'Найпопулярніші напої',         'css' => 'drink-item'],
  'dessert_items'    => ['title' => 'Очікувані десерти',           'css' => 'dessert-item'],
];
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Coffee Time</title>
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/slider.css">
  <link rel="stylesheet" href="../static/css/slider_food.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
<?php
  $page = 'home';
  include '../includes/header.php';
?>
<main>
  <section class="hero">
    <div class="slider">
      <button class="arrow left">&#10094;</button>
      <button class="arrow right">&#10095;</button>
      <?php foreach ($heroSlides as $i => $s): ?>
        <div class="slide<?= $i === 0 ? ' active' : '' ?>"
             style="background-image: url('../<?= $s['image'] ?>')">
          <div class="hero-text"><h1><?= $s['text'] ?></h1></div>
        </div>
      <?php endforeach; ?>
      <div class="slider-controls">
        <?php foreach ($heroSlides as $i => $_): ?>
          <span class="dot<?= $i === 0 ? ' active' : '' ?>"></span>
        <?php endforeach; ?>
      </div>
    </div>
  </section>

  <?php foreach ($sections as $table => $cfg): ?>
    <section>
      <h2><?= $cfg['title'] ?></h2>
      <div class="slider category-slider">
        <button class="arrow left">&#10094;</button>
        <button class="arrow right">&#10095;</button>
        <div class="slider-track">
          <?php
            $res = $conn->query("SELECT name, image FROM `{$table}` ORDER BY popularity DESC LIMIT 5");
            while ($item = $res->fetch_assoc()):
              $img = '../' . ltrim($item['image'], '/');
          ?>
            <div class="slide">
              <div class="item-card <?= $cfg['css'] ?>">
                <img src="<?= htmlspecialchars($img) ?>"
                     alt="<?= htmlspecialchars($item['name']) ?>">
              </div>
            </div>
          <?php endwhile; ?>
        </div>
      </div>
    </section>
  <?php endforeach; ?>
</main>

<?php include '../includes/footer.php'; ?>
<script src="../static/js/header.js"></script>
<script src="../static/js/slider.js"></script>
<script src="../static/js/scroll-reveal.js"></script>
</body>
</html>
