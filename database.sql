-- ============================================
-- 🗄️ DATABASE SCHEMA (FINAL PRODUCTION)
-- Driver Drowsiness Detection System
-- Version: 1.2 (Fully Synced with User & Alert Models)
-- ============================================

-- 1. Tạo Database
CREATE DATABASE IF NOT EXISTS drowsiness_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE drowsiness_db;

-- ============================================
-- 2. BẢNG: users (Tài khoản)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL COMMENT 'Hash password',
    full_name VARCHAR(100) DEFAULT NULL,
    email VARCHAR(100) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,       -- [ĐÃ THÊM] Cho khớp với UserModel
    avatar VARCHAR(255) DEFAULT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL      -- [ĐÃ THÊM] Để theo dõi lần đăng nhập cuối
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 3. BẢNG: alert_history (Lịch sử cảnh báo)
-- ============================================
CREATE TABLE IF NOT EXISTS alert_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    alert_type VARCHAR(50) NOT NULL, 
    alert_level INT NOT NULL DEFAULT 1,
    
    -- Các thông số kỹ thuật
    ear_value FLOAT DEFAULT 0,
    mar_value FLOAT DEFAULT 0,
    head_pitch FLOAT DEFAULT 0,
    head_yaw FLOAT DEFAULT 0,
    
    duration_seconds FLOAT DEFAULT 0,
    screenshot_path VARCHAR(255) DEFAULT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_alert_type (alert_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 4. BẢNG: driving_sessions (Phiên lái xe)
-- ============================================
CREATE TABLE IF NOT EXISTS driving_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME DEFAULT NULL,
    
    total_alerts INT DEFAULT 0,
    drowsy_count INT DEFAULT 0,
    yawn_count INT DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'ACTIVE',
    notes TEXT DEFAULT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_date (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 5. BẢNG: user_settings (Cấu hình cá nhân)
-- ============================================
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    
    -- Các ngưỡng phát hiện
    ear_threshold FLOAT DEFAULT 0.25,
    mar_threshold FLOAT DEFAULT 0.70,
    head_threshold FLOAT DEFAULT 25.0,
    
    -- Các cài đặt hệ thống [ĐÃ THÊM ĐẦY ĐỦ]
    alert_volume FLOAT DEFAULT 0.8,
    sensitivity_level VARCHAR(10) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH
    enable_sound BOOLEAN DEFAULT TRUE,
    enable_vibration BOOLEAN DEFAULT TRUE,
    
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================
-- 6. VIEWS (Thống kê)
-- ============================================
CREATE OR REPLACE VIEW daily_statistics AS
SELECT 
    user_id,
    DATE(timestamp) AS date,
    COUNT(*) AS total_alerts,
    SUM(CASE WHEN alert_type = 'DROWSY' THEN 1 ELSE 0 END) AS drowsy_count,
    SUM(CASE WHEN alert_type = 'YAWN' THEN 1 ELSE 0 END) AS yawn_count,
    SUM(CASE WHEN alert_type = 'HEAD_DOWN' THEN 1 ELSE 0 END) AS head_down_count,
    AVG(ear_value) AS avg_ear,
    AVG(mar_value) AS avg_mar,
    MAX(alert_level) AS max_alert_level
FROM alert_history
GROUP BY user_id, DATE(timestamp);

CREATE OR REPLACE VIEW weekly_statistics AS
SELECT 
    user_id,
    DATE(timestamp) AS alert_date,
    COUNT(*) AS total_alerts
FROM alert_history
WHERE timestamp >= DATE(NOW()) - INTERVAL 7 DAY
GROUP BY user_id, DATE(timestamp)
ORDER BY alert_date ASC;

-- ============================================
-- 7. DỮ LIỆU MẪU (Seed Data)
-- ============================================
INSERT INTO users (username, password, full_name, email) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.6FG6CMJa/JwYHO', 'System Admin', 'admin@drowsiness.com')
ON DUPLICATE KEY UPDATE full_name = 'System Admin';

-- Tạo Setting mặc định
INSERT INTO user_settings (user_id)
SELECT id FROM users WHERE username = 'admin'
ON DUPLICATE KEY UPDATE user_id = user_id;

-- Xác nhận
SELECT "Database Setup Completed Successfully!" as Status;