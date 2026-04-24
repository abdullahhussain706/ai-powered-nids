from collections import defaultdict

FLOW_TIMEOUT = 30  # seconds


class Flow:
    def __init__(self, key, first_packet):
        self.key = key
        self.start_time = first_packet["timestamp"]
        self.last_seen = first_packet["timestamp"]

        self.packet_count = 1
        self.total_bytes = first_packet["length"]

    def update(self, packet):
        self.last_seen = packet["timestamp"]
        self.packet_count += 1
        self.total_bytes += packet["length"]

    def duration(self):
        return self.last_seen - self.start_time

    def to_dict(self):
        return {
            "flow_id": self.key,
            "packet_count": self.packet_count,
            "total_bytes": self.total_bytes,
            "start_time": self.start_time,
            "end_time": self.last_seen,
            "duration": self.duration()
        }


def get_flow_key(pkt):
    """
    Bidirectional key (IMPORTANT)
    """
    ip_pair = sorted([pkt["src_ip"], pkt["dst_ip"]])
    port_pair = sorted([pkt["src_port"], pkt["dst_port"]])

    return f"{ip_pair[0]}-{ip_pair[1]}-{port_pair[0]}-{port_pair[1]}-{pkt['protocol']}"


def build_flows(packets):
    flows = {}
    completed_flows = []

    for pkt in packets:
        key = get_flow_key(pkt)
        now = pkt["timestamp"]

        if key not in flows:
            flows[key] = Flow(key, pkt)
        else:
            flow = flows[key]

            # 🔥 TIMEOUT CHECK
            if now - flow.last_seen > FLOW_TIMEOUT:
                completed_flows.append(flow.to_dict())
                flows[key] = Flow(key, pkt)
            else:
                flow.update(pkt)

    # 🔥 flush remaining flows
    for flow in flows.values():
        completed_flows.append(flow.to_dict())

    print(f"📊 Total flows built: {len(completed_flows)}")
    print(f"Unique flows: {len(flows)} keys: {list(flows.keys())[:5]}")
    return completed_flows