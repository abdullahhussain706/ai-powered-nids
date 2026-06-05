import unittest

from core.anomaly_engine import run_anomaly_engine


def flow(
    flow_id,
    packets=10,
    total_bytes=1000,
    duration=10,
    syn_count=0,
    bwd_packets=5,
):
    fwd_packets = packets - bwd_packets
    return {
        "flow_id": flow_id,
        "src_ip": "10.0.0.1",
        "dst_ip": "10.0.0.2",
        "src_port": 12345,
        "dst_port": 80,
        "protocol": 6,
        "duration": duration,
        "fwd_packets": fwd_packets,
        "bwd_packets": bwd_packets,
        "total_packets": packets,
        "fwd_bytes": total_bytes // 2,
        "bwd_bytes": total_bytes - (total_bytes // 2),
        "total_bytes": total_bytes,
        "syn_count": syn_count,
        "fin_count": 0,
        "psh_count": 0,
        "ack_count": max(0, packets - syn_count),
        "rst_count": 0,
        "packet_sizes": [max(1, total_bytes // packets)] * packets,
    }


class AnomalyEngineTest(unittest.TestCase):
    def test_flags_absolute_high_rate_anomaly(self):
        suspicious = flow(
            "suspicious",
            packets=400,
            total_bytes=200_000,
            duration=1,
            syn_count=350,
            bwd_packets=0,
        )

        results = run_anomaly_engine([suspicious])

        alerts = results[0]["alerts"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["category"], "Anomaly")
        self.assertGreaterEqual(alerts[0]["confidence"], 0.7)

    def test_flags_batch_outlier_against_baseline(self):
        normal = [flow(f"normal-{idx}") for idx in range(6)]
        suspicious = flow("outlier", packets=80, total_bytes=80_000, duration=1)

        results = run_anomaly_engine([*normal, suspicious])

        alerts_by_flow = {
            result["flow"]["flow_id"]: result["alerts"]
            for result in results
        }
        self.assertFalse(any(alerts_by_flow[f"normal-{idx}"] for idx in range(6)))
        self.assertTrue(alerts_by_flow["outlier"])


if __name__ == "__main__":
    unittest.main()
