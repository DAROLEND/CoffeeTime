<?php
// Для локального налагодження — відображати всі помилки
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();
require_once __DIR__ . '/../db/db.php';

// 1) Якщо кошик порожній — редірект на головну
if (empty($_SESSION['cart']) || !is_array($_SESSION['cart'])) {
    header('Location: ../pages/index.php');
    exit;
}

$cart = $_SESSION['cart'];
$user = $_SESSION['user'] ?? null;

// 2) Завантажуємо товари з БД і рахуємо загальну суму
$orderDetails = [];
$total = 0.0;
foreach ($cart as $ci) {
    $table = $ci['category'];
    $id    = (int)$ci['id'];
    $stmt  = $conn->prepare("SELECT name, image, price FROM `$table` WHERE id = ?");
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $res = $stmt->get_result();
    if ($row = $res->fetch_assoc()) {
        $row['quantity'] = $ci['quantity'];
        $row['subtotal'] = $row['price'] * $ci['quantity'];
        $total += $row['subtotal'];
        $orderDetails[] = $row;
    }
    $stmt->close();
}

// 3) Підготовка полів: POST → профіль → порожньо
$firstName = $_POST['first_name'] ?? ($user['client_name']        ?? '');
$lastName  = $_POST['last_name']  ?? ($user['client_surname']     ?? '');
$phone     = $_POST['phone']      ?? ($user['client_PhoneNumber'] ?? '');
$readyTime = $_POST['ready_time'] ?? '';
$comment   = $_POST['comment']    ?? '';
$payment   = $_POST['payment']    ?? '';

$successMessage = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 4) Базова валідація
    if (!$firstName || !$lastName || !$phone || !$readyTime || !$payment) {
        $successMessage = "❌ Будь ласка, заповніть усі обов’язкові поля.";
    } else {
        // 5) Перевірка часу готовності
        $day = (int)date('w');
        list($h, $m) = explode(':', $readyTime);
        $minutes = $h * 60 + $m;
        if ($day >= 1 && $day <= 5) {
            $min = 8 * 60;   $max = 20 * 60;
        } elseif ($day === 6) {
            $min = 10 * 60;  $max = 20 * 60;
        } else {
            $min = 12 * 60;  $max = 20 * 60;
        }
        if ($minutes < $min || $minutes > $max) {
            $successMessage = "❌ Ми працюємо:\n"
                . "Пн–Пт 08:00–20:00,\n"
                . "Сб 10:00–20:00,\n"
                . "Нд 12:00–20:00.\n"
                . "Оберіть інший час.";
        } else {
            // 6) Вставка в orders: завжди передаємо user_id (0 для гостей)
            $userIdParam = $user['client_id'] ?? 0;
            $sql = "
              INSERT INTO orders
                (user_id, total, delivery_address, phone, status,
                 customer_name, customer_surname, comment, ready_time, payment_method)
              VALUES (?, ?, '', ?, 'pending', ?, ?, ?, ?, ?)
            ";
            $stmt = $conn->prepare($sql);
            $stmt->bind_param(
                'idssssss',
                $userIdParam,
                $total,
                $phone,
                $firstName,
                $lastName,
                $comment,
                $readyTime,
                $payment
            );

            if ($stmt->execute()) {
                $orderId = $stmt->insert_id;
                $stmt->close();

                // 7) Додаємо позиції в order_items
                foreach ($cart as $ci) {
                    $stmt2 = $conn->prepare("
                      INSERT INTO order_items (order_id, product_id, quantity, price)
                      VALUES (?, ?, ?, ?)
                    ");
                    $stmt2->bind_param(
                        'iiid',
                        $orderId,
                        $ci['id'],
                        $ci['quantity'],
                        $ci['price']
                    );
                    $stmt2->execute();
                    $stmt2->close();
                }

                unset($_SESSION['cart']);
                $successMessage = "✅ Ваше замовлення успішно оформлено!";
            } else {
                $successMessage = "❌ Помилка при оформленні: " . $stmt->error;
                $stmt->close();
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <title>Оформлення замовлення — Coffee Time</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/checkout.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
<?php 
  $page = 'checkout';
  include '../includes/header.php'; 
?>
<main>
  <section class="checkout">
    <h1>Оформлення замовлення</h1>

    <?php if ($successMessage): ?>
      <p class="checkout-message"><?= nl2br(htmlspecialchars($successMessage)) ?></p>
    <?php endif; ?>

    <form method="post" class="checkout-form">
      <label for="first_name">Ім’я *</label>
      <input type="text" id="first_name" name="first_name"
             value="<?= htmlspecialchars($firstName, ENT_QUOTES) ?>" required>

      <label for="last_name">Прізвище *</label>
      <input type="text" id="last_name" name="last_name"
             value="<?= htmlspecialchars($lastName, ENT_QUOTES) ?>" required>

      <label for="phone">Телефон *</label>
      <input type="tel" id="phone" name="phone"
             value="<?= htmlspecialchars($phone, ENT_QUOTES) ?>" required>

      <label for="ready_time">Година готовності *</label>
      <input
        type="time"
        id="ready_time"
        name="ready_time"
        value="<?= htmlspecialchars($readyTime) ?>"
        step="1800"
        required
      >
      <small class="hint">або введіть вручну у форматі HH:MM</small>

      <label for="comment">Коментар</label>
      <textarea id="comment" name="comment" rows="3"
        placeholder="Додаткові побажання…"><?= htmlspecialchars($comment) ?></textarea>

      <label for="payment">Спосіб оплати *</label>
      <select id="payment" name="payment" required>
        <option value="">Оберіть спосіб</option>
        <option value="apple_pay"      <?= $payment==='apple_pay'      ? 'selected':'' ?>>Apple Pay</option>
        <option value="google_pay"     <?= $payment==='google_pay'     ? 'selected':'' ?>>Google Pay</option>
        <option value="card_online"    <?= $payment==='card_online'    ? 'selected':'' ?>>Visa/Mastercard</option>
        <option value="cash_on_pickup" <?= $payment==='cash_on_pickup' ? 'selected':'' ?>>Оплата при отриманні</option>
      </select>

      <div class="cart-summary">
        <h3>Ваше замовлення:</h3>
        <ul class="order-list">
          <?php foreach($orderDetails as $it): ?>
            <li>
              <img src="../<?= htmlspecialchars($it['image'],ENT_QUOTES) ?>"
                   alt="<?= htmlspecialchars($it['name'],ENT_QUOTES) ?>">
              <div>
                <span><?= htmlspecialchars($it['name'],ENT_QUOTES) ?> × <?= $it['quantity'] ?> шт.</span>
                <span>
                  <?= number_format($it['price'],2,',',' ') ?> ₴ × <?= $it['quantity'] ?> =
                  <strong><?= number_format($it['subtotal'],2,',',' ') ?> ₴</strong>
                </span>
              </div>
            </li>
          <?php endforeach; ?>
        </ul>
        <p class="order-total">
          <strong>Загальна сума: <?= number_format($total,2,',',' ') ?> ₴</strong>
        </p>
      </div>

      <button type="submit" class="btn-submit">Оформити замовлення</button>
    </form>
  </section>
</main>
<?php include '../includes/footer.php'; ?>
</body>
</html>
