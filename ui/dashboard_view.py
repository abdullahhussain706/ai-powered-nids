# dashboard_view.py - Complete Corrected Version

import math
import re
import sqlite3
import pyqtgraph as pg
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtCore import QRectF


BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"
LOG_PATH = BASE_DIR / "logs" / "capture.log"
DB_PATH = BASE_DIR / "database" / "ids.db"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SUMMARY_RE = re.compile(r"Packets:\s*(\d+)\s*\|\s*Flows:\s*(\d+)")
CAPTURE_RE = re.compile(r"Capturing\b")
PARSED_RE = re.compile(r"Parsed packets:\s*(\d+)")
FLOWS_RE = re.compile(r"Flows:\s*(\d+)")
LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


def _parse_log_time(line):
    try:
        return datetime.strptime(line[:23], LOG_TIME_FORMAT)
    except ValueError:
        return None


def load_traffic_series(limit=30):
    if not LOG_PATH.exists():
        return [], [], []

    records = []
    capture_started_at = None
    pending_packets = None
    pending_recorded = False
    with LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            ts = _parse_log_time(line)
            if not ts:
                continue
            if CAPTURE_RE.search(line):
                capture_started_at = ts
                pending_packets = None
                pending_recorded = False
                continue
            match = SUMMARY_RE.search(line)
            if match:
                start_ts = capture_started_at or ts
                record = (start_ts, ts, int(match.group(1)), int(match.group(2)))
                if pending_recorded and records:
                    records[-1] = record
                else:
                    records.append(record)
                capture_started_at = None
                pending_packets = None
                pending_recorded = False
                continue

            parsed_match = PARSED_RE.search(line)
            if parsed_match:
                pending_packets = int(parsed_match.group(1))
                continue

            flows_match = FLOWS_RE.search(line)
            if pending_packets is not None and flows_match and "Packets:" not in line:
                start_ts = capture_started_at or ts
                records.append((start_ts, ts, pending_packets, int(flows_match.group(1))))
                pending_recorded = True

    if not records:
        return [], [], []

    records = records[-limit:]
    packet_rates = []
    flow_rates = []
    timeline = []

    for start_ts, end_ts, packets, flows in records:
        seconds = max((end_ts - start_ts).total_seconds(), 1)
        packet_rates.append(round(packets / seconds, 1))
        flow_rates.append(round(flows / seconds, 1))
        timeline.append(end_ts.strftime("%H:%M:%S"))

    return packet_rates, flow_rates, timeline


def get_current_rates():
    packet_series, flow_series, _ = load_traffic_series(limit=1)
    packet_rate = packet_series[-1] if packet_series else 0
    flow_rate = flow_series[-1] if flow_series else 0
    return packet_rate, flow_rate


def get_alert_count():
    if not DB_PATH.exists():
        return 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    except sqlite3.Error:
        return 0


def get_host_count():
    if not DB_PATH.exists():
        return 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return conn.execute("""
                SELECT COUNT(DISTINCT ip)
                FROM (
                    SELECT src_ip AS ip FROM alerts WHERE src_ip IS NOT NULL AND src_ip != ''
                    UNION
                    SELECT dst_ip AS ip FROM alerts WHERE dst_ip IS NOT NULL AND dst_ip != ''
                )
            """).fetchone()[0]
    except sqlite3.Error:
        return 0


def get_top_source_ips(limit=5):
    if not DB_PATH.exists():
        return [("192.168.1.100", 15), ("10.0.0.5", 7), ("172.16.0.23", 5)]

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT src_ip, COUNT(*) as count
                FROM alerts
                WHERE src_ip IS NOT NULL AND src_ip != ''
                GROUP BY src_ip
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            if rows:
                return [(row[0], row[1]) for row in rows]
            return [("No data", 0)]
    except sqlite3.Error:
        return [("192.168.1.100", 15), ("10.0.0.5", 7), ("172.16.0.23", 5)]


def get_top_ports(limit=5):
    if not DB_PATH.exists():
        return [("80 (http)", 1250), ("443 (https)", 980), ("22 (ssh)", 340)]

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dst_port, COUNT(*) as count
                FROM alerts
                WHERE dst_port IS NOT NULL AND dst_port != ''
                GROUP BY dst_port
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            if rows:
                port_names = {
                    80: "http", 443: "https", 22: "ssh", 53: "dns", 3389: "rdp",
                    21: "ftp", 25: "smtp", 110: "pop3", 143: "imap", 3306: "mysql",
                    5432: "postgres", 27017: "mongodb", 6379: "redis", 8080: "http-alt"
                }
                result = []
                for row in rows:
                    port = row[0]
                    count = row[1]
                    service = port_names.get(port, "unknown")
                    result.append((f"{port} ({service})", count))
                return result
            return [("No data", 0)]
    except sqlite3.Error:
        return [("80 (http)", 1250), ("443 (https)", 980), ("22 (ssh)", 340)]


def get_recent_alerts(limit=8):
    if not DB_PATH.exists():
        return None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT first_seen, severity, category, src_ip, dst_ip, protocol, name
                FROM alerts
                ORDER BY first_seen DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            if rows:
                return rows
            return None
    except sqlite3.Error:
        return None


def get_protocol_distribution():
    fallback_data = [
        ("TCP", 62.1, "#2f80ed"),
        ("UDP", 21.4, "#27ae60"),
        ("ICMP", 8.7, "#f2994a"),
        ("HTTP", 5.1, "#9b51e0"),
        ("Other", 2.7, "#8b98a8"),
    ]
    if not DB_PATH.exists():
        return fallback_data

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT protocol, COUNT(*) as count
                FROM alerts
                WHERE protocol IS NOT NULL AND protocol != ''
                GROUP BY protocol
                ORDER BY count DESC
            """)
            rows = cursor.fetchall()
            if not rows:
                return fallback_data

            total = sum(row[1] for row in rows)
            protocol_colors = {
                "TCP": "#2f80ed",
                "UDP": "#27ae60",
                "ICMP": "#f2994a",
                "HTTP": "#9b51e0",
                "HTTPS": "#eb5757",
                "DNS": "#56ccf2",
                "ARP": "#f2c94c",
                "SSH": "#6fcf97",
                "TLS": "#bb6bd9",
                "ICMPV6": "#ff6b35",
                "IGMP": "#f72585",
                "Other": "#8b98a8"
            }
            fallback_colors = [
                "#2f80ed", "#27ae60", "#f2994a", "#9b51e0",
                "#eb5757", "#56ccf2", "#f2c94c", "#6fcf97",
                "#bb6bd9", "#ff6b35", "#f72585", "#00a896",
            ]
            protocol_names = {
                "1": "ICMP",
                "6": "TCP",
                "17": "UDP",
                "58": "ICMPV6",
            }
            result = []
            for index, (protocol, count) in enumerate(rows):
                percent = round((count / total) * 100, 1)
                proto_upper = str(protocol).strip().upper()
                proto_upper = protocol_names.get(proto_upper, proto_upper or "Other")
                color = protocol_colors.get(
                    proto_upper,
                    fallback_colors[index % len(fallback_colors)]
                )
                result.append((proto_upper, percent, color))
            
            result.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to top 6, combine rest into "Other"
            if len(result) > 6:
                top_6 = result[:6]
                other_percent = sum(p for _, p, _ in result[6:])
                other_color = "#8b98a8"
                top_6.append(("Other", round(other_percent, 1), other_color))
                result = top_6
            
            return result
    except sqlite3.Error:
        return fallback_data


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


def format_timestamp(ts_str):
    try:
        if 'T' in ts_str:
            date_part = ts_str.split('T')[0]
            time_part = ts_str.split('T')[1].split('.')[0]
            return f"{date_part} {time_part}"
        return ts_str
    except:
        return ts_str


# =========================
# 🔹 STAT CARD
# =========================
class StatCard(QFrame):
    def __init__(self, title, value, icon_path=None, border_color=None):
        super().__init__()
        self.setMinimumHeight(100)
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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        icon_path = Path(icon_path) if icon_path else None
        if icon_path and icon_path.exists():
            icon = QLabel()
            pix = QPixmap(str(icon_path)).scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pix)
            icon.setFixedWidth(55)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)
        else:
            icon = QLabel("📊")
            icon.setStyleSheet("font-size: 20px;")
            icon.setFixedWidth(55)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(self.value_lbl)
        layout.addLayout(text_layout)
        layout.addStretch()

    def set_value(self, value):
        self.value_lbl.setText(str(value))


# =========================
# 🔹 CARDS ROW
# =========================
class CardsRow(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.packet_card = StatCard("Packets/sec", "0",
            base_path / "icons" / "packet.png", border_color="#2196f3")
        self.flow_card = StatCard("Flows/sec", "0",
            base_path / "icons" / "flow.png", border_color="#4caf50")
        self.alert_card = StatCard("Alerts", "0",
            base_path / "icons" / "alert.png", border_color="#f44336")
        self.host_card = StatCard("Hosts", "0",
            base_path / "icons" / "host.png", border_color="#ff9800")

        layout.addWidget(self.packet_card)
        layout.addWidget(self.flow_card)
        layout.addWidget(self.alert_card)
        layout.addWidget(self.host_card)

    def update_values(self, packet_rate, flow_rate, alerts, hosts):
        self.packet_card.set_value(packet_rate)
        self.flow_card.set_value(flow_rate)
        self.alert_card.set_value(alerts)
        self.host_card.set_value(hosts)


# =========================
# 🔹 TRAFFIC GRAPH
# =========================
class TrafficGraph(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        title = QLabel("Traffic Overview")
        title.setStyleSheet("color: white; font-weight: bold;")
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch()
        packets_legend = self.legend_item("#2196f3", "Packets/sec")
        flows_legend = self.legend_item("#4caf50", "Flows/sec")
        header.addWidget(packets_legend)
        header.addWidget(flows_legend)
        layout.addLayout(header)
        self.graph = pg.PlotWidget()
        self.graph.setBackground("#1e1e2f")
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.setLabel("bottom", "Timeline")
        self.graph.setLabel("left", "Rate/sec")
        self.graph.getAxis("bottom").setTextPen("#a0a0b0")
        self.graph.getAxis("left").setTextPen("#a0a0b0")
        layout.addWidget(self.graph)

    def legend_item(self, color, text):
        item = QLabel(f"<span style='color:{color}; font-size:18px;'>●</span> {text}")
        item.setMinimumWidth(95)
        item.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setTextFormat(Qt.RichText)
        item.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
                padding: 0;
            }
        """)
        return item

    def set_series(self, packets, flows, timeline):
        packets = packets[-30:]
        flows = flows[-30:]
        timeline = timeline[-30:]
        x_values = list(range(len(packets)))

        self.graph.clear()
        if not x_values:
            self.graph.getAxis("bottom").setTicks([])
            return

        tick_step = max(1, len(timeline) // 6)
        ticks = [(i, label) for i, label in enumerate(timeline) if i % tick_step == 0]
        if timeline and (len(timeline) - 1, timeline[-1]) not in ticks:
            ticks.append((len(timeline) - 1, timeline[-1]))
        self.graph.getAxis("bottom").setTicks([ticks])

        self.graph.plot(x_values, packets, pen=pg.mkPen("#2196f3", width=2),
                        fillLevel=0, brush=pg.mkBrush(33, 150, 243, 80))
        self.graph.plot(x_values, flows, pen=pg.mkPen("#4caf50", width=2),
                        fillLevel=0, brush=pg.mkBrush(76, 175, 80, 100))


# =========================
# 🔹 DONUT CHART (Multi-color)
# =========================
class DonutChart(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setMinimumSize(128, 128)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        margin = 14
        side = min(self.width(), self.height()) - (margin * 2)
        if side <= 0:
            return
        x = (self.width() - side) / 2
        y = (self.height() - side) / 2
        rect = QRectF(x, y, side, side)
        
        total = sum(percent for _, percent, _ in self.data)
        if total <= 0:
            return
            
        ring_width = max(22, int(side * 0.22))
        pen = QPen()
        pen.setWidth(ring_width)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        inset = ring_width / 2
        arc_rect = rect.adjusted(inset, inset, -inset, -inset)
        start_angle = 90 * 16
        labels = []
        
        for name, percent, color in self.data:
            span_angle = int(-360 * 16 * percent / total)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(arc_rect, start_angle, span_angle)
            
            if percent >= 6:
                mid_angle = math.radians((start_angle + span_angle / 2) / 16)
                label_radius = (side / 2) - (ring_width / 2) + 2
                label_x = rect.center().x() + math.cos(mid_angle) * label_radius
                label_y = rect.center().y() - math.sin(mid_angle) * label_radius
                label_rect = QRectF(label_x - 28, label_y - 14, 56, 28)
                labels.append((label_rect, f"{name}\n{percent:.0f}%"))
            
            start_angle += span_angle

        center_radius = max(18, int(side * 0.24))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e1e2f"))
        painter.drawEllipse(rect.center(), center_radius, center_radius)

        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(max(7, min(10, int(side * 0.055))))
        painter.setFont(font)
        for label_rect, label in labels:
            painter.drawText(label_rect, Qt.AlignCenter, label)


# =========================
# 🔹 PROTOCOL PIE (With Colors and Names)
# =========================
class ProtocolPie(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        self.title = QLabel("Protocol Distribution")
        self.title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)

        self.chart = DonutChart([])
        body.addWidget(self.chart, 3)

        self.legend_widget = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setSpacing(1)
        self.legend_widget.setMinimumWidth(92)
        self.legend_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        body.addWidget(self.legend_widget, 2)
        layout.addLayout(body, 1)

        self.refresh()

    def _refresh_table_legacy(self):
        return
        data = get_protocol_distribution()
        self.chart.set_data(data)
        self.legend_table.setRowCount(len(data))

        for row, (name, percent, color) in enumerate(data):
            protocol_item = QTableWidgetItem(f"■ {name}")
            protocol_item.setForeground(QColor(color))
            protocol_item.setToolTip(name)

            percent_item = QTableWidgetItem(f"{percent:.1f}")
            percent_item.setForeground(QColor("#c8d0dc"))
            percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.legend_table.setItem(row, 0, protocol_item)
            self.legend_table.setItem(row, 1, percent_item)

        table_height = 24 + (len(data) * 20)
        self.legend_table.setFixedHeight(table_height)

    def refresh(self):
        data = get_protocol_distribution()
        self.chart.set_data(data)

        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    subitem = item.layout().takeAt(0)
                    if subitem.widget():
                        subitem.widget().deleteLater()

        for name, percent, color in data:
            row = QWidget()
            row.setFixedHeight(18)
            row.setStyleSheet("background: transparent; border: none; padding: 0;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            color_dot = QLabel()
            color_dot.setFixedSize(8, 8)
            color_dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            row_layout.addWidget(color_dot)

            name_label = QLabel(name)
            name_label.setToolTip(name)
            name_label.setStyleSheet("color: #ffffff; font-size: 9px; background: transparent;")
            row_layout.addWidget(name_label, 1)

            percent_label = QLabel(f"{percent:.0f}%")
            percent_label.setFixedWidth(30)
            percent_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            percent_label.setStyleSheet("color: #c8d0dc; font-size: 9px; background: transparent;")
            row_layout.addWidget(percent_label)

            self.legend_layout.addWidget(row)

        self.legend_layout.addStretch()


# =========================
# 🔹 TOP SOURCE IP
# =========================
class TopSourceIPs(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)

        self.title = QLabel("Top Source IPs")
        self.title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title)

        self.table = QFrame()
        self.table.setMinimumHeight(112)
        self.table.setStyleSheet("""
            QFrame {
                background-color: rgba(11, 18, 28, 0.35);
                border: 1px solid #2b3442;
                border-radius: 8px;
                padding: 0;
            }
        """)
        self.table_layout = QVBoxLayout(self.table)
        self.table_layout.setContentsMargins(8, 6, 8, 6)
        self.table_layout.setSpacing(0)

        self.table_layout.addWidget(self.source_row("IP Address", "Alerts", is_header=True))

        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self):
        while self.table_layout.count() > 1:
            item = self.table_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        rows = get_top_source_ips(limit=5)
        for ip, count in rows:
            self.table_layout.addWidget(self.source_row(str(ip), str(count)))

    def source_row(self, ip, alerts, is_header=False):
        row = QFrame()
        row.setFixedHeight(24 if is_header else 23)
        row.setStyleSheet("""
            QFrame {
                background: transparent; border: none;
                border-bottom: 1px solid #2b3442;
                border-radius: 0; padding: 0;
            }
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        ip_label = QLabel(ip)
        ip_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #2b3442; border: none;")

        alert_label = QLabel(alerts)
        alert_label.setFixedWidth(36)
        alert_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if is_header:
            ip_label.setStyleSheet("color: #d7dce5; font-size: 9px;")
            alert_label.setStyleSheet("color: #d7dce5; font-size: 9px;")
        else:
            ip_label.setStyleSheet("color: #ffffff; font-size: 9px;")
            alert_label.setStyleSheet("color: #ff4d4f; font-size: 9px; font-weight: bold;")

        layout.addWidget(ip_label, 1)
        layout.addWidget(divider)
        layout.addWidget(alert_label)
        return row


# =========================
# 🔹 TOP PORTS
# =========================
class TopPorts(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)

        self.title = QLabel("Top Ports")
        self.title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title)

        self.table = QFrame()
        self.table.setMinimumHeight(112)
        self.table.setStyleSheet("""
            QFrame {
                background-color: rgba(11, 18, 28, 0.35);
                border: 1px solid #2b3442;
                border-radius: 8px;
                padding: 0;
            }
        """)
        self.table_layout = QVBoxLayout(self.table)
        self.table_layout.setContentsMargins(8, 6, 8, 6)
        self.table_layout.setSpacing(0)

        self.table_layout.addWidget(self._row("Port (Service)", "Count", is_header=True))

        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self):
        while self.table_layout.count() > 1:
            item = self.table_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        rows = get_top_ports(limit=5)
        for port, count in rows:
            self.table_layout.addWidget(self._row(str(port), str(count)))

    def _row(self, port, count, is_header=False):
        row = QFrame()
        row.setFixedHeight(24 if is_header else 23)
        row.setStyleSheet("""
            QFrame {
                background: transparent; border: none;
                border-bottom: 1px solid #2b3442;
                border-radius: 0; padding: 0;
            }
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        port_label = QLabel(port)
        port_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #2b3442; border: none;")

        count_label = QLabel(count)
        count_label.setFixedWidth(36)
        count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        if is_header:
            port_label.setStyleSheet("color: #d7dce5; font-size: 9px;")
            count_label.setStyleSheet("color: #d7dce5; font-size: 9px;")
        else:
            port_label.setStyleSheet("color: #ffffff; font-size: 9px;")
            count_label.setStyleSheet("color: #2196f3; font-size: 9px; font-weight: bold;")

        layout.addWidget(port_label, 1)
        layout.addWidget(divider)
        layout.addWidget(count_label)
        return row


# =========================
# 🔹 MIDDLE ROW
# =========================
class MiddleRow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.traffic_graph = TrafficGraph()
        self.protocol_pie = ProtocolPie()
        self.top_source_ips = TopSourceIPs()
        layout.addWidget(self.traffic_graph, 2)
        layout.addWidget(self.protocol_pie, 1)
        layout.addWidget(self.top_source_ips, 1)

    def update_graph(self, packet_series, flow_series, timeline):
        self.traffic_graph.set_series(packet_series, flow_series, timeline)

    def refresh(self):
        self.top_source_ips.refresh()
        self.protocol_pie.refresh()


# =========================
# 🔹 ALERT TABLE
# =========================
class AlertsTable(QFrame):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame { background-color: #1e1e2f; border-radius: 8px; padding: 0px; }
            QTableWidget { background-color: #1e1e2f; color: white; gridline-color: #2d2d3a; border: none; }
            QHeaderView::section {
                background-color: #2d2d3a; color: #a0a0b0;
                padding: 6px; border: none; font-weight: bold; font-size: 11px;
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
        self.table.setFixedHeight(246)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 150)

        layout.addWidget(self.table)

        self.view_all = QLabel("View all alerts  →")
        self.view_all.setStyleSheet("color: #0d6efd; font-size: 12px; font-weight: bold; margin-top: 6px;")
        self.view_all.setCursor(Qt.PointingHandCursor)
        self.view_all.mousePressEvent = self.go_to_alerts_page
        layout.addWidget(self.view_all, alignment=Qt.AlignRight)

        self.refresh()

    def refresh(self):
        rows = get_recent_alerts(limit=8)

        if not rows:
            self.load_demo_data()
            return

        self.table.setRowCount(len(rows))
        for row, alert in enumerate(rows):
            timestamp = format_timestamp(alert[0])
            severity = normalize_severity(alert[1])

            self.table.setItem(row, 0, QTableWidgetItem(timestamp))
            sev_item = QTableWidgetItem(severity)
            if severity == "High":
                sev_item.setForeground(QColor("#ff4d4f"))
            elif severity == "Medium":
                sev_item.setForeground(QColor("#ffb020"))
            else:
                sev_item.setForeground(QColor("#21d07a"))
            self.table.setItem(row, 1, sev_item)
            self.table.setItem(row, 2, QTableWidgetItem(alert[2] or "Unknown"))
            self.table.setItem(row, 3, QTableWidgetItem(alert[3] or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(alert[4] or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(alert[6] or alert[5] or "-"))

    def load_demo_data(self):
        demo_alerts = [
            ("2025-05-24 12:45:21", "High", "Port Scan", "192.168.1.100", "10.0.0.5", "Multiple ports"),
            ("2025-05-24 12:45:10", "High", "DoS Attack", "203.184.216.34", "192.168.1.1", "SYN flood"),
            ("2025-05-24 12:44:58", "Medium", "Failed Logins", "10.0.0.5", "192.168.1.50", "SSH brute force"),
            ("2025-05-24 12:44:37", "Medium", "ICMP Flood", "172.16.0.23", "192.168.1.1", "High ICMP"),
            ("2025-05-24 12:44:21", "Low", "Suspicious", "192.168.1.77", "8.8.8.8", "Unusual pattern"),
            ("2025-05-24 12:43:58", "Medium", "DNS Amplification", "10.0.0.15", "192.168.1.100", "DNS reflection"),
            ("2025-05-24 12:43:33", "High", "Port Scan", "192.168.1.200", "10.0.0.10", "Ports 22,80,443"),
            ("2025-05-24 12:42:59", "Medium", "Brute Force", "172.16.0.50", "192.168.1.20", "FTP attack"),
        ]
        self.table.setRowCount(len(demo_alerts))
        for row, (time, severity, atype, src, dst, det) in enumerate(demo_alerts):
            self.table.setItem(row, 0, QTableWidgetItem(time))
            sev_item = QTableWidgetItem(severity)
            if severity == "High":
                sev_item.setForeground(QColor("#ff4d4f"))
            elif severity == "Medium":
                sev_item.setForeground(QColor("#ffb020"))
            else:
                sev_item.setForeground(QColor("#21d07a"))
            self.table.setItem(row, 1, sev_item)
            self.table.setItem(row, 2, QTableWidgetItem(atype))
            self.table.setItem(row, 3, QTableWidgetItem(src))
            self.table.setItem(row, 4, QTableWidgetItem(dst))
            self.table.setItem(row, 5, QTableWidgetItem(det))

    def go_to_alerts_page(self, event):
        main_window = self.window()
        if hasattr(main_window, 'stack'):
            main_window.stack.setCurrentIndex(1)


# =========================
# 🔹 BOTTOM ROW
# =========================
class BottomRow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.alerts_table = AlertsTable()
        self.top_ports = TopPorts()
        layout.addWidget(self.alerts_table, 3)
        layout.addWidget(self.top_ports, 1)

    def refresh(self):
        self.alerts_table.refresh()
        self.top_ports.refresh()


# =========================
# 🔹 MAIN DASHBOARD
# =========================
class DashboardView(QWidget):
    def __init__(self):
        super().__init__()

        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(8)

        header_widget = QWidget()
        header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        dashboard_title = QLabel("Dashboard")
        dashboard_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(dashboard_title)

        subtitle = QLabel("Real-time overview of network activity and security events")
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignVCenter)
        header_layout.addWidget(subtitle)

        header_layout.addStretch()
        main.addWidget(header_widget)

        self.cards_row = CardsRow(UI_DIR)
        self.middle_row = MiddleRow()
        self.bottom_row = BottomRow()

        main.addWidget(self.cards_row)
        main.addWidget(self.middle_row)
        main.addWidget(self.bottom_row)

        main.setStretch(0, 0)
        main.setStretch(1, 0)
        main.setStretch(2, 3)
        main.setStretch(3, 4)

        # Timer for traffic data (1 second)
        self.traffic_timer = QTimer()
        self.traffic_timer.timeout.connect(self.refresh_traffic)
        self.traffic_timer.start(1000)

        # Timer for database data (5 seconds)
        self.db_timer = QTimer()
        self.db_timer.timeout.connect(self.refresh_db_data)
        self.db_timer.start(5000)

        self.refresh_traffic()
        self.refresh_db_data()

    def refresh_traffic(self):
        packet_series, flow_series, timeline = load_traffic_series(limit=30)
        packet_rate = packet_series[-1] if packet_series else 0
        flow_rate = flow_series[-1] if flow_series else 0

        self.cards_row.update_values(
            packet_rate,
            flow_rate,
            get_alert_count(),
            get_host_count()
        )
        self.middle_row.update_graph(packet_series, flow_series, timeline)

    def refresh_db_data(self):
        packet_val = self.cards_row.packet_card.value_lbl.text()
        flow_val = self.cards_row.flow_card.value_lbl.text()
        packet_rate = float(packet_val) if packet_val.replace('.', '').isdigit() else 0
        flow_rate = float(flow_val) if flow_val.replace('.', '').isdigit() else 0

        self.cards_row.update_values(
            packet_rate,
            flow_rate,
            get_alert_count(),
            get_host_count()
        )
        self.middle_row.refresh()
        self.bottom_row.refresh()
