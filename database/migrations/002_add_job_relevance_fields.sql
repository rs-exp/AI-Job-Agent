-- Store explainable job-relevance evaluation results.

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS relevance_score INTEGER;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS is_relevant BOOLEAN;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS relevance_details JSONB;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS relevance_evaluated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_jobs_relevance_score
ON jobs(relevance_score DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_is_relevant
ON jobs(is_relevant);