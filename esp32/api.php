<?php

// ======================================
// ERRORS
// ======================================

error_reporting(E_ALL);
ini_set('display_errors', 1);

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

    die("DB Connection Failed");
}

// ======================================
// RECEIVE PULSE
// ======================================

if (isset($_GET['pulse'])) {

    $pulse = intval($_GET['pulse']);

    $createdAt = date('Y-m-d H:i:s');

    $stmt = $conn->prepare(
        "INSERT INTO pulse_data
        (pulse, created_at)
        VALUES (?, ?)"
    );

    $stmt->bind_param(
        "is",
        $pulse,
        $createdAt
    );

    if ($stmt->execute()) {

        echo "SUCCESS";
    }
    else {

        echo "FAILED";
    }

    $stmt->close();
}
else {

    echo "NO_DATA";
}

$conn->close();

?>