# settings_view.py - Clean, no background glitches

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QFormLayout, QCheckBox, QComboBox, QLineEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, QTimer


BASE_DIR = Path(__file__).resolve().parent.parent
RULE_DIR = BASE_DIR / "rule"
DEFAULT_ALERT_LOG = BASE_DIR / "logs" / "alerts.jsonl"
DEFAULT_ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)


def load_rule_rows():
    rows = []

    if not RULE_DIR.is_dir():
        return rows

    for path in sorted(RULE_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                rules = json.load(f)
        except Exception:
            continue

        if not isinstance(rules, list):
            continue

        for rule in rules:
            rows.append((
                rule.get("id", ""),
                rule.get("name", "Unnamed Rule"),
                rule.get("category", path.name),
                "Enabled" if rule.get("enabled", True) else "Disabled",
            ))

    return rows


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()

        # Make the whole widget background transparent so it inherits main window's #12121f
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Scroll area – no background
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        main_layout.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # ---- Header ----
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: white; background: transparent;")
        content_layout.addWidget(header)

        subtitle = QLabel("Configure IDS preferences and system settings.")
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 13px; background: transparent; margin-bottom: 8px;")
        content_layout.addWidget(subtitle)

        # ----- Row 1: Detection + Network Interface -----
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Detection Group
        detection_group = self._create_group("Detection")
        detection_layout = QVBoxLayout(detection_group)

        self.ids_enabled = QCheckBox("Enable Intrusion Detection System")
        self.ids_enabled.setChecked(True)
        detection_layout.addWidget(self.ids_enabled)

        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("Sensitivity Level:"))
        self.sensitivity = QComboBox()
        self.sensitivity.addItems(["Low", "Medium", "High"])
        self.sensitivity.setCurrentText("High")
        sens_layout.addWidget(self.sensitivity)
        sens_layout.addStretch()
        sens_layout.addWidget(QLabel("Packet Inspection Depth:"))
        self.inspection_depth = QComboBox()
        self.inspection_depth.addItems(["Basic", "Deep", "Full"])
        self.inspection_depth.setCurrentText("Deep")
        sens_layout.addWidget(self.inspection_depth)
        detection_layout.addLayout(sens_layout)

        self.anomaly_detection = QCheckBox("Anomaly Detection")
        self.anomaly_detection.setChecked(True)
        detection_layout.addWidget(self.anomaly_detection)

        warn = QLabel("High sensitivity may generate more alerts. Use with caution in high traffic environments.")
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #ffb020; font-size: 11px; margin-top: 5px; background: transparent;")
        detection_layout.addWidget(warn)

        # Network Interface Group
        net_group = self._create_group("Network Interface")
        net_layout = QFormLayout(net_group)
        net_layout.setSpacing(8)
        net_layout.setLabelAlignment(Qt.AlignRight)

        self.capture_interface = QLineEdit("Ethernet (eth0)")
        net_layout.addRow("Capture Interface:", self.capture_interface)

        self.capture_mode = QComboBox()
        self.capture_mode.addItems(["Live Capture", "Offline Capture"])
        self.capture_mode.setCurrentText("Live Capture")
        net_layout.addRow("Capture Mode:", self.capture_mode)

        self.promiscuous = QCheckBox("Promiscuous Mode")
        net_layout.addRow("", self.promiscuous)

        self.bpf_filter = QLineEdit()
        self.bpf_filter.setPlaceholderText("e.g., port 80 or host 192.168.1.1")
        net_layout.addRow("BPF Filter (optional):", self.bpf_filter)

        row1.addWidget(detection_group, 1)
        row1.addWidget(net_group, 1)
        content_layout.addLayout(row1)

        # ----- Row 2: Alert Settings + Logging Settings -----
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # Alert Settings
        alert_group = self._create_group("Alert Settings")
        alert_layout = QVBoxLayout(alert_group)

        self.alerts_enabled = QCheckBox("Enable Alerts")
        self.alerts_enabled.setChecked(True)
        alert_layout.addWidget(self.alerts_enabled)

        notify_layout = QHBoxLayout()
        self.desktop_notify = QCheckBox("Desktop Notifications")
        self.sound_alert = QCheckBox("Sound Alert")
        notify_layout.addWidget(self.desktop_notify)
        notify_layout.addWidget(self.sound_alert)
        notify_layout.addStretch()
        alert_layout.addLayout(notify_layout)

        severity_retention = QHBoxLayout()
        severity_retention.addWidget(QLabel("Severity Filter:"))
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "High", "Medium", "Low"])
        self.severity_filter.setCurrentText("All")
        severity_retention.addWidget(self.severity_filter)
        severity_retention.addStretch()
        severity_retention.addWidget(QLabel("Alert Retention (days):"))
        self.retention_days = QSpinBox()
        self.retention_days.setRange(1, 365)
        self.retention_days.setValue(30)
        severity_retention.addWidget(self.retention_days)
        alert_layout.addLayout(severity_retention)

        # Logging Settings
        log_group = self._create_group("Logging Settings")
        log_layout = QFormLayout(log_group)
        log_layout.setSpacing(8)
        log_layout.setLabelAlignment(Qt.AlignRight)

        self.logging_enabled = QCheckBox("Enable Logging")
        log_layout.addRow("", self.logging_enabled)

        self.log_format = QComboBox()
        self.log_format.addItems(["JSON", "CSV", "Plain Text"])
        self.log_format.setCurrentText("JSON")
        log_layout.addRow("Log Format:", self.log_format)

        self.log_file_path = QLineEdit(str(DEFAULT_ALERT_LOG))
        log_layout.addRow("Log File Path:", self.log_file_path)

        self.max_log_size = QSpinBox()
        self.max_log_size.setRange(1, 1000)
        self.max_log_size.setValue(100)
        log_layout.addRow("Max Log File Size (MB):", self.max_log_size)

        self.auto_delete = QCheckBox("Auto Delete Logs")
        log_layout.addRow("", self.auto_delete)

        self.delete_after_days = QSpinBox()
        self.delete_after_days.setRange(1, 365)
        self.delete_after_days.setValue(7)
        log_layout.addRow("Delete Logs After (days):", self.delete_after_days)

        row2.addWidget(alert_group, 1)
        row2.addWidget(log_group, 1)
        content_layout.addLayout(row2)

        # ----- Rule Management Table -----
        rule_group = self._create_group("Rule Management")
        rule_layout = QVBoxLayout(rule_group)

        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(5)
        self.rule_table.setHorizontalHeaderLabels(["ID", "Rule Name", "Description", "Status", "Action"])
        self.rule_table.verticalHeader().setVisible(False)
        self.rule_table.setAlternatingRowColors(True)
        self.rule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rule_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rule_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(11, 18, 28, 0.35);
                color: white;
                border: 1px solid #2b3442;
                border-radius: 8px;
                font-size: 12px;
                gridline-color: #2b3442;
            }
            QHeaderView::section {
                background-color: #1f2a3a;
                color: #e0e0e0;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        self.rule_defaults = load_rule_rows()
        rules = self.rule_defaults
        self.rule_table.setRowCount(len(rules))
        for row, (rid, name, desc, status) in enumerate(rules):
            self.rule_table.setItem(row, 0, QTableWidgetItem(str(rid)))
            self.rule_table.setItem(row, 1, QTableWidgetItem(name))
            self.rule_table.setItem(row, 2, QTableWidgetItem(desc))
            self.rule_table.setItem(row, 3, QTableWidgetItem(status))
            cb = QCheckBox()
            cb.setChecked(status == "Enabled")
            cb.stateChanged.connect(lambda state, r=row: self.toggle_rule_status(r, state))
            self.rule_table.setCellWidget(row, 4, cb)
        self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.rule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rule_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.rule_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.rule_table.setFixedHeight(200)
        rule_layout.addWidget(self.rule_table)

        content_layout.addWidget(rule_group)

        # ----- Reset Button -----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(self.reset_btn)
        content_layout.addLayout(btn_layout)

        # ----- Bottom Status Bar -----
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("🟢 System Status Running")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold; background: transparent;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.uptime_label = QLabel("Uptime: 02:14:35")
        self.uptime_label.setStyleSheet("color: #a0a0b0; background: transparent;")
        status_layout.addWidget(self.uptime_label)
        self.time_label = QLabel("12:45:30 PM  May 24, 2025")
        self.time_label.setStyleSheet("color: #a0a0b0; background: transparent;")
        status_layout.addWidget(self.time_label)

        content_layout.addWidget(status_frame)

        # Dummy uptime timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_uptime)
        self.timer.start(1000)
        self.uptime_seconds = 2*3600 + 14*60 + 35

    def _create_group(self, title):
        """Create a QGroupBox with clean dark styling"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e2f;
                border: 1px solid #2d2d3a;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                color: white;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel, QCheckBox, QComboBox, QLineEdit, QSpinBox {
                background: transparent;
                color: white;
            }
            QCheckBox::indicator {
                background-color: #2d2d3a;
                border: 1px solid #3d3d4a;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
            }
            QComboBox, QLineEdit, QSpinBox {
                background-color: #2d2d3a;
                border: 1px solid #3d3d4a;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        return group

    def toggle_rule_status(self, row, state):
        status = "Enabled" if state == Qt.Checked else "Disabled"
        self.rule_table.setItem(row, 3, QTableWidgetItem(status))

    def reset_to_default(self):
        # Detection
        self.ids_enabled.setChecked(True)
        self.sensitivity.setCurrentText("High")
        self.inspection_depth.setCurrentText("Deep")
        self.anomaly_detection.setChecked(True)
        # Network
        self.capture_interface.setText("Ethernet (eth0)")
        self.capture_mode.setCurrentText("Live Capture")
        self.promiscuous.setChecked(False)
        self.bpf_filter.clear()
        # Alert Settings
        self.alerts_enabled.setChecked(True)
        self.desktop_notify.setChecked(False)
        self.sound_alert.setChecked(False)
        self.severity_filter.setCurrentText("All")
        self.retention_days.setValue(30)
        # Logging Settings
        self.logging_enabled.setChecked(True)
        self.log_format.setCurrentText("JSON")
        self.log_file_path.setText(str(DEFAULT_ALERT_LOG))
        self.max_log_size.setValue(100)
        self.auto_delete.setChecked(True)
        self.delete_after_days.setValue(7)
        # Rules
        self.rule_defaults = load_rule_rows()
        for row, (_, _, _, status) in enumerate(self.rule_defaults):
            if row >= self.rule_table.rowCount():
                break
            self.rule_table.setItem(row, 3, QTableWidgetItem(status))
            cb = self.rule_table.cellWidget(row, 4)
            if cb:
                cb.setChecked(status == "Enabled")
        QMessageBox.information(self, "Reset", "All settings have been reset to default values.")

    def update_uptime(self):
        self.uptime_seconds += 1
        hours = self.uptime_seconds // 3600
        minutes = (self.uptime_seconds % 3600) // 60
        seconds = self.uptime_seconds % 60
        self.uptime_label.setText(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
