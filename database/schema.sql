CREATE TABLE IF NOT EXISTS job_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,
    target_role VARCHAR(100),
    status VARCHAR(50) DEFAULT 'not_tested',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_check_results (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES job_sources(id) ON DELETE CASCADE,
    check_status VARCHAR(50) NOT NULL,
    http_status_code INTEGER,
    error_message TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);