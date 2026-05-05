CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_key TEXT NOT NULL,
    rule_id INTEGER,
    name TEXT,
    category TEXT,
    severity TEXT,
    confidence REAL,
    src_ip TEXT,
    dst_ip TEXT,
    src_port INTEGER,
    dst_port INTEGER,
    protocol TEXT,
    flow_id TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    details_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_key ON alerts(alert_key);
CREATE INDEX IF NOT EXISTS idx_alerts_last_seen ON alerts(last_seen);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
