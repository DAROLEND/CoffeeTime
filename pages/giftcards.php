<?php
session_start();

$page      = 'giftcards';
$pageTitle = 'Подарункові сертифікати — Coffee Time';
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title><?= htmlspecialchars($pageTitle) ?></title>
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
  <?php include '../includes/header.php'; ?>

  <main class="page-content">
    <h1>Подарункові сертифікати</h1>
    <div class="expand-grid">
      <div class="food-item">
        <img src="../static/images/certs/cert-500.png" alt="Сертифікат 500 грн">
        <div class="card-content">
          <h3>Сертифікат 500 ₴</h3>
          <p>Подаруйте 500 грн на перекус для друзів</p>
          <button class="auth-btn">Купити</button>
        </div>
      </div>
      <div class="food-item">
        <img src="../static/images/certs/cert-1000.png" alt="Сертифікат 1000 грн">
        <div class="card-content">
          <h3>Сертифікат 1000 ₴</h3>
          <p>Подаруйте 1000 грн, щоб важлива для для вас людина могла насолодитися.</p>
          <button class="auth-btn">Купити</button>
        </div>
      </div>
      <div class="food-item">
        <img src="../static/images/certs/cert-2000.png" alt="Сертифікат 2000 грн">
        <div class="card-content">
          <h3>Сертифікат 2000 ₴</h3>
          <p>Ідеальний подарунок для справжньої компанії друзів чи родини.</p>
          <button class="auth-btn">Купити</button>
        </div>
      </div>
    </div>
  </main>

  <?php include '../includes/footer.php'; ?>
</body>
</html>
