#!/usr/bin/env python3

import subprocess
import os
from datetime import datetime


OUTPUT_DIR = "/home/muhammad-abdullah/ai-powered-nids/data/raw_packets"
PACKET_COUNT = 500



# FUNCTIONS

def list_interfaces():
    """Show available network interfaces"""
    print("\nAvailable Interfaces:\n")
    subprocess.run(["tshark", "-D"])


def get_interface():
    """Ask user to select interface"""
    interface = input("\nEnter interface (e.g. wlp2s0): ").strip()
    return interface


def create_output_file():
    """Generate timestamped pcap file path"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"capture_{ts}.pcap")


def capture_packets(interface, output_file):
    """Run tshark capture"""
    cmd = [
        "tshark",
        "-i", interface,
        "-c", str(PACKET_COUNT),
        "-w", output_file
    ]

    print("\nStarting packet capture...\n")

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ Packets saved to: {output_file}")

    except subprocess.CalledProcessError:
        print("\n❌ Error capturing packets!")
        print("👉 Make sure to run with sudo:")
        print("   sudo python3 packet_capture.py")


# =========================
# MAIN
# =========================

def main():
    print("==== AI Powered NIDS - Packet Capture ====")

    list_interfaces()
    interface = get_interface()

    if not interface:
        print("❌ No interface provided. Exiting.")
        return

    output_file = create_output_file()
    capture_packets(interface, output_file)


if __name__ == "__main__":
    main()