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
# PATH SETUP (CROSS PLATFORM)
# =========================
DATA_PATH = BASE_DIR / "data" / "datasets" / "stage2_attack_dataset.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR = BASE_DIR / "ml" / "reports" / "stage2"
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
y = df["label"]

# Encode labels
label_map = {
    "DOS": 0,
    "DDOS": 1,
    "PORTSCAN": 2,
    "WEB_ATTACK": 3
}
target_names = ["DOS", "DDOS", "PORTSCAN", "WEB_ATTACK"]
labels = [0, 1, 2, 3]

y = y.map(label_map)

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
rf_report_dict = classification_report(
    y_test,
    rf_pred,
    labels=labels,
    target_names=target_names,
    output_dict=True,
    zero_division=0,
)

print("\n================ RF RESULTS ================")
print("Accuracy:", rf_acc)
print(classification_report(y_test, rf_pred, labels=labels, target_names=target_names, zero_division=0))
print("Confusion Matrix:\n", confusion_matrix(y_test, rf_pred, labels=labels))

# =========================
# XGBOOST
# =========================
xgb = XGBClassifier(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="mlogloss",
    random_state=42
)

xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)

xgb_acc = accuracy_score(y_test, xgb_pred)
xgb_report_dict = classification_report(
    y_test,
    xgb_pred,
    labels=labels,
    target_names=target_names,
    output_dict=True,
    zero_division=0,
)

print("\n================ XGB RESULTS ================")
print("Accuracy:", xgb_acc)
print(classification_report(y_test, xgb_pred, labels=labels, target_names=target_names, zero_division=0))
print("Confusion Matrix:\n", confusion_matrix(y_test, xgb_pred, labels=labels))

# =========================
# FINAL DECISION (BY ACCURACY)
# =========================
print("\n================ FINAL DECISION ================")

if xgb_acc >= rf_acc:
    best_model = xgb
    model_name = "xgboost"
    best_acc = xgb_acc
    best_pred = xgb_pred
    best_report = xgb_report_dict
else:
    best_model = rf
    model_name = "randomforest"
    best_acc = rf_acc
    best_pred = rf_pred
    best_report = rf_report_dict

print("BEST MODEL:", model_name)
print("BEST ACCURACY:", best_acc)

# =========================
# SAVE EVALUATION ARTIFACTS
# =========================
save_classification_outputs(y_test, rf_pred, target_names, REPORT_DIR, "stage2_random_forest", labels)
save_confusion_matrix(y_test, rf_pred, labels, target_names, REPORT_DIR, "stage2_random_forest")

save_classification_outputs(y_test, xgb_pred, target_names, REPORT_DIR, "stage2_xgboost", labels)
save_confusion_matrix(y_test, xgb_pred, labels, target_names, REPORT_DIR, "stage2_xgboost")

save_classification_outputs(y_test, best_pred, target_names, REPORT_DIR, "stage2_best", labels)
save_confusion_matrix(y_test, best_pred, labels, target_names, REPORT_DIR, "stage2_best")
save_feature_importance(best_model, X.columns, REPORT_DIR, "stage2_best")

summary = {
    "dataset_path": str(DATA_PATH),
    "dataset_shape": list(df.shape),
    "class_distribution": df["label"].value_counts().to_dict(),
    "train_shape": list(X_train.shape),
    "test_shape": list(X_test.shape),
    "best_model": model_name,
    "best_accuracy": float(best_acc),
    "decision_metric": "accuracy",
    "models": {
        "random_forest": {
            "accuracy": float(rf_acc),
            "recall": float(rf_report_dict["macro avg"]["recall"]),
            "report": rf_report_dict,
        },
        "xgboost": {
            "accuracy": float(xgb_acc),
            "recall": float(xgb_report_dict["macro avg"]["recall"]),
            "report": xgb_report_dict,
        },
    },
    "best_report": best_report,
}
save_metrics_summary(summary, REPORT_DIR, "stage2")

print("\nEVALUATION ARTIFACTS SAVED AT:", REPORT_DIR)

# =========================
# SAVE MODEL (.pkl)
# =========================
MODEL_PATH = MODEL_DIR / f"stage2_{model_name}.pkl"

joblib.dump(best_model, MODEL_PATH)

print("\nMODEL SAVED SUCCESSFULLY")
print("PATH:", MODEL_PATH)
