import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RULE_DIR = BASE_DIR / "rule"


def load_rule_rows(rule_dir=RULE_DIR):
    rows = []
    rule_dir = Path(rule_dir)
    if not rule_dir.is_dir():
        return rows

    for path in sorted(rule_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                rules = json.load(f)
        except Exception:
            continue

        if not isinstance(rules, list):
            continue

        for rule in rules:
            rows.append({
                "file": path,
                "id": rule.get("id", ""),
                "name": rule.get("name", "Unnamed Rule"),
                "category": rule.get("category", path.name),
                "enabled": bool(rule.get("enabled", True)),
            })

    return rows


def write_rule_enabled(rule_file, rule_id, enabled):
    rule_file = Path(rule_file)
    with rule_file.open("r", encoding="utf-8") as f:
        rules = json.load(f)

    if not isinstance(rules, list):
        raise ValueError(f"Invalid rule file format: {rule_file.name}")

    updated = False
    for rule in rules:
        if str(rule.get("id")) == str(rule_id):
            rule["enabled"] = bool(enabled)
            updated = True
            break

    if not updated:
        raise ValueError(f"Rule id {rule_id} not found in {rule_file.name}")

    with rule_file.open("w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
        f.write("\n")

    return True
