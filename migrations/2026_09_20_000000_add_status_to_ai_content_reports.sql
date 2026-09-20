-- Track the admin review outcome for every AI content report.

ALTER TABLE cep_public.ai_content_reports
    ADD COLUMN status ENUM(
        'unreviewed',
        'not_significant',
        'needs_investigation',
        'action_taken'
    ) NOT NULL DEFAULT 'unreviewed' AFTER language,
    ADD INDEX idx_ai_content_reports_status_id (status, id);
