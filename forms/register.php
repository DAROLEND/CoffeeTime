<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);
session_start();
require_once '../db/db.php';

$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $login = trim($_POST['login'] ?? '');
    $password = trim($_POST['password'] ?? '');
    $confirm = trim($_POST['confirm'] ?? '');

    if (empty($email) || empty($login) || empty($password) || empty($confirm)) {
        $error = 'Ви заповнили не всі поля!';
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $error = 'Некоректна електронна пошта!';
    } elseif ($password !== $confirm) {
        $error = 'Паролі не співпадають!';
    } else {
        $login = htmlspecialchars($login);
        $email = htmlspecialchars($email);
        $hashedPassword = password_hash($password, PASSWORD_DEFAULT);

        $stmt = $conn->prepare("SELECT id FROM users WHERE login = ?");
        $stmt->bind_param("s", $login);
        $stmt->execute();
        $stmt->store_result();

        if ($stmt->num_rows > 0) {
            $error = 'Такий логін вже існує. Оберіть інший.';
        } else {
            $stmt->close();

            $stmt = $conn->prepare("INSERT INTO users (email, login, password) VALUES (?, ?, ?)");
            $stmt->bind_param("sss", $email, $login, $hashedPassword);

            if ($stmt->execute()) {
                $success = 'Реєстрація успішна! <a href="login.php" class="auth-button1">Увійти</a>';
            } else {
                $error = 'Помилка під час реєстрації: ' . $stmt->error;
            }
        }
        $stmt->close();
        $conn->close();
    }
}

$page = 'register';
include '../includes/header.php';
?>
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Реєстрація — Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
</head>
<main class="auth-container">
    <h2>Реєстрація</h2>
    <?php if ($error): ?>
        <p class="auth-error"><?= htmlspecialchars($error) ?></p>
    <?php elseif ($success): ?>
        <p class="auth-success"><?= $success ?></p>
    <?php endif; ?>
    <form method="post" class="auth-form">
        <input type="email" name="email" placeholder="Електронна пошта" required>
        <input type="text" name="login" placeholder="Логін" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <input type="password" name="confirm" placeholder="Підтвердіть пароль" required>
        <button type="submit">Зареєструватися</button>
        <p>Вже маєте акаунт? <a href="login.php" class="auth-button1">Увійти</a></p>
    </form>
</main>

<?php include '../includes/footer.php'; ?>
