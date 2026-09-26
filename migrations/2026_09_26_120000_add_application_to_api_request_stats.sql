-- Historical requests cannot be assigned to an application after the fact.
-- Keep the session in cep_admin so the migration marker is recorded there.

ALTER TABLE cep_public.api_requests
    ADD COLUMN application VARCHAR(32) NOT NULL DEFAULT 'unknown' AFTER user_agent,
    ADD INDEX idx_application_created_at (application, created_at);
ALTER TABLE cep_public.api_requests ALTER COLUMN application DROP DEFAULT;

ALTER TABLE cep_public.api_request_daily_stats
    DROP INDEX uk_date_endpoint,
    ADD COLUMN application VARCHAR(32) NOT NULL DEFAULT 'unknown' AFTER endpoint,
    ADD UNIQUE KEY uk_date_endpoint_application (date, endpoint, application);
ALTER TABLE cep_public.api_request_daily_stats ALTER COLUMN application DROP DEFAULT;
