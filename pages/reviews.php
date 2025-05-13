<?php
session_start();

$page      = 'reviews';
$pageTitle = 'Відгуки — Coffee Time';
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
    <h1>Відгуки наших клієнтів</h1>
    <div class="expand-grid">
      <div class="testimonial-item">
        <p>«Найсмачніша кава в місті, дуже привітний персонал!»</p>
        <strong>— Марія С.</strong>
      </div>
      <div class="testimonial-item">
        <p>«Замовляю десерти та каву з доставкою — завжди гаряче і швидко.»</p>
        <strong>— Олег Т.</strong>
      </div>
      <div class="testimonial-item">
        <p>«Чудова атмосфера та стабільно відмінний латте.»</p>
        <strong>— Наталія К.</strong>
      </div>
      <div class="testimonial-item">
        <p>«Ідеально для роботи чи зустрічей — wifi, затишок, смачна їжа!»</p>
        <strong>— Андрій П.</strong>
      </div>
    </div>
  </main>

  <?php include '../includes/footer.php'; ?>
</body>
</html>
