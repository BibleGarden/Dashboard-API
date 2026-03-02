-- Migration: add_status_to_voice_anomalies
-- Created: 2025-07-23 23:45:39

-- Add status column to voice_anomalies table
-- Status values:
-- detected - anomaly detected (default)
-- confirmed - anomaly confirmed
-- disproved - anomaly disproved, not confirmed by review
-- corrected - manual correction applied
-- already_resolved - already fixed earlier

ALTER TABLE `voice_anomalies` 
ADD COLUMN `status` ENUM('detected', 'confirmed', 'disproved', 'corrected', 'already_resolved') 
NOT NULL DEFAULT 'detected' 
COMMENT 'Status of anomaly: detected, confirmed, disproved, corrected, already_resolved';

-- Add index for better performance when filtering by status
CREATE INDEX `idx_voice_anomalies_status` ON `voice_anomalies` (`status`);

-- Add composite index for voice + status filtering
CREATE INDEX `idx_voice_anomalies_voice_status` ON `voice_anomalies` (`voice`, `status`);
