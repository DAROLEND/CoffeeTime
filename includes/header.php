<header>
    <div class="logo">
        <a href="../pages/index.php"><img src="../static/images/main/logo.png" alt="Logo Coffee Time"></a>  
    </div>

    <div class="nav-auth">
        <nav>
            <ul>
                <li><a href="../pages/index.php" class="<?php echo ($page == 'home') ? 'active' : ''; ?>">Головна</a></li>
                <li><a href="../pages/menu.php" class="<?php echo ($page == 'menu') ? 'active' : ''; ?>">Меню</a></li>
                <li><a href="../pages/reservation.php" class="<?php echo ($page == 'reservation') ? 'active' : ''; ?>">Бронювати</a></li>
                <li><a href="../pages/about.php" class="<?php echo ($page == 'about') ? 'active' : ''; ?>">Про нас</a></li>
                <li><a href="../pages/contact.php" class="<?php echo ($page == 'contact') ? 'active' : ''; ?>">Контакти</a></li>
            </ul>
        </nav>

        <div class="auth-buttons">
            <div class="cart-wrapper">
                <a href="../pages/cart.php">
                    <img src="../static/images/main/cart.png" alt="Cart">
                    <?php
                    $cartCount = isset($_SESSION['cart']) ? count($_SESSION['cart']) : 0;
                    if ($cartCount > 0): ?>
                        <span class="cart-count"><?php echo $cartCount; ?></span>
                    <?php endif; ?>
                </a>
            </div>
            <a href="../forms/login.php" class="auth-link-button">Log in</a>
            <a href="../forms/register.php" class="auth-link-button">Sign up</a>
        </div>


    </div>
</header>