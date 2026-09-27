-- The local migration marker stays in cep_admin. Production applies this SQL
-- directly to cep_public, which has no migration ledger.
-- Separate guards allow a rerun after either DDL statement has committed.

-- Referencing the table fails if the target schema is missing it.
SET @alignment_table_check = (
    SELECT COUNT(*) FROM cep_public.voice_alignments WHERE 1 = 0
);

SET @alignment_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.statistics
            WHERE table_schema = 'cep_public' AND table_name = 'voice_alignments'
              AND index_name = 'voice_alignments_translation_verse_idx'),
    'ALTER TABLE cep_public.voice_alignments DROP INDEX voice_alignments_translation_verse_idx',
    'SET @alignment_noop = 1'
);
PREPARE alignment_stmt FROM @alignment_ddl;
EXECUTE alignment_stmt;
DEALLOCATE PREPARE alignment_stmt;

SET @alignment_ddl = IF(
    EXISTS (SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'cep_public' AND table_name = 'voice_alignments'
              AND column_name = 'translation_verse'),
    'ALTER TABLE cep_public.voice_alignments DROP COLUMN translation_verse',
    'SET @alignment_noop = 1'
);
PREPARE alignment_stmt FROM @alignment_ddl;
EXECUTE alignment_stmt;
DEALLOCATE PREPARE alignment_stmt;
