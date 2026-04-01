#!/usr/bin/env python3

import threading
import subprocess
import os
import time

# =========================
# Script Paths
# =========================
CAPTURE_SCRIPT = os.path.join("core", "packet_capture.py")
PARSER_SCRIPT = os.path.join("core", "packet_parser.py")

# =========================
# Function to run a script safely
# =========================
def run_script(script_path):
    try:
        subprocess.run(["python3", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_path}: {e}")

# =========================
# Main
# =========================
if __name__ == "__main__":
    print("==== AI Powered NIDS - Live IDS Pipeline ====\n")

    # Thread 1: Live Packet Capture
    capture_thread = threading.Thread(target=run_script, args=(CAPTURE_SCRIPT,), daemon=True)
    capture_thread.start()
    print("📥 Packet capture started...")

    # Thread 2: Continuous Stable Parsing
    parser_thread = threading.Thread(target=run_script, args=(PARSER_SCRIPT,), daemon=True)
    parser_thread.start()
    print("📊 Continuous parser started...\n")

    try:
        # Keep main thread alive while both threads run
        while True:
            time.sleep(1)  # just sleep, threads are daemon
    except KeyboardInterrupt:
        print("\n🛑 Stopping IDS pipeline... Please wait.")