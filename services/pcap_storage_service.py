import logging
import time
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PCAP_DIR = BASE_DIR / "data" / "raw_packets"


@dataclass
class PcapStoragePolicy:
    max_files: int = 50
    max_total_mb: int = 1024
    retention_days: int = 7
    keep_empty_files: bool = False


def _capture_config():
    try:
        from utils.helpers import load_config

        return load_config("capture_config.yaml")
    except Exception:
        return {}


def get_pcap_dir(config=None):
    config = config or _capture_config()
    raw_path = config.get("pcap_dir") or config.get("output_dir") or "data/raw_packets"
    path = Path(raw_path)
    return path if path.is_absolute() else BASE_DIR / path


def get_storage_policy(config=None):
    config = config or _capture_config()
    return PcapStoragePolicy(
        max_files=int(config.get("max_files", 50)),
        max_total_mb=int(config.get("max_total_mb", 1024)),
        retention_days=int(config.get("retention_days", 7)),
        keep_empty_files=bool(config.get("keep_empty_files", False)),
    )


def pcap_stats(pcap_dir=None):
    pcap_dir = Path(pcap_dir or get_pcap_dir())
    files = sorted(pcap_dir.glob("*.pcap"), key=lambda path: path.stat().st_mtime)
    total_bytes = sum(path.stat().st_size for path in files)
    return {
        "directory": str(pcap_dir),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 3),
        "oldest_file": str(files[0]) if files else None,
        "newest_file": str(files[-1]) if files else None,
    }


def _delete_file(path):
    try:
        size = path.stat().st_size
        path.unlink()
        return True, size, None
    except Exception as e:
        return False, 0, str(e)


def cleanup_pcap_storage(pcap_dir=None, policy=None):
    pcap_dir = Path(pcap_dir or get_pcap_dir())
    policy = policy or get_storage_policy()
    pcap_dir.mkdir(parents=True, exist_ok=True)

    deleted = []
    errors = []
    now = time.time()
    max_age_seconds = max(0, policy.retention_days) * 24 * 60 * 60

    files = sorted(pcap_dir.glob("*.pcap"), key=lambda path: path.stat().st_mtime)

    for path in list(files):
        try:
            age_expired = max_age_seconds > 0 and (now - path.stat().st_mtime) > max_age_seconds
            empty_expired = not policy.keep_empty_files and path.stat().st_size == 0
            if age_expired or empty_expired:
                ok, size, error = _delete_file(path)
                if ok:
                    deleted.append({"path": str(path), "bytes": size, "reason": "age_or_empty"})
                    files.remove(path)
                else:
                    errors.append({"path": str(path), "error": error})
        except Exception as e:
            errors.append({"path": str(path), "error": str(e)})

    if policy.max_files > 0 and len(files) > policy.max_files:
        overflow = len(files) - policy.max_files
        for path in files[:overflow]:
            ok, size, error = _delete_file(path)
            if ok:
                deleted.append({"path": str(path), "bytes": size, "reason": "max_files"})
            else:
                errors.append({"path": str(path), "error": error})

    files = sorted(pcap_dir.glob("*.pcap"), key=lambda path: path.stat().st_mtime)
    max_total_bytes = max(0, policy.max_total_mb) * 1024 * 1024
    total_bytes = sum(path.stat().st_size for path in files)

    if max_total_bytes > 0:
        for path in files:
            if total_bytes <= max_total_bytes:
                break
            ok, size, error = _delete_file(path)
            if ok:
                total_bytes -= size
                deleted.append({"path": str(path), "bytes": size, "reason": "max_total_mb"})
            else:
                errors.append({"path": str(path), "error": error})

    result = {
        "deleted_count": len(deleted),
        "deleted_bytes": sum(item["bytes"] for item in deleted),
        "deleted": deleted,
        "errors": errors,
        "stats": pcap_stats(pcap_dir),
    }

    if deleted:
        logging.info(
            f"PCAP cleanup deleted {result['deleted_count']} file(s), "
            f"{result['deleted_bytes']} bytes"
        )
    if errors:
        logging.warning(f"PCAP cleanup errors: {len(errors)}")

    return result


def delete_all_pcaps(pcap_dir=None):
    pcap_dir = Path(pcap_dir or get_pcap_dir())
    pcap_dir.mkdir(parents=True, exist_ok=True)

    deleted = 0
    errors = []
    for path in pcap_dir.glob("*.pcap"):
        ok, _, error = _delete_file(path)
        if ok:
            deleted += 1
        else:
            errors.append({"path": str(path), "error": error})

    return {
        "deleted_count": deleted,
        "errors": errors,
        "stats": pcap_stats(pcap_dir),
    }
