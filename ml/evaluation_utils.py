import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_classification_outputs(y_true, y_pred, target_names, output_dir, prefix, labels=None):
    output_dir = ensure_dir(output_dir)

    report_dict = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=target_names,
        zero_division=0,
    )

    report_df = pd.DataFrame(report_dict).transpose()
    csv_path = output_dir / f"{prefix}_classification_report.csv"
    txt_path = output_dir / f"{prefix}_classification_report.txt"

    report_df.to_csv(csv_path)
    txt_path.write_text(report_text, encoding="utf-8")

    return report_dict, csv_path, txt_path


def save_confusion_matrix(y_true, y_pred, labels, target_names, output_dir, prefix):
    output_dir = ensure_dir(output_dir)
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    csv_path = output_dir / f"{prefix}_confusion_matrix.csv"
    png_path = output_dir / f"{prefix}_confusion_matrix.png"

    pd.DataFrame(matrix, index=target_names, columns=target_names).to_csv(csv_path)

    plt.figure(figsize=(7, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=target_names,
        yticklabels=target_names,
        cbar=False,
    )
    plt.title(f"{prefix.replace('_', ' ').title()} Confusion Matrix")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.tight_layout()
    plt.savefig(png_path, dpi=160)
    plt.close()

    return matrix, csv_path, png_path


def save_feature_importance(model, feature_names, output_dir, prefix, top_n=20):
    output_dir = ensure_dir(output_dir)
    png_path = output_dir / f"{prefix}_feature_importance.png"
    csv_path = output_dir / f"{prefix}_feature_importance.csv"

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        return None, None

    data = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(top_n)
    )
    data.to_csv(csv_path, index=False)

    plt.figure(figsize=(8, 6))
    sns.barplot(data=data, x="importance", y="feature", color="#2f80ed")
    plt.title(f"Top {top_n} Feature Importances")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(png_path, dpi=160)
    plt.close()

    return csv_path, png_path


def save_metrics_summary(summary, output_dir, prefix):
    output_dir = ensure_dir(output_dir)
    json_path = output_dir / f"{prefix}_metrics_summary.json"
    md_path = output_dir / f"{prefix}_metrics_summary.md"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        f"# {prefix.replace('_', ' ').title()} Metrics",
        "",
        f"- Dataset shape: {summary.get('dataset_shape')}",
        f"- Train shape: {summary.get('train_shape')}",
        f"- Test shape: {summary.get('test_shape')}",
        f"- Best model: {summary.get('best_model')}",
        f"- Decision metric: {summary.get('decision_metric')}",
        "",
        "## Model Scores",
    ]

    for name, metrics in summary.get("models", {}).items():
        lines.append(f"- {name}: accuracy={metrics.get('accuracy'):.4f}, recall={metrics.get('recall'):.4f}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
