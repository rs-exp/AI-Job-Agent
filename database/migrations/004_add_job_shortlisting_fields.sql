ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS shortlist_status VARCHAR(30)
NOT NULL DEFAULT 'not_reviewed';

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS shortlist_notes TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS shortlist_decided_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_jobs_shortlist_status'
          AND conrelid = 'jobs'::regclass
    ) THEN
        ALTER TABLE jobs
        ADD CONSTRAINT chk_jobs_shortlist_status
        CHECK (
            shortlist_status IN (
                'not_reviewed',
                'shortlisted',
                'rejected'
            )
        );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_jobs_shortlist_status
ON jobs(shortlist_status);