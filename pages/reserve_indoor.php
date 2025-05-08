<?php
session_start();
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

$page = 'reservation';
include '../includes/header.php';
include '../db/db.php';

$result = mysqli_query($conn, "SELECT table_number FROM reservations WHERE location = 'indoor'");
$bookedTables = [];
while ($row = mysqli_fetch_assoc($result)) {
    $bookedTables[] = $row['table_number'];
}
?>

<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <title>Бронювання столика</title>
    <link rel="stylesheet" href="../static/css/reserve_indoor.css">
    <link rel="stylesheet" href="../static/css/style.css">
</head>
<body>
<main class="data-container">
    <h2>Виберіть столик</h2>
    <div class="table-map">
        <?php
        for ($i = 1; $i <= 20; $i++) {
            $class = in_array($i, $bookedTables) ? 'booked' : '';
            echo "<div class='table $class' data-table='$i'>$i</div>";
        }
        ?>
    </div>
    <form id="reserveForm" action="save_reservation.php" method="POST">
        <input type="hidden" name="selected_tables" id="selected_tables">
        <button type="submit">Забронювати</button>
    </form>
</main>
<script src="../static/js/reserve_indoor.js"></script>
</body>
</html>
