import pandas as pd
from pathlib import Path
import joblib
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from xgboost import XGBClassifier

from ml.evaluation_utils import (
    save_classification_outputs,
    save_confusion_matrix,
    save_feature_importance,
    save_metrics_summary,
)

# =========================
# PATH SETUP
# =========================
DATA_PATH = BASE_DIR / "data" / "datasets" / "stage1_binary_dataset.csv"

MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = BASE_DIR / "ml" / "reports" / "stage1"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LOAD DATA
# =========================
df = pd.read_csv(DATA_PATH)

print("\nDataset shape:", df.shape)
print("\nClass distribution:\n", df["label"].value_counts())

# =========================
# FEATURES / LABEL
# =========================
X = df.drop("label", axis=1)
y = df["label"].map({"BENIGN": 0, "ATTACK": 1})

# =========================
# TRAIN TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("\nTrain shape:", X_train.shape)
print("Test shape:", X_test.shape)

# =========================
# IMBALANCE WEIGHT
# =========================
benign = (y_train == 0).sum()
attack = (y_train == 1).sum()
scale_pos_weight = benign / attack

print("\nScale Pos Weight:", round(scale_pos_weight, 2))

# =========================
# RANDOM FOREST
# =========================
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

rf.fit(X_train, y_train)
rf_pred = rf.predict(X_test)

rf_acc = accuracy_score(y_test, rf_pred)
rf_report = classification_report(y_test, rf_pred, target_names=["BENIGN", "ATTACK"], zero_division=0)
rf_report_dict = classification_report(y_test, rf_pred, target_names=["BENIGN", "ATTACK"], output_dict=True, zero_division=0)
rf_cm = confusion_matrix(y_test, rf_pred)

print("\n================ RF RESULTS ================")
print("Accuracy:", rf_acc)
print(rf_report)
print("Confusion Matrix:\n", rf_cm)

# =========================
# XGBOOST
# =========================
xgb = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric="logloss",
    random_state=42
)

xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)

xgb_acc = accuracy_score(y_test, xgb_pred)
xgb_report = classification_report(y_test, xgb_pred, target_names=["BENIGN", "ATTACK"], zero_division=0)
xgb_report_dict = classification_report(y_test, xgb_pred, target_names=["BENIGN", "ATTACK"], output_dict=True, zero_division=0)
xgb_cm = confusion_matrix(y_test, xgb_pred)

print("\n================ XGB RESULTS ================")
print("Accuracy:", xgb_acc)
print(xgb_report)
print("Confusion Matrix:\n", xgb_cm)

# =========================
# FINAL DECISION (BY RECALL)
# =========================
rf_recall = rf_report_dict["ATTACK"]["recall"]
xgb_recall = xgb_report_dict["ATTACK"]["recall"]

print("\n================ FINAL DECISION ================")
print("RF Recall:", rf_recall)
print("XGB Recall:", xgb_recall)

if xgb_recall >= rf_recall:
    best_model = xgb
    model_name = "XGBOOST"
    best_pred = xgb_pred
    best_report = xgb_report_dict
else:
    best_model = rf
    model_name = "RANDOM_FOREST"
    best_pred = rf_pred
    best_report = rf_report_dict

print("\nBEST MODEL:", model_name)

# =========================
# SAVE EVALUATION ARTIFACTS
# =========================
target_names = ["BENIGN", "ATTACK"]
labels = [0, 1]

save_classification_outputs(y_test, rf_pred, target_names, REPORT_DIR, "stage1_random_forest", labels)
save_confusion_matrix(y_test, rf_pred, labels, target_names, REPORT_DIR, "stage1_random_forest")

save_classification_outputs(y_test, xgb_pred, target_names, REPORT_DIR, "stage1_xgboost", labels)
save_confusion_matrix(y_test, xgb_pred, labels, target_names, REPORT_DIR, "stage1_xgboost")

save_classification_outputs(y_test, best_pred, target_names, REPORT_DIR, "stage1_best", labels)
save_confusion_matrix(y_test, best_pred, labels, target_names, REPORT_DIR, "stage1_best")
save_feature_importance(best_model, X.columns, REPORT_DIR, "stage1_best")

summary = {
    "dataset_path": str(DATA_PATH),
    "dataset_shape": list(df.shape),
    "class_distribution": df["label"].value_counts().to_dict(),
    "train_shape": list(X_train.shape),
    "test_shape": list(X_test.shape),
    "best_model": model_name,
    "decision_metric": "ATTACK recall",
    "models": {
        "random_forest": {
            "accuracy": float(rf_acc),
            "recall": float(rf_recall),
            "report": rf_report_dict,
        },
        "xgboost": {
            "accuracy": float(xgb_acc),
            "recall": float(xgb_recall),
            "report": xgb_report_dict,
        },
    },
    "best_report": best_report,
}
save_metrics_summary(summary, REPORT_DIR, "stage1")

print("\nEVALUATION ARTIFACTS SAVED AT:", REPORT_DIR)

# =========================
# SAVE MODEL
# =========================
MODEL_PATH = MODEL_DIR / f"stage1_{model_name}.pkl"
joblib.dump(best_model, MODEL_PATH)

print("\nMODEL SAVED AT:", MODEL_PATH)
