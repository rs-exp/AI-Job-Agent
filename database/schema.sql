-- =========================================================
-- AI JOB AGENT DATABASE SCHEMA
-- =========================================================


-- =========================================================
-- 1. JOB SOURCES
-- Stores websites, APIs, ATS platforms, and portals
-- that the AI Job Agent can test or scrape.
-- =========================================================

CREATE TABLE IF NOT EXISTS job_sources (
    id BIGSERIAL PRIMARY KEY,

    source_name VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,

    target_role VARCHAR(150),

    status VARCHAR(50) NOT NULL DEFAULT 'not_tested',
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_jobs_shortlist_status
    CHECK (
        shortlist_status IN (
            'not_reviewed',
            'shortlisted',
            'rejected'
        )
    )
);


-- =========================================================
-- 2. SOURCE CHECK RESULTS
-- Stores every accessibility test performed against a source.
-- One source can have many historical check results.
-- =========================================================

CREATE TABLE IF NOT EXISTS source_check_results (
    id BIGSERIAL PRIMARY KEY,

    source_id BIGINT NOT NULL
        REFERENCES job_sources(id)
        ON DELETE CASCADE,

    check_status VARCHAR(50) NOT NULL,
    http_status_code INTEGER,

    error_message TEXT,
    response_time_ms INTEGER,

    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 3. JOBS
-- Stores standardized jobs collected from all sources.
-- URL is unique to prevent duplicate job entries.
-- =========================================================

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,

    source VARCHAR(100) NOT NULL,
    fingerprint VARCHAR(64),
    relevance_score INTEGER,
    is_relevant BOOLEAN,
    relevance_details JSONB,
    relevance_evaluated_at TIMESTAMPTZ,
    suitability_score INTEGER,
    is_suitable BOOLEAN,
    suitability_details JSONB,
    suitability_evaluated_at TIMESTAMPTZ,
    shortlist_status VARCHAR(30)
    NOT NULL DEFAULT 'not_reviewed',

    shortlist_notes TEXT,

    shortlist_decided_at TIMESTAMPTZ,

    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),

    salary TEXT,
    description TEXT,

    url TEXT NOT NULL UNIQUE,

    employment_type VARCHAR(100),
    posted_date TIMESTAMPTZ,

    remote BOOLEAN NOT NULL DEFAULT FALSE,

    status VARCHAR(50) NOT NULL DEFAULT 'new',

    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );


-- =========================================================
-- 4. INDEXES FOR JOB SOURCES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_job_sources_source_name
ON job_sources(source_name);

CREATE INDEX IF NOT EXISTS idx_job_sources_status
ON job_sources(status);

CREATE INDEX IF NOT EXISTS idx_job_sources_source_type
ON job_sources(source_type);


-- =========================================================
-- 5. INDEXES FOR SOURCE CHECK RESULTS
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_source_check_results_source_id
ON source_check_results(source_id);

CREATE INDEX IF NOT EXISTS idx_source_check_results_check_status
ON source_check_results(check_status);

CREATE INDEX IF NOT EXISTS idx_source_check_results_checked_at
ON source_check_results(checked_at DESC);


-- =========================================================
-- 6. INDEXES FOR JOBS
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_jobs_source
ON jobs(source);

CREATE INDEX IF NOT EXISTS idx_jobs_title
ON jobs(title);

CREATE INDEX IF NOT EXISTS idx_jobs_company
ON jobs(company);

CREATE INDEX IF NOT EXISTS idx_jobs_location
ON jobs(location);

CREATE INDEX IF NOT EXISTS idx_jobs_status
ON jobs(status);

CREATE INDEX IF NOT EXISTS idx_jobs_remote
ON jobs(remote);

CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint
ON jobs(fingerprint);

CREATE INDEX IF NOT EXISTS idx_jobs_posted_date
ON jobs(posted_date DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_collected_at
ON jobs(collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_relevance_score
ON jobs(relevance_score DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_is_relevant
ON jobs(is_relevant);

CREATE INDEX IF NOT EXISTS idx_jobs_suitability_score
ON jobs(suitability_score DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_is_suitable
ON jobs(is_suitable);

CREATE INDEX IF NOT EXISTS idx_jobs_shortlist_status
ON jobs(shortlist_status);

CREATE TABLE IF NOT EXISTS jobs_raw (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    external_job_id VARCHAR(100),
    job_title TEXT,
    company_name TEXT,
    job_url TEXT UNIQUE,
    raw_payload JSONB NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs_normalized (
    id SERIAL PRIMARY KEY,
    raw_job_id INTEGER REFERENCES jobs_raw(id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,
    external_job_id VARCHAR(100),
    title TEXT NOT NULL,
    company_name TEXT,
    location TEXT,
    job_type TEXT,
    category TEXT,
    tags JSONB,
    salary TEXT,
    job_url TEXT UNIQUE NOT NULL,
    description TEXT,
    publication_date TIMESTAMP,
    normalized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(raw_job_id)
);

ALTER TABLE jobs_normalized
ADD COLUMN IF NOT EXISTS dedupe_key TEXT;

ALTER TABLE jobs_normalized
ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;

ALTER TABLE jobs_normalized
ADD COLUMN IF NOT EXISTS duplicate_of_job_id INTEGER;

ALTER TABLE jobs_normalized
ADD COLUMN IF NOT EXISTS dedupe_reason TEXT;

ALTER TABLE jobs_normalized
ADD COLUMN IF NOT EXISTS deduped_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_jobs_normalized_dedupe_key
ON jobs_normalized(dedupe_key);

CREATE TABLE IF NOT EXISTS job_scores (
    id SERIAL PRIMARY KEY,
    normalized_job_id INTEGER REFERENCES jobs_normalized(id) ON DELETE CASCADE,
    scoring_version VARCHAR(50) NOT NULL DEFAULT 'rule_v0.1',
    overall_score INTEGER NOT NULL,
    role_score INTEGER NOT NULL,
    skill_score INTEGER NOT NULL,
    experience_score INTEGER NOT NULL,
    location_score INTEGER NOT NULL,
    penalty_score INTEGER NOT NULL DEFAULT 0,
    matched_keywords JSONB,
    missing_keywords JSONB,
    red_flags JSONB,
    score_summary TEXT,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(normalized_job_id, scoring_version)
);

CREATE INDEX IF NOT EXISTS idx_job_scores_overall_score
ON job_scores(overall_score DESC);

CREATE INDEX IF NOT EXISTS idx_job_scores_normalized_job_id
ON job_scores(normalized_job_id);