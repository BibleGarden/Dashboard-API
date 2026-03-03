-- Create API request statistics tables in cep_public database
-- These tables track Public API usage for the dashboard

USE cep_public;

-- Raw request log (purged after 14 days)
CREATE TABLE IF NOT EXISTS api_requests (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code SMALLINT UNSIGNED NOT NULL,
    response_time_ms INT UNSIGNED NOT NULL,
    client_ip VARCHAR(45) NOT NULL,
    user_agent VARCHAR(512) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_endpoint (endpoint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Aggregated daily stats (permanent)
CREATE TABLE IF NOT EXISTS api_request_daily_stats (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_count INT UNSIGNED NOT NULL DEFAULT 0,
    unique_ips INT UNSIGNED NOT NULL DEFAULT 0,
    avg_response_time_ms INT UNSIGNED NOT NULL DEFAULT 0,
    error_count INT UNSIGNED NOT NULL DEFAULT 0,
    UNIQUE KEY uk_date_endpoint (date, endpoint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
