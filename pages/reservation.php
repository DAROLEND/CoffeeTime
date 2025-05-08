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
    <title>Бронювання — Coffee Time</title>
    <link rel="stylesheet" href="../static/css/style.css">
    <link rel="stylesheet" href="../static/css/reservation.css">

</head>
<body>
    <main class="reservation-container">
        <h2>Бронювання столика</h2>
        <div class="reservation-categories">
            <div class="reservation-option">
                <a href="reserve_indoor.php" ><img src="../static/images/main/indoor.jpg" alt="У приміщенні"></a>
                <h3>У приміщенні</h3>
                <a href="reserve_indoor.php" class="reserve-button">Обрати</a>
            </div>

            <div class="reservation-option">
                <a href="reserve_terasa.php" ><img src="../static/images/main/terasa.jpg" alt="На терасі"></a>
            <h3>На терасі</h3>
                <a href="reserve_terasa.php" class="reserve-button">Обрати</a>
            </div>
        </div>
    </main>

    <?php include '../includes/footer.php'; ?>
</body>
</html>
