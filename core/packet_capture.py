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
INTERFACE = os.getenv("IDS_INTERFACE", "wlp2s0")
PACKET_LIMIT = int(os.getenv("IDS_PACKET_LIMIT", 500))
OUTPUT_DIR = Path("data/raw_packets")
DELAY = float(os.getenv("IDS_DELAY", 1))
MAX_FILES = int(os.getenv("IDS_MAX_FILES", 50))
TSHARK_TIMEOUT = int(os.getenv("IDS_TSHARK_TIMEOUT", 120))

# =========================
# LOGGING SETUP
# =========================
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.packet_parser import parse_pcap


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


def rotate_files():
    """Delete old pcaps if limit exceeded"""
    files = sorted(OUTPUT_DIR.glob("*.pcap"), key=os.path.getmtime)

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
def capture_packets():
    pcap_file = generate_filename()

    logging.info(f"📥 Capturing {PACKET_LIMIT} packets → {pcap_file}")

    cmd = [
        "tshark",
        "-i", INTERFACE,
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logging.info(f"🔌 Using interface: {INTERFACE}")

    iteration = 0

    while True:
        start_time = time.time()

        try:
            # STEP 1: Capture
            pcap_file = capture_packets()
            if not pcap_file:
                continue

            # STEP 2: Parse
            packets, flows, alerts = parse_pcap(str(pcap_file))

            logging.info(f"📊 Packets: {len(packets)} | Flows: {len(flows)} | Alerts: {len(alerts)}")

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