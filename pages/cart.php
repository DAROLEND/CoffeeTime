<?php
session_start();

if (!isset($_POST['quantity'==0])) {
    $_POST['quantity'] = 1;
}
if (!isset($_SESSION['cart'])) {
    $_SESSION['cart'] = [];
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_quantity'])) {
    $index = (int)$_POST['index'];
    $quantity = 1;

    if (!empty($_POST['custom_quantity'])) {
        $quantity = max(1, (int)$_POST['custom_quantity']);
    } elseif (!empty($_POST['select_quantity'])) {
        $quantity = max(1, (int)$_POST['select_quantity']);
    }

    if (isset($_SESSION['cart'][$index])) {
        $_SESSION['cart'][$index]['quantity'] = $quantity;
    }
}

if (isset($_GET['action']) && $_GET['action'] == 'add') {
    $category = $_GET['category'];
    $name = $_GET['name'];
    $price = $_GET['price'];
    $image = $_GET['image'];
    $description = $_GET['description'];

    $_SESSION['lastCategory'] = $category;

    $exists = false;
    foreach ($_SESSION['cart'] as &$item) {
        if ($item['name'] == $name) {
            
            $exists = true;
            break;
        }
    }
    unset($item);

    if (!$exists) {
        $_SESSION['cart'][] = [
            'category' => $category,
            'name' => $name,
            'price' => $price,
            'image' => $image,
            'description' => $description,
            'quantity' => 1
        ];
    }
}

if (isset($_GET['remove'])) {
    $removeIndex = $_GET['remove'];
    unset($_SESSION['cart'][$removeIndex]);
    $_SESSION['cart'] = array_values($_SESSION['cart']);
}

$totalPrice = 0;
foreach ($_SESSION['cart'] as $item) {
    $totalPrice += $item['price'] * $item['quantity'];
}

?>

<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <title>Корзина — Coffee Time</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="../static/css/style.css">
    <link rel="stylesheet" href="../static/css/cart.css">
</head>
<body>
<?php include '../includes/header.php'; ?>

<main>
    <section class="cart">
        <h1>Ваша корзина</h1>

        <?php if (empty($_SESSION['cart'])): ?>
            <p>Ваша корзина порожня.</p>
        <?php else: ?>
            <div class="cart-items">
                <?php foreach ($_SESSION['cart'] as $index => $item): ?>
                    <div class="cart-item">
                        <img src="<?= htmlspecialchars($item['image']) ?>" alt="<?= htmlspecialchars($item['name']) ?>">
                        <div class="cart-item-info">
                            <h3><?= htmlspecialchars($item['name']) ?></h3>
                            <p><?= htmlspecialchars($item['description']) ?></p>
                            <div class="cart-item-price">
                                <span class="price"><?= $item['price'] ?> грн × <?= $item['quantity'] ?> = <strong><?= $item['price'] * $item['quantity'] ?> грн</strong></span>
                                <a href="?remove=<?= $index ?>" class="remove-item">Видалити</a>
                            </div>

                            <form method="post" class="quantity-form">
                                <input type="hidden" name="index" value="<?= $index ?>">
                                <input type="hidden" name="update_quantity" value="1">

                                <label for="quantity-<?= $index ?>">Кількість:</label>
                                <div class="custom-select-wrapper">
                                    <select name="select_quantity" class="custom-select" onchange="handleQuantityChange(this, <?= $index ?>)">
                                        <?php for ($i = 1; $i <= 5; $i++): ?>
                                            <option value="<?= $i ?>" <?= $item['quantity'] == $i ? 'selected' : '' ?>><?= $i ?></option>
                                        <?php endfor; ?>
                                        <option value="custom" <?= $item['quantity'] > 5 ? 'selected' : '' ?>>Інше...</option>
                                    </select>

                                    <input
                                        type="number"
                                        name="custom_quantity"
                                        class="custom-input"
                                        min="1"
                                        max="99"
                                        placeholder="Введіть кількість"
                                        value="<?= $item['quantity'] > 5 ? $item['quantity'] : '' ?>"
                                        onchange="this.form.submit()"
                                        style="<?= $item['quantity'] > 5 ? 'display:block;' : 'display:none;' ?>"
                                    >
                                </div>
                            </form>

                        </div>
                    </div>
                <?php endforeach; ?>
            </div>

            <div class="cart-summary">
                <h2>Підсумок</h2>
                <p>Загальна сума: <span class="total-price"><?= $totalPrice ?> грн</span></p>
                
                <form action="../checkout.php" method="post">
                    <button type="submit" class="checkout-btn">Оформити замовлення</button>
                    <?php $lastCategory = $_SESSION['lastCategory'] ?? ''; ?>
                    <a href="menu.php?category=<?= urlencode($lastCategory) ?>" class="add-to-cart">Повернутися до товарів</a>
                </form>
            </div>
        <?php endif; ?>
    </section>
</main>
<script src="../static/js/quantity_cart.js"></script>
<?php include '../includes/footer.php'; ?>
</body>
</html>