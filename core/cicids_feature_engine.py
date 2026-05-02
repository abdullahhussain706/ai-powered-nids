import numpy as np
import logging


# =========================
# SAFE DIV
# =========================
def safe_div(a, b):
    return a / b if b != 0 else 0.0


# =========================
# FLOW-BASED CICIDS FEATURES
# =========================
def extract_cicids_features(flow):
    try:
        duration = flow.get("duration", 0)

        fwd_packets = flow.get("fwd_packets", 0)
        bwd_packets = flow.get("bwd_packets", 0)

        fwd_bytes = flow.get("fwd_bytes", 0)
        bwd_bytes = flow.get("bwd_bytes", 0)

        total_packets = flow.get("packet_count", flow.get("total_packets", 0))
        total_bytes = flow.get("total_bytes", 0)

        syn = flow.get("syn_count", 0)
        fin = flow.get("fin_count", 0)
        psh = flow.get("psh_count", 0)

        # =========================
        # BASIC FLOW FEATURES
        # =========================
        flow_bytes_per_sec = safe_div(total_bytes, duration)
        flow_packets_per_sec = safe_div(total_packets, duration)

        # =========================
        # FORWARD / BACKWARD FEATURES
        # =========================
        fwd_pkt_ratio = safe_div(fwd_packets, total_packets)
        bwd_pkt_ratio = safe_div(bwd_packets, total_packets)

        fwd_byte_ratio = safe_div(fwd_bytes, total_bytes)
        bwd_byte_ratio = safe_div(bwd_bytes, total_bytes)

        # =========================
        # INTER-ARRIVAL (approx from duration)
        # =========================
        flow_iat_mean = safe_div(duration, total_packets)
        flow_iat_std = 0  # placeholder (needs packet timestamps history)

        # =========================
        # FLAG FEATURES
        # =========================
        syn_ratio = safe_div(syn, total_packets)
        fin_ratio = safe_div(fin, total_packets)
        psh_ratio = safe_div(psh, total_packets)

        # =========================
        # STRUCTURE FEATURES
        # =========================
        unique_dst_ports = flow.get("unique_dst_ports", 0)

        # =========================
        # FINAL FEATURE VECTOR (CICIDS STYLE)
        # =========================
        features = {
            # identity
            "flow_id": flow.get("flow_id"),
            "src_ip": flow.get("src_ip"),
            "dst_ip": flow.get("dst_ip"),
            "protocol": flow.get("protocol"),

            # time
            "flow_duration": duration,

            # volume
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "flow_packets_per_sec": flow_packets_per_sec,
            "flow_bytes_per_sec": flow_bytes_per_sec,

            # forward/backward
            "fwd_packets": fwd_packets,
            "bwd_packets": bwd_packets,
            "fwd_bytes": fwd_bytes,
            "bwd_bytes": bwd_bytes,
            "fwd_pkt_ratio": fwd_pkt_ratio,
            "bwd_pkt_ratio": bwd_pkt_ratio,
            "fwd_byte_ratio": fwd_byte_ratio,
            "bwd_byte_ratio": bwd_byte_ratio,

            # inter-arrival
            "flow_iat_mean": flow_iat_mean,
            "flow_iat_std": flow_iat_std,

            # tcp flags
            "syn_count": syn,
            "fin_count": fin,
            "psh_count": psh,
            "syn_ratio": syn_ratio,
            "fin_ratio": fin_ratio,
            "psh_ratio": psh_ratio,

            # structure
            "unique_dst_ports": unique_dst_ports,

            # behavioral flags (helpful for ML)
            "is_short_flow": duration < 5,
            "is_long_flow": duration > 60,
            "is_unidirectional": bwd_packets == 0,
            "is_high_rate": flow_packets_per_sec > 50,
        }

        return features

    except Exception as e:
        logging.error(f"CICIDS feature extraction error: {e}")
        return None


# =========================
# BATCH PROCESSING
# =========================
def extract_cicids_batch(flows):
    dataset = []

    for flow in flows:
        feat = extract_cicids_features(flow)
        if feat:
            dataset.append(feat)

    logging.info(f"🧠 CICIDS features generated: {len(dataset)}")
    return dataset