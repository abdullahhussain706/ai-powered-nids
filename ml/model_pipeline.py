#!/usr/bin/env python3

import logging
from pathlib import Path

import joblib
import pandas as pd

from core.cicids_feature_engine import TRAINING_FEATURES, extract_cicids_features
from utils.helpers import load_config


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "ml" / "models"

# Load settings from model_config.yaml
model_conf = load_config("model_config.yaml")

STAGE1_MODEL_PATTERN = model_conf.get("stage1_model_pattern", "stage1_*.pkl")
STAGE2_MODEL_PATTERN = model_conf.get("stage2_model_pattern", "stage2_*.pkl")

raw_stage1_labels = model_conf.get("stage1_labels", {0: "BENIGN", 1: "ATTACK"})
STAGE1_LABELS = {int(k): v for k, v in raw_stage1_labels.items()}

raw_stage2_labels = model_conf.get("stage2_labels", {0: "DOS", 1: "DDOS", 2: "PORTSCAN", 3: "WEB_ATTACK"})
STAGE2_LABELS = {int(k): v for k, v in raw_stage2_labels.items()}

_STAGE1_MODEL = None
_STAGE2_MODEL = None


def _latest_model(pattern):
    models = sorted(MODEL_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)
    return models[-1] if models else None


def _load_model(pattern, stage_name):
    model_path = _latest_model(pattern)
    if not model_path:
        logging.warning(f"{stage_name} model not found in {MODEL_DIR}")
        return None

    try:
        model = joblib.load(model_path)
        logging.info(f"{stage_name} model loaded: {model_path.name}")
        return model
    except Exception as e:
        logging.error(f"{stage_name} model load failed: {e}")
        return None


def get_stage1_model():
    global _STAGE1_MODEL
    if _STAGE1_MODEL is None:
        _STAGE1_MODEL = _load_model(STAGE1_MODEL_PATTERN, "Stage 1")
    return _STAGE1_MODEL


def get_stage2_model():
    global _STAGE2_MODEL
    if _STAGE2_MODEL is None:
        _STAGE2_MODEL = _load_model(STAGE2_MODEL_PATTERN, "Stage 2")
    return _STAGE2_MODEL


def _feature_frame(features):
    row = {name: features.get(name, 0) for name in TRAINING_FEATURES}
    return pd.DataFrame([row], columns=TRAINING_FEATURES).astype(float)


def _prediction_label(raw_prediction, labels):
    if hasattr(raw_prediction, "tolist"):
        raw_prediction = raw_prediction.tolist()
    if isinstance(raw_prediction, list):
        raw_prediction = raw_prediction[0]

    if isinstance(raw_prediction, str):
        return raw_prediction.upper()

    try:
        return labels.get(int(raw_prediction), str(raw_prediction))
    except (TypeError, ValueError):
        return str(raw_prediction).upper()


def _prediction_confidence(model, frame, predicted_index=None):
    if not hasattr(model, "predict_proba"):
        return 0.0

    try:
        probabilities = model.predict_proba(frame)[0]
        if predicted_index is None:
            return float(max(probabilities))
        return float(probabilities[int(predicted_index)])
    except Exception:
        return 0.0


def _prediction_index(raw_prediction):
    if hasattr(raw_prediction, "tolist"):
        raw_prediction = raw_prediction.tolist()
    if isinstance(raw_prediction, list):
        raw_prediction = raw_prediction[0]
    try:
        return int(raw_prediction)
    except (TypeError, ValueError):
        return None


def _is_attack(stage1_label):
    return str(stage1_label).upper() not in {"0", "BENIGN", "NORMAL"}


def _ml_alert(flow, stage1_confidence, stage2_label, stage2_confidence):
    confidence = stage2_confidence or stage1_confidence
    category = stage2_label or "ATTACK"

    return {
        "rule_id": f"ML_STAGE2_{category}",
        "name": f"ML Detected {category}",
        "category": category,
        "severity": "high",
        "confidence": confidence,
        "src_ip": flow.get("src_ip"),
        "dst_ip": flow.get("dst_ip"),
        "src_port": flow.get("src_port"),
        "dst_port": flow.get("dst_port"),
        "protocol": flow.get("protocol"),
        "flow_id": flow.get("flow_id"),
    }


def run_stage_pipeline(flows):
    stage1_model = get_stage1_model()
    stage2_model = get_stage2_model()

    if stage1_model is None:
        return []

    results = []

    for flow in flows:
        features = extract_cicids_features(flow, include_identity=False)
        if not features:
            continue

        frame = _feature_frame(features)

        try:
            stage1_raw = stage1_model.predict(frame)
            stage1_index = _prediction_index(stage1_raw)
            stage1_label = _prediction_label(stage1_raw, STAGE1_LABELS)
            stage1_confidence = _prediction_confidence(stage1_model, frame, stage1_index)

            result = {
                "source": "ml",
                "flow": flow,
                "features": features,
                "stage1": {
                    "label": stage1_label,
                    "confidence": stage1_confidence,
                },
                "stage2": None,
                "alerts": [],
            }

            if _is_attack(stage1_label):
                stage2_label = "ATTACK"
                stage2_confidence = stage1_confidence

                if stage2_model is not None:
                    stage2_raw = stage2_model.predict(frame)
                    stage2_index = _prediction_index(stage2_raw)
                    stage2_label = _prediction_label(stage2_raw, STAGE2_LABELS)
                    stage2_confidence = _prediction_confidence(
                        stage2_model,
                        frame,
                        stage2_index,
                    )

                result["stage2"] = {
                    "label": stage2_label,
                    "confidence": stage2_confidence,
                }
                result["alerts"].append(
                    _ml_alert(flow, stage1_confidence, stage2_label, stage2_confidence)
                )

            results.append(result)

        except Exception as e:
            logging.error(f"ML stage pipeline error for flow {flow.get('flow_id')}: {e}")

    logging.info(f"ML stage results generated: {len(results)}")
    return results
