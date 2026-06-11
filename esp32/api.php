<?php

error_reporting(E_ALL);
ini_set('display_errors', 1);

date_default_timezone_set('Asia/Dhaka');

$servername = "localhost";
$username   = "root";
$password   = "";
$database   = "medimate";

$conn = new mysqli($servername, $username, $password, $database);

if ($conn->connect_error) {
    die("DB Connection Failed");
}

if (isset($_GET['pulse']) && isset($_GET['patient_id'])) {

    $pulse     = intval($_GET['pulse']);
    $patientId = intval($_GET['patient_id']);
    $createdAt = date('Y-m-d H:i:s');

    $stmt = $conn->prepare(
        "INSERT INTO pulse_data (patient_id, pulse, created_at) VALUES (?, ?, ?)"
    );
    $stmt->bind_param("iis", $patientId, $pulse, $createdAt);

    if ($stmt->execute()) {
        echo "SUCCESS";
    } else {
        echo "FAILED";
    }

    $stmt->close();

} else {
    echo "NO_DATA";
}

$conn->close();
?>
