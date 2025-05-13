<?php
session_start();
require_once '../db/db.php';

// Якщо не залогінені – на логін
if (!isset($_SESSION['user'])) {
  header('Location: ../forms/login.php');
  exit;
}

$user     = $_SESSION['user'];
$allowed  = ['indoor','terrace'];
$location = $_REQUEST['location'] ?? null;
$success  = '';
$error    = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $loc     = in_array($_POST['location'], $allowed) ? $_POST['location'] : 'indoor';
  $tables  = array_filter(explode(',', $_POST['tables'] ?? ''), 'strlen');
  $dt      = $_POST['datetime'] ?? '';

  if (empty($tables) || !$dt) {
    $error = 'Виберіть хоча б один стіл і заповніть дату/час.';
  } else {
    $stmt = $conn->prepare("
      INSERT INTO reservations
        (user_id, table_number, location, reservation_datetime)
      VALUES (?,?,?,?)
    ");
    foreach ($tables as $t) {
      $tn = (int)$t;
      $stmt->bind_param('iiss', $user['client_id'], $tn, $loc, $dt);
      $stmt->execute();
    }
    $stmt->close();
    $success = '✅ Ваші столи №'.implode(',',$tables)." заброньовані на {$dt}.";
  }
}

?><!DOCTYPE html>
<html lang="uk">
<head>
  <meta charset="UTF-8">
  <title>Бронювання — Coffee Time</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="stylesheet" href="../static/css/style.css">
  <link rel="stylesheet" href="../static/css/reservation.css">
  <link rel="stylesheet" href="../static/css/footer.css">
</head>
<body>
  <?php $page='reservation'; include '../includes/header.php'; ?>
  <main class="reservation-container">
    <h1>Бронювання столика</h1>

    <?php if($success): ?>
      <div class="notification success"><?= htmlspecialchars($success) ?></div>
    <?php elseif($error): ?>
      <div class="notification error"><?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <?php if (!$location): ?>
      <div class="reservation-categories">
        <div class="reservation-option">
          <img src="../static/images/main/indoor.jpg" alt="У приміщенні">
          <h3>У приміщенні</h3>
          <a href="?location=indoor" class="reserve-button">Обрати</a>
        </div>
        <div class="reservation-option">
          <img src="../static/images/main/terasa.jpg" alt="На терасі">
          <h3>На терасі</h3>
          <a href="?location=terrace" class="reserve-button">Обрати</a>
        </div>
      </div>

    <?php else:
      $max = $location==='terrace'?15:10;
      $stmt = $conn->prepare("SELECT table_number FROM reservations WHERE location=?");
      $stmt->bind_param('s',$location);
      $stmt->execute();
      $rs = $stmt->get_result();
      $booked = [];
      while($r=$rs->fetch_assoc()) $booked[] = (int)$r['table_number'];
      $stmt->close();
    ?>
      <p>Оберіть столи <?= $location==='terrace'?'на терасі':'в залі' ?>:</p>
      <div class="table-grid">
        <?php for($i=1;$i<=$max;$i++):
          $cls = in_array($i,$booked)?'booked':'available';
        ?>
          <div class="table <?= $cls ?>" data-table="<?= $i ?>"><?= $i ?></div>
        <?php endfor; ?>
      </div>

      <div class="reservation-footer">
        <div>Вибрано: <span id="selected-number">—</span></div>
        <label for="datetime">Дата і час:</label>
        <input type="datetime-local" id="datetime">
        <button id="reserve-btn" class="btn" disabled>Підтвердити</button>
      </div>

      <form id="reserve-form" method="post" style="display:none;">
        <input type="hidden" name="location" value="<?= htmlspecialchars($location) ?>">
        <input type="hidden" name="tables"   id="f-tables">
        <input type="hidden" name="datetime" id="f-dt">
      </form>

      <script src="../static/js/reservation.js"></script>
      </script>
    <?php endif; ?>
  </main>
  <?php include '../includes/footer.php'; ?>
</body>
</html>
