#!/usr/bin/env python3

import subprocess
import os

# =========================
# FILE PATHS (EDIT HERE)
# =========================
pcap_path = "/home/muhammad-abdullah/ai-powered-nids/data/raw_packets/capture_20260331_075941.pcap"
output_csv = "/home/muhammad-abdullah/ai-powered-nids/data/processed/packets_parsed.csv"

# Create output directory if not exists
os.makedirs(os.path.dirname(output_csv), exist_ok=True)

print(f"📥 Reading PCAP from: {pcap_path}")
print(f"📤 Saving CSV to: {output_csv}")

# =========================
# TSHARK COMMAND
# =========================
cmd = [
    "tshark",
    "-r", pcap_path,
    "-T", "fields",

    # Fields (customize later if needed)
    "-e", "frame.time",
    "-e", "ip.src",
    "-e", "ip.dst",
    "-e", "ip.proto",
    "-e", "tcp.srcport",
    "-e", "tcp.dstport",
    "-e", "udp.srcport",
    "-e", "udp.dstport",

    "-E", "header=y",
    "-E", "separator=,",
]

# =========================
# EXECUTE
# =========================
try:
    with open(output_csv, "w") as f:
        subprocess.run(cmd, stdout=f, check=True)

    print("\n✅ CSV file created successfully!")

except subprocess.CalledProcessError:
    print("\n❌ Error while converting PCAP to CSV")
    print("👉 Make sure tshark is installed and file path is correct")