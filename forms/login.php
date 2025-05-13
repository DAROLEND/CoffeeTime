<?php
session_start();
require_once '../db/db.php';

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $emailOrLogin = trim($_POST['email'] ?? '');
    $password     = trim($_POST['password'] ?? '');
    $remember     = isset($_POST['remember']);

    if ($emailOrLogin === '' || $password === '') {
        $error = 'Будь ласка, заповніть усі поля!';
    } else {
        $stmt = $conn->prepare("
            SELECT client_id, login, email, client_name, client_surname, client_PhoneNumber, password
            FROM users
            WHERE email = ? OR login = ?
        ");
        $stmt->bind_param("ss", $emailOrLogin, $emailOrLogin);
        $stmt->execute();
        $stmt->store_result();

        if ($stmt->num_rows === 1) {
            $stmt->bind_result(
                $client_id, $login, $email, $client_name, $client_surname, $client_PhoneNumber, $hashedPassword
            );
            $stmt->fetch();

            if (password_verify($password, $hashedPassword)) {
                // Зберігаємо дані в сесію
                $_SESSION['user'] = compact(
                    'client_id','login','email','client_name','client_surname','client_PhoneNumber'
                );
                // Запам’ятати мене
                if ($remember) {
                    setcookie('remember_me', $emailOrLogin, time() + 7*24*3600, "/");
                }
                header('Location: ../pages/index.php');
                exit;
            } else {
                $error = '❌ Невірний пароль.';
            }
        } else {
            $error = '❌ Користувача не знайдено.';
        }

        $stmt->close();
        $conn->close();
    }
}
?>
<!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Авторизація — Coffee Time</title>
  <!-- Основні стилі -->
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/auth.css">
  <link rel="stylesheet" href="../static/css/footer.css">
  <!-- за потреби можна добавить інші CSS тут -->
</head>
<body>
  <!-- Ваша шапка сайту -->
  <?php include '../includes/header.php'; ?>

  <main class="auth-container">
    <div class="auth-card">
      <h2>Авторизація</h2>

      <?php if ($error): ?>
        <p class="auth-error"><?= htmlspecialchars($error) ?></p>
      <?php endif; ?>

      <form method="post" class="auth-form" novalidate>
        <div class="input-group">
          <label for="email">Електронна пошта або логін</label>
          <input
            id="email"
            name="email"
            type="text"
            value="<?= htmlspecialchars($_COOKIE['remember_me'] ?? '') ?>"
            required
          >
        </div>

        <div class="input-group password-group">
          <label for="password">Пароль</label>
          <div class="password-wrapper">
            <input
              id="password"
              name="password"
              type="password"
              required
            >
            <button
              type="button"
              class="toggle-password"
              aria-label="Показати пароль"
            >👁️</button>
          </div>
        </div>

        <div class="controls">
          <label class="remember-me">
            <input
              type="checkbox"
              name="remember"
              <?= isset($_COOKIE['remember_me']) ? 'checked' : '' ?>
            >
            Запам’ятати мене
          </label>
          <a href="forgot.php" class="forgot-link">Забули пароль?</a>
        </div>

        <button type="submit" class="auth-btn">Увійти</button>

        <p class="register-cta">
          Ще не маєте акаунту?
          <a href="register.php" class="auth-link">Зареєструватися</a>
        </p>
      </form>
    </div>
  </main>

  <!-- Ваш футер сайту -->
  <?php include '../includes/footer.php'; ?>

  <!-- Скріпт для показу/приховування пароля -->
  <script>
    document.querySelectorAll('.toggle-password').forEach(btn => {
      btn.addEventListener('click', () => {
        const inp = btn.closest('.password-wrapper').querySelector('input');
        if (inp.type === 'password') {
          inp.type = 'text';
          btn.textContent = '🙈';
        } else {
          inp.type = 'password';
          btn.textContent = '👁️';
        }
      });
    });
  </script>
</body>
</html>
