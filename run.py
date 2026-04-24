#!/usr/bin/env python3

import subprocess
import time
import os
import signal
import sys

# =========================
# Script Paths
# =========================
CAPTURE_SCRIPT = os.path.join("core", "packet_capture.py")
PARSER_SCRIPT  = os.path.join("core", "packet_parser.py")
FLOW_SCRIPT    = os.path.join("core", "flow_builder.py")

def start_process(script):
    return subprocess.Popen(["python3", script])

def stop_all(procs):
    print("\n🛑 Stopping IDS pipeline...")
    for name, proc in procs.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"   ✅ {name} stopped")
        except Exception as e:
            print(f"   ⚠️  {name} force kill: {e}")
            proc.kill()
    print("✅ All processes stopped cleanly.")

if __name__ == "__main__":
    print("==== AI Powered NIDS - Live IDS Pipeline ====\n")

    procs = {}

    try:
        procs["capture"] = start_process(CAPTURE_SCRIPT)
        print("📥 Packet capture started...")
        time.sleep(1)  # capture ko settle hone do

        # procs["parser"] = start_process(PARSER_SCRIPT)
        # print("📊 Parser started...")
        # time.sleep(1)

        # procs["flow_builder"] = start_process(FLOW_SCRIPT)
        # print("🔹 Flow builder started...\n")

        while True:
            # health check — agar koi crash kare to restart
            for name, proc in procs.items():
                if proc.poll() is not None:
                    print(f"⚠️  {name} crashed! Restarting...")
                    script_map = {
                        "capture"      : CAPTURE_SCRIPT,
                        "parser"       : PARSER_SCRIPT,
                        "flow_builder" : FLOW_SCRIPT,
                    }
                    procs[name] = start_process(script_map[name])

            time.sleep(2)

    except KeyboardInterrupt:
        stop_all(procs)
        sys.exit(0)