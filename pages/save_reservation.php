<?php
session_start();
include '../db/db.php';
if (!$conn) {
    die("Помилка підключення до бази даних: " . mysqli_connect_error());
}
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $tables = explode(',', $_POST['selected_tables']);

    foreach ($tables as $table) {
        $table = intval($table);
        $check = mysqli_query($conn, "SELECT * FROM reservations WHERE table_number = $table AND location = 'indoor'");
        if (mysqli_num_rows($check) === 0) {
            mysqli_query($conn, "INSERT INTO reservations (table_number, location) VALUES ($table, 'indoor')");
        }
    }

    header("Location: reserve_success.php");
    exit();
}
?>