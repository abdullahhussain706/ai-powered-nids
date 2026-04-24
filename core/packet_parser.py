import subprocess
import json
import os
import tempfile
from core.flow_builder import build_flows

print("🔥 PARSER CALLED")

def parse_pcap(pcap_file, run_flow_builder=True):
    """
    Stable packet parser using tshark fields mode
    No JSON dependency → avoids empty parsing issues
    """

    cmd = [
        "tshark",
        "-r", pcap_file,

        # --------- DIRECT FIELDS OUTPUT (IMPORTANT) ----------
        "-T", "fields",

        "-e", "frame.time_epoch",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "ipv6.src",
        "-e", "ipv6.dst",
        "-e", "ip.proto",
        "-e", "tcp.srcport",
        "-e", "tcp.dstport",
        "-e", "udp.srcport",
        "-e", "udp.dstport",
        "-e", "frame.len",

        "-E", "separator=|",
        "-E", "occurrence=f"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")

    except Exception as e:
        print("❌ tshark failed:", e)
        return []


    parsed_packets = []

    for line in lines:
        try:
            fields = line.split("|")

            if len(fields) < 6:
                continue

            # -------------------
            # Extract safely
            # -------------------
            timestamp = float(fields[0] or 0)

            src_ip = fields[1] or fields[3]  # ipv6 fallback
            dst_ip = fields[2] or fields[4]

            # ❌ skip non-IP packets
            if not src_ip or not dst_ip:
                continue

            protocol = int(fields[5] or 0)

            tcp_s = fields[6]
            tcp_d = fields[7]
            udp_s = fields[8]
            udp_d = fields[9]

            src_port = int(tcp_s or udp_s or 0)
            dst_port = int(tcp_d or udp_d or 0)

            length = int(fields[10] or 0)

            parsed_packets.append({
                "timestamp": timestamp,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "protocol": protocol,
                "length": length
            })

        except:
            continue

    print(f"📊 Parsed packets: {len(parsed_packets)}")

    # ============================
    # 🔥 SAFE FLOW PIPELINE ADDITION
    # ============================
    flows = []

    if run_flow_builder and parsed_packets:

        # 👉 TEMP FILE (safe handoff, avoids race condition)
        # tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")

        # json.dump(parsed_packets, tmp_file)
        # tmp_file.close()

        # print(f"📁 Packets saved for flow builder: {tmp_file.name}")

        print("⚙️ Running Flow Builder...")

        # flow builder reads file instead of shared memory
        flows = build_flows(parsed_packets)

        print(f"📊 Flows generated: {len(flows)}")

        # optional cleanup
        # os.remove(tmp_file.name)

    return parsed_packets, flows