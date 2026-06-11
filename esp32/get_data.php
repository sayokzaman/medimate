<?php

header('Content-Type: application/json');

date_default_timezone_set('Asia/Dhaka');

$servername = "localhost";
$username   = "root";
$password   = "";
$database   = "medimate";

$conn = new mysqli($servername, $username, $password, $database);

if ($conn->connect_error) {
    die(json_encode(["status" => "error", "message" => "DB connection failed"]));
}

// ======================================
// SINGLE PATIENT + PULSE DATA
// ======================================

if (isset($_GET['patient_id'])) {

    $patientId = intval($_GET['patient_id']);

    $pStmt = $conn->prepare("SELECT * FROM patients WHERE id = ?");
    $pStmt->bind_param("i", $patientId);
    $pStmt->execute();
    $patient = $pStmt->get_result()->fetch_assoc();
    $pStmt->close();

    if (!$patient) {
        echo json_encode(["status" => "error", "message" => "Patient not found"]);
        $conn->close();
        exit;
    }

    $dStmt = $conn->prepare(
        "SELECT * FROM pulse_data WHERE patient_id = ? ORDER BY id DESC LIMIT 30"
    );
    $dStmt->bind_param("i", $patientId);
    $dStmt->execute();
    $result = $dStmt->get_result();

    $data = [];
    while ($row = $result->fetch_assoc()) {
        $data[] = $row;
    }
    $data = array_reverse($data);
    $dStmt->close();

    $deviceStatus = "Offline";
    if (!empty($data)) {
        $diff = time() - strtotime(end($data)['created_at']);
        if ($diff <= 30) $deviceStatus = "Connected";
    }

    echo json_encode([
        "status"        => "success",
        "patient"       => $patient,
        "device_status" => $deviceStatus,
        "data"          => $data
    ]);

// ======================================
// ALL PATIENTS LIST
// ======================================

} else {

    $patients = [];
    $result   = $conn->query("SELECT * FROM patients ORDER BY id ASC");

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $patients[] = $row;
        }
    }

    echo json_encode([
        "status"   => "success",
        "patients" => $patients
    ]);
}

$conn->close();
?>
