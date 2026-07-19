-- Add deterministic cross-source job fingerprint support.

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint
ON jobs(fingerprint);