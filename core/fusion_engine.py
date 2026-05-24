import logging
from collections import defaultdict


ML_SOURCES = {"ml", "anomaly"}


def _flow_key(alert):
    return (
        alert.get("flow_id"),
        alert.get("src_ip"),
        alert.get("dst_ip"),
        alert.get("src_port"),
        alert.get("dst_port"),
        alert.get("protocol"),
    )


def _severity(signature_alerts, ml_alerts):
    severities = [
        str(alert.get("severity") or "").lower()
        for alert in signature_alerts + ml_alerts
    ]
    if "critical" in severities:
        return "critical"
    if signature_alerts and ml_alerts:
        return "critical"
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _confidence(signature_alerts, ml_alerts):
    scores = [
        float(alert.get("confidence") or 0.0)
        for alert in signature_alerts + ml_alerts
    ]
    if not scores:
        return 0.0
    return round(min(1.0, max(scores) + 0.05), 4)


def _hybrid_alert(flow_key, signature_alerts, ml_alerts):
    sample = signature_alerts[0] if signature_alerts else ml_alerts[0]
    signature_names = [alert.get("name") for alert in signature_alerts]
    ml_names = [alert.get("name") for alert in ml_alerts]
    ml_categories = [alert.get("category") for alert in ml_alerts if alert.get("category")]
    category = ml_categories[0] if ml_categories else sample.get("category", "Hybrid")

    return {
        "rule_id": f"HYBRID_{category}",
        "name": f"Hybrid Detection - {category}",
        "category": category,
        "severity": _severity(signature_alerts, ml_alerts),
        "confidence": _confidence(signature_alerts, ml_alerts),
        "src_ip": sample.get("src_ip"),
        "dst_ip": sample.get("dst_ip"),
        "src_port": sample.get("src_port"),
        "dst_port": sample.get("dst_port"),
        "protocol": sample.get("protocol"),
        "flow_id": flow_key[0] or sample.get("flow_id"),
        "details": {
            "signature_alerts": signature_names,
            "ml_alerts": ml_names,
            "fusion_reason": "Signature and ML/anomaly engines agreed on the same flow",
        },
    }


def build_hybrid_results(feature_results):
    grouped = defaultdict(lambda: {"signature": [], "ml": []})

    for result in feature_results:
        source = result.get("source", "signature")
        if source not in {"signature", *ML_SOURCES}:
            continue

        for alert in result.get("alerts", []):
            key = _flow_key(alert)
            if not any(key):
                continue
            if source == "signature":
                grouped[key]["signature"].append(alert)
            elif source in ML_SOURCES:
                grouped[key]["ml"].append(alert)

    hybrid_alerts = []
    for key, alerts in grouped.items():
        if alerts["signature"] and alerts["ml"]:
            hybrid_alerts.append(_hybrid_alert(key, alerts["signature"], alerts["ml"]))

    if hybrid_alerts:
        logging.warning(f"Hybrid alerts generated: {len(hybrid_alerts)}")
        feature_results.append({
            "source": "hybrid",
            "features": {},
            "alerts": hybrid_alerts,
        })

    return feature_results
