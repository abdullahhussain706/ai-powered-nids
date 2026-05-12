# logs_view.py - Real log file reader with pagination

import os
import re
from datetime import datetime
from collections import Counter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSizePolicy, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QPixmap


# === CONFIGURATION ===
LOG_FILE_PATH = "logs/capture.log"   # Change to your actual log file path
ROWS_PER_PAGE = 10


class LogStatCard(QFrame):
    def __init__(self, title, value, border_color=None, subtitle=None):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMaximumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        border_style = f"border-left: 4px solid {border_color};" if border_color else ""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1e1e2f;
                border-radius: 12px;
                {border_style}
                padding: 0px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Icon placeholder
        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 24px;")
        icon.setFixedWidth(50)
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # Text area
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #a0a0b0; font-size: 12px;")

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")

        text_layout.addWidget(title_lbl)
        text_layout.addWidget(self.value_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #6a6a7a; font-size: 10px;")
            text_layout.addWidget(sub_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()

    def set_value(self, value):
        self.value_lbl.setText(value)


class LogsView(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        self.all_logs = []          # list of dicts with keys: timestamp, level, message
        self.filtered_logs = []     # after level filter
        self.current_page = 0
        self.total_pages = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header = QLabel("Logs")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        main_layout.addWidget(header)

        subtitle = QLabel("View and analyze system logs and events.")
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 13px; margin-bottom: 8px;")
        main_layout.addWidget(subtitle)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        self.total_card = LogStatCard("Total Logs", "0", border_color="#2196f3")
        self.error_card = LogStatCard("Error Logs", "0", border_color="#f44336", subtitle="% of total")
        self.warning_card = LogStatCard("Warning Logs", "0", border_color="#ff9800", subtitle="% of total")
        self.info_card = LogStatCard("Info Logs", "0", border_color="#4caf50", subtitle="% of total")

        stats_layout.addWidget(self.total_card)
        stats_layout.addWidget(self.error_card)
        stats_layout.addWidget(self.warning_card)
        stats_layout.addWidget(self.info_card)
        main_layout.addLayout(stats_layout)

        # Filter bar
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background-color: #1e1e2f; border-radius: 8px; padding: 6px 12px;")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.addWidget(QLabel("Filter by Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All", "ERROR", "WARNING", "INFO", "DEBUG"])
        self.level_filter.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.level_filter)
        filter_layout.addStretch()
        main_layout.addWidget(filter_bar)

        # Logs Table
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(4)   # Time, Level, Source, Message
        self.logs_table.setHorizontalHeaderLabels(["Time", "Level", "Source", "Message"])
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.verticalHeader().setVisible(False)
        self.logs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.logs_table.setStyleSheet("""
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
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Level
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Source
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Message
        main_layout.addWidget(self.logs_table, 1)   # takes stretch space

        # Pagination controls
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.prev_page)
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("color: white;")
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        main_layout.addLayout(pagination_layout)

        # Bottom Timestamp
        timestamp_frame = QFrame()
        timestamp_frame.setStyleSheet("background-color: #1e1e2f; border-radius: 8px; padding: 6px 12px;")
        timestamp_layout = QHBoxLayout(timestamp_frame)
        timestamp_layout.setContentsMargins(0, 0, 0, 0)
        timestamp_layout.addStretch()
        self.timestamp_label = QLabel()
        self.timestamp_label.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        timestamp_layout.addWidget(self.timestamp_label)
        main_layout.addWidget(timestamp_frame)

        # Load real logs
        self.load_logs_from_file()
        self.update_timestamp()

        # Optional: auto-refresh every 30 seconds (can be disabled)
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.reload_logs)
        # self.timer.start(30000)

    def parse_log_line(self, line):
        """Parse a single log line. Return dict or None."""
        # Pattern: 2026-05-01 10:20:57,294 [INFO] message
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+\[(\w+)\]\s+(.*)$'
        match = re.match(pattern, line.strip())
        if match:
            timestamp = match.group(1)
            level = match.group(2).upper()
            message = match.group(3)
            # Simple source extraction: first word of message (or "System")
            source = "IDS"
            # Try to extract a subsystem (e.g., "Packet capture" -> "Capture")
            if "Starting IDS Capture" in message:
                source = "Capture"
            elif "Using interface" in message:
                source = "Interface"
            elif "Capture complete" in message:
                source = "Capture"
            elif "Parsed packets" in message:
                source = "Parser"
            elif "Flows built" in message:
                source = "Flow Builder"
            elif "Alerts generated" in message:
                source = "Detector"
            elif "Unexpected error" in message or "KeyError" in message:
                source = "Error"
            return {
                "timestamp": timestamp,
                "level": level,
                "source": source,
                "message": message
            }
        return None

    def load_logs_from_file(self):
        """Read log file and populate self.all_logs."""
        if not os.path.exists(LOG_FILE_PATH):
            QMessageBox.warning(self, "Log File Missing", f"Log file not found:\n{LOG_FILE_PATH}")
            self.all_logs = []
            self.update_stats()
            self.apply_filter()
            return

        self.all_logs = []
        try:
            with open(LOG_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed = self.parse_log_line(line)
                    if parsed:
                        self.all_logs.append(parsed)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read log file:\n{str(e)}")
        # Reverse so newest first (most recent at top)
        self.all_logs.reverse()
        self.update_stats()
        self.apply_filter()   # also resets pagination

    def reload_logs(self):
        """Reload logs (called by timer or manually)."""
        self.load_logs_from_file()

    def update_stats(self):
        """Update stat cards from self.all_logs."""
        total = len(self.all_logs)
        level_counts = Counter(log["level"] for log in self.all_logs)
        errors = level_counts.get("ERROR", 0)
        warnings = level_counts.get("WARNING", 0)
        infos = level_counts.get("INFO", 0)

        self.total_card.set_value(str(total))
        self.error_card.set_value(str(errors))
        self.warning_card.set_value(str(warnings))
        self.info_card.set_value(str(infos))

        # Update percentages in subtitle
        if total > 0:
            self.error_card.set_value(f"{errors} ({errors*100//total}%)")
            self.warning_card.set_value(f"{warnings} ({warnings*100//total}%)")
            self.info_card.set_value(f"{infos} ({infos*100//total}%)")

    def apply_filter(self):
        """Apply level filter and reset to first page."""
        level = self.level_filter.currentText()
        if level == "All":
            self.filtered_logs = self.all_logs.copy()
        else:
            self.filtered_logs = [log for log in self.all_logs if log["level"] == level]
        self.current_page = 0
        self.update_pagination()
        self.display_current_page()

    def update_pagination(self):
        total = len(self.filtered_logs)
        self.total_pages = (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE if total > 0 else 1
        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        if self.current_page < 0:
            self.current_page = 0
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")

    def display_current_page(self):
        start = self.current_page * ROWS_PER_PAGE
        end = start + ROWS_PER_PAGE
        page_logs = self.filtered_logs[start:end]

        self.logs_table.setRowCount(len(page_logs))
        for row, log in enumerate(page_logs):
            self.logs_table.setItem(row, 0, QTableWidgetItem(log["timestamp"]))
            level_item = QTableWidgetItem(log["level"])
            # Color level
            if log["level"] == "ERROR":
                level_item.setForeground(QBrush(QColor("#f44336")))
            elif log["level"] == "WARNING":
                level_item.setForeground(QBrush(QColor("#ff9800")))
            elif log["level"] == "INFO":
                level_item.setForeground(QBrush(QColor("#4caf50")))
            elif log["level"] == "DEBUG":
                level_item.setForeground(QBrush(QColor("#2196f3")))
            self.logs_table.setItem(row, 1, level_item)
            self.logs_table.setItem(row, 2, QTableWidgetItem(log["source"]))
            self.logs_table.setItem(row, 3, QTableWidgetItem(log["message"]))
        self.logs_table.resizeRowsToContents()

    def next_page(self):
        if self.current_page + 1 < self.total_pages:
            self.current_page += 1
            self.update_pagination()
            self.display_current_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_pagination()
            self.display_current_page()

    def update_timestamp(self):
        now = datetime.now()
        self.timestamp_label.setText(now.strftime("%I:%M:%S %p  %b %d, %Y"))