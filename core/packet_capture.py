#!/usr/bin/env python3

import subprocess
import os
from datetime import datetime
import time

INTERFACE = "wlp2s0"  # change if needed
PACKET_LIMIT = 500     # packets per file
OUTPUT_DIR = "/home/muhammad-abdullah/ai-powered-nids/data/raw_packets"
PACKET_COUNT = 500

# Optional: time delay between captures (seconds)
DELAY_BETWEEN_CAPTURES = 1  

print("==== AI Powered NIDS - Live Packet Capture ====")
print(f"Interface: {INTERFACE}")
print(f"Packets per file: {PACKET_LIMIT}")
print(f"Output directory: {OUTPUT_DIR}\n")

# LIVE CAPTURE LOOP
# =========================
try:
    while True:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pcap_file = os.path.join(OUTPUT_DIR, f"capture_{ts}.pcap")

        print(f"📥 Capturing {PACKET_LIMIT} packets → {pcap_file}")

        cmd = [
            "tshark",
            "-i", INTERFACE,
            "-c", str(PACKET_LIMIT),
            "-w", pcap_file
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Saved packets to: {pcap_file}\n")
        except subprocess.CalledProcessError:
            print("❌ Error capturing packets. Make sure tshark is installed and permissions are correct.\n")

        # small delay to avoid tight loop
        time.sleep(DELAY_BETWEEN_CAPTURES)

except KeyboardInterrupt:
    print("\n🛑 Live capture stopped by user.")