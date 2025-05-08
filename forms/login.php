<?php
session_start();
require_once '../db/db.php';

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $emailOrLogin = trim($_POST['email'] ?? '');
    $password = trim($_POST['password'] ?? '');

    if (empty($emailOrLogin) || empty($password)) {
        $error = 'Будь ласка, заповніть усі поля!';
    } else {
        $stmt = $conn->prepare("SELECT id, login, password FROM users WHERE email = ? OR login = ?");
        $stmt->bind_param("ss", $emailOrLogin, $emailOrLogin);
        $stmt->execute();
        $stmt->store_result();

        if ($stmt->num_rows === 1) {
            $stmt->bind_result($id, $login, $hashedPassword);
            $stmt->fetch();

            if (password_verify($password, $hashedPassword)) {
                $_SESSION['user'] = $login;
                header('Location: ../index.php');
                exit;
            } else {
                $error = 'Неправильний пароль.';
            }
        } else {
            $error = 'Користувача не знайдено.';
        }

        $stmt->close();
        $conn->close();
    }
}

$page = 'login';
include '../includes/header.php';
?>
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Авторизація — Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
</head>
<main class="auth-container">
    <h2>Авторизація</h2>
    <?php if ($error): ?>
        <p class="auth-error"><?= htmlspecialchars($error) ?></p>
    <?php endif; ?>
    <form method="post" class="auth-form">
        <input type="text" name="email" placeholder="Електронна пошта або логін" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button type="submit">Увійти</button>
        <p>Ще не маєте акаунту? <a href="register.php" class="auth-button1">Зареєструватися</a></p>
    </form>
</main>

<?php include '../includes/footer.php'; ?>
