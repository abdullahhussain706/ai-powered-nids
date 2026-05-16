#!/usr/bin/env python3

import subprocess
import os
import time
import sys
import logging
from datetime import datetime
from pathlib import Path

# =========================
# CONFIG
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
INTERFACE = os.getenv("IDS_INTERFACE")
PACKET_LIMIT = int(os.getenv("IDS_PACKET_LIMIT", 500))
OUTPUT_DIR = BASE_DIR / "data" / "raw_packets"
DELAY = float(os.getenv("IDS_DELAY", 1))
MAX_FILES = int(os.getenv("IDS_MAX_FILES", 50))
TSHARK_TIMEOUT = int(os.getenv("IDS_TSHARK_TIMEOUT", 120))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOGGING SETUP
# =========================
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "capture.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

# =========================
# IMPORT PARSER
# =========================
sys.path.append(str(BASE_DIR))
from core.packet_parser import parse_pcap
from core.alert_manager import handle_alerts


# =========================
# HELPERS
# =========================
def check_tshark():
    """Ensure tshark exists"""
    try:
        subprocess.run(["tshark", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        logging.error("❌ tshark not installed!")
        sys.exit(1)


def get_interfaces():
    """List available interfaces"""
    result = subprocess.run(["tshark", "-D"], capture_output=True, text=True)
    return result.stdout


def get_default_interface():
    """Pick the first tshark interface when IDS_INTERFACE is not configured."""
    for line in get_interfaces().splitlines():
        if "." not in line:
            continue
        return line.split(".", 1)[0].strip()
    return None


def rotate_files():
    """Delete old pcaps if limit exceeded"""
    files = sorted(OUTPUT_DIR.glob("*.pcap"), key=lambda path: path.stat().st_mtime)

    if len(files) > MAX_FILES:
        for f in files[:len(files) - MAX_FILES]:
            try:
                f.unlink()
                logging.info(f"🗑️ Deleted old file: {f}")
            except Exception as e:
                logging.warning(f"Failed to delete {f}: {e}")


def generate_filename():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return OUTPUT_DIR / f"capture_{ts}.pcap"


# =========================
# CAPTURE FUNCTION
# =========================
def capture_packets(interface):
    pcap_file = generate_filename()

    logging.info(f"📥 Capturing {PACKET_LIMIT} packets → {pcap_file}")

    cmd = [
        "tshark",
        "-i", interface,
        "-c", str(PACKET_LIMIT),
        "-w", str(pcap_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TSHARK_TIMEOUT
        )

        if result.returncode != 0:
            logging.error(f"❌ tshark error:\n{result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logging.error("⏳ tshark timeout — killing process")
        return None

    if not pcap_file.exists() or pcap_file.stat().st_size == 0:
        logging.warning("⚠️ Empty capture file")
        return None

    logging.info(f"✅ Capture complete: {pcap_file} ({pcap_file.stat().st_size} bytes)")
    return pcap_file


# =========================
# MAIN LOOP
# =========================
def main_loop():
    logging.info("🚀 Starting IDS Capture Pipeline")

    check_tshark()

    interface = INTERFACE or get_default_interface()
    if not interface:
        logging.error("❌ No capture interface found. Set IDS_INTERFACE manually.")
        sys.exit(1)

    logging.info(f"🔌 Using interface: {interface}")

    iteration = 0

    while True:
        start_time = time.time()

        try:
            # STEP 1: Capture
            pcap_file = capture_packets(interface)
            if not pcap_file:
                continue

            # STEP 2: Parse
            packets, flows, feature_results = parse_pcap(str(pcap_file))
            alerts = [
                alert
                for result in feature_results
                for alert in result.get("alerts", [])
            ]
            saved_alerts = handle_alerts(alerts, source="signature")

            logging.info(
                f"📊 Packets: {len(packets)} | Flows: {len(flows)} | "
                f"Feature Records: {len(feature_results)} | "
                f"Alerts: {len(alerts)} | New Alerts: {len(saved_alerts)}"
            )

            # STEP 3: Rotate old files
            rotate_files()

        except Exception as e:
            logging.exception(f"❌ Unexpected error: {e}")

        # smart delay (keeps consistent interval)
        elapsed = time.time() - start_time
        sleep_time = max(0, DELAY - elapsed)
        time.sleep(sleep_time)

        iteration += 1


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    main_loop()
