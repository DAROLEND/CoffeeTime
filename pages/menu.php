<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();
require '../db/db.php';

$tables = [
    'coffee_items'      => 'Кава',
    'fast_food_items'   => 'Фаст-фуд',
    'pizza_items'       => 'Піца',
    'cold_drink_items'  => 'Холодні напої',
    'dessert_items'     => 'Десерти',
];

$current = $_GET['category'] ?? key($tables);
if (!isset($tables[$current])) {
    $current = key($tables);
}

function e(string $v): string {
    return htmlspecialchars($v, ENT_QUOTES);
}
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Меню – Coffee Time</title>
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/menu.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
<?php
  $page = 'menu';
  include '../includes/header.php';
  ?>

<main class="menu">
  <h1>Меню</h1>

  <nav class="categories-nav">
    <?php foreach ($tables as $tbl => $label): ?>
      <a href="?category=<?= urlencode($tbl) ?>"
         class="category-link <?= $tbl === $current ? 'active' : '' ?>">
        <?= e($label) ?>
      </a>
    <?php endforeach; ?>
  </nav>

  <section class="category" id="<?= e($current) ?>">
    <h2><?= e($tables[$current]) ?></h2>

    <div class="menu-items">
      <?php
      $stmt = $conn->prepare("SELECT id,name,description,image,price FROM `$current`");
      $stmt->execute();
      $res = $stmt->get_result();
      while ($item = $res->fetch_assoc()):
        $url = 'cart.php?action=add'
             . '&category=' . urlencode($current)
             . '&id=' . (int)$item['id'];
      ?>
        <div class="menu-item">
          <img src="../<?= e($item['image']) ?>"
               alt="<?= e($item['name']) ?>"
               loading="lazy">
          <h3><?= e($item['name']) ?></h3>
          <p><?= e($item['description']) ?></p>
          <span class="price"><?= number_format($item['price'],2,',',' ') ?> ₴</span>
          <a href="<?= $url ?>" class="add-to-cart">Додати</a>
        </div>
      <?php endwhile;
      $stmt->close();
      ?>
    </div>
  </section>

  <section id="all-items" style="display:none;">
    <?php foreach ($tables as $tbl => $label):
      $all = $conn->query("SELECT id,name,description,image,price FROM `$tbl`");
      while ($it = $all->fetch_assoc()):
        $url = 'cart.php?action=add'
             . '&category=' . urlencode($tbl)
             . '&id=' . (int)$it['id'];
    ?>
      <div class="menu-item">
        <img src="../<?= e($it['image']) ?>"
             alt="<?= e($it['name']) ?>"
             loading="lazy">
        <h3><?= e($it['name']) ?></h3>
        <p><?= e($it['description']) ?></p>
        <span class="price"><?= number_format($it['price'],2,',',' ') ?> ₴</span>
        <a href="<?= $url ?>" class="add-to-cart">Додати</a>
      </div>
    <?php 
      endwhile;
    endforeach; ?>
  </section>
</main>

<?php include '../includes/footer.php'; ?>
<script src="../static/js/menu.js"></script>
</body>
</html>
