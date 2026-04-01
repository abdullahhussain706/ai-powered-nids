#!/usr/bin/env python3

import os
import time
import subprocess
from datetime import datetime

# -----------------------
RAW_DIR = "/home/muhammad-abdullah/ai-powered-nids/data/raw_packets"
OUTPUT_DIR = "/home/muhammad-abdullah/ai-powered-nids/data/datasets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Keep track of already processed files
processed_files = set()

print("==== Continuous PCAP Parser Started ====")
print(f"Watching directory: {RAW_DIR}")

def is_file_stable(file_path, wait_time=2):
    """Check if file size is stable for wait_time seconds"""
    initial_size = os.path.getsize(file_path)
    time.sleep(wait_time)
    final_size = os.path.getsize(file_path)
    return initial_size == final_size

try:
    while True:
        files = sorted(os.listdir(RAW_DIR))
        for file in files:
            if file.endswith(".pcap") and file not in processed_files:
                pcap_path = os.path.join(RAW_DIR, file)

                if not is_file_stable(pcap_path):
                    continue  # skip for now, check next loop

                csv_name = file.replace(".pcap", ".csv")
                csv_path = os.path.join(OUTPUT_DIR, csv_name)

                print(f"📥 Parsing: {pcap_path} → {csv_path}")

                cmd = [
                    "tshark",
                    "-r", pcap_path,
                    "-T", "fields",
                    "-e", "frame.time",
                    "-e", "ip.src",
                    "-e", "ip.dst",
                    "-e", "ip.proto",
                    "-e", "tcp.srcport",
                    "-e", "tcp.dstport",
                    "-e", "udp.srcport",
                    "-e", "udp.dstport",
                    "-E", "header=y",
                    "-E", "separator=,"
                ]

                try:
                    with open(csv_path, "w") as f:
                        subprocess.run(cmd, stdout=f, check=True)
                    print(f"✅ Parsed CSV saved: {csv_path}\n")
                    processed_files.add(file)
                except subprocess.CalledProcessError:
                    print(f"❌ Error parsing {pcap_path}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Continuous parser stopped by user.")