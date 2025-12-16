CREATE TABLE IF NOT EXISTS short_urls (
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    user_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicks INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ip_stats (
    id SERIAL PRIMARY KEY,
    short_url_id INTEGER NOT NULL REFERENCES short_urls(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,
    click_date DATE NOT NULL,
    click_count INTEGER DEFAULT 1,
    UNIQUE (short_url_id, ip_address, click_date)
);
