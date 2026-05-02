import os
import random
import pyqtgraph as pg

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor
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

        layout = QHBoxLayout(self)
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
        layout.addWidget(title)

        self.graph = pg.PlotWidget()
        self.graph.setBackground("#1e1e2f")
        self.graph.showGrid(x=True, y=True, alpha=0.3)

        layout.addWidget(self.graph)

        self.packets = []
        self.flows = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(1000)

    def update_graph(self):
        self.packets.append(random.randint(80, 300))
        self.flows.append(random.randint(20, 150))

        if len(self.packets) > 30:
            self.packets.pop(0)
            self.flows.pop(0)

        self.graph.clear()

        self.graph.plot(
            self.packets,
            pen=pg.mkPen("#4caf50", width=2),
            fillLevel=0,
            brush=pg.mkBrush(76, 175, 80, 100)
        )

        self.graph.plot(
            self.flows,
            pen=pg.mkPen("#2196f3", width=2),
            fillLevel=0,
            brush=pg.mkBrush(33, 150, 243, 80)
        )


# =========================
# 🔹 PIE CHART
# =========================
class ProtocolPie(QFrame):
    def __init__(self):
        super().__init__()

        self.setMinimumHeight(100)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 10px;
            }
        """)

        self.data = [
            ("TCP", 40, "#4caf50"),
            ("UDP", 25, "#2196f3"),
            ("ICMP", 20, "#ff9800"),
            ("Other", 15, "#f44336")
        ]

        layout = QVBoxLayout(self)

        title = QLabel("Protocols")
        title.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(title)

        self.chart = QWidget()
        layout.addWidget(self.chart)

        self.chart.paintEvent = self.draw_chart

    def draw_chart(self, event):
        painter = QPainter(self.chart)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(20, 20, 140, 140)

        total = sum(v for _, v, _ in self.data)
        start = 0

        for _, val, color in self.data:
            angle = 360 * val / total
            painter.setBrush(QColor(color))
            painter.drawPie(rect, int(start * 16), int(angle * 16))
            start += angle


# =========================
# 🔹 TOP SOURCE IP
# =========================
class TopSourceIPs(QFrame):
    def __init__(self):
        super().__init__()

        self.setMinimumHeight(200)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("Top Source IPs")
        title.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(title)

        for ip, val in [
            ("192.168.1.10", 25),
            ("10.0.0.5", 18),
            ("172.16.0.2", 12),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(ip))
            row.addStretch()
            row.addWidget(QLabel(str(val)))
            layout.addLayout(row)


# =========================
# 🔹 MIDDLE ROW
# =========================
class MiddleRow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setSpacing(5)

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
                padding: 5px;
            }
            QTableWidget {
                background: transparent;
                color: white;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("Recent Alerts")
        title.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(title)

        table = QTableWidget(5, 5)
        table.setHorizontalHeaderLabels(["Time", "Type", "IP"])

        for r, row in enumerate([
            ("12:01", "Port Scan", "192.168.1.10"),
            ("12:02", "DoS", "10.0.0.5"),
        ]):
            for c, val in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(val))

        layout.addWidget(table)


# =========================
# 🔹 DEST PORTS
# =========================
class TopPorts(QFrame):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(200)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Top Ports"))

        for p, v in [("80", 40), ("443", 30), ("22", 15)]:
            row = QHBoxLayout()
            row.addWidget(QLabel(p))
            row.addStretch()
            row.addWidget(QLabel(str(v)))
            layout.addLayout(row)


# =========================
# 🔹 BOTTOM ROW
# =========================
class BottomRow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setSpacing(2)

        layout.addWidget(AlertsTable(), 2)
        layout.addWidget(TopPorts(), 1)


# =========================
# 🔹 MAIN DASHBOARD
# =========================
class DashboardView(QWidget):
    def __init__(self):
        super().__init__()

        BASE = os.path.dirname(os.path.abspath(__file__))

        main = QVBoxLayout(self)
        main.setSpacing(0.2)

        main.addWidget(CardsRow(BASE))
        main.addWidget(MiddleRow())
        main.addWidget(BottomRow())

        # responsive stretch
        main.setStretch(0, 1)
        main.setStretch(1, 3)
        main.setStretch(2, 3)