import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
DEFAULT_ALERT_LOG = BASE_DIR / "logs" / "alerts.jsonl"
DEFAULT_CAPTURE_LOG = BASE_DIR / "logs" / "capture.log"


def load_settings():
    if not SETTINGS_FILE.exists():
        return {}

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logging.warning(f"Scheduler failed to read settings: {e}")
        return {}


def resolve_path(path_value, default_path):
    path_text = str(path_value or "").strip()
    if not path_text:
        return Path(default_path)

    path = Path(path_text)
    return path if path.is_absolute() else BASE_DIR / path


def rotate_log_if_needed():
    settings = load_settings()
    if not settings.get("logging_enabled", True):
        return {"rotated": False, "reason": "logging disabled"}

    log_path = resolve_path(settings.get("log_file_path"), DEFAULT_ALERT_LOG)
    if not log_path.exists():
        return {"rotated": False, "reason": "log file missing"}

    max_size_mb = int(settings.get("max_log_size_mb") or 100)
    size_mb = log_path.stat().st_size / (1024 * 1024)
    if size_mb <= max_size_mb:
        return {"rotated": False, "size_mb": round(size_mb, 3)}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = log_path.with_suffix(f".{timestamp}{log_path.suffix}")
    log_path.rename(backup_path)
    log_path.touch()

    logging.info(f"Rotated log file: {backup_path}")
    return {
        "rotated": True,
        "backup_path": str(backup_path),
        "size_mb": round(size_mb, 3),
    }


def cleanup_old_logs():
    settings = load_settings()
    if not settings.get("auto_delete_logs", False):
        return {"deleted": 0, "reason": "auto delete disabled"}

    days = int(settings.get("delete_after_days") or 7)
    cutoff = datetime.now() - timedelta(days=days)
    log_path = resolve_path(settings.get("log_file_path"), DEFAULT_ALERT_LOG)
    log_dir = log_path.parent

    if not log_dir.exists():
        return {"deleted": 0, "reason": "log directory missing"}

    protected = {
        log_path.resolve(),
        DEFAULT_CAPTURE_LOG.resolve(),
    }
    deleted = 0

    for pattern in ("*.jsonl.*", "*.log.*"):
        for path in log_dir.glob(pattern):
            try:
                if path.resolve() in protected:
                    continue
                if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                    path.unlink()
                    deleted += 1
            except Exception as e:
                logging.warning(f"Failed to delete old log {path}: {e}")

    if deleted:
        logging.info(f"Deleted old log files: {deleted}")

    return {"deleted": deleted, "cutoff": cutoff.isoformat()}


def cleanup_old_alerts(db_path=None):
    from database.db_manager import DB_PATH, get_connection, init_db

    db_path = db_path or DB_PATH
    settings = load_settings()
    days = int(settings.get("alert_retention_days") or 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM alerts WHERE last_seen < ?",
            (cutoff_iso,),
        )
        conn.commit()
        deleted = cursor.rowcount if cursor.rowcount is not None else 0

    if deleted:
        logging.info(f"Deleted old alerts: {deleted}")

    return {"deleted": deleted, "cutoff": cutoff_iso}


def cleanup_pcap_files():
    from services.pcap_storage_service import cleanup_pcap_storage

    return cleanup_pcap_storage()


@dataclass
class ScheduledJob:
    name: str
    interval_seconds: int
    callback: Callable[[], object]
    run_on_start: bool = False
    last_run: Optional[float] = None
    last_result: Optional[object] = None
    last_error: Optional[str] = None
    run_count: int = 0
    next_run: float = field(default_factory=time.time)

    def due(self, now):
        return now >= self.next_run

    def run(self):
        self.last_run = time.time()
        self.last_error = None
        try:
            self.last_result = self.callback()
        except Exception as e:
            self.last_error = str(e)
            logging.exception(f"Scheduled job failed: {self.name}")
        finally:
            self.run_count += 1
            self.next_run = time.time() + self.interval_seconds

    def to_dict(self):
        return {
            "name": self.name,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }


class SchedulerService:
    def __init__(self, poll_seconds=1):
        self.poll_seconds = poll_seconds
        self.jobs = []
        self._stop_event = threading.Event()
        self._thread = None

    def add_job(self, name, interval_seconds, callback, run_on_start=False):
        job = ScheduledJob(
            name=name,
            interval_seconds=int(interval_seconds),
            callback=callback,
            run_on_start=run_on_start,
        )
        if not run_on_start:
            job.next_run = time.time() + job.interval_seconds
        self.jobs.append(job)
        return job

    def start(self):
        if self.is_running():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="SchedulerService",
            daemon=True,
        )
        self._thread.start()
        logging.info("Scheduler service started")

    def stop(self, timeout=5):
        if not self._thread:
            return

        self._stop_event.set()
        self._thread.join(timeout=timeout)
        logging.info("Scheduler service stopped")

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def run_pending(self):
        now = time.time()
        for job in self.jobs:
            if job.due(now):
                logging.info(f"Running scheduled job: {job.name}")
                job.run()

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.run_pending()
            self._stop_event.wait(self.poll_seconds)

    def status(self):
        return {
            "running": self.is_running(),
            "jobs": [job.to_dict() for job in self.jobs],
        }


def build_default_scheduler():
    scheduler = SchedulerService()
    scheduler.add_job(
        "rotate_alert_log",
        interval_seconds=15 * 60,
        callback=rotate_log_if_needed,
        run_on_start=False,
    )
    scheduler.add_job(
        "cleanup_old_logs",
        interval_seconds=60 * 60,
        callback=cleanup_old_logs,
        run_on_start=False,
    )
    scheduler.add_job(
        "cleanup_old_alerts",
        interval_seconds=6 * 60 * 60,
        callback=cleanup_old_alerts,
        run_on_start=False,
    )
    scheduler.add_job(
        "cleanup_pcap_files",
        interval_seconds=30 * 60,
        callback=cleanup_pcap_files,
        run_on_start=False,
    )
    return scheduler


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    scheduler = build_default_scheduler()
    scheduler.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nScheduler shutdown requested.")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
