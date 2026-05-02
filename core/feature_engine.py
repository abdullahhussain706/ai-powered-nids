# core/feature_extractor.py

import logging
from core.signature_engine import run_signature_engine   # 👈 only call


# =========================
# SAFE DIVISION
# =========================
def safe_div(a, b):
    return a / b if b != 0 else 0


# =========================
# FEATURE EXTRACTION
# =========================
def extract_features(flow):
    try:
        duration = flow.get("duration", 0)
        total_packets = flow.get("total_packets", 0)
        total_bytes = flow.get("total_bytes", 0)

        fwd_packets = flow.get("fwd_packets", 0)
        bwd_packets = flow.get("bwd_packets", 0)

        fwd_bytes = flow.get("fwd_bytes", 0)
        bwd_bytes = flow.get("bwd_bytes", 0)

        syn = flow.get("syn_count", 0)
        fin = flow.get("fin_count", 0)
        psh = flow.get("psh_count", 0)

        unique_ports = flow.get("unique_dst_ports", 0)

        # =========================
        # BASIC FEATURES
        # =========================
        packet_rate = safe_div(total_packets, duration)
        byte_rate = safe_div(total_bytes, duration)

        # =========================
        # RATIOS
        # =========================
        syn_ratio = safe_div(syn, total_packets)
        fin_ratio = safe_div(fin, total_packets)
        psh_ratio = safe_div(psh, total_packets)

        fwd_bwd_packet_ratio = safe_div(fwd_packets, bwd_packets)
        fwd_bwd_byte_ratio = safe_div(fwd_bytes, bwd_bytes)

        # =========================
        # FEATURE OBJECT
        # =========================
        features = {
            "flow_id": flow.get("flow_id"),
            "src_ip": flow.get("src_ip"),
            "dst_ip": flow.get("dst_ip"),
            "dst_port": flow.get("dst_port"),
            "protocol": flow.get("protocol"),

            "duration": duration,
            "total_packets": total_packets,
            "total_bytes": total_bytes,

            "packet_rate": packet_rate,
            "byte_rate": byte_rate,

            "syn_ratio": syn_ratio,
            "fin_ratio": fin_ratio,
            "psh_ratio": psh_ratio,

            "fwd_bwd_packet_ratio": fwd_bwd_packet_ratio,
            "fwd_bwd_byte_ratio": fwd_bwd_byte_ratio,

            "unique_dst_ports": unique_ports,

            # FLAGS
            "is_short_flow": duration < 5,
            "is_long_flow": duration > 60,
            "is_high_packet": total_packets > 100,
            "is_low_packet": total_packets < 5,
            "is_high_rate": packet_rate > 50,
            "is_high_byte_rate": byte_rate > 5000,
            "is_syn_heavy": syn_ratio > 0.5,
            "is_unidirectional": bwd_packets == 0 or fwd_packets == 0,
            "is_multi_port": unique_ports > 10
        }

        # =========================
        # 🔥 SIGNATURE ENGINE CALL
        # =========================
        alerts = run_signature_engine(features)

        return {
            "features": features,
            "alerts": alerts
        }

    except Exception as e:
        logging.error(f"❌ Feature extraction error: {e}")
        return None


# =========================
# BULK FEATURE EXTRACTION
# =========================
def extract_features_batch(flows):
    results = []

    for flow in flows:
        output = extract_features(flow)
        if output:
            results.append(output)

    logging.info(f"🧠 Processed flows: {len(results)}")
    return results