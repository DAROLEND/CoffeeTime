<?php
session_start();
require '../db/db.php';

$allowedTables = [
    'coffee_items',
    'fast_food_items',
    'pizza_items',
    'cold_drink_items',
    'dessert_items'
];

if (isset($_GET['action']) && $_GET['action'] === 'clear') {
    unset($_SESSION['cart']);
    header('Location: cart.php');
    exit;
}

if (!isset($_SESSION['cart']) || !is_array($_SESSION['cart'])) {
    $_SESSION['cart'] = [];
}

if (isset($_GET['action'], $_GET['category'], $_GET['id']) && $_GET['action'] === 'add') {
    $table = $_GET['category'];
    $id    = (int)$_GET['id'];
    if (in_array($table, $allowedTables, true) && $id > 0) {
        $_SESSION['lastCategory'] = $table;
        $found = null;
        foreach ($_SESSION['cart'] as $i => $it) {
            if ($it['category'] === $table && $it['id'] === $id) {
                $found = $i;
                break;
            }
        }
        if ($found !== null) {
            $_SESSION['cart'][$found]['quantity']++;
        } else {
            $_SESSION['cart'][] = [
                'category' => $table,
                'id'       => $id,
                'quantity' => 1
            ];
        }
    }
    header('Location: cart.php');
    exit;
}

if (isset($_GET['remove'])) {
    $idx = (int)$_GET['remove'];
    if (isset($_SESSION['cart'][$idx])) {
        unset($_SESSION['cart'][$idx]);
        $_SESSION['cart'] = array_values($_SESSION['cart']);
    }
    header('Location: cart.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_quantity'])) {
    $idx = (int)($_POST['index'] ?? -1);
    if (isset($_SESSION['cart'][$idx])) {
        $q = max(1, (int)($_POST['quantity'] ?? 1));
        $_SESSION['cart'][$idx]['quantity'] = $q;
    }
    header('Location: cart.php');
    exit;
}

$total = 0;
$items = [];
$stmt  = null;
$prevTable = '';

foreach ($_SESSION['cart'] as $idx => $it) {
    if (!in_array($it['category'], $allowedTables, true)) continue;
    $table = $it['category'];
    $id    = $it['id'];

    if (!$stmt || $prevTable !== $table) {
        $stmt = $conn->prepare("SELECT name, description, image, price FROM `$table` WHERE id = ?");
        $prevTable = $table;
    }
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $res = $stmt->get_result();

    if ($row = $res->fetch_assoc()) {
        $row['quantity'] = $it['quantity'];
        $row['idx']      = $idx;
        $row['subtotal'] = $row['price'] * $it['quantity'];
        $total += $row['subtotal'];
        $items[] = $row;
    }
}
if ($stmt) {
    $stmt->close();
}

$backCat = $_SESSION['lastCategory'] ?? 'coffee_items';
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <title>Корзина — Coffee Time</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/cart.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
  <?php include '../includes/header.php'; ?>
  <main>
    <section class="cart">
      <h1>Ваша корзина</h1>

      <?php if (empty($items)): ?>
        <p>Ваша корзина порожня.</p>
        <a href="menu.php?category=<?= urlencode($backCat) ?>" class="btn">
          Повернутися до меню
        </a>
      <?php else: ?>
        <div class="cart-items">
          <?php foreach ($items as $it): ?>
            <div class="cart-item">
              <img
                src="../<?= htmlspecialchars($it['image'], ENT_QUOTES) ?>"
                alt="<?= htmlspecialchars($it['name'], ENT_QUOTES) ?>"
                loading="lazy"
              >
              <div class="cart-item-info">
                <h3><?= htmlspecialchars($it['name'], ENT_QUOTES) ?></h3>
                <p><?= htmlspecialchars($it['description'], ENT_QUOTES) ?></p>
                <div class="cart-item-price">
                  <span>
                    <?= number_format($it['price'], 2, ',', ' ') ?> ₴ × <?= $it['quantity'] ?>
                    = <strong><?= number_format($it['subtotal'], 2, ',', ' ') ?> ₴</strong>
                  </span>
                  <a href="?remove=<?= $it['idx'] ?>" class="remove-item">
                    Видалити
                  </a>
                </div>
                <form method="post" class="quantity-form">
                  <input type="hidden" name="index" value="<?= $it['idx'] ?>">
                  <input type="hidden" name="update_quantity" value="1">
                  <label>Кількість:</label>
                  <input
                    type="number"
                    name="quantity"
                    min="1"
                    value="<?= $it['quantity'] ?>"
                    onchange="this.form.submit()"
                  >
                </form>
              </div>
            </div>
          <?php endforeach; ?>
        </div>

        <div class="cart-summary">
          <h2>Підсумок</h2>
          <p>Загальна сума: <span class="total-price"><?= number_format($total, 2, ',', ' ') ?> ₴</span></p>
          <div class="cart-actions">
            <form action="checkout.php" method="post">
              <button type="submit" class="checkout-btn">Оформити замовлення</button>
            </form>
            <a href="menu.php?category=<?= urlencode($backCat) ?>" class="btn">
              Повернутися до меню
            </a>
            <a href="cart.php?action=clear"
               class="btn btn-clear"
               onclick="return confirm('Ви впевнені, що хочете очистити корзину?');">
              Очистити корзину
            </a>
          </div>
        </div>
      <?php endif; ?>
    </section>
  </main>
  <?php include '../includes/footer.php'; ?>
</body>
</html>
