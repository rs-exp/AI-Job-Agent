ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS application_status VARCHAR(30)
NOT NULL DEFAULT 'not_applied';

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS application_notes TEXT;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;

ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS application_updated_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_jobs_application_status'
          AND conrelid = 'jobs'::regclass
    ) THEN
        ALTER TABLE jobs
        ADD CONSTRAINT chk_jobs_application_status
        CHECK (
            application_status IN (
                'not_applied',
                'applied',
                'screening',
                'interviewing',
                'offer',
                'rejected',
                'withdrawn'
            )
        );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_jobs_application_status
ON jobs(application_status);

CREATE INDEX IF NOT EXISTS idx_jobs_applied_at
ON jobs(applied_at DESC);