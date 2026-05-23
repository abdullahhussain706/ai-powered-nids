import logging
import statistics


TRAINING_FEATURES = [
    "duration",
    "total_packets",
    "total_bytes",
    "flow_packets_per_sec",
    "flow_bytes_per_sec",
    "fwd_packets",
    "bwd_packets",
    "fwd_bytes",
    "bwd_bytes",
    "fwd_pkt_ratio",
    "bwd_pkt_ratio",
    "fwd_byte_ratio",
    "bwd_byte_ratio",
    "syn_count",
    "fin_count",
    "psh_count",
    "ack_count",
    "rst_count",
    "syn_ratio",
    "fin_ratio",
    "psh_ratio",
    "syn_per_packet",
    "avg_packet_size",
    "max_packet_size",
    "min_packet_size",
    "packet_size_variance",
    "burst_rate",
    "is_idle_flow",
    "is_short_flow",
    "is_long_flow",
    "is_unidirectional",
    "is_high_rate",
    "is_tcp",
    "is_udp",
    "is_icmp",
]


IDENTITY_FEATURES = [
    "flow_id",
    "src_ip",
    "dst_ip",
    "protocol",
]


def safe_div(a, b):
    return a / b if b != 0 else 0.0


def _packet_sizes(flow, total_bytes, total_packets):
    sizes = flow.get("packet_sizes") or []
    sizes = [size for size in sizes if isinstance(size, (int, float))]

    if sizes:
        return sizes
    if total_packets > 0:
        return [safe_div(total_bytes, total_packets)] * total_packets
    return [0]


def extract_cicids_features(flow, include_identity=False):
    try:
        duration = flow.get("duration", 0)
        duration_for_rate = duration if duration > 0 else 0.001

        fwd_packets = flow.get("fwd_packets", 0)
        bwd_packets = flow.get("bwd_packets", 0)

        fwd_bytes = flow.get("fwd_bytes", 0)
        bwd_bytes = flow.get("bwd_bytes", 0)

        total_packets = flow.get("total_packets", flow.get("packet_count", 0))
        total_bytes = flow.get("total_bytes", fwd_bytes + bwd_bytes)

        syn = flow.get("syn_count", 0)
        fin = flow.get("fin_count", 0)
        psh = flow.get("psh_count", 0)
        ack = flow.get("ack_count", 0)
        rst = flow.get("rst_count", 0)

        packet_sizes = _packet_sizes(flow, total_bytes, total_packets)

        flow_packets_per_sec = safe_div(total_packets, duration_for_rate)
        flow_bytes_per_sec = safe_div(total_bytes, duration_for_rate)

        fwd_pkt_ratio = safe_div(fwd_packets, total_packets)
        bwd_pkt_ratio = safe_div(bwd_packets, total_packets)
        fwd_byte_ratio = safe_div(fwd_bytes, total_bytes)
        bwd_byte_ratio = safe_div(bwd_bytes, total_bytes)

        syn_ratio = safe_div(syn, total_packets)
        fin_ratio = safe_div(fin, total_packets)
        psh_ratio = safe_div(psh, total_packets)
        syn_per_packet = safe_div(syn, total_packets)

        avg_packet_size = safe_div(total_bytes, total_packets)
        max_packet_size = max(packet_sizes)
        min_packet_size = min(packet_sizes)
        packet_size_variance = (
            statistics.variance(packet_sizes) if len(packet_sizes) > 1 else 0
        )

        burst_rate = flow_packets_per_sec * duration
        protocol = str(flow.get("protocol", "")).upper()

        features = {
            "duration": duration,
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "flow_packets_per_sec": flow_packets_per_sec,
            "flow_bytes_per_sec": flow_bytes_per_sec,
            "fwd_packets": fwd_packets,
            "bwd_packets": bwd_packets,
            "fwd_bytes": fwd_bytes,
            "bwd_bytes": bwd_bytes,
            "fwd_pkt_ratio": fwd_pkt_ratio,
            "bwd_pkt_ratio": bwd_pkt_ratio,
            "fwd_byte_ratio": fwd_byte_ratio,
            "bwd_byte_ratio": bwd_byte_ratio,
            "syn_count": syn,
            "fin_count": fin,
            "psh_count": psh,
            "ack_count": ack,
            "rst_count": rst,
            "syn_ratio": syn_ratio,
            "fin_ratio": fin_ratio,
            "psh_ratio": psh_ratio,
            "syn_per_packet": syn_per_packet,
            "avg_packet_size": avg_packet_size,
            "max_packet_size": max_packet_size,
            "min_packet_size": min_packet_size,
            "packet_size_variance": packet_size_variance,
            "burst_rate": burst_rate,
            "is_idle_flow": flow_packets_per_sec < 1,
            "is_short_flow": duration < 5,
            "is_long_flow": duration > 60,
            "is_unidirectional": bwd_packets == 0,
            "is_high_rate": flow_packets_per_sec > 50,
            "is_tcp": protocol == "TCP",
            "is_udp": protocol == "UDP",
            "is_icmp": protocol == "ICMP",
        }

        if include_identity:
            return {
                "flow_id": flow.get("flow_id"),
                "src_ip": flow.get("src_ip"),
                "dst_ip": flow.get("dst_ip"),
                "protocol": protocol,
                **features,
            }

        return features

    except Exception as e:
        logging.error(f"CICIDS feature extraction error: {e}")
        return None


def extract_features(flow):
    return extract_cicids_features(flow)


def extract_training_features(flow):
    return extract_cicids_features(flow, include_identity=False)


def extract_cicids_batch(flows, include_identity=False):
    dataset = []

    for flow in flows:
        feat = extract_cicids_features(flow, include_identity=include_identity)
        if feat:
            dataset.append(feat)

    logging.info(f"CICIDS features generated: {len(dataset)}")
    return dataset


def batch_extract(flows):
    return extract_cicids_batch(flows)
