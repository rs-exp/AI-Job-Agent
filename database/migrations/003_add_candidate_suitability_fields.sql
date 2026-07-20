ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS suitability_score INTEGER;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS is_suitable BOOLEAN;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS suitability_details JSONB;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS suitability_evaluated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_jobs_suitability_score
ON jobs(suitability_score DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_is_suitable
ON jobs(is_suitable);