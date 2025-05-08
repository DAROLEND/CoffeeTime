<?php
session_start();
?>
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
    <link rel="stylesheet" href="../static/css/slider.css">
    <link rel="stylesheet" href="../static/css/slider_food.css">

</head>
<body>
<?php 
$page = 'home';
include '../includes/header.php'; 
?>
    <main>
        <section class="hero">
            <div class="slider">
                <div class="arrow left">&#10094;</div>
                <div class="arrow right">&#10095;</div>

                <div class="slide active" style="background-image: url('../static/images/categories/coffee_category.jpg');">
                    <div class="hero-text">
                        <h1>Кожен ковток — <br>тепла історія, що<br> дарує натхнення</h1>
                    </div>
                </div>
                <div class="slide" style="background-image: url('../static/images/categories/dessert.jpg');">
                    <div class="hero-text">
                        <h1>Неможливо встояти… <br>А чи потрібно?</h1>
                    </div>
                </div>
                <div class="slide" style="background-image: url('../static/images/categories/fast_food.jpg');">
                    <div class="hero-text">
                        <h1>Ідеальне комбо<br>для швидкого перекусу</h1>
                    </div>
                </div>
            </div>

            <div class="slider-controls-wrapper">
                <div class="slider-controls">
                    <span class="dot active"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>

        </section>
        <section class="popular-food">
            <h2>Їжа, яку найчастіше обирають</h2>
            <div class="food-grid expand-grid">
                <div class="food-item side left"><a href="#"><img src="../static/images/categories/fast_food.jpg" alt="Fast Food" height="350"></a></div>
                <!--<div class="food-item center"><a href="#"><img src="../static/images/categories/fast_food.jpg" alt="Fast Food" height="350"></a></div>-->
                <div class="food-item center"><a href="#"><img src="../static/images/categories/fast_food.jpg" alt="Fast Food" height="350"></a></div>
                <!--<div class="food-item center"><a href="#"><img src="../static/images/categories/fast_food.jpg" alt="Fast Food" height="350"></a></div>-->
                <div class="food-item side right"><a href="#"><img src="../static/images/categories/fast_food.jpg" alt="Fast Food" height="350"></a></div>
            </div>
        </section>
        <section class="popular-drinks">
            <h2>Найпопулярніші напої</h2>
            <div class="drink-grid expand-grid">
                <div class="drink-item side left"><a href="#"><img src="../static/images/categories/coffee_category.jpg" alt="Coffee" width="350"></a></div>
                <!--<div class="drink-item center"><a href="#"><img src="../static/images/categories/coffee_category.jpg" alt="Coffee" width="350"></a></div>-->
                <div class="drink-item center"><a href="#"><img src="../static/images/categories/coffee_category.jpg" alt="Coffee" width="350"></a></div>
                <!--<div class="drink-item center"><a href="#"><img src="../static/images/categories/coffee_category.jpg" alt="Coffee" width="350"></a></div>-->
                <div class="drink-item side right"><a href="#"><img src="../static/images/categories/coffee_category.jpg" alt="Coffee" width="350"></a></div>
            </div>
        </section>

        <section class="desserts">
            <h2>Очікувані десерти</h2>
            <div class="dessert-grid expand-grid">
                <div class="dessert-item side left"><a href="#"><img src="../static/images/categories/dessert.jpg" alt="Dessert" width="404"></a></div>
                <div class="dessert-item center"><a href="#"><img src="../static/images/categories/dessert.jpg" alt="Dessert" width="404"></a></div>
                <div class="dessert-item side right"><a href="#"><img src="../static/images/categories/dessert.jpg" alt="Dessert" width="404"></a></div>
            </div>
        </section>
    </main>
    <?php include '../includes/footer.php'; ?>
    <script src="../static/js/slider.js"></script>
</body>
</html>