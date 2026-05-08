# alerts_view.py - COMPLETE FINAL VERSION
# All issues fixed: balanced layout, colored severity dots, tight spacing, 12-row table,
# header subtitle inline, filters 2‑lines, pagination larger.

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QLineEdit, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPixmap, QPainter, QIcon


# ─────────────────────────────────────────────────────────────
def create_color_icon(color_hex, size=12):
    """Create a colored circle icon for severity levels."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pixmap)


# =========================
# 🔹 STAT CARD (taller, better spacing)
# =========================
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

        if icon_path and os.path.exists(icon_path):
            icon = QLabel()
            pix = QPixmap(icon_path).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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


# =========================
# 🔹 STATS ROW (4 cards)
# =========================
class AlertsStatsRow(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.high_card = AlertStatCard("High Severity", "0",
            os.path.join(base_path, "icons/high.png"), border_color="#f44336")
        self.medium_card = AlertStatCard("Medium Severity", "0",
            os.path.join(base_path, "icons/medium.png"), border_color="#ff9800")
        self.low_card = AlertStatCard("Low Severity", "0",
            os.path.join(base_path, "icons/low.png"), border_color="#4caf50")
        self.total_card = AlertStatCard("Total Alerts", "0",
            os.path.join(base_path, "icons/total.png"), border_color="#2196f3")

        layout.addWidget(self.high_card)
        layout.addWidget(self.medium_card)
        layout.addWidget(self.low_card)
        layout.addWidget(self.total_card)


# =========================
# 🔹 FILTERS BAR (2 lines, comfortable)
# =========================
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

        # Row 1: labels
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

        # Row 2: inputs + buttons
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


# =========================
# 🔹 ALERTS TABLE (12 rows, colored dot icons)
# =========================
class AlertsTable(QFrame):
    def __init__(self):
        super().__init__()
        # Header ~34px + 12 rows × 27px + 2px = 360px – exact fit, no scrollbar
        self.setFixedHeight(360)
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
        self.table.setFixedHeight(360)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)

        self.all_alerts = []
        self.rows_per_page = 12
        self.current_page = 0
        self.load_demo_data()
        layout.addWidget(self.table)

    def load_demo_data(self):
        self.all_alerts = [
            ("2025-05-24 12:45:21", "High", "Port Scan", "192.168.1.100", "10.0.0.5", "Multiple ports"),
            ("2025-05-24 12:45:10", "High", "DoS Attack", "203.184.216.34", "192.168.1.1", "SYN flood"),
            ("2025-05-24 12:44:58", "Medium", "Failed Logins", "10.0.0.5", "192.168.1.50", "SSH brute force"),
            ("2025-05-24 12:44:37", "Medium", "ICMP Flood", "172.16.0.23", "192.168.1.1", "High ICMP"),
            ("2025-05-24 12:44:21", "Low", "Suspicious", "192.168.1.77", "8.8.8.8", "Unusual pattern"),
            ("2025-05-24 12:43:58", "Medium", "DNS Amplification", "10.0.0.15", "192.168.1.100", "DNS reflection"),
            ("2025-05-24 12:43:33", "High", "Port Scan", "192.168.1.200", "10.0.0.10", "Ports 22,80,443"),
            ("2025-05-24 12:42:59", "Medium", "Brute Force", "172.16.0.50", "192.168.1.20", "FTP attack"),
            ("2025-05-24 12:42:30", "Low", "Policy Violation", "192.168.1.150", "10.0.0.30", "Blocked protocol"),
            ("2025-05-24 12:41:55", "Medium", "Malformed Packet", "10.0.0.60", "192.168.1.40", "Invalid flags"),
            ("2025-05-24 12:40:22", "High", "Port Scan", "192.168.1.55", "10.0.0.8", "Port 445"),
            ("2025-05-24 12:39:10", "Medium", "Failed Logins", "10.0.0.9", "192.168.1.70", "RDP brute"),
            ("2025-05-24 12:38:05", "Low", "Suspicious", "8.8.8.8", "192.168.1.90", "DNS tunneling"),
            ("2025-05-24 12:37:22", "High", "DoS Attack", "203.184.216.35", "192.168.1.1", "UDP flood"),
            ("2025-05-24 12:36:44", "Medium", "ICMP Flood", "172.16.0.77", "192.168.1.1", "Ping flood"),
            ("2025-05-24 12:35:33", "Low", "Policy Violation", "192.168.1.120", "10.0.0.45", "Torrent"),
            ("2025-05-24 12:34:20", "High", "Port Scan", "192.168.1.202", "10.0.0.30", "Port 22,23"),
            ("2025-05-24 12:33:15", "Medium", "Brute Force", "10.0.0.80", "192.168.1.30", "SSH attack"),
            ("2025-05-24 12:32:02", "Low", "Malformed Packet", "192.168.1.99", "10.0.0.99", "Invalid TCP"),
            ("2025-05-24 12:30:45", "High", "DoS Attack", "203.184.216.36", "192.168.1.1", "SYN flood")
        ]
        self.total_alerts = len(self.all_alerts)
        self.update_display()

    def update_display(self):
        start = self.current_page * self.rows_per_page
        end = min(start + self.rows_per_page, self.total_alerts)
        page_alerts = self.all_alerts[start:end]
        self.table.setRowCount(len(page_alerts))

        for row, (time, severity, atype, src, dst, det) in enumerate(page_alerts):
            self.table.setItem(row, 0, QTableWidgetItem(time))

            # Create colored dot icon based on severity
            if severity == "High":
                icon = create_color_icon("#f44336")
            elif severity == "Medium":
                icon = create_color_icon("#ff9800")
            else:
                icon = create_color_icon("#4caf50")

            sev_item = QTableWidgetItem(severity)
            sev_item.setIcon(icon)                # icon appears left of text
            if severity == "High":
                sev_item.setForeground(QBrush(QColor("#f44336")))
            elif severity == "Medium":
                sev_item.setForeground(QBrush(QColor("#ff9800")))
            else:
                sev_item.setForeground(QBrush(QColor("#4caf50")))
            self.table.setItem(row, 1, sev_item)

            self.table.setItem(row, 2, QTableWidgetItem(atype))
            self.table.setItem(row, 3, QTableWidgetItem(src))
            self.table.setItem(row, 4, QTableWidgetItem(dst))
            self.table.setItem(row, 5, QTableWidgetItem(det))

    def go_to_page(self, page):
        self.current_page = page
        self.update_display()

    def next_page(self):
        if (self.current_page + 1) * self.rows_per_page < self.total_alerts:
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


# =========================
# 🔹 PAGINATION BAR (larger buttons, clear info)
# =========================
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


# =========================
# 🔹 MAIN ALERTS VIEW (compact, subtitle inline, complete)
# =========================
class AlertsView(QWidget):
    def __init__(self):
        super().__init__()
        BASE = os.path.dirname(os.path.abspath(__file__))
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Header row: title + subtitle inline, export button right
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

        # Stats row
        self.stats_row = AlertsStatsRow(BASE)
        main_layout.addWidget(self.stats_row)

        # Filters bar
        self.filters_bar = FiltersBar()
        main_layout.addWidget(self.filters_bar)

        # Table (12 rows, colored severity dots)
        self.alerts_table = AlertsTable()
        main_layout.addWidget(self.alerts_table)

        # Pagination
        self.pagination = PaginationBar(
            on_page_change=self.on_page_change,
            on_next=self.on_next_page,
            on_prev=self.on_prev_page
        )
        main_layout.addWidget(self.pagination)

        # Connect filter buttons
        self.filters_bar.apply_btn.clicked.connect(self.apply_filters)
        self.filters_bar.reset_btn.clicked.connect(self.reset_filters)

        self.update_pagination_info()
        self.update_demo_stats()

    def update_demo_stats(self):
        # placeholder stats – replace with backend later
        self.stats_row.high_card.value_lbl.setText("5")
        self.stats_row.medium_card.value_lbl.setText("9")
        self.stats_row.low_card.value_lbl.setText("6")
        self.stats_row.total_card.value_lbl.setText("20")

    def update_pagination_info(self):
        total = self.alerts_table.total_alerts
        per_page = self.alerts_table.rows_per_page
        current = self.alerts_table.current_page
        start = current * per_page + 1
        end = min((current + 1) * per_page, total)
        self.pagination.update_info(start, end, total)
        total_pages = (total + per_page - 1) // per_page
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

    def apply_filters(self):
        QMessageBox.information(self, "Filter", "Filter feature will be implemented in backend.")

    def reset_filters(self):
        self.filters_bar.severity_combo.setCurrentIndex(0)
        self.filters_bar.type_combo.setCurrentIndex(0)
        self.filters_bar.protocol_combo.setCurrentIndex(0)
        self.filters_bar.src_ip.clear()
        QMessageBox.information(self, "Reset", "Filters reset.")

    def export_csv(self):
        QMessageBox.information(self, "Export CSV", "📎 Export CSV feature will be implemented in the backend.\nThis is a frontend placeholder.")