import subprocess
import logging

# =========================
# CONFIG
# =========================
TSHARK_FIELDS = [
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "ipv6.src",
    "ipv6.dst",
    "ip.proto",
    "tcp.srcport",
    "tcp.dstport",
    "udp.srcport",
    "udp.dstport",
    "frame.len",
    "tcp.flags"
]


# =========================
# SAFE CONVERTERS
# =========================
def to_int(val, default=0):
    try:
        return int(val)
    except:
        return default


def to_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default


# =========================
# PARSE SINGLE LINE
# =========================
def parse_line(line):
    parts = line.strip().split("|")

    if len(parts) < len(TSHARK_FIELDS):
        return None

    try:
        timestamp = to_float(parts[0])

        src_ip = parts[1] or parts[3]
        dst_ip = parts[2] or parts[4]

        if not src_ip or not dst_ip:
            return None

        protocol = to_int(parts[5])

        tcp_s, tcp_d = parts[6], parts[7]
        udp_s, udp_d = parts[8], parts[9]

        src_port = to_int(tcp_s or udp_s)
        dst_port = to_int(tcp_d or udp_d)

        length = to_int(parts[10])
        tcp_flags = parts[11] if parts[11] else ""

        return {
            "timestamp": timestamp,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": protocol,
            "length": length,
            "tcp_flags": tcp_flags
        }

    except Exception as e:
        logging.debug(f"Parse error: {e}")
        return None


# =========================
# MAIN PIPELINE
# =========================
def parse_pcap(pcap_file, run_flow_builder=True, run_feature_engine=True):

    cmd = [
        "tshark",
        "-r", pcap_file,
        "-T", "fields",
        "-E", "separator=|",
        "-E", "occurrence=f",
        "-n"
    ]

    for field in TSHARK_FIELDS:
        cmd.extend(["-e", field])

    packets = []

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # =========================
        # STREAM PARSING
        # =========================
        for line in process.stdout:
            pkt = parse_line(line)
            if pkt:
                packets.append(pkt)

        process.wait()

        if process.returncode != 0:
            err = process.stderr.read()
            logging.error(f"tshark error: {err}")

    except Exception as e:
        logging.error(f"Parser failed: {e}")
        return [], [], []

    logging.info(f"📊 Parsed packets: {len(packets)}")

    # =========================
    # FLOW BUILDER
    # =========================
    flows = []
    if run_flow_builder and packets:
        from core.flow_builder import build_flows
        flows = build_flows(packets)
        logging.info(f"📊 Flows: {len(flows)}")

    # =========================
    # FEATURE ENGINE
    # =========================
    features = []
    if run_feature_engine and flows:
        from core.feature_engine import extract_features_batch
        features = extract_features_batch(flows)
        logging.info(f"🧠 Features: {len(features)}")

    return packets, flows, features
