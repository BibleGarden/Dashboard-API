-- Fully qualify data tables so the migration marker stays in cep_admin.
-- MySQL DDL commits per statement. Guard each change for a partial rerun.
-- degraded_reason holds a short code only, never request content.
-- NULL daily counters mark days aggregated before these columns existed.

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_requests'
              AND column_name = 'degraded_reason'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_requests ADD COLUMN degraded_reason VARCHAR(32) NULL DEFAULT NULL AFTER application'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND column_name = 'server_error_count'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_request_daily_stats ADD COLUMN server_error_count INT UNSIGNED NULL DEFAULT NULL AFTER error_count'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND column_name = 'degraded_count'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_request_daily_stats ADD COLUMN degraded_count INT UNSIGNED NULL DEFAULT NULL AFTER server_error_count'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;
