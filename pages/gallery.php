<?php
session_start();

$page      = 'gallery';
$pageTitle = 'Галерея — Coffee Time';
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
    <h1>Галерея</h1>
    <div class="expand-grid">
      <img src="../static/images/gallery/1.jpg" alt="Інтер'єр кафе">
      <img src="../static/images/gallery/2.jpg" alt="Атмосфера на терасі">
      <img src="../static/images/gallery/3.jpg" alt="Кавові зерна">
      <img src="../static/images/gallery/4.jpg" alt="Бариста за роботою">
      <img src="../static/images/gallery/5.jpg" alt="Десерти на вітрині">
      <img src="../static/images/gallery/6.jpg" alt="Гості в кафе">
    </div>
  </main>

  <?php include '../includes/footer.php'; ?>
</body>
</html>
