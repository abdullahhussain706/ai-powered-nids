#!/usr/bin/env python3

import subprocess
import os
import time
import sys
import logging
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import tempfile

# =========================
# CONFIG & PATHS
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from utils.helpers import load_config
from services.pcap_storage_service import cleanup_pcap_storage, get_pcap_dir

capture_conf = load_config("capture_config.yaml")

INTERFACE = capture_conf.get("interface") or os.getenv("IDS_INTERFACE")
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
PACKET_LIMIT = int(capture_conf.get("packet_limit") or os.getenv("IDS_PACKET_LIMIT", 500))
CAPTURE_SECONDS = float(capture_conf.get("capture_seconds") or os.getenv("IDS_CAPTURE_SECONDS", 5.0))
OUTPUT_DIR = get_pcap_dir(capture_conf)
DELAY = float(capture_conf.get("delay") or os.getenv("IDS_DELAY", 1.0))
_timeout_conf = capture_conf.get("tshark_timeout")
TSHARK_TIMEOUT = int(_timeout_conf or os.getenv("IDS_TSHARK_TIMEOUT", max(20, int(CAPTURE_SECONDS) + 10)))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOGGING SETUP
# =========================
from utils.logger import setup_logger
setup_logger(default_file="logs/capture.log")

# =========================
# IMPORT PARSER & ALERTS
# =========================
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


def parse_interfaces():
    interfaces = []
    for line in get_interfaces().splitlines():
        if "." not in line:
            continue

        number, description = line.split(".", 1)
        interfaces.append((number.strip(), description.strip()))

    return interfaces


def load_runtime_settings():
    if not SETTINGS_FILE.exists():
        return {}

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logging.warning(f"Failed to read runtime settings: {e}")
        return {}


def _interface_label(interface):
    number, description = interface
    return f"{number}. {description}"


def _is_real_capture_interface(interface):
    _, description = interface
    desc = description.lower()
    unsupported = (
        "androiddump",
        "ciscodump",
        "randpkt",
        "sshdump",
        "udpdump",
        "wifidump",
        "etwdump",
        "sdjournal",
    )
    return not any(name in desc for name in unsupported)


def _match_configured_interface(selection, interfaces):
    selected = str(selection or "").strip()
    if not selected:
        return None

    if "." in selected:
        number = selected.split(".", 1)[0].strip()
        if number.isdigit():
            return number

    if selected.isdigit():
        return selected

    selected_lower = selected.lower()
    for number, description in interfaces:
        if selected_lower == description.lower():
            return number
        if selected_lower in description.lower():
            return number

    return selected


def resolve_capture_targets():
    settings = load_runtime_settings()
    interfaces = parse_interfaces()
    configured = INTERFACE or settings.get("capture_interface") or "All"
    configured_text = str(configured).strip()

    if configured_text.lower() == "all":
        targets = [
            number
            for number, description in interfaces
            if _is_real_capture_interface((number, description))
        ]
        if targets:
            labels = [
                _interface_label(item)
                for item in interfaces
                if item[0] in targets
            ]
            logging.info("Using all capture interfaces: " + ", ".join(labels))
            return targets, settings

        default_interface = get_default_interface()
        return ([default_interface] if default_interface else []), settings

    target = _match_configured_interface(configured_text, interfaces)
    if target:
        logging.info(f"Using configured capture interface: {configured_text} -> {target}")
        return [target], settings

    default_interface = get_default_interface()
    return ([default_interface] if default_interface else []), settings


def has_live_packets(interface, duration=2):
    with tempfile.TemporaryDirectory() as tmp_dir:
        probe_file = Path(tmp_dir) / "probe.pcap"
        cmd = [
            "tshark",
            "-i", interface,
            "-a", f"duration:{duration}",
            "-c", "1",
            "-w", str(probe_file),
        ]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=duration + 4,
            )
        except subprocess.TimeoutExpired:
            return False

        return probe_file.exists() and probe_file.stat().st_size > 464


def get_default_interface():
    """Pick an active physical tshark interface when IDS_INTERFACE is not configured."""
    interfaces = parse_interfaces()
    if not interfaces:
        return None

    def priority(item):
        _, description = item
        desc = description.lower()
        if "wi-fi" in desc or "wifi" in desc:
            return 0
        if "ethernet" in desc and "loopback" not in desc:
            return 1
        if "loopback" in desc or "etw" in desc or "local area connection*" in desc:
            return 3
        return 2

    for interface, description in sorted(interfaces, key=priority):
        logging.info(f"Probing interface {interface}: {description}")
        if has_live_packets(interface):
            logging.info(f"Selected active interface {interface}: {description}")
            return interface

    fallback, description = sorted(interfaces, key=priority)[0]
    logging.warning(
        f"No active interface detected during probe; falling back to {fallback}: {description}"
    )
    return fallback


def rotate_files():
    """Apply PCAP storage cleanup policy."""
    return cleanup_pcap_storage(OUTPUT_DIR)


def generate_filename():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return OUTPUT_DIR / f"capture_{ts}.pcap"


# =========================
# CAPTURE FUNCTION
# =========================
def capture_packets(interfaces, settings=None):
    settings = settings or {}
    interfaces = interfaces if isinstance(interfaces, list) else [interfaces]
    pcap_file = generate_filename()
    interface_label = ", ".join(str(interface) for interface in interfaces)
    logging.info(
        f"Capturing up to {PACKET_LIMIT} packets for {CAPTURE_SECONDS}s "
        f"on interface(s) {interface_label} -> {pcap_file}"
    )

    logging.info(f"📥 Capturing {PACKET_LIMIT} packets → {pcap_file}")

    cmd = ["tshark"]
    for interface in interfaces:
        cmd.extend(["-i", str(interface)])

    if not settings.get("promiscuous_mode", False):
        cmd.append("-p")

    bpf_filter = str(settings.get("bpf_filter") or "").strip()
    if bpf_filter:
        cmd.extend(["-f", bpf_filter])

    cmd.extend([
        "-c", str(PACKET_LIMIT),
        "-a", f"duration:{CAPTURE_SECONDS}",
        "-w", str(pcap_file),
    ])

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

    capture_targets, settings = resolve_capture_targets()
    last_target_key = tuple(capture_targets)
    if not capture_targets:
        logging.error("❌ No capture interface found. Set IDS_INTERFACE manually.")
        sys.exit(1)

    logging.info(f"🔌 Using interface(s): {', '.join(capture_targets)}")

    iteration = 0

    while True:
        start_time = time.time()

        try:
            capture_targets, settings = resolve_capture_targets()
            target_key = tuple(capture_targets)
            if target_key != last_target_key:
                logging.info(f"Capture interface selection changed: {', '.join(capture_targets)}")
                last_target_key = target_key

            if not capture_targets:
                logging.error("No capture interface available for current settings.")
                time.sleep(DELAY)
                continue

            # STEP 1: Capture
            pcap_file = capture_packets(capture_targets, settings=settings)
            if not pcap_file:
                logging.info(
                    "Packets: 0 | Flows: 0 | Feature Records: 0 | Alerts: 0 | New Alerts: 0"
                )
                continue

            # STEP 2: Parse
            packets, flows, feature_results = parse_pcap(str(pcap_file))

            alerts_by_source = defaultdict(list)
            for result in feature_results:
                source = result.get("source", "signature")
                for alert in result.get("alerts", []):
                    alerts_by_source[source].append(alert)

            saved_alerts = []
            alert_count = 0
            for source, source_alerts in alerts_by_source.items():
                alert_count += len(source_alerts)
                saved_alerts.extend(handle_alerts(source_alerts, source=source))

            logging.info(
                f"📊 Packets: {len(packets)} | Flows: {len(flows)} | "
                f"Feature Records: {len(feature_results)} | "
                f"Alerts: {alert_count} | New Alerts: {len(saved_alerts)}"
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
