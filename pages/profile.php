<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();

require_once '../db/db.php';

if (empty($_SESSION['user']) || !is_array($_SESSION['user'])) {
    header("Location: ../forms/login.php");
    exit();
}

$user = $_SESSION['user'];
$successMessage = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $firstName = trim($_POST['first_name'] ?? '');
    $lastName  = trim($_POST['last_name']  ?? '');
    $phone     = trim($_POST['phone']      ?? '');

    $stmt = $conn->prepare("
        UPDATE users
           SET client_name = ?, client_surname = ?, client_PhoneNumber = ?
         WHERE client_id = ?
    ");
    $stmt->bind_param("sssi", $firstName, $lastName, $phone, $user['client_id']);
    if ($stmt->execute()) {
        $_SESSION['user']['client_name']        = $firstName;
        $_SESSION['user']['client_surname']     = $lastName;
        $_SESSION['user']['client_PhoneNumber'] = $phone;
        $user = $_SESSION['user'];
        $successMessage = "✅ Дані успішно оновлено!";
    } else {
        $successMessage = "❌ Помилка: " . $stmt->error;
    }
    $stmt->close();
}

$stmt = $conn->prepare("
    SELECT COUNT(*) 
      FROM order_items oi
      JOIN orders o
        ON oi.order_id = o.order_id
     WHERE o.user_id = ?
");
$stmt->bind_param("i", $user['client_id']);
$stmt->execute();
$stmt->bind_result($ordersCount);
$stmt->fetch();
$stmt->close();

if (empty($user['created_at'])) {
    $stmt = $conn->prepare("
        SELECT created_at 
          FROM users 
         WHERE client_id = ?
    ");
    $stmt->bind_param("i", $user['client_id']);
    $stmt->execute();
    $stmt->bind_result($createdAtDb);
    if ($stmt->fetch()) {
        $user['created_at'] = $createdAtDb;
        $_SESSION['user']['created_at'] = $createdAtDb;
    }
    $stmt->close();
}

$registeredAt = !empty($user['created_at'])
    ? date('d.m.Y', strtotime($user['created_at']))
    : '—';

?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <title>Профіль — Coffee Time</title>
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/profile.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>

  <?php 
    $page = 'profile';
    include '../includes/header.php'; 
  ?>

  <main class="profile">
    <h1>Ваш профіль</h1>

    <?php if ($successMessage): ?>
      <div class="notification success"><?= htmlspecialchars($successMessage) ?></div>
    <?php endif; ?>

    <div class="profile-meta">
      <p><strong>Email:</strong> <?= htmlspecialchars($user['email']) ?></p>
      <p><strong>Зареєстровані з:</strong> <?= htmlspecialchars($registeredAt) ?></p>
      <p><strong>Всього замовлень:</strong> <?= $ordersCount ?></p>
      <a href="change_password.php" class="change-password">Змінити пароль</a>
    </div>

    <form method="post" class="profile-form">
      <label for="first_name">Ім’я:</label>
      <input type="text" id="first_name" name="first_name"
             value="<?= htmlspecialchars($user['client_name'] ?? '') ?>" required>

      <label for="last_name">Прізвище:</label>
      <input type="text" id="last_name" name="last_name"
             value="<?= htmlspecialchars($user['client_surname'] ?? '') ?>" required>

      <label for="phone">Телефон:</label>
      <input type="tel" id="phone" name="phone"
             value="<?= htmlspecialchars($user['client_PhoneNumber'] ?? '') ?>" required>

      <div class="form-actions">
        <button type="submit" class="save-btn">Зберегти зміни</button>
        <a href="../pages/logout.php" class="logout-btn">Вийти</a>
      </div>
    </form>
  </main>

  <?php include '../includes/footer.php'; ?>
</body>
</html>
