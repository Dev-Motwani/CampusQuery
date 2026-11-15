-- ========================================================
-- CampusQuery Database Schema (MySQL 8.0+)
-- Phase 2: Complete Relational Schema
-- Character Set: utf8mb4 | Collation: utf8mb4_unicode_ci
-- ========================================================

CREATE DATABASE IF NOT EXISTS `campusqueri_db`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `campusqueri_db`;

-- --------------------------------------------------------
-- 1. Table: users
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `roll_number` VARCHAR(50) NULL UNIQUE,
    `role` ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 2. Table: categories
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(80) NOT NULL UNIQUE,
    `slug` VARCHAR(80) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL,
    `icon` VARCHAR(50) NOT NULL DEFAULT 'bi-bookmark',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_categories_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 3. Table: office_information (SAMPLE Data)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `office_information` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `office_name` VARCHAR(120) NOT NULL,
    `department` VARCHAR(100) NULL,
    `building_room` VARCHAR(100) NOT NULL,
    `contact_person` VARCHAR(100) NOT NULL,
    `contact_email` VARCHAR(120) NOT NULL,
    `contact_phone` VARCHAR(30) NULL,
    `office_hours` VARCHAR(100) NOT NULL DEFAULT '[SAMPLE] Mon-Fri 10:00 AM - 04:30 PM',
    `visit_instructions` TEXT NULL,
    `is_sample` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_office_name` (`office_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 4. Table: notices (Publication status separate from deadlines)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notices` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `slug` VARCHAR(220) NOT NULL UNIQUE,
    `summary` VARCHAR(300) NULL,
    `content` TEXT NOT NULL,
    `category_id` INT NOT NULL,
    `priority` ENUM('low', 'medium', 'high', 'urgent') NOT NULL DEFAULT 'medium',
    `status` ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'draft',
    `published_at` DATETIME NULL,
    `expires_at` DATETIME NULL,
    `created_by` INT NOT NULL,
    `eligibility` TEXT NULL,
    `required_documents` TEXT NULL,
    `submission_instructions` TEXT NULL,
    `office_id` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_notices_slug` (`slug`),
    INDEX `idx_notices_category` (`category_id`),
    INDEX `idx_notices_status` (`status`),
    INDEX `idx_notices_priority` (`priority`),
    INDEX `idx_notices_published_at` (`published_at`),
    INDEX `idx_notices_office` (`office_id`),
    CONSTRAINT `fk_notices_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_notices_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_notices_office` FOREIGN KEY (`office_id`) REFERENCES `office_information` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 5. Table: deadlines (Multiple milestones per notice)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `deadlines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `notice_id` INT NOT NULL,
    `milestone_name` VARCHAR(150) NOT NULL,
    `due_date` DATETIME NOT NULL,
    `status` ENUM('upcoming', 'ongoing', 'extended', 'closed') NOT NULL DEFAULT 'upcoming',
    `office_id` INT NULL,
    `instructions` VARCHAR(300) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_deadlines_notice` (`notice_id`),
    INDEX `idx_deadlines_due_date` (`due_date`),
    INDEX `idx_deadlines_status` (`status`),
    INDEX `idx_deadlines_office` (`office_id`),
    CONSTRAINT `fk_deadlines_notice` FOREIGN KEY (`notice_id`) REFERENCES `notices` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_deadlines_office` FOREIGN KEY (`office_id`) REFERENCES `office_information` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 6. Table: documents (Metadata only, files kept in filesystem)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `documents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `filename` VARCHAR(255) NOT NULL,
    `original_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_size` INT NOT NULL,
    `file_type` VARCHAR(100) NOT NULL,
    `label` VARCHAR(100) NOT NULL DEFAULT 'Supporting Document',
    `description` TEXT NULL,
    `extracted_text` MEDIUMTEXT NULL,
    `extraction_status` VARCHAR(50) NOT NULL DEFAULT 'pending',
    `sha256_hash` VARCHAR(64) NULL,
    `uploaded_by` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_documents_uploader` (`uploaded_by`),
    INDEX `idx_documents_label` (`label`),
    INDEX `idx_documents_status` (`extraction_status`),
    CONSTRAINT `fk_documents_uploader` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 7. Table: notice_documents (Junction Table)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notice_documents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `notice_id` INT NOT NULL,
    `document_id` INT NOT NULL,
    `display_label` VARCHAR(150) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_notice_document` (`notice_id`, `document_id`),
    INDEX `idx_nd_notice` (`notice_id`),
    INDEX `idx_nd_document` (`document_id`),
    CONSTRAINT `fk_nd_notice` FOREIGN KEY (`notice_id`) REFERENCES `notices` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_nd_document` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 8. Table: flowcharts
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `flowcharts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(150) NOT NULL,
    `slug` VARCHAR(180) NOT NULL UNIQUE,
    `description` VARCHAR(300) NULL,
    `graph_data` JSON NOT NULL,
    `created_by` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_flowcharts_slug` (`slug`),
    INDEX `idx_flowcharts_creator` (`created_by`),
    CONSTRAINT `fk_flowcharts_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 9. Table: notice_flowcharts (Junction Table)
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notice_flowcharts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `notice_id` INT NOT NULL,
    `flowchart_id` INT NOT NULL,
    `caption` VARCHAR(150) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_notice_flowchart` (`notice_id`, `flowchart_id`),
    INDEX `idx_nf_notice` (`notice_id`),
    INDEX `idx_nf_flowchart` (`flowchart_id`),
    CONSTRAINT `fk_nf_notice` FOREIGN KEY (`notice_id`) REFERENCES `notices` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_nf_flowchart` FOREIGN KEY (`flowchart_id`) REFERENCES `flowcharts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- 10. Table: notifications
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `notice_id` INT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` VARCHAR(300) NOT NULL,
    `notification_type` VARCHAR(50) NOT NULL DEFAULT 'info',
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_notifications_user` (`user_id`),
    INDEX `idx_notifications_read` (`is_read`),
    CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifications_notice` FOREIGN KEY (`notice_id`) REFERENCES `notices` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
