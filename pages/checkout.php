<?php
session_start();

if (empty($_SESSION['cart'])) {
    header('Location: cart.php');
    exit;
}


$_SESSION['cart'] = []; 
?>

<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <title>Замовлення оформлено — Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
</head>
<body>
<?php include '../includes/header.php'; ?>

<main class="checkout-confirmation">
    <h1>Дякуємо за замовлення!</h1>
    <p>Ваше замовлення прийнято. Ми зв’яжемося з вами найближчим часом.</p>
    <a href="../menu.php" class="back-to-menu">Повернутися до меню</a>
</main>

<?php include '../includes/footer.php'; ?>
</body>
</html>
