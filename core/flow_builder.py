from collections import defaultdict
import logging

FLOW_TIMEOUT = 30  # seconds


# =========================
# FLOW CLASS
# =========================
class Flow:
    def __init__(self, pkt):
        self.src_ip = pkt["src_ip"]
        self.dst_ip = pkt["dst_ip"]
        self.src_port = pkt["src_port"]
        self.dst_port = pkt["dst_port"]
        self.protocol = pkt["protocol"]

        # timing
        self.start_time = pkt["timestamp"]
        self.last_seen = pkt["timestamp"]

        # forward stats
        self.fwd_packets = 1
        self.fwd_bytes = pkt["length"]

        # backward stats
        self.bwd_packets = 0
        self.bwd_bytes = 0

        # flags
        self.syn_count = 0
        self.fin_count = 0
        self.psh_count = 0

        self._update_flags(pkt)

    # =========================
    def _update_flags(self, pkt):
        flags = pkt.get("tcp_flags", "")
        if "S" in flags:
            self.syn_count += 1
        if "F" in flags:
            self.fin_count += 1
        if "P" in flags:
            self.psh_count += 1

    # =========================
    def update(self, pkt, direction):
        self.last_seen = pkt["timestamp"]

        if direction == "fwd":
            self.fwd_packets += 1
            self.fwd_bytes += pkt["length"]
        else:
            self.bwd_packets += 1
            self.bwd_bytes += pkt["length"]

        self._update_flags(pkt)

    # =========================
    def duration(self):
        return max(0, self.last_seen - self.start_time)

    def total_packets(self):
        return self.fwd_packets + self.bwd_packets

    def total_bytes(self):
        return self.fwd_bytes + self.bwd_bytes

    def packet_rate(self):
        d = self.duration()
        return self.total_packets() / d if d > 0 else self.total_packets()

    def byte_rate(self):
        d = self.duration()
        return self.total_bytes() / d if d > 0 else self.total_bytes()

    # =========================
    def to_dict(self):
        return {
            "flow_id": f"{self.src_ip}:{self.src_port}->{self.dst_ip}:{self.dst_port}",

            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,

            "start_time": self.start_time,
            "end_time": self.last_seen,
            "duration": self.duration(),

            "fwd_packets": self.fwd_packets,
            "bwd_packets": self.bwd_packets,
            "total_packets": self.total_packets(),

            "fwd_bytes": self.fwd_bytes,
            "bwd_bytes": self.bwd_bytes,
            "total_bytes": self.total_bytes(),

            "packet_rate": self.packet_rate(),
            "byte_rate": self.byte_rate(),

            "syn_count": self.syn_count,
            "fin_count": self.fin_count,
            "psh_count": self.psh_count
        }


# =========================
# FLOW KEY
# =========================
def get_flow_keys(pkt):
    fwd_key = (
        pkt["src_ip"],
        pkt["src_port"],
        pkt["dst_ip"],
        pkt["dst_port"],
        pkt["protocol"]
    )

    bwd_key = (
        pkt["dst_ip"],
        pkt["dst_port"],
        pkt["src_ip"],
        pkt["src_port"],
        pkt["protocol"]
    )

    return fwd_key, bwd_key


# =========================
# MAIN BUILDER
# =========================
def build_flows(packets):
    flows = {}
    completed = []

    for pkt in packets:

        fwd_key, bwd_key = get_flow_keys(pkt)
        now = pkt["timestamp"]

        if fwd_key in flows:
            flow = flows[fwd_key]
            direction = "fwd"

        elif bwd_key in flows:
            flow = flows[bwd_key]
            direction = "bwd"

        else:
            flows[fwd_key] = Flow(pkt)
            continue

        # timeout handling
        if now - flow.last_seen > FLOW_TIMEOUT:
            completed.append(flow.to_dict())
            flows[fwd_key] = Flow(pkt)
            continue

        flow.update(pkt, direction)

    # flush remaining
    for flow in flows.values():
        completed.append(flow.to_dict())

    ports_by_peer = defaultdict(set)
    for flow in completed:
        key = (flow["src_ip"], flow["dst_ip"], flow["protocol"])
        ports_by_peer[key].add(flow["dst_port"])

    for flow in completed:
        key = (flow["src_ip"], flow["dst_ip"], flow["protocol"])
        flow["unique_dst_ports"] = len(ports_by_peer[key])

    logging.info(f"📊 Flows built: {len(completed)}")
    
    return completed
