-- --------------------------------------------------------
-- MediMate Database Setup and Seed Data Script
-- Date: June 11, 2026
--
-- INSTRUCTIONS:
-- Import this file into MySQL to create the 'medimate' database,
-- set up the tables, and seed it with realistic fake patient data.
-- You can run this command in your terminal:
--   mysql -u root -p < esp32/medimate.sql
-- --------------------------------------------------------

-- Create database if it does not exist
CREATE DATABASE IF NOT EXISTS `medimate`;
USE `medimate`;

-- Clear existing data to ensure a clean, reproducible state
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `pulse_data`;
DROP TABLE IF EXISTS `patients`;
SET FOREIGN_KEY_CHECKS = 1;

-- ========================================================
-- 1. TABLE CREATION
-- ========================================================

-- Table structure for patients (users)
CREATE TABLE `patients` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(100) NOT NULL,
  `age` INT NOT NULL,
  `gender` VARCHAR(10) NOT NULL,
  `diagnosis` VARCHAR(255) DEFAULT 'No diagnosis',
  `admitted_date` DATETIME NOT NULL,
  `release_date` DATETIME DEFAULT NULL,
  `image` VARCHAR(255) DEFAULT NULL,
  INDEX (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table structure for pulse readings
CREATE TABLE `pulse_data` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `patient_id` INT NOT NULL,
  `pulse` INT NOT NULL,
  `created_at` DATETIME NOT NULL,
  CONSTRAINT `fk_pulse_data_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
  INDEX (`patient_id`),
  INDEX (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================================
-- 2. SEED DATA - PATIENTS
-- ========================================================

-- We insert 8 patients with varied demographic data and medical diagnoses.
-- Leaving 'image' as NULL allows index.php to automatically generate 
-- clean, professional UI avatars based on their names.
INSERT INTO `patients` (`id`, `name`, `age`, `gender`, `diagnosis`, `admitted_date`, `release_date`, `image`) VALUES
(1, 'John Doe', 45, 'Male', 'Hypertension', '2026-06-01 10:00:00', NULL, NULL),
(2, 'Jane Smith', 29, 'Female', 'Arrhythmia', '2026-06-05 08:30:00', NULL, NULL),
(3, 'Robert Johnson', 68, 'Male', 'Coronary Artery Disease', '2026-05-20 14:15:00', '2026-06-10 11:00:00', NULL),
(4, 'Emily Davis', 34, 'Female', 'Normal Checkup', '2026-06-09 09:00:00', '2026-06-09 17:00:00', NULL),
(5, 'Michael Brown', 52, 'Male', 'Tachycardia', '2026-06-08 11:20:00', NULL, NULL),
(6, 'Sarah Wilson', 71, 'Female', 'Bradycardia', '2026-06-03 16:45:00', NULL, NULL),
(7, 'William Taylor', 19, 'Male', 'Athletic Evaluation', '2026-06-11 07:00:00', NULL, NULL),
(8, 'Olivia Martinez', 41, 'Female', 'Recovering from Surgery', '2026-06-04 13:10:00', NULL, NULL);

-- ========================================================
-- 3. SEED DATA - PULSE READINGS
-- ========================================================

-- For active patients (NULL release_date), the last reading is set to 
-- CURRENT_TIMESTAMP or very close to NOW() so that they show up as 
-- "Device Connected" (within the 30-second window expected by get_data.php).
-- For released patients, the pulse data matches their release timeline.

-- --------------------------------------------------------
-- Patient 1: John Doe (Hypertension, elevated but relatively stable pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(1, 85, DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(1, 88, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(1, 92, DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(1, 90, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(1, 89, DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(1, 93, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(1, 97, DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(1, 95, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(1, 99, DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(1, 94, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(1, 91, DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(1, 95, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(1, 92, DATE_SUB(NOW(), INTERVAL 5 SECOND));

-- --------------------------------------------------------
-- Patient 2: Jane Smith (Arrhythmia, highly erratic pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(2, 72,  DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(2, 115, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(2, 65,  DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(2, 120, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(2, 58,  DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(2, 110, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(2, 74,  DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(2, 125, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(2, 62,  DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(2, 118, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(2, 68,  DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(2, 121, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(2, 60,  DATE_SUB(NOW(), INTERVAL 5 SECOND));

-- --------------------------------------------------------
-- Patient 3: Robert Johnson (Coronary Artery Disease, released on June 10)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(3, 72, '2026-06-10 08:00:00'),
(3, 74, '2026-06-10 08:15:00'),
(3, 75, '2026-06-10 08:30:00'),
(3, 78, '2026-06-10 08:45:00'),
(3, 73, '2026-06-10 09:00:00'),
(3, 76, '2026-06-10 09:15:00'),
(3, 75, '2026-06-10 09:30:00'),
(3, 74, '2026-06-10 09:45:00'),
(3, 72, '2026-06-10 10:00:00'),
(3, 71, '2026-06-10 10:15:00'),
(3, 73, '2026-06-10 10:30:00'),
(3, 75, '2026-06-10 10:45:00'),
(3, 74, '2026-06-10 11:00:00');

-- --------------------------------------------------------
-- Patient 4: Emily Davis (Normal Checkup, released on June 9)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(4, 68, '2026-06-09 09:00:00'),
(4, 70, '2026-06-09 09:45:00'),
(4, 72, '2026-06-09 10:30:00'),
(4, 71, '2026-06-09 11:15:00'),
(4, 69, '2026-06-09 12:00:00'),
(4, 72, '2026-06-09 12:45:00'),
(4, 74, '2026-06-09 13:30:00'),
(4, 73, '2026-06-09 14:15:00'),
(4, 71, '2026-06-09 15:00:00'),
(4, 70, '2026-06-09 15:45:00'),
(4, 68, '2026-06-09 16:30:00'),
(4, 69, '2026-06-09 17:00:00');

-- --------------------------------------------------------
-- Patient 5: Michael Brown (Tachycardia, consistently high resting pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(5, 102, DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(5, 105, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(5, 108, DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(5, 112, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(5, 110, DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(5, 115, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(5, 118, DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(5, 114, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(5, 111, DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(5, 109, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(5, 113, DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(5, 116, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(5, 112, DATE_SUB(NOW(), INTERVAL 5 SECOND));

-- --------------------------------------------------------
-- Patient 6: Sarah Wilson (Bradycardia, consistently low resting pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(6, 52, DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(6, 49, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(6, 48, DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(6, 51, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(6, 53, DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(6, 50, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(6, 47, DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(6, 46, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(6, 49, DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(6, 51, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(6, 52, DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(6, 48, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(6, 50, DATE_SUB(NOW(), INTERVAL 5 SECOND));

-- --------------------------------------------------------
-- Patient 7: William Taylor (Athletic Evaluation, low-normal athletic pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(7, 58, DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(7, 56, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(7, 55, DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(7, 54, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(7, 57, DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(7, 58, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(7, 56, DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(7, 55, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(7, 53, DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(7, 54, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(7, 56, DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(7, 55, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(7, 54, DATE_SUB(NOW(), INTERVAL 5 SECOND));

-- --------------------------------------------------------
-- Patient 8: Olivia Martinez (Recovering from Surgery, normal resting pulse)
-- --------------------------------------------------------
INSERT INTO `pulse_data` (`patient_id`, `pulse`, `created_at`) VALUES
(8, 78, DATE_SUB(NOW(), INTERVAL 60 MINUTE)),
(8, 80, DATE_SUB(NOW(), INTERVAL 55 MINUTE)),
(8, 82, DATE_SUB(NOW(), INTERVAL 50 MINUTE)),
(8, 85, DATE_SUB(NOW(), INTERVAL 45 MINUTE)),
(8, 83, DATE_SUB(NOW(), INTERVAL 40 MINUTE)),
(8, 81, DATE_SUB(NOW(), INTERVAL 35 MINUTE)),
(8, 79, DATE_SUB(NOW(), INTERVAL 30 MINUTE)),
(8, 82, DATE_SUB(NOW(), INTERVAL 25 MINUTE)),
(8, 84, DATE_SUB(NOW(), INTERVAL 20 MINUTE)),
(8, 86, DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
(8, 83, DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
(8, 80, DATE_SUB(NOW(), INTERVAL 5 MINUTE)),
(8, 81, DATE_SUB(NOW(), INTERVAL 5 SECOND));
