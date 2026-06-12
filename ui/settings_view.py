import sys
import json
import subprocess
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGroupBox, QFormLayout, QCheckBox, QComboBox, QLineEdit,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QScrollArea, QMessageBox, QFileDialog,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QDateTime

from services.pcap_storage_service import delete_all_pcaps, pcap_stats
from services.rule_service import load_rule_rows, write_rule_enabled


BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
ALERTS_LOG = BASE_DIR / "logs" / "alerts.jsonl"
CAPTURE_LOG = BASE_DIR / "logs" / "capture.log"
SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_system_uptime():
    """Get system uptime in seconds."""
    if sys.platform == "win32":
        try:
            result = subprocess.run(['wmic', 'os', 'get', 'LastBootUpTime'], 
                                   capture_output=True, text=True, shell=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                boot_time_str = lines[1].split('.')[0]
                boot_time = datetime.strptime(boot_time_str, "%Y%m%d%H%M%S")
                uptime_seconds = (datetime.now() - boot_time).total_seconds()
                return int(uptime_seconds)
        except:
            pass
    else:
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return int(uptime_seconds)
        except:
            pass
    
    return 0


def format_uptime(seconds):
    """Convert seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_available_interfaces():
    """Get capture interfaces in the same format used by tshark."""
    interfaces = ["All"]

    try:
        result = subprocess.run(["tshark", "-D"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if "." in line and line not in interfaces:
                    interfaces.append(line)
            if len(interfaces) > 1:
                return interfaces
    except Exception:
        pass

    try:
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, shell=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            match = re.search(r'([a-zA-Z0-9\s]+)adapter\s+([^:]+):', line, re.IGNORECASE)
            if match:
                iface = match.group(2).strip()
                if iface and iface not in interfaces:
                    interfaces.append(iface)
    except Exception:
        pass
    
    if len(interfaces) <= 1:
        interfaces.extend(["eth0", "eth1", "wlan0", "wlp2s0", "en0", "en1", "Local Area Connection", "Wi-Fi"])
    
    return interfaces


def choose_interface_value(saved_value, available_interfaces):
    saved = str(saved_value or "All").strip()
    if saved in available_interfaces:
        return saved

    saved_lower = saved.lower()
    for interface in available_interfaces:
        if saved_lower and saved_lower in interface.lower():
            return interface

    return "All"


class SettingsManager:
    """Manage application settings persistence."""
    
    def __init__(self):
        self.settings = self.load_settings()
    
    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return self.get_defaults()
        return self.get_defaults()
    
    def get_defaults(self):
        return {
            "logging_enabled": True,
            "log_format": "JSON",
            "log_file_path": str(ALERTS_LOG),
            "max_log_size_mb": 100,
            "auto_delete_logs": True,
            "delete_after_days": 7,
            "capture_interface": "All",
            "capture_mode": "Live Capture",
            "promiscuous_mode": False,
            "bpf_filter": "",
            "alerts_enabled": True,
            "desktop_notifications": False,
            "sound_alerts": False,
            "severity_filter": "All",
            "alert_retention_days": 30
        }
    
    def save(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=4)
    
    def get(self, key, default=None):
        return self.settings.get(key, default)
    
    def set(self, key, value):
        self.settings[key] = value
        self.save()
    
    def get_log_file_size(self):
        log_path = Path(self.get("log_file_path"))
        if log_path.exists():
            return round(log_path.stat().st_size / (1024 * 1024), 2)
        return 0
    
    def get_log_entry_count(self):
        log_path = Path(self.get("log_file_path"))
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    return sum(1 for _ in f)
            except:
                return 0
        return 0
    
    def get_log_age_days(self):
        log_path = Path(self.get("log_file_path"))
        if log_path.exists():
            import time
            age_days = (time.time() - log_path.stat().st_mtime) / (24 * 3600)
            return round(age_days, 1)
        return 0
    
    def rotate_log(self):
        if not self.get("logging_enabled"):
            return False
        
        log_path = Path(self.get("log_file_path"))
        if not log_path.exists():
            return False
        
        size_mb = log_path.stat().st_size / (1024 * 1024)
        max_size = self.get("max_log_size_mb")
        
        if size_mb > max_size:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = log_path.with_suffix(f".{timestamp}.jsonl")
            log_path.rename(backup_path)
            return True
        return False
    
    def cleanup_old_logs(self):
        if not self.get("auto_delete_logs"):
            return 0
        
        log_dir = Path(self.get("log_file_path")).parent
        days = self.get("delete_after_days")
        cutoff = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for log_file in log_dir.glob("*.jsonl*"):
            if log_file.stat().st_mtime < cutoff.timestamp():
                log_file.unlink()
                deleted_count += 1
        
        return deleted_count
    
    def delete_all_logs(self):
        log_dir = Path(self.get("log_file_path")).parent
        deleted_count = 0
        
        for log_file in log_dir.glob("*.jsonl*"):
            log_file.unlink()
            deleted_count += 1
        
        if CAPTURE_LOG.exists():
            CAPTURE_LOG.unlink()
        
        return deleted_count

    def get_pcap_stats(self):
        return pcap_stats()

    def delete_all_pcaps(self):
        return delete_all_pcaps()


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        
        self.settings_mgr = SettingsManager()
        
        # Get initial system uptime
        self.system_start_time = get_system_uptime()
        self.uptime_seconds = self.system_start_time

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        main_layout.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: white; background: transparent;")
        content_layout.addWidget(header)

        subtitle = QLabel("Configure IDS preferences and system settings.")
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 13px; background: transparent; margin-bottom: 8px;")
        content_layout.addWidget(subtitle)

        # Responsive: Wrap two columns in a container that can adjust
        two_column_container = QWidget()
        two_column_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        two_column_layout = QHBoxLayout(two_column_container)
        two_column_layout.setSpacing(16)
        two_column_layout.setContentsMargins(0, 0, 0, 0)

        # ==================== LEFT COLUMN ====================
        left_column = QWidget()
        left_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        left_layout = QVBoxLayout(left_column)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Network Interface Group
        net_group = self._create_group("Network Interface")
        net_layout = QFormLayout(net_group)
        net_layout.setSpacing(8)
        net_layout.setLabelAlignment(Qt.AlignRight)
        net_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.capture_interface = QComboBox()
        interfaces = get_available_interfaces()
        self.capture_interface.addItems(interfaces)
        current_iface = self.settings_mgr.get("capture_interface", "All")
        self.capture_interface.setCurrentText(choose_interface_value(current_iface, interfaces))
        self.capture_interface.setMinimumWidth(150)
        net_layout.addRow("Capture Interface:", self.capture_interface)

        self.capture_mode = QComboBox()
        self.capture_mode.addItems(["Live Capture", "Offline Capture"])
        self.capture_mode.setCurrentText(self.settings_mgr.get("capture_mode", "Live Capture"))
        net_layout.addRow("Capture Mode:", self.capture_mode)

        self.promiscuous = QCheckBox("Promiscuous Mode")
        self.promiscuous.setChecked(self.settings_mgr.get("promiscuous_mode", False))
        net_layout.addRow("", self.promiscuous)

        self.bpf_filter = QLineEdit()
        self.bpf_filter.setText(self.settings_mgr.get("bpf_filter", ""))
        self.bpf_filter.setPlaceholderText("e.g., port 80 or host 192.168.1.1")
        net_layout.addRow("BPF Filter (optional):", self.bpf_filter)

        left_layout.addWidget(net_group)

        # Alert Settings Group
        alert_group = self._create_group("Alert Settings")
        alert_layout = QVBoxLayout(alert_group)

        self.alerts_enabled = QCheckBox("Enable Alerts")
        self.alerts_enabled.setChecked(self.settings_mgr.get("alerts_enabled", True))
        alert_layout.addWidget(self.alerts_enabled)

        notify_layout = QHBoxLayout()
        self.desktop_notify = QCheckBox("Desktop Notifications")
        self.desktop_notify.setChecked(self.settings_mgr.get("desktop_notifications", False))
        self.sound_alert = QCheckBox("Sound Alert")
        self.sound_alert.setChecked(self.settings_mgr.get("sound_alerts", False))
        notify_layout.addWidget(self.desktop_notify)
        notify_layout.addWidget(self.sound_alert)
        notify_layout.addStretch()
        alert_layout.addLayout(notify_layout)

        severity_retention = QHBoxLayout()
        severity_retention.addWidget(QLabel("Severity Filter:"))
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "High", "Medium", "Low"])
        self.severity_filter.setCurrentText(self.settings_mgr.get("severity_filter", "All"))
        severity_retention.addWidget(self.severity_filter)
        severity_retention.addStretch()
        severity_retention.addWidget(QLabel("Alert Retention (days):"))
        self.retention_days = QSpinBox()
        self.retention_days.setRange(1, 365)
        self.retention_days.setValue(self.settings_mgr.get("alert_retention_days", 30))
        severity_retention.addWidget(self.retention_days)
        alert_layout.addLayout(severity_retention)

        left_layout.addWidget(alert_group)

        # ==================== RIGHT COLUMN ====================
        right_column = QWidget()
        right_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        right_layout = QVBoxLayout(right_column)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Logging Settings Group
        log_group = self._create_group("Logging Settings")
        log_layout = QFormLayout(log_group)
        log_layout.setSpacing(8)
        log_layout.setLabelAlignment(Qt.AlignRight)
        log_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.logging_enabled = QCheckBox("Enable Logging")
        self.logging_enabled.setChecked(self.settings_mgr.get("logging_enabled", True))
        log_layout.addRow("", self.logging_enabled)

        self.log_format = QComboBox()
        self.log_format.addItems(["JSON", "CSV", "Plain Text"])
        self.log_format.setCurrentText(self.settings_mgr.get("log_format", "JSON"))
        log_layout.addRow("Log Format:", self.log_format)

        # Log file path with browse button
        path_layout = QHBoxLayout()
        self.log_file_path = QLineEdit(self.settings_mgr.get("log_file_path", str(ALERTS_LOG)))
        path_layout.addWidget(self.log_file_path, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self.browse_log_path)
        path_layout.addWidget(browse_btn)
        log_layout.addRow("Log File Path:", path_layout)

        self.max_log_size = QSpinBox()
        self.max_log_size.setRange(1, 1000)
        self.max_log_size.setValue(self.settings_mgr.get("max_log_size_mb", 100))
        log_layout.addRow("Max Log File Size (MB):", self.max_log_size)

        # Log stats display
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #2d2d3a; border-radius: 4px; padding: 8px;")
        stats_layout = QVBoxLayout(stats_frame)
        self.log_stats_label = QLabel()
        self.log_stats_label.setStyleSheet("color: #a0a0b0; font-size: 10px;")
        stats_layout.addWidget(self.log_stats_label)
        log_layout.addRow("Log Statistics:", stats_frame)

        # Log management buttons
        btn_layout = QHBoxLayout()
        self.rotate_now_btn = QPushButton("Rotate Log Now")
        self.rotate_now_btn.setFixedWidth(120)
        self.rotate_now_btn.clicked.connect(self.rotate_log_now)
        btn_layout.addWidget(self.rotate_now_btn)
        
        self.delete_logs_btn = QPushButton("Delete All Logs")
        self.delete_logs_btn.setFixedWidth(120)
        self.delete_logs_btn.setStyleSheet("background-color: #f44336;")
        self.delete_logs_btn.clicked.connect(self.delete_all_logs)
        btn_layout.addWidget(self.delete_logs_btn)
        
        btn_layout.addStretch()
        log_layout.addRow("", btn_layout)

        self.auto_delete = QCheckBox("Auto Delete Old Logs")
        self.auto_delete.setChecked(self.settings_mgr.get("auto_delete_logs", True))
        log_layout.addRow("", self.auto_delete)

        self.delete_after_days = QSpinBox()
        self.delete_after_days.setRange(1, 365)
        self.delete_after_days.setValue(self.settings_mgr.get("delete_after_days", 7))
        log_layout.addRow("Delete Logs After (days):", self.delete_after_days)

        right_layout.addWidget(log_group)

        # PCAP Storage Group
        pcap_group = self._create_group("PCAP Storage")
        pcap_layout = QFormLayout(pcap_group)
        pcap_layout.setSpacing(8)
        pcap_layout.setLabelAlignment(Qt.AlignRight)
        pcap_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        pcap_stats_frame = QFrame()
        pcap_stats_frame.setStyleSheet("background-color: #2d2d3a; border-radius: 4px; padding: 8px;")
        pcap_stats_layout = QVBoxLayout(pcap_stats_frame)
        self.pcap_stats_label = QLabel()
        self.pcap_stats_label.setStyleSheet("color: #a0a0b0; font-size: 10px;")
        self.pcap_stats_label.setWordWrap(True)
        pcap_stats_layout.addWidget(self.pcap_stats_label)
        pcap_layout.addRow("Storage:", pcap_stats_frame)

        self.delete_pcaps_btn = QPushButton("Delete All PCAPs")
        self.delete_pcaps_btn.setFixedWidth(130)
        self.delete_pcaps_btn.setStyleSheet("background-color: #f44336;")
        self.delete_pcaps_btn.clicked.connect(self.delete_all_pcap_files)
        pcap_btn_layout = QHBoxLayout()
        pcap_btn_layout.addWidget(self.delete_pcaps_btn)
        pcap_btn_layout.addStretch()
        pcap_layout.addRow("", pcap_btn_layout)

        right_layout.addWidget(pcap_group)

        # Add both columns to the two-column layout
        two_column_layout.addWidget(left_column, 1)
        two_column_layout.addWidget(right_column, 1)
        content_layout.addWidget(two_column_container)

        # ----- Rule Management Table (Full Width Below) -----
        rule_group = self._create_group("Rule Management")
        rule_layout = QVBoxLayout(rule_group)

        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(5)
        self.rule_table.setHorizontalHeaderLabels(["ID", "Rule Name", "Description", "Status", "Action"])
        self.rule_table.verticalHeader().setVisible(False)
        self.rule_table.setAlternatingRowColors(True)
        self.rule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rule_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rule_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        self.rule_records = load_rule_rows()
        self.rule_defaults = [dict(rule) for rule in self.rule_records]
        self.rule_table.setRowCount(len(self.rule_records))
        for row, rule in enumerate(self.rule_records):
            rid = rule["id"]
            name = rule["name"]
            desc = rule["category"]
            status = "Enabled" if rule["enabled"] else "Disabled"
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
        self.rule_table.setMinimumHeight(200)
        self.rule_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rule_layout.addWidget(self.rule_table, 1)

        content_layout.addWidget(rule_group, 1)

        # ----- Save & Reset Buttons -----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_btn.setMinimumWidth(120)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        
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
        self.reset_btn.setMinimumWidth(120)
        self.reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(self.reset_btn)
        
        content_layout.addLayout(btn_layout)

        # ----- Bottom Status Bar with Real Uptime -----
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
        
        self.uptime_label = QLabel(f"Uptime: {format_uptime(self.uptime_seconds)}")
        self.uptime_label.setStyleSheet("color: #a0a0b0; background: transparent;")
        status_layout.addWidget(self.uptime_label)
        
        self.time_label = QLabel(datetime.now().strftime("%I:%M:%S %p  %b %d, %Y"))
        self.time_label.setStyleSheet("color: #a0a0b0; background: transparent;")
        status_layout.addWidget(self.time_label)

        content_layout.addWidget(status_frame)

        # Update stats and start timers
        self.update_log_stats()
        self.update_pcap_stats()
        
        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.update_uptime)
        self.uptime_timer.start(1000)
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_log_stats)
        self.stats_timer.start(5000)

        self.pcap_stats_timer = QTimer()
        self.pcap_stats_timer.timeout.connect(self.update_pcap_stats)
        self.pcap_stats_timer.start(5000)
        
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

    def _create_group(self, title):
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
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

    def browse_log_path(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Log File Path", 
            str(self.log_file_path.text()), 
            "JSONL Files (*.jsonl);;All Files (*)"
        )
        if file_path:
            self.log_file_path.setText(file_path)

    def update_log_stats(self):
        size_mb = self.settings_mgr.get_log_file_size()
        entry_count = self.settings_mgr.get_log_entry_count()
        age_days = self.settings_mgr.get_log_age_days()
        
        self.log_stats_label.setText(
            f"📊 Size: {size_mb} MB | 📝 Entries: {entry_count} | 📅 Oldest: {age_days} days ago"
        )

    def update_pcap_stats(self):
        stats = self.settings_mgr.get_pcap_stats()
        self.pcap_stats_label.setText(
            f"Files: {stats['file_count']} | Size: {stats['total_mb']} MB | "
            f"Directory: {stats['directory']}"
        )

    def rotate_log_now(self):
        if self.settings_mgr.rotate_log():
            QMessageBox.information(self, "Log Rotated", "Log file has been rotated successfully.")
            self.update_log_stats()
        else:
            QMessageBox.information(self, "No Rotation Needed", 
                f"Log file size is within limit ({self.settings_mgr.get_log_file_size()} MB).")

    def delete_all_logs(self):
        reply = QMessageBox.question(
            self, "Delete All Logs", 
            "Are you sure you want to delete ALL log files?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            deleted = self.settings_mgr.delete_all_logs()
            QMessageBox.information(self, "Logs Deleted", f"Deleted {deleted} log file(s).")
            self.update_log_stats()

    def delete_all_pcap_files(self):
        reply = QMessageBox.question(
            self, "Delete All PCAPs",
            "Are you sure you want to delete all captured PCAP files?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            result = self.settings_mgr.delete_all_pcaps()
            QMessageBox.information(
                self,
                "PCAPs Deleted",
                f"Deleted {result['deleted_count']} PCAP file(s)."
            )
            self.update_pcap_stats()

    def save_settings(self):
        self.settings_mgr.set("capture_interface", self.capture_interface.currentText())
        self.settings_mgr.set("capture_mode", self.capture_mode.currentText())
        self.settings_mgr.set("promiscuous_mode", self.promiscuous.isChecked())
        self.settings_mgr.set("bpf_filter", self.bpf_filter.text())
        
        self.settings_mgr.set("alerts_enabled", self.alerts_enabled.isChecked())
        self.settings_mgr.set("desktop_notifications", self.desktop_notify.isChecked())
        self.settings_mgr.set("sound_alerts", self.sound_alert.isChecked())
        self.settings_mgr.set("severity_filter", self.severity_filter.currentText())
        self.settings_mgr.set("alert_retention_days", self.retention_days.value())
        
        self.settings_mgr.set("logging_enabled", self.logging_enabled.isChecked())
        self.settings_mgr.set("log_format", self.log_format.currentText())
        self.settings_mgr.set("log_file_path", self.log_file_path.text())
        self.settings_mgr.set("max_log_size_mb", self.max_log_size.value())
        self.settings_mgr.set("auto_delete_logs", self.auto_delete.isChecked())
        self.settings_mgr.set("delete_after_days", self.delete_after_days.value())
        self.save_rule_states()
        
        QMessageBox.information(self, "Settings Saved", "All settings have been saved successfully.")

    def toggle_rule_status(self, row, state):
        enabled = state == Qt.Checked or state == Qt.CheckState.Checked
        status = "Enabled" if enabled else "Disabled"
        self.rule_table.setItem(row, 3, QTableWidgetItem(status))
        try:
            self.save_rule_state(row, enabled)
        except Exception as e:
            QMessageBox.critical(self, "Rule Update Error", f"Failed to update rule:\n{e}")

    def save_rule_state(self, row, enabled):
        if row < 0 or row >= len(self.rule_records):
            return False

        rule = self.rule_records[row]
        write_rule_enabled(rule["file"], rule["id"], enabled)
        rule["enabled"] = bool(enabled)
        return True

    def save_rule_states(self):
        for row, rule in enumerate(self.rule_records):
            checkbox = self.rule_table.cellWidget(row, 4)
            if not checkbox:
                continue
            enabled = checkbox.isChecked()
            write_rule_enabled(rule["file"], rule["id"], enabled)
            rule["enabled"] = enabled

    def reset_to_default(self):
        reply = QMessageBox.question(
            self, "Reset Settings", 
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            interfaces = get_available_interfaces()
            self.capture_interface.clear()
            self.capture_interface.addItems(interfaces)
            self.capture_interface.setCurrentText("All")
            self.capture_mode.setCurrentText("Live Capture")
            self.promiscuous.setChecked(False)
            self.bpf_filter.clear()
            
            self.alerts_enabled.setChecked(True)
            self.desktop_notify.setChecked(False)
            self.sound_alert.setChecked(False)
            self.severity_filter.setCurrentText("All")
            self.retention_days.setValue(30)
            
            self.logging_enabled.setChecked(True)
            self.log_format.setCurrentText("JSON")
            self.log_file_path.setText(str(ALERTS_LOG))
            self.max_log_size.setValue(100)
            self.auto_delete.setChecked(True)
            self.delete_after_days.setValue(7)
            
            for row, rule in enumerate(self.rule_defaults):
                if row >= self.rule_table.rowCount():
                    break
                status = "Enabled" if rule["enabled"] else "Disabled"
                self.rule_table.setItem(row, 3, QTableWidgetItem(status))
                cb = self.rule_table.cellWidget(row, 4)
                if cb:
                    cb.setChecked(rule["enabled"])
            
            self.save_settings()
            
            QMessageBox.information(self, "Reset Complete", "All settings have been reset to default values.")

    def update_uptime(self):
        self.uptime_seconds += 1
        self.uptime_label.setText(f"Uptime: {format_uptime(self.uptime_seconds)}")

    def update_time(self):
        self.time_label.setText(datetime.now().strftime("%I:%M:%S %p  %b %d, %Y"))