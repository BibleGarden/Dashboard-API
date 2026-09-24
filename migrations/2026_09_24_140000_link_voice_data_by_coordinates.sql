-- Keep verse links stable when translation text is deleted and re-imported.
ALTER TABLE `translation_verses`
ADD UNIQUE INDEX `uq_translation_verses_coordinates`
    (`translation`, `book_number`, `chapter_number`, `verse_number`);

ALTER TABLE `voice_anomalies`
DROP INDEX `idx_voice_anomalies_verse`,
DROP COLUMN `translation_verse_id`;

ALTER TABLE `voice_alignments`
DROP INDEX `voice_alignments_translation_verse_idx`,
DROP COLUMN `translation_verse`;
