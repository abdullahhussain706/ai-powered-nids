from collections import defaultdict

FLOW_TIMEOUT = 30  # seconds


class Flow:
    def __init__(self, key, pkt):
        self.key = key

        self.start_time = pkt.get("timestamp", 0)
        self.last_seen = pkt.get("timestamp", 0)

        self.packet_count = 1
        self.total_bytes = pkt.get("length", 0)

        # 🔥 optional ML-ready stats (future use)
        self.src_ip = pkt.get("src_ip")
        self.dst_ip = pkt.get("dst_ip")
        self.protocol = pkt.get("protocol")

    def update(self, pkt):
        self.last_seen = pkt.get("timestamp", self.last_seen)
        self.packet_count += 1
        self.total_bytes += pkt.get("length", 0)

    def duration(self):
        return max(0, self.last_seen - self.start_time)

    def to_dict(self):
        return {
            "flow_id": self.key,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "protocol": self.protocol,

            "packet_count": self.packet_count,
            "total_bytes": self.total_bytes,

            "start_time": self.start_time,
            "end_time": self.last_seen,
            "duration": self.duration()
        }


def get_flow_key(pkt):
    """
    Bidirectional flow key (stable for ML + IDS)
    """
    ip_pair = sorted([pkt.get("src_ip", ""), pkt.get("dst_ip", "")])
    port_pair = sorted([pkt.get("src_port", 0), pkt.get("dst_port", 0)])

    return f"{ip_pair[0]}-{ip_pair[1]}-{port_pair[0]}-{port_pair[1]}-{pkt.get('protocol', 0)}"


def build_flows(packets, flush_all=True):
    flows = {}
    completed_flows = []

    if not packets:
        return []

    for pkt in packets:

        # 🔥 safety guard (prevents parser crash leaks)
        if not pkt.get("src_ip") or not pkt.get("dst_ip"):
            continue

        key = get_flow_key(pkt)
        now = pkt.get("timestamp", 0)

        if key not in flows:
            flows[key] = Flow(key, pkt)

        else:
            flow = flows[key]

            # timeout based split
            if now - flow.last_seen > FLOW_TIMEOUT:
                completed_flows.append(flow.to_dict())
                flows[key] = Flow(key, pkt)
            else:
                flow.update(pkt)

    # 🔥 final flush (controlled)
    if flush_all:
        for flow in flows.values():
            completed_flows.append(flow.to_dict())

    print(f"📊 Total flows built: {len(completed_flows)}")
    print(f"🧠 Active flow buckets: {len(flows)}")

    return completed_flows