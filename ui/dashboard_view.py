import os
import random
import math
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QSizePolicy, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PySide6.QtCore import QRectF


# =========================
# 🔹 STAT CARD
# =========================
class StatCard(QFrame):
    def __init__(self, title, value, icon_path=None):
        super().__init__()

        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QHBoxLayout(self)

        if icon_path and os.path.exists(icon_path):
            icon = QLabel()
            pix = QPixmap(icon_path).scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pix)
            icon.setFixedWidth(55)
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

        text_layout = QVBoxLayout()

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: gray; font-size: 12px;")

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")

        text_layout.addWidget(title_lbl)
        text_layout.addWidget(value_lbl)

        layout.addLayout(text_layout)


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

        layout.addWidget(StatCard("Packets/sec", "1248", os.path.join(base_path, "icons/packet.png")))
        layout.addWidget(StatCard("Flows/sec", "532", os.path.join(base_path, "icons/flow.png")))
        layout.addWidget(StatCard("Alerts", "847", os.path.join(base_path, "icons/alert.png")))
        layout.addWidget(StatCard("Hosts", "156", os.path.join(base_path, "icons/host.png")))


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

        layout.addWidget(self.graph)

        self.packets = []
        self.flows = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(1000)

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

    def update_graph(self):
        self.packets.append(random.randint(80, 300))
        self.flows.append(random.randint(20, 150))

        if len(self.packets) > 30:
            self.packets.pop(0)
            self.flows.pop(0)

        self.graph.clear()

        self.graph.plot(
            self.packets,
            pen=pg.mkPen("#2196f3", width=2),
            fillLevel=0,
            brush=pg.mkBrush(33, 150, 243, 80)
        )

        self.graph.plot(
            self.flows,
            pen=pg.mkPen("#4caf50", width=2),
            fillLevel=0,
            brush=pg.mkBrush(76, 175, 80, 100)
        )


# =========================
# 🔹 DONUT CHART
# =========================
class DonutChart(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setMinimumSize(84, 84)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 6
        side = min(self.width(), self.height()) - (margin * 2)
        if side <= 0:
            return

        x = (self.width() - side) / 2
        y = (self.height() - side) / 2
        rect = QRectF(x, y, side, side)

        total = sum(value for _, value, _ in self.data)
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

        for _, value, color in self.data:
            span_angle = int(-360 * 16 * value / total)
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(arc_rect, start_angle, span_angle)

            percent = (value / total) * 100
            if percent >= 7:
                mid_angle = math.radians((start_angle + span_angle / 2) / 16)
                label_radius = (side / 2) - (ring_width / 2)
                label_x = rect.center().x() + math.cos(mid_angle) * label_radius
                label_y = rect.center().y() - math.sin(mid_angle) * label_radius
                label_rect = QRectF(label_x - 20, label_y - 9, 40, 18)

                painter.setPen(QColor("#ffffff"))
                font = QFont()
                font.setBold(True)
                font.setPointSize(max(8, int(side * 0.055)))
                painter.setFont(font)
                painter.drawText(label_rect, Qt.AlignCenter, f"{percent:.0f}%")

            start_angle += span_angle


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

        self.data = [
            ("TCP", 62.1, "#0d6efd"),
            ("UDP", 21.4, "#18b65b"),
            ("ICMP", 8.7, "#ff9800"),
            ("HTTP", 5.1, "#7b42d6"),
            ("Other", 2.7, "#8b98a8")
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        title = QLabel("Protocol Distribution")
        title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)

        self.chart = DonutChart(self.data)
        body.addWidget(self.chart, 3)

        legend = QWidget()
        legend_layout = QVBoxLayout(legend)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(0)
        legend.setMinimumWidth(112)
        legend.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        for name, value, color in self.data:
            item = QLabel(
                f"<span style='color:{color}; font-size:16px;'>■</span>"
                f"&nbsp;&nbsp;<span style='color:#ffffff; font-weight:700;'>{name}</span>"
                f"&nbsp;&nbsp;<span style='color:#c8d0dc;'>{value:.1f}%</span>"
            )
            item.setTextFormat(Qt.RichText)
            item.setMinimumHeight(14)
            item.setMinimumWidth(112)
            item.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item.setStyleSheet("""
                QLabel {
                    background: transparent;
                    font-size: 9px;
                    padding: 0;
                }
            """)
            legend_layout.addWidget(item)

        legend_layout.addStretch()
        body.addWidget(legend, 2)
        layout.addLayout(body, 1)


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

        title = QLabel("Top Source IPs")
        title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        rows = [
            ("192.168.1.100", 15),
            ("10.0.0.5", 7),
            ("172.16.0.23", 5),
        ]

        table = QFrame()
        table.setMinimumHeight(112)
        table.setStyleSheet("""
            QFrame {
                background-color: rgba(11, 18, 28, 0.35);
                border: 1px solid #2b3442;
                border-radius: 8px;
                padding: 0;
            }
        """)

        table_layout = QVBoxLayout(table)
        table_layout.setContentsMargins(8, 6, 8, 6)
        table_layout.setSpacing(0)
        table_layout.addWidget(self.source_row("IP Address", "Alerts", is_header=True))

        for ip, count in rows:
            table_layout.addWidget(self.source_row(ip, str(count)))

        layout.addWidget(table, 1)

    def source_row(self, ip, alerts, is_header=False):
        row = QFrame()
        row.setFixedHeight(24 if is_header else 23)
        row.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                border-bottom: 1px solid #2b3442;
                border-radius: 0;
                padding: 0;
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

        layout.addWidget(TrafficGraph(), 2)
        layout.addWidget(ProtocolPie(), 1)
        layout.addWidget(TopSourceIPs(), 1)


# =========================
# 🔹 ALERT TABLE
# =========================
class AlertsTable(QFrame):
    def __init__(self):
        super().__init__()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        title = QLabel("Recent Alerts")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        rows = [
            ("12:45:21", "High", "Possible Port Scan", "192.168.1.100", "10.0.0.5", "TCP", "Multiple ports scanned"),
            ("12:45:10", "High", "DoS Attack Detected", "203.184.216.34", "192.168.1.1", "TCP", "SYN flood detected"),
            ("12:44:58", "Medium", "Multiple Failed Logins", "10.0.0.5", "192.168.1.50", "TCP", "SSH brute force attempt"),
            ("12:44:37", "Medium", "ICMP Flood", "172.16.0.23", "192.168.1.1", "ICMP", "High ICMP traffic"),
            ("12:44:21", "Low", "Suspicious Activity", "192.168.1.77", "8.8.8.8", "UDP", "Unusual traffic pattern"),
        ]

        table = QTableWidget(len(rows), 7)
        table.setHorizontalHeaderLabels([
            "Time", "Severity", "Alert Type", "Source IP",
            "Destination IP", "Protocol", "Details"
        ])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setGridStyle(Qt.SolidLine)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setFocusPolicy(Qt.NoFocus)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setMinimumHeight(160)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(11, 18, 28, 0.35);
                color: #ffffff;
                border: 1px solid #2b3442;
                border-radius: 8px;
                gridline-color: #2b3442;
                font-size: 9px;
            }
            QHeaderView::section {
                background-color: rgba(24, 34, 48, 0.9);
                color: #d7dce5;
                border: none;
                border-right: 1px solid #2b3442;
                border-bottom: 1px solid #2b3442;
                padding: 3px 5px;
                font-size: 9px;
                font-weight: normal;
            }
            QTableWidget::item {
                border: none;
                padding: 3px 5px;
            }
        """)

        header = table.horizontalHeader()
        header.setFixedHeight(32)
        header.setStretchLastSection(False)
        fixed_widths = {
            0: 66,
            1: 78,
            5: 58,
        }
        for column, width in fixed_widths.items():
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            table.setColumnWidth(column, width)
        for column in [2, 3, 4, 6]:
            header.setSectionResizeMode(column, QHeaderView.Stretch)

        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                if column_index == 1:
                    table.setCellWidget(row_index, column_index, self.severity_badge(value))
                    continue

                item = QTableWidgetItem(value)
                item.setForeground(QColor("#ffffff"))
                if column_index == 5:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row_index, column_index, item)
            table.setRowHeight(row_index, 24)

        layout.addWidget(table, 1)

        view_all = QLabel("View all alerts  →")
        view_all.setStyleSheet("color: #0d6efd; font-size: 13px; font-weight: bold;")
        layout.addWidget(view_all)

    def severity_badge(self, severity):
        colors = {
            "High": ("#7f1d1d", "#ff4d4f"),
            "Medium": ("#7a4a00", "#ffb020"),
            "Low": ("#064e2f", "#21d07a"),
        }
        background, text_color = colors.get(severity, ("#263241", "#d7dce5"))

        badge = QLabel(severity)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(58, 20)
        badge.setContentsMargins(0, 0, 0, 0)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {background};
                color: {text_color};
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
            }}
        """)
        return badge


# =========================
# 🔹 DEST PORTS
# =========================
class TopPorts(QFrame):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Top Ports")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        for p, v in [("80", 40), ("443", 30), ("22", 15)]:
            row = QHBoxLayout()
            port = QLabel(p)
            port.setStyleSheet("color: #ffffff; font-size: 13px;")
            count = QLabel(str(v))
            count.setStyleSheet("color: #ffffff; font-size: 13px;")
            count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(port)
            row.addStretch()
            row.addWidget(count)
            layout.addLayout(row)


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

        layout.addWidget(AlertsTable(), 3)
        layout.addWidget(TopPorts(), 1)


# =========================
# 🔹 MAIN DASHBOARD
# =========================
class DashboardView(QWidget):
    def __init__(self):
        super().__init__()

        BASE = os.path.dirname(os.path.abspath(__file__))

        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(8)

        main.addWidget(CardsRow(BASE))
        main.addWidget(MiddleRow())
        main.addWidget(BottomRow())

        # responsive stretch
        main.setStretch(0, 0)
        main.setStretch(1, 3)
        main.setStretch(2, 4)
