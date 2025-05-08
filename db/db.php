<?php
$servername = "localhost";
$username = "root";
$password =
"";
$dbname = "CoffeeTime";
$conn = mysqli_connect($servername, $username, $password, $dbname);
if (mysqli_connect_errno()) {
    echo "При підключенні до бази даних виникла помилка: (" .
mysqli_connect_errno() . "): " . mysqli_connect_error();
    exit();
}
?>