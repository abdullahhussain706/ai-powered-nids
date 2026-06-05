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
def parse_pcap(
    pcap_file,
    run_flow_builder=True,
    run_feature_engine=True,
    run_ml_engine=True,
    run_anomaly_detection=True,
):

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
    feature_results = []
    if run_feature_engine and flows:
        from core.feature_engine import extract_features_batch
        signature_results = extract_features_batch(flows)
        features = signature_results
        for result in signature_results:
            result["source"] = "signature"
        feature_results.extend(signature_results)
        logging.info(f"🧠 Features: {len(features)}")

    if run_ml_engine and flows:
        try:
            from ml.model_pipeline import run_stage_pipeline
            ml_results = run_stage_pipeline(flows)
            feature_results.extend(ml_results)
            logging.info(f"ML feature results: {len(ml_results)}")
        except Exception as e:
            logging.error(f"ML engine unavailable: {e}")

    if run_anomaly_detection and flows:
        try:
            from core.anomaly_engine import run_anomaly_engine
            anomaly_results = run_anomaly_engine(flows)
            feature_results.extend(anomaly_results)
            logging.info(f"Anomaly feature results: {len(anomaly_results)}")
        except Exception as e:
            logging.error(f"Anomaly engine unavailable: {e}")

    if feature_results:
        from core.fusion_engine import build_hybrid_results
        feature_results = build_hybrid_results(feature_results)

    return packets, flows, feature_results
