-- ============================================================
-- PatientPath AI - MySQL Database Setup
-- ============================================================
-- Run this script to create the database before starting the app.
--
-- Usage:
--   mysql -u root -p < create_database.sql
-- ============================================================

-- Create database with UTF-8 support
CREATE DATABASE IF NOT EXISTS patientpath
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Use the database
USE patientpath;

-- Grant privileges (adjust user/host as needed)
-- GRANT ALL PRIVILEGES ON patientpath.* TO 'root'@'localhost';
-- FLUSH PRIVILEGES;

SELECT 'Database "patientpath" created successfully!' AS status;
