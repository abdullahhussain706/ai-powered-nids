#!/usr/bin/env python3

import subprocess
import os
import time
from datetime import datetime

# ✅ FIX: add project root to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ now import works
from core.packet_parser import parse_pcap


INTERFACE = "wlp2s0"
PACKET_LIMIT = 500
OUTPUT_DIR = "data/raw_packets"
DELAY = 1


os.makedirs(OUTPUT_DIR, exist_ok=True)


def capture_packets():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pcap_file = os.path.join(OUTPUT_DIR, f"capture_{ts}.pcap")

    print(f"\n📥 Capturing {PACKET_LIMIT} packets → {pcap_file}")

    cmd = [
        "tshark",
        "-i", INTERFACE,
        "-c", str(PACKET_LIMIT),
        "-w", pcap_file
    ]

    subprocess.run(cmd, check=True)

    print(f"✅ Capture complete: {pcap_file}")
    return pcap_file


def main_loop():
    print("🚀 Starting Sequential Capture → Parse Pipeline")

    while True:
        try:
            # STEP 1: Capture
            pcap_file = capture_packets()

            # STEP 2: Parse (NO RACE CONDITION)
            packets = parse_pcap(pcap_file)

            print(f"📦 Parsed packets: {len(packets)}")
            print(f"File created: {pcap_file}")
            print(f"File size: {os.path.getsize(pcap_file)} bytes")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(DELAY)


if __name__ == "__main__":
    main_loop()