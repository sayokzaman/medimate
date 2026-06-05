<?php

header('Content-Type: application/json');

// ======================================
// TIMEZONE
// ======================================

date_default_timezone_set('Asia/Dhaka');

// ======================================
// DATABASE
// ======================================

$servername = "localhost";
$username = "u837808682_medimate_user";
$password = "Medimate_user1";
$database = "u837808682_medimate";

$conn = new mysqli(
    $servername,
    $username,
    $password,
    $database
);

// ======================================
// CONNECTION CHECK
// ======================================

if ($conn->connect_error) {

    die(json_encode([
        "status" => "error"
    ]));
}

// ======================================
// GET LATEST DATA
// ======================================

$result = $conn->query("
    SELECT *
    FROM pulse_data
    ORDER BY id DESC
    LIMIT 30
");

$data = [];

while ($row = $result->fetch_assoc()) {

    $data[] = $row;
}

$data = array_reverse($data);

// ======================================
// DEVICE STATUS
// ======================================

$deviceStatus = "Offline";

if (!empty($data)) {

    $latest = end($data);

    $lastTimestamp =
        strtotime($latest['created_at']);

    $currentTimestamp = time();

    $difference =
        $currentTimestamp - $lastTimestamp;

    if ($difference <= 10) {

        $deviceStatus = "Connected";
    }
}

// ======================================
// RESPONSE
// ======================================

echo json_encode([

    "status" => "success",

    "device_status" => $deviceStatus,

    "data" => $data
]);

$conn->close();

?>