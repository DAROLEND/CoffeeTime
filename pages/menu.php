<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

session_start();

// Демо дані для меню
$menuItems = [
    'coffee' => [
        ['name' => 'Еспресо', 'price' => 50, 'description' => 'Сильний та ароматний еспресо', 'image' => '../static/images/categories/coffee_category.jpg'],
        ['name' => 'Капучино', 'price' => 60, 'description' => 'Кремовий капучино з молоком', 'image' => '../static/images/categories/coffee_category.jpg'],
        ['name' => 'Латте', 'price' => 65, 'description' => 'Латте з ніжним молоком', 'image' => '../static/images/categories/coffee_category.jpg'],
    ],
    'fast_food' => [
        ['name' => 'Бургер', 'price' => 120, 'description' => 'Соковитий бургер з м’ясом', 'image' => '../static/images/categories/fast_food.jpg'],
        ['name' => 'Фрі', 'price' => 40, 'description' => 'Хрустка картопля фрі', 'image' => '../static/images/categories/fast_food.jpg'],
        ['name' => 'Хот-Дог', 'price' => 70, 'description' => 'Класичний французький хот-дог', 'image' => '../static/images/categories/fast_food.jpg'],
    ],
    'pizza' => [
        ['name' => 'Маргарита', 'price' => 180, 'description' => 'Класична піца з моцарелою', 'image' => '../static/images/menu_items/pizza.jpg'],
        ['name' => 'Пепероні', 'price' => 210, 'description' => 'Піца з пепероні та сиром', 'image' => '../static/images/menu_items/pizza.jpg'],
        ['name' => 'Гавайська', 'price' => 220, 'description' => 'Піца з ананасами та куркою', 'image' => '../static/images/menu_items/pizza.jpg'],
    ],
    'cold_drinks' => [
        ['name' => 'Лимонад', 'price' => 50, 'description' => 'Смачний лимонад на основі цитрусових', 'image' => '../static/images/menu_items/mohito.jpg'],
        ['name' => 'Мохіто', 'price' => 60, 'description' => 'Охолоджений мохіто з м’ятою', 'image' => '../static/images/menu_items/mohito.jpg'],
        ['name' => 'Смузі', 'price' => 65, 'description' => 'Фрукти в пікантному смузі', 'image' => '../static/images/menu_items/mohito.jpg'],
    ],
    'desserts' => [
        ['name' => 'Торт', 'price' => 90, 'description' => 'Ніжний торт з шоколадною глазур’ю', 'image' => '../static/images/categories/dessert.jpg'],
        ['name' => 'Пиріжок', 'price' => 50, 'description' => 'Пиріжок з фруктовою начинкою', 'image' => '../static/images/categories/dessert.jpg'],
        ['name' => 'Мафін', 'price' => 45, 'description' => 'Мафін з ягодами та шоколадом', 'image' => '../static/images/categories/dessert.jpg'],
    ],
];

// Категорія за замовчуванням — coffee
$currentCategory = isset($_GET['category']) ? $_GET['category'] : 'coffee';

?>

<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Меню - Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
    <link rel="stylesheet" href="../static/css/menu.css">
    <link rel="stylesheet" href="../static/css/menu_cat.css">
</head>
<body>

<?php 
$page = 'menu';
include '../includes/header.php'; 
?>

<main>
    <section class="menu">
        <h1>Меню</h1>

        <div class="categories-nav">
            <a href="menu.php?category=coffee" class="category-link <?= $currentCategory == 'coffee' ? 'active-category' : '' ?>">Кава</a>
            <a href="menu.php?category=fast_food" class="category-link <?= $currentCategory == 'fast_food' ? 'active-category' : '' ?>">Фаст-фуд</a>
            <a href="menu.php?category=pizza" class="category-link <?= $currentCategory == 'pizza' ? 'active-category' : '' ?>">Піца</a>
            <a href="menu.php?category=cold_drinks" class="category-link <?= $currentCategory == 'cold_drinks' ? 'active-category' : '' ?>">Холодні напої</a>
            <a href="menu.php?category=desserts" class="category-link <?= $currentCategory == 'desserts' ? 'active-category' : '' ?>">Десерти</a>
        </div>

        <?php if (isset($menuItems[$currentCategory])): ?>
            <div class="category" id="<?= $currentCategory ?>">
                <h2><?php echo ucfirst($currentCategory); ?></h2>
                <div class="menu-items">
                    <?php foreach ($menuItems[$currentCategory] as $item): ?>
                        <div class="menu-item">
                            <img src="<?php echo $item['image']; ?>" alt="<?php echo $item['name']; ?>">
                            <h3><?php echo $item['name']; ?></h3>
                            <p><?php echo $item['description']; ?></p>
                            <span class="price"><?php echo $item['price']; ?> грн</span>
                            <a href="cart.php?action=add&category=<?php echo $currentCategory; ?>&name=<?php echo urlencode($item['name']); ?>&price=<?php echo $item['price']; ?>&image=<?php echo urlencode($item['image']); ?>&description=<?php echo urlencode($item['description']); ?>" class="add-to-cart">Додати в корзину</a>
                        </div>
                    <?php endforeach; ?>
                </div>
            </div>
        <?php else: ?>
            <p>Виберіть категорію для перегляду товарів.</p>
        <?php endif; ?>
    </section>
</main>

<?php include '../includes/footer.php'; ?>

</body>
</html>
