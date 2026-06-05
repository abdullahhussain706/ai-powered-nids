#!/usr/bin/env python3

import logging
import statistics

from core.cicids_feature_engine import extract_cicids_features


ANOMALY_FEATURES = {
    "flow_packets_per_sec": "Packet rate",
    "flow_bytes_per_sec": "Byte rate",
    "total_packets": "Packet count",
    "total_bytes": "Byte volume",
    "duration": "Flow duration",
    "syn_ratio": "SYN ratio",
    "packet_size_variance": "Packet size variance",
}

MIN_BASELINE_SIZE = 5
ROBUST_Z_THRESHOLD = 6.0


def _safe_median(values):
    values = [float(value) for value in values if value is not None]
    return statistics.median(values) if values else 0.0


def _mad(values, median):
    deviations = [abs(float(value) - median) for value in values if value is not None]
    return statistics.median(deviations) if deviations else 0.0


def _baseline(feature_rows):
    baseline = {}
    for feature_name in ANOMALY_FEATURES:
        values = [row.get(feature_name, 0.0) for row in feature_rows]
        median = _safe_median(values)
        mad = _mad(values, median)
        baseline[feature_name] = {
            "median": median,
            "mad": mad,
        }
    return baseline


def _robust_z(value, median, mad):
    value = float(value)
    if mad <= 0:
        if value > median and (value - median) >= max(10.0, abs(median) * 2):
            return 10.0
        return 0.0
    return 0.6745 * (value - median) / mad


def _severity(score):
    if score >= 12:
        return "critical"
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _confidence(score, evidence_count):
    base = min(0.98, 0.45 + (score / 20.0))
    evidence_bonus = min(0.12, evidence_count * 0.03)
    return round(min(0.99, base + evidence_bonus), 4)


def _absolute_evidence(features):
    evidence = []

    if features.get("flow_packets_per_sec", 0) >= 300 and features.get("total_packets", 0) >= 100:
        evidence.append({
            "feature": "flow_packets_per_sec",
            "label": "Very high packet rate",
            "value": features.get("flow_packets_per_sec", 0),
            "score": 8.0,
        })

    if features.get("flow_bytes_per_sec", 0) >= 2_000_000 and features.get("total_bytes", 0) >= 5_000_000:
        evidence.append({
            "feature": "flow_bytes_per_sec",
            "label": "Very high byte rate",
            "value": features.get("flow_bytes_per_sec", 0),
            "score": 7.0,
        })

    if features.get("is_unidirectional") and features.get("total_packets", 0) >= 100:
        evidence.append({
            "feature": "is_unidirectional",
            "label": "Long one-way flow",
            "value": True,
            "score": 5.5,
        })

    if features.get("syn_ratio", 0) >= 0.75 and features.get("syn_count", 0) >= 25:
        evidence.append({
            "feature": "syn_ratio",
            "label": "SYN-heavy flow",
            "value": features.get("syn_ratio", 0),
            "score": 6.5,
        })

    return evidence


def _statistical_evidence(features, baseline):
    evidence = []

    for feature_name, label in ANOMALY_FEATURES.items():
        stats = baseline.get(feature_name, {})
        score = _robust_z(
            features.get(feature_name, 0.0),
            stats.get("median", 0.0),
            stats.get("mad", 0.0),
        )

        if score >= ROBUST_Z_THRESHOLD:
            evidence.append({
                "feature": feature_name,
                "label": f"Unusual {label.lower()}",
                "value": features.get(feature_name, 0.0),
                "baseline_median": stats.get("median", 0.0),
                "score": round(score, 3),
            })

    return evidence


def _build_alert(flow, features, evidence):
    strongest = max(item.get("score", 0.0) for item in evidence)
    primary = max(evidence, key=lambda item: item.get("score", 0.0))
    category = "Anomaly"

    return {
        "rule_id": "ANOMALY_ENGINE",
        "name": f"Anomaly Detected - {primary['label']}",
        "category": category,
        "severity": _severity(strongest),
        "confidence": _confidence(strongest, len(evidence)),
        "src_ip": flow.get("src_ip"),
        "dst_ip": flow.get("dst_ip"),
        "src_port": flow.get("src_port"),
        "dst_port": flow.get("dst_port"),
        "protocol": flow.get("protocol"),
        "flow_id": flow.get("flow_id"),
        "details": {
            "evidence": evidence,
            "features": {
                "duration": features.get("duration"),
                "total_packets": features.get("total_packets"),
                "total_bytes": features.get("total_bytes"),
                "flow_packets_per_sec": features.get("flow_packets_per_sec"),
                "flow_bytes_per_sec": features.get("flow_bytes_per_sec"),
                "syn_ratio": features.get("syn_ratio"),
            },
        },
    }


def run_anomaly_engine(flows):
    feature_rows = []
    for flow in flows:
        features = extract_cicids_features(flow, include_identity=False)
        if features:
            feature_rows.append((flow, features))

    if not feature_rows:
        return []

    baseline = _baseline([features for _, features in feature_rows])
    use_statistical_baseline = len(feature_rows) >= MIN_BASELINE_SIZE
    results = []

    for flow, features in feature_rows:
        evidence = _absolute_evidence(features)
        if use_statistical_baseline:
            evidence.extend(_statistical_evidence(features, baseline))

        alerts = []
        if evidence:
            alerts.append(_build_alert(flow, features, evidence))

        results.append({
            "source": "anomaly",
            "flow": flow,
            "features": features,
            "alerts": alerts,
        })

    alert_count = sum(len(result["alerts"]) for result in results)
    logging.info(f"Anomaly results generated: {len(results)} | Alerts: {alert_count}")
    return results
