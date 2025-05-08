<?php
session_start();
$page = 'reservation';
include '../includes/header.php';
?>

<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Бронювання на терасі — Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
</head>
<body>
<main class="data-container">
    <h2>Бронювання на терасі</h2>
    <form class="auth-form" action="reserve_handler.php" method="post">
        <input type="hidden" name="location" value="terrace">
        <input type="text" name="name" placeholder="Ваше ім'я" required>
        <input type="tel" name="phone" placeholder="Номер телефону" required>
        <input type="datetime-local" name="date" required>
        <input type="number" name="people" placeholder="Кількість людей" required min="1" max="20">
        <button type="submit">Забронювати</button>
    </form>
</main>

<?php include '../includes/footer.php'; ?>
</body>
</html>
