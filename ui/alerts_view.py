

import csv
import sqlite3
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QLineEdit, QSizePolicy, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPixmap, QPainter, QIcon


BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"
DB_PATH = BASE_DIR / "database" / "ids.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def create_color_icon(color_hex, size=12):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pixmap)


def format_timestamp(ts_str):
    try:
        if 'T' in ts_str:
            date_part = ts_str.split('T')[0]
            time_part = ts_str.split('T')[1].split('.')[0]
            return f"{date_part} {time_part}"
        return ts_str
    except:
        return ts_str


def normalize_severity(sev):
    if not sev:
        return "Low"
    s = sev.lower()
    if s == "high":
        return "High"
    elif s == "medium":
        return "Medium"
    else:
        return "Low"


def normalize_protocol(proto):
    protocol_map = {
        "1": "ICMP",
        "6": "TCP",
        "17": "UDP",
        "58": "ICMPV6",
    }
    proto_text = str(proto or "").strip().upper()
    return protocol_map.get(proto_text, proto_text or "-")


class AlertStatCard(QFrame):
    def __init__(self, title, value, icon_path=None, border_color=None):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        border_style = f"border-left: 4px solid {border_color};" if border_color else ""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e2f;
                border-radius: 8px;
                {border_style}
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        icon_path = Path(icon_path) if icon_path else None
        if icon_path and icon_path.exists():
            icon = QLabel()
            pix = QPixmap(str(icon_path)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pix)
            icon.setFixedWidth(40)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)
        else:
            icon = QLabel("📊")
            icon.setStyleSheet("font-size: 22px;")
            icon.setFixedWidth(40)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(self.value_lbl)
        layout.addLayout(text_layout)
        layout.addStretch()


class AlertsStatsRow(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.high_card = AlertStatCard("High Severity", "0",
            base_path / "icons" / "high.png", border_color="#f44336")
        self.medium_card = AlertStatCard("Medium Severity", "0",
            base_path / "icons" / "medium.png", border_color="#ff9800")
        self.low_card = AlertStatCard("Low Severity", "0",
            base_path / "icons" / "low.png", border_color="#4caf50")
        self.total_card = AlertStatCard("Total Alerts", "0",
            base_path / "icons" / "total.png", border_color="#2196f3")

        layout.addWidget(self.high_card)
        layout.addWidget(self.medium_card)
        layout.addWidget(self.low_card)
        layout.addWidget(self.total_card)


class FiltersBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QComboBox, QLineEdit {
                background-color: #2d2d3a;
                color: white;
                border: 1px solid #3d3d4a;
                border-radius: 4px;
                padding: 5px 6px;
                font-size: 11px;
            }
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#resetBtn { background-color: #f44336; }
            QPushButton#resetBtn:hover { background-color: #da190b; }
            QLabel {
                color: #a0a0b0;
                font-size: 11px;
                margin-bottom: 3px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(5)

        labels_layout = QHBoxLayout()
        labels_layout.setSpacing(8)
        labels_layout.setContentsMargins(0, 0, 0, 0)

        lbl_severity = QLabel("Severity")
        lbl_severity.setFixedWidth(75)
        labels_layout.addWidget(lbl_severity)

        lbl_type = QLabel("Alert Type")
        lbl_type.setFixedWidth(95)
        labels_layout.addWidget(lbl_type)

        lbl_proto = QLabel("Protocol")
        lbl_proto.setFixedWidth(65)
        labels_layout.addWidget(lbl_proto)

        lbl_src = QLabel("Source IP")
        lbl_src.setFixedWidth(95)
        labels_layout.addWidget(lbl_src)

        labels_layout.addStretch()
        main_layout.addLayout(labels_layout)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["All", "High", "Medium", "Low"])
        self.severity_combo.setFixedWidth(75)
        controls_layout.addWidget(self.severity_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "Port Scan", "DoS", "Brute Force", "ICMP Flood"])
        self.type_combo.setFixedWidth(95)
        controls_layout.addWidget(self.type_combo)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["All", "TCP", "UDP", "ICMP", "HTTP"])
        self.protocol_combo.setFixedWidth(65)
        controls_layout.addWidget(self.protocol_combo)

        self.src_ip = QLineEdit()
        self.src_ip.setPlaceholderText("IP")
        self.src_ip.setFixedWidth(95)
        controls_layout.addWidget(self.src_ip)

        controls_layout.addStretch()
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setFixedWidth(65)
        controls_layout.addWidget(self.apply_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("resetBtn")
        self.reset_btn.setFixedWidth(65)
        controls_layout.addWidget(self.reset_btn)

        main_layout.addLayout(controls_layout)


class AlertsTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 8px;
                padding: 0px;
            }
            QTableWidget {
                background-color: #1e1e2f;
                color: white;
                gridline-color: #2d2d3a;
                border: none;
            }
            QHeaderView::section {
                background-color: #2d2d3a;
                color: #a0a0b0;
                padding: 6px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Time", "Severity", "Alert Type", "Source IP", "Destination IP", "Details"])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.verticalHeader().setDefaultSectionSize(27)
        self.table.setFixedHeight(380)  # Increased from 360

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)

        self.all_alerts = []
        self.filtered_alerts = []
        self.rows_per_page = 12
        self.current_page = 0
        self.total_pages = 0
        layout.addWidget(self.table)
        self.load_from_db()

    def load_from_db(self):
        if not DB_PATH.exists():
            QMessageBox.warning(self, "Database Missing", f"Database not found:\n{DB_PATH}\nUsing empty data.")
            self.all_alerts = []
        else:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                # Updated query to match new schema
                cursor.execute("""
                    SELECT first_seen, severity, category, src_ip, dst_ip, protocol, name
                    FROM alerts
                    ORDER BY first_seen DESC
                """)
                rows = cursor.fetchall()
                conn.close()
                
                if not rows:
                    QMessageBox.information(self, "No Data", "No alerts found in database.")
                    self.all_alerts = []
                else:
                    self.all_alerts = []
                    for row in rows:
                        ts_raw = row[0]
                        ts_display = format_timestamp(ts_raw)
                        sev_normalized = normalize_severity(row[1])
                        proto_normalized = normalize_protocol(row[5])
                        # Handle NULL values
                        category = row[2] if row[2] else "Unknown"
                        src_ip = row[3] if row[3] else "-"
                        dst_ip = row[4] if row[4] else "-"
                        name = row[6] if row[6] else "Alert"
                        self.all_alerts.append((ts_display, sev_normalized, category, src_ip, dst_ip, proto_normalized, name))
                    
                    print(f"Loaded {len(self.all_alerts)} alerts from database")  # Debug
                    
            except Exception as e:
                QMessageBox.critical(self, "DB Error", f"Failed to read alerts:\n{str(e)}")
                self.all_alerts = []

        self.filtered_alerts = self.all_alerts.copy()
        self.update_pagination()
        self.update_display()

    def apply_filter(self, severity, alert_type, protocol, src_ip):
        filtered = []
        for alert in self.all_alerts:
            if severity != "All" and alert[1] != severity:
                continue
            if alert_type != "All" and alert[2] != alert_type:
                continue
            if protocol != "All" and alert[5] != protocol:
                continue
            if src_ip and src_ip not in alert[3]:
                continue
            filtered.append(alert)
        return filtered

    def update_pagination(self):
        total = len(self.filtered_alerts)
        self.total_pages = (total + self.rows_per_page - 1) // self.rows_per_page if total > 0 else 1
        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        if self.current_page < 0:
            self.current_page = 0

    def update_display(self):
        start = self.current_page * self.rows_per_page
        end = min(start + self.rows_per_page, len(self.filtered_alerts))
        page_alerts = self.filtered_alerts[start:end]

        self.table.setRowCount(len(page_alerts))
        for row, alert in enumerate(page_alerts):
            timestamp, severity, atype, src, dst, proto, name = alert
            self.table.setItem(row, 0, QTableWidgetItem(timestamp))
            sev_item = QTableWidgetItem(severity)
            if severity == "High":
                icon = create_color_icon("#f44336")
                sev_item.setForeground(QBrush(QColor("#f44336")))
            elif severity == "Medium":
                icon = create_color_icon("#ff9800")
                sev_item.setForeground(QBrush(QColor("#ff9800")))
            else:
                icon = create_color_icon("#4caf50")
                sev_item.setForeground(QBrush(QColor("#4caf50")))
            sev_item.setIcon(icon)
            self.table.setItem(row, 1, sev_item)
            self.table.setItem(row, 2, QTableWidgetItem(atype))
            self.table.setItem(row, 3, QTableWidgetItem(src))
            self.table.setItem(row, 4, QTableWidgetItem(dst))
            self.table.setItem(row, 5, QTableWidgetItem(name))
        self.table.resizeRowsToContents()

    def go_to_page(self, page):
        self.current_page = page
        self.update_display()

    def next_page(self):
        if self.current_page + 1 < self.total_pages:
            self.current_page += 1
            self.update_display()
            return True
        return False

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_display()
            return True
        return False


class PaginationBar(QFrame):
    def __init__(self, on_page_change, on_next, on_prev):
        super().__init__()
        self.on_page_change = on_page_change
        self.on_next = on_next
        self.on_prev = on_prev
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 8px;
                padding: 4px 12px;
            }
            QPushButton {
                background-color: #2d2d3a;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 32px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4caf50; }
            QPushButton#activePage { background-color: #4caf50; }
            QLabel {
                color: #a0a0b0;
                font-size: 11px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        self.info_label = QLabel("Showing 1 to 12 of 0 alerts")
        layout.addWidget(self.info_label)
        layout.addStretch()

        self.prev_btn = QPushButton("←")
        self.prev_btn.setFixedSize(32, 30)
        self.prev_btn.clicked.connect(self._prev)
        layout.addWidget(self.prev_btn)

        self.page_btns = []
        for i in range(3):
            btn = QPushButton(str(i+1))
            btn.setFixedSize(32, 30)
            btn.clicked.connect(lambda checked, p=i: self._page(p))
            self.page_btns.append(btn)
            layout.addWidget(btn)

        self.next_btn = QPushButton("→")
        self.next_btn.setFixedSize(32, 30)
        self.next_btn.clicked.connect(self._next)
        layout.addWidget(self.next_btn)

        layout.addStretch()
        self.status_label = QLabel("🟢 System Running")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _page(self, idx):
        self.on_page_change(idx)
        self._set_active(idx)

    def _next(self):
        if self.on_next():
            pass

    def _prev(self):
        self.on_prev()

    def _set_active(self, idx):
        for i, btn in enumerate(self.page_btns):
            if i == idx:
                btn.setObjectName("activePage")
                btn.setStyleSheet("background-color: #4caf50;")
            else:
                btn.setObjectName("")
                btn.setStyleSheet("")

    def update_info(self, start, end, total):
        self.info_label.setText(f"Showing {start} to {end} of {total} alerts")

    def set_page_buttons(self, current_page, total_pages):
        for i, btn in enumerate(self.page_btns):
            if i < total_pages:
                btn.setText(str(i+1))
                btn.setVisible(True)
            else:
                btn.setVisible(False)
        self._set_active(current_page)


class AlertsView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title = QLabel("Alerts")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        header_layout.addWidget(title)

        subtitle = QLabel("View and manage all security alerts detected by the system.")
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 11px; margin-left: 6px;")
        subtitle.setAlignment(Qt.AlignVCenter)
        header_layout.addWidget(subtitle)

        header_layout.addStretch()
        self.export_btn = QPushButton("📎 Export CSV")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0b7dda; }
        """)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_csv)
        header_layout.addWidget(self.export_btn)

        main_layout.addLayout(header_layout)

        self.stats_row = AlertsStatsRow(UI_DIR)
        main_layout.addWidget(self.stats_row)

        self.filters_bar = FiltersBar()
        main_layout.addWidget(self.filters_bar)

        self.alerts_table = AlertsTable()
        main_layout.addWidget(self.alerts_table)

        self.pagination = PaginationBar(
            on_page_change=self.on_page_change,
            on_next=self.on_next_page,
            on_prev=self.on_prev_page
        )
        main_layout.addWidget(self.pagination)

        self.filters_bar.apply_btn.clicked.connect(self.apply_filters)
        self.filters_bar.reset_btn.clicked.connect(self.reset_filters)

        self.update_stats()
        self.update_pagination_info()

    def update_stats(self):
        total = len(self.alerts_table.all_alerts)
        high = sum(1 for a in self.alerts_table.all_alerts if a[1] == "High")
        medium = sum(1 for a in self.alerts_table.all_alerts if a[1] == "Medium")
        low = sum(1 for a in self.alerts_table.all_alerts if a[1] == "Low")
        self.stats_row.high_card.value_lbl.setText(str(high))
        self.stats_row.medium_card.value_lbl.setText(str(medium))
        self.stats_row.low_card.value_lbl.setText(str(low))
        self.stats_row.total_card.value_lbl.setText(str(total))

    def apply_filters(self):
        severity = self.filters_bar.severity_combo.currentText()
        alert_type = self.filters_bar.type_combo.currentText()
        protocol = self.filters_bar.protocol_combo.currentText()
        src_ip = self.filters_bar.src_ip.text().strip()
        filtered = self.alerts_table.apply_filter(severity, alert_type, protocol, src_ip)
        self.alerts_table.filtered_alerts = filtered
        self.alerts_table.current_page = 0
        self.alerts_table.update_pagination()
        self.alerts_table.update_display()
        self.update_pagination_info()

    def reset_filters(self):
        self.filters_bar.severity_combo.setCurrentIndex(0)
        self.filters_bar.type_combo.setCurrentIndex(0)
        self.filters_bar.protocol_combo.setCurrentIndex(0)
        self.filters_bar.src_ip.clear()
        self.alerts_table.filtered_alerts = self.alerts_table.all_alerts.copy()
        self.alerts_table.current_page = 0
        self.alerts_table.update_pagination()
        self.alerts_table.update_display()
        self.update_pagination_info()
        QMessageBox.information(self, "Reset", "Filters reset to show all alerts.")

    def update_pagination_info(self):
        total = len(self.alerts_table.filtered_alerts)
        per_page = self.alerts_table.rows_per_page
        current = self.alerts_table.current_page
        start = current * per_page + 1
        end = min((current + 1) * per_page, total)
        if total == 0:
            start = 0
            end = 0
        self.pagination.update_info(start, end, total)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        self.pagination.set_page_buttons(current, total_pages)

    def on_page_change(self, page_index):
        self.alerts_table.go_to_page(page_index)
        self.update_pagination_info()

    def on_next_page(self):
        if self.alerts_table.next_page():
            self.update_pagination_info()
            return True
        return False

    def on_prev_page(self):
        self.alerts_table.prev_page()
        self.update_pagination_info()

    def export_csv(self):
        if not self.alerts_table.filtered_alerts:
            QMessageBox.warning(self, "No Data", "No alerts to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV File", "alerts_export.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with Path(file_path).open("w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Time", "Severity", "Alert Type", "Source IP", "Destination IP", "Protocol", "Details"])
                for alert in self.alerts_table.filtered_alerts:
                    writer.writerow([alert[0], alert[1], alert[2], alert[3], alert[4], alert[5], alert[6]])
            QMessageBox.information(self, "Export Successful", f"Alerts exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{str(e)}")