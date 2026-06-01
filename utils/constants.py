"""Common constants for the AI‑Hybrid NIDS project.

All modules should import values from this file instead of hard‑coding
paths, timeouts or other magic numbers.  Keeping them in a single place
ensures consistency and makes future adjustments straightforward.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project layout
# ---------------------------------------------------------------------------
# Base directory of the repository (resolved at import time).  ``Path`` is
# used so the constants work on both Windows and POSIX platforms.
BASE_DIR: Path = Path(__file__).resolve().parents[1]

# Directory where log files are stored.  The directory is created on import
# to guarantee that any logger that references ``LOG_DIR`` can write files
# without additional checks.
LOG_DIR: Path = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Default runtime parameters
# ---------------------------------------------------------------------------
# Timeout (seconds) for external commands such as ``tshark``.  This value is
# used by ``core.packet_capture`` and can be overridden via the
# ``IDS_TSHARK_TIMEOUT`` environment variable.
DEFAULT_TIMEOUT: int = 30

# Default number of packets to capture when the ``IDS_INTERFACE`` environment
# variable is not set.
DEFAULT_PACKET_LIMIT: int = 500

# Default capture duration (seconds) when not overridden by configuration.
DEFAULT_CAPTURE_SECONDS: int = 5

# Default delay (seconds) between successive capture iterations.
DEFAULT_DELAY: int = 1

# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
# Name of the SQLite database file used by ``database/db_manager.py``.
DB_FILE: Path = BASE_DIR / "database" / "ids.db"

