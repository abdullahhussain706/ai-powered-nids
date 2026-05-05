import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from database.db_manager import DB_PATH, get_connection, init_db


BASE_DIR = Path(__file__).resolve().parent.parent
ALERT_LOG = BASE_DIR / "logs" / "alerts.jsonl"

SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class AlertManager:
    def __init__(self, db_path=DB_PATH, alert_log=ALERT_LOG, dedup_window_sec=300):
        self.db_path = db_path
        self.alert_log = Path(alert_log)
        self.dedup_window_sec = dedup_window_sec
        self.recent_alerts = {}

        self.alert_log.parent.mkdir(parents=True, exist_ok=True)
        init_db(self.db_path)

    def handle_alerts(self, alerts, source="signature"):
        saved = []

        for raw_alert in alerts:
            alert = self.normalize_alert(raw_alert, source)

            if self.is_duplicate(alert):
                self.update_duplicate(alert)
                continue

            self.remember(alert)
            self.save_alert(alert)
            saved.append(alert)

        if saved:
            logging.warning(f"🚨 New alerts saved: {len(saved)}")

        return saved

    def normalize_alert(self, alert, source):
        normalized = {
            "timestamp": utc_now(),
            "source": source,
            "rule_id": alert.get("rule_id"),
            "name": alert.get("name") or "Unknown Alert",
            "category": alert.get("category") or "Unknown",
            "severity": str(alert.get("severity") or "medium").lower(),
            "confidence": float(alert.get("confidence") or 0.0),
            "src_ip": alert.get("src_ip"),
            "dst_ip": alert.get("dst_ip"),
            "src_port": alert.get("src_port"),
            "dst_port": alert.get("dst_port"),
            "protocol": alert.get("protocol"),
            "flow_id": alert.get("flow_id"),
        }

        normalized["severity_score"] = SEVERITY_RANK.get(normalized["severity"], 2)
        normalized["alert_key"] = self.make_alert_key(normalized)
        return normalized

    def make_alert_key(self, alert):
        parts = [
            str(alert.get("rule_id")),
            str(alert.get("src_ip")),
            str(alert.get("dst_ip")),
            str(alert.get("dst_port")),
            str(alert.get("protocol")),
        ]
        raw_key = "|".join(parts)
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def is_duplicate(self, alert):
        previous = self.recent_alerts.get(alert["alert_key"])
        if not previous:
            return False

        age = datetime.fromisoformat(alert["timestamp"]) - datetime.fromisoformat(previous)
        return age.total_seconds() < self.dedup_window_sec

    def remember(self, alert):
        alert_time = alert["timestamp"]
        self.recent_alerts[alert["alert_key"]] = alert_time

        expired = []
        now = datetime.fromisoformat(alert_time)
        for key, seen_at in self.recent_alerts.items():
            age = now - datetime.fromisoformat(seen_at)
            if age.total_seconds() >= self.dedup_window_sec:
                expired.append(key)

        for key in expired:
            self.recent_alerts.pop(key, None)

    def save_alert(self, alert):
        self.write_jsonl(alert)
        self.insert_db(alert)

    def write_jsonl(self, alert):
        with self.alert_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(alert, sort_keys=True) + "\n")

    def insert_db(self, alert):
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO alerts (
                    alert_key, rule_id, name, category, severity, confidence,
                    src_ip, dst_ip, src_port, dst_port, protocol, flow_id,
                    status, first_seen, last_seen, duplicate_count, details_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["alert_key"],
                    alert["rule_id"],
                    alert["name"],
                    alert["category"],
                    alert["severity"],
                    alert["confidence"],
                    alert["src_ip"],
                    alert["dst_ip"],
                    alert["src_port"],
                    alert["dst_port"],
                    str(alert["protocol"]),
                    alert["flow_id"],
                    "new",
                    alert["timestamp"],
                    alert["timestamp"],
                    0,
                    json.dumps(alert, sort_keys=True),
                ),
            )
            conn.commit()

    def update_duplicate(self, alert):
        self.recent_alerts[alert["alert_key"]] = alert["timestamp"]

        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE alerts
                SET last_seen = ?,
                    duplicate_count = duplicate_count + 1
                WHERE id = (
                    SELECT id
                    FROM alerts
                    WHERE alert_key = ?
                    ORDER BY last_seen DESC
                    LIMIT 1
                )
                """,
                (alert["timestamp"], alert["alert_key"]),
            )
            conn.commit()

    def get_recent_alerts(self, limit=50):
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM alerts
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]


_DEFAULT_MANAGER = None


def get_alert_manager():
    global _DEFAULT_MANAGER

    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = AlertManager()

    return _DEFAULT_MANAGER


def handle_alerts(alerts, source="signature"):
    return get_alert_manager().handle_alerts(alerts, source=source)
