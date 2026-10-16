-- Visitor Management System - MySQL Schema
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS visitor_management
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE visitor_management;

-- Hosts are the employees being visited
CREATE TABLE IF NOT EXISTS hosts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    department VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Staff / front-desk / security users who can log into the dashboard
CREATE TABLE IF NOT EXISTS staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(120) NOT NULL,
    role ENUM('admin', 'security', 'frontdesk') NOT NULL DEFAULT 'frontdesk',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Visitors (a person can visit multiple times, so identity is separate from each visit)
CREATE TABLE IF NOT EXISTS visitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    company VARCHAR(150),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Each visit / appointment gets a unique QR token
CREATE TABLE IF NOT EXISTS visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id INT NOT NULL,
    host_id INT NOT NULL,
    purpose VARCHAR(255),
    token VARCHAR(36) NOT NULL UNIQUE,          -- UUID4, encoded in the QR
    qr_path VARCHAR(255),                        -- path to generated QR image
    status ENUM('pending', 'checked_in', 'checked_out', 'cancelled')
        NOT NULL DEFAULT 'pending',
    scheduled_time DATETIME,
    check_in_time DATETIME NULL,
    check_out_time DATETIME NULL,
    registered_by ENUM('self', 'staff') NOT NULL DEFAULT 'self',
    created_by_staff_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visitor_id) REFERENCES visitors(id) ON DELETE CASCADE,
    FOREIGN KEY (host_id) REFERENCES hosts(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_staff_id) REFERENCES staff(id) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_token (token)
);

-- Seed a default admin user (username: admin / password: admin123 -- CHANGE THIS)
-- Password hash generated with werkzeug.security.generate_password_hash('admin123')
-- Run scripts/create_admin.py instead of inserting manually — see README.
