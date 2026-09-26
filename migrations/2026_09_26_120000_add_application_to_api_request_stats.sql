-- Fully qualify data tables so the migration marker stays in cep_admin.
-- MySQL DDL commits per statement. Guard each change for a partial rerun.
-- Keep DEFAULT 'unknown' while the old Bible-API writer is still running.

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_requests'
              AND column_name = 'application'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_requests ADD COLUMN application VARCHAR(32) NOT NULL DEFAULT ''unknown'' AFTER user_agent'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_requests'
              AND column_name = 'application'
              AND column_default = 'unknown'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_requests ALTER COLUMN application SET DEFAULT ''unknown'''
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.statistics
            WHERE table_schema = 'cep_public' AND table_name = 'api_requests'
              AND index_name = 'idx_application_created_at'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_requests ADD INDEX idx_application_created_at (application, created_at)'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND column_name = 'application'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_request_daily_stats ADD COLUMN application VARCHAR(32) NOT NULL DEFAULT ''unknown'' AFTER endpoint'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND column_name = 'application'
              AND column_default = 'unknown'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_request_daily_stats ALTER COLUMN application SET DEFAULT ''unknown'''
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.statistics
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND index_name = 'uk_date_endpoint'),
    'ALTER TABLE cep_public.api_request_daily_stats DROP INDEX uk_date_endpoint',
    'SET @stats_noop = 1'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;

SET @stats_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.statistics
            WHERE table_schema = 'cep_public' AND table_name = 'api_request_daily_stats'
              AND index_name = 'uk_date_endpoint_application'),
    'SET @stats_noop = 1',
    'ALTER TABLE cep_public.api_request_daily_stats ADD UNIQUE KEY uk_date_endpoint_application (date, endpoint, application)'
);
PREPARE stats_stmt FROM @stats_ddl;
EXECUTE stats_stmt;
DEALLOCATE PREPARE stats_stmt;
