<?php
// pages/forms/forgot.php
session_start();

// тут можна підключити вашу БД, якщо плануєте перевіряти наявність email
// require_once __DIR__ . '/../../db/db.php';

$error   = '';
$success = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');

    if ($email === '') {
        $error = 'Будь ласка, введіть вашу електронну пошту.';
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $error = 'Неправильний формат електронної пошти.';
    } else {
        // TODO: Тут логіка генерації токена та відправки листа
        // mail($email, ...);
        $success = true;
    }
}
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Відновлення пароля — Coffee Time</title>

  <!-- Основні стилі -->
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/forgot.css">
  <link rel="stylesheet" href="../static/css/footer.css">
  <!-- Додайте інші CSS, якщо потрібно -->
</head>
<body>

  <!-- Шапка сайту з навігацією -->
  <?php include '../includes/header.php'; ?>

  <main class="auth-container">
    <div class="auth-card">
      <h2>Відновлення пароля</h2>

      <?php if ($success): ?>
        <p class="auth-success">
          Якщо цей email зареєстрований, ми надішлемо вам листа з інструкціями.
        </p>
        <p class="register-cta">
          Повернутися до
          <a href="login.php" class="auth-link">Авторизації</a>
        </p>

      <?php else: ?>

        <?php if ($error): ?>
          <p class="auth-error"><?= htmlspecialchars($error) ?></p>
        <?php endif; ?>

        <form method="post" class="auth-form" novalidate>
          <div class="input-group">
            <label for="email">Ваша електронна пошта</label>
            <input
              id="email"
              name="email"
              type="email"
              value="<?= htmlspecialchars($_POST['email'] ?? '') ?>"
              required
            >
          </div>

          <button type="submit" class="auth-btn">Надіслати запит</button>

          <p class="register-cta">
            Повернутися до
            <a href="login.php" class="auth-link">Авторизації</a>
          </p>
        </form>

      <?php endif; ?>
    </div>
  </main>

  <!-- Футер сайту -->
  <?php include '../includes/footer.php'; ?>

</body>
</html>
