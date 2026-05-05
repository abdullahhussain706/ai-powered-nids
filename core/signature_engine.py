# core/signature_engine.py

import json
import os
import logging

# =========================
# GLOBAL CACHE
# =========================
RULES = []
RULES_LOADED = False


# =========================
# PATH HANDLING (IMPORTANT FIX)
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(BASE_DIR, "rule")


# =========================
# LOAD RULES SAFELY
# =========================
def load_rules():
    global RULES, RULES_LOADED

    if RULES_LOADED:
        return RULES

    RULES = []

    try:
        if not os.path.exists(RULES_DIR):
            logging.error(f"❌ Rules directory not found: {RULES_DIR}")
            return []

        files = [f for f in os.listdir(RULES_DIR) if f.endswith(".json")]

        if not files:
            logging.warning("⚠️ No rule files found")
            return []

        for file in files:
            path = os.path.join(RULES_DIR, file)

            try:
                with open(path, "r") as f:
                    data = json.load(f)

                    if isinstance(data, list):
                        RULES.extend(data)
                    else:
                        logging.warning(f"⚠️ Skipping invalid rule format: {file}")

            except json.JSONDecodeError as e:
                logging.error(f"❌ JSON error in {file}: {e}")

            except Exception as e:
                logging.error(f"❌ Failed reading {file}: {e}")

        RULES_LOADED = True
        logging.info(f"📜 Rules loaded successfully: {len(RULES)}")

        return RULES

    except Exception as e:
        logging.error(f"❌ Rule loading critical error: {e}")
        return []


# =========================
# RULE MATCH ENGINE
# =========================
def match_rule(features, rule):

    try:
        # -------------------------
        # BASIC FILTERS
        # -------------------------
        rule_proto = rule.get("protocol")
        if rule_proto and rule_proto != "ANY":
            if features.get("protocol") != rule_proto:
                return False

        rule_port = rule.get("dst_port")
        if rule_port not in [None, "ANY"]:
            if features.get("dst_port") != rule_port:
                return False

        # Optional flow guards reduce false positives for broad patterns.
        guard_map = {
            "min_packets": ("total_packets", lambda actual, expected: actual >= expected),
            "max_packets": ("total_packets", lambda actual, expected: actual <= expected),
            "min_bytes": ("total_bytes", lambda actual, expected: actual >= expected),
            "min_packet_rate": ("packet_rate", lambda actual, expected: actual >= expected),
            "max_packet_rate": ("packet_rate", lambda actual, expected: actual <= expected),
            "min_duration": ("duration", lambda actual, expected: actual >= expected),
            "max_duration": ("duration", lambda actual, expected: actual <= expected),
            "min_unique_dst_ports": ("unique_dst_ports", lambda actual, expected: actual >= expected),
            "min_syn_ratio": ("syn_ratio", lambda actual, expected: actual >= expected),
        }

        for guard, (feature_name, compare) in guard_map.items():
            if guard in rule:
                if not compare(features.get(feature_name, 0), rule[guard]):
                    return False

        threshold = rule.get("threshold", 0)
        pattern = rule.get("pattern")

        # -------------------------
        # FLOW-BASED DETECTION
        # -------------------------

        if pattern == "high_rate":
            return features.get("packet_rate", 0) > threshold

        if pattern == "syn_flood":
            return (
                features.get("syn_ratio", 0) > 0.5 and
                features.get("packet_rate", 0) > threshold
            )

        if pattern == "multi_port":
            return features.get("unique_dst_ports", 0) > threshold

        if pattern == "large_flow":
            return features.get("total_bytes", 0) > threshold

        if pattern == "long_connection":
            return features.get("duration", 0) > threshold

        if pattern == "short_burst":
            return (
                features.get("is_short_flow", False) and
                features.get("packet_rate", 0) > threshold
            )

        if pattern == "unidirectional":
            return features.get("is_unidirectional", False)

        if pattern == "high_packets":
            return features.get("total_packets", 0) > threshold

        if pattern == "high_bytes":
            return features.get("total_bytes", 0) > threshold

        if pattern == "syn_heavy":
            return features.get("is_syn_heavy", False)

        if pattern == "burst":
            return features.get("packet_rate", 0) > threshold

        # fallback
        return False

    except Exception as e:
        logging.error(f"❌ Rule match error: {e}")
        return False


# =========================
# MAIN ENGINE
# =========================
def run_signature_engine(features):
    alerts = []

    rules = load_rules()

    if not rules:
        logging.warning("⚠️ No rules loaded — engine inactive")
        return alerts

    for rule in rules:

        if not rule.get("enabled", True):
            continue

        # flow-based only
        if not rule.get("flow_required", False):
            continue

        if match_rule(features, rule):

            alerts.append({
                "rule_id": rule.get("id"),
                "name": rule.get("name"),
                "category": rule.get("category"),
                "severity": rule.get("severity"),
                "confidence": rule.get("confidence_score"),
                "src_ip": features.get("src_ip"),
                "dst_ip": features.get("dst_ip"),
                "src_port": features.get("src_port"),
                "dst_port": features.get("dst_port"),
                "protocol": features.get("protocol"),
                "flow_id": features.get("flow_id"),
            })

    return alerts
