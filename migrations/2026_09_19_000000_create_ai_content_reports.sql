-- Store reports about AI-generated content received by Bible-API.
-- The table belongs to the live public service data and is never populated by
-- the cep_admin -> cep_public content import.

USE cep_public;

CREATE TABLE IF NOT EXISTS ai_content_reports (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content_type ENUM('question', 'scripture') NOT NULL,
    content_text TEXT NOT NULL,
    user_comment VARCHAR(1000) DEFAULT NULL,
    language VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ai_content_reports_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
