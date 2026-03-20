-- ============================================================
-- PatientPath AI - Use-Case Prefixed Tables (Additive Schema)
-- ============================================================
-- These tables are additive for analytics/audit purposes.
-- They do NOT replace or modify existing core domain tables.
-- Safe to run repeatedly (uses IF NOT EXISTS).
-- No foreign key constraints - core tables are managed by
-- SQLAlchemy ORM and may not exist in MySQL at SQL-run time.
--
-- Usage:
--   mysql -u root -p patientpath < usecase_schema.sql
-- ============================================================

USE patientpath;

-- ============================================================
-- STAFF USE-CASE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS staff_usecase_assignments (
    id INT NOT NULL AUTO_INCREMENT,
    staff_user_id INT NOT NULL,
    staff_generated_id VARCHAR(20),
    staff_name VARCHAR(100),
    department VARCHAR(50),
    assigned_by_user_id INT,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'assigned',
    notes TEXT,
    PRIMARY KEY (id),
    INDEX idx_staff_assign_user (staff_user_id),
    INDEX idx_staff_assign_dept (department),
    INDEX idx_staff_assign_status (status),
    INDEX idx_staff_assign_at (assigned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staff_usecase_checkins (
    id INT NOT NULL AUTO_INCREMENT,
    staff_user_id INT NOT NULL,
    department VARCHAR(50) NOT NULL,
    checkin_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    checkout_time DATETIME,
    session_status VARCHAR(20) DEFAULT 'active',
    PRIMARY KEY (id),
    INDEX idx_staff_checkin_user (staff_user_id),
    INDEX idx_staff_checkin_dept (department),
    INDEX idx_staff_checkin_status (session_status),
    INDEX idx_staff_checkin_time (checkin_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS staff_usecase_escalations (
    id INT NOT NULL AUTO_INCREMENT,
    staff_id VARCHAR(50) NOT NULL,
    department VARCHAR(50),
    issue_type VARCHAR(50),
    description TEXT,
    status VARCHAR(20) DEFAULT 'OPEN',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_staff_esc_dept (department),
    INDEX idx_staff_esc_status (status),
    INDEX idx_staff_esc_time (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- PATIENT USE-CASE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS patient_usecase_journey (
    id INT NOT NULL AUTO_INCREMENT,
    patient_tracking_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100),
    mobile VARCHAR(20),
    status VARCHAR(20) DEFAULT 'entered',
    current_zone VARCHAR(50),
    entry_time DATETIME,
    exit_time DATETIME,
    last_action VARCHAR(200),
    action_history_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_pj_tracking (patient_tracking_id),
    INDEX idx_pj_status (status),
    INDEX idx_pj_zone (current_zone),
    INDEX idx_pj_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient_usecase_wait_predictions (
    id INT NOT NULL AUTO_INCREMENT,
    patient_tracking_id VARCHAR(50) NOT NULL,
    department VARCHAR(50) NOT NULL,
    predicted_wait_minutes FLOAT,
    queue_size INT DEFAULT 0,
    predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_pwp_tracking (patient_tracking_id),
    INDEX idx_pwp_dept (department),
    INDEX idx_pwp_time (predicted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS patient_usecase_navigator_events (
    id INT NOT NULL AUTO_INCREMENT,
    patient_tracking_id VARCHAR(50) NOT NULL,
    zone VARCHAR(50),
    event_type VARCHAR(50),
    event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(100),
    details_json TEXT,
    PRIMARY KEY (id),
    INDEX idx_pne_tracking (patient_tracking_id),
    INDEX idx_pne_zone (zone),
    INDEX idx_pne_time (event_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- DOCTOR USE-CASE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS doctor_usecase_status (
    id INT NOT NULL AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    doctor_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'offline',
    last_check_in DATETIME,
    last_check_out DATETIME,
    PRIMARY KEY (id),
    INDEX idx_dus_doctor (doctor_id),
    INDEX idx_dus_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS doctor_usecase_consultations (
    id INT NOT NULL AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    patient_tracking_id VARCHAR(50),
    start_time DATETIME,
    end_time DATETIME,
    notes TEXT,
    PRIMARY KEY (id),
    INDEX idx_duc_doctor (doctor_id),
    INDEX idx_duc_patient (patient_tracking_id),
    INDEX idx_duc_start (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS doctor_usecase_prescriptions (
    id INT NOT NULL AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    patient_id VARCHAR(50),
    diagnosis TEXT,
    prescription TEXT,
    next_visit DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_dup_doctor (doctor_id),
    INDEX idx_dup_patient (patient_id),
    INDEX idx_dup_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- ADMIN USE-CASE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_usecase_approvals (
    id INT NOT NULL AUTO_INCREMENT,
    target_user_id INT NOT NULL,
    target_role VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,
    approved_by_user_id INT,
    approved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    PRIMARY KEY (id),
    INDEX idx_aua_target (target_user_id),
    INDEX idx_aua_role (target_role),
    INDEX idx_aua_action (action),
    INDEX idx_aua_time (approved_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_usecase_alert_actions (
    id INT NOT NULL AUTO_INCREMENT,
    alert_id INT NOT NULL,
    action_type VARCHAR(30) NOT NULL,
    acted_by VARCHAR(100),
    acted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    PRIMARY KEY (id),
    INDEX idx_auaa_alert (alert_id),
    INDEX idx_auaa_type (action_type),
    INDEX idx_auaa_time (acted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_usecase_activity_logs (
    id INT NOT NULL AUTO_INCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(200) NOT NULL,
    details TEXT,
    severity VARCHAR(20) DEFAULT 'info',
    role VARCHAR(20),
    user_id VARCHAR(50),
    PRIMARY KEY (id),
    INDEX idx_aual_time (timestamp),
    INDEX idx_aual_role (role),
    INDEX idx_aual_severity (severity),
    INDEX idx_aual_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_usecase_dashboard_snapshots (
    id INT NOT NULL AUTO_INCREMENT,
    snapshot_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_patients INT DEFAULT 0,
    active_patients INT DEFAULT 0,
    avg_dwell_time FLOAT DEFAULT 0,
    total_alerts INT DEFAULT 0,
    critical_alerts INT DEFAULT 0,
    warning_alerts INT DEFAULT 0,
    zones_payload_json TEXT,
    PRIMARY KEY (id),
    INDEX idx_auds_time (snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- VERIFICATION
-- ============================================================

SELECT 'Use-case schema created successfully!' AS status;
SELECT COUNT(*) AS usecase_table_count FROM information_schema.tables
WHERE table_schema = 'patientpath' AND table_name LIKE '%_usecase_%';
