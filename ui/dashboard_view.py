import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPainterPath


# 🔥 Rounded pixmap function (SAFE)
def get_rounded_pixmap(pixmap, radius=10):
    rounded = QPixmap(pixmap.size())
    rounded.fill(Qt.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)

    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return rounded


class StatCard(QFrame):
    def __init__(self, title, value, icon_path=None):
        super().__init__()

        # ✅ Fixed small height (space for graph)
        self.setFixedHeight(130)

        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2f;
                border-radius: 12px;
                padding: 10px;
            }
        """)

        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()

        # 🔹 ICON
        if icon_path:
            icon_label = QLabel()

            pixmap = QPixmap(icon_path)

            print("ICON:", icon_path)
            print("EXISTS:", os.path.exists(icon_path))
            print("NULL:", pixmap.isNull())

            ICON_SIZE = 40

            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    ICON_SIZE,
                    ICON_SIZE,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                pixmap = get_rounded_pixmap(pixmap, 8)
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText("❌")

            icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
            icon_label.setAlignment(Qt.AlignCenter)

            top_layout.addWidget(icon_label)

        # 🔹 TITLE
        self.title = QLabel(title)
        self.title.setStyleSheet("color: gray; font-size: 13px;")
        top_layout.addWidget(self.title)

        top_layout.addStretch()

        # 🔹 VALUE
        self.value = QLabel(value)
        self.value.setStyleSheet(
            "color: white; font-size: 20px; font-weight: bold;"
        )

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.value)

        self.setLayout(main_layout)


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        cards_layout = QHBoxLayout()

        # 🔥 SAFE PATH (works with python -m)
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        packet_icon = os.path.join(BASE_DIR, "icons", "packet.png")
        flow_icon = os.path.join(BASE_DIR, "icons", "flow.png")
        alert_icon = os.path.join(BASE_DIR, "icons", "alert.png")
        host_icon = os.path.join(BASE_DIR, "icons", "host.png")

        # 🔹 CARDS
        self.packets_card = StatCard("Packets/sec", "0", packet_icon)
        self.flows_card = StatCard("Flows/sec", "0", flow_icon)
        self.alerts_card = StatCard("Alerts", "0", alert_icon)
        self.hosts_card = StatCard("Active Hosts", "0", host_icon)

        cards_layout.addWidget(self.packets_card, 1)
        cards_layout.addWidget(self.flows_card, 1)
        cards_layout.addWidget(self.alerts_card, 1)
        cards_layout.addWidget(self.hosts_card, 1)

        cards_layout.setSpacing(15)

        # 🔥 Wrap cards (important)
        cards_container = QWidget()
        cards_container.setLayout(cards_layout)
        cards_container.setMaximumHeight(150)

        main_layout.addWidget(cards_container)

        # 🔥 Placeholder for graph (next step)
        graph_placeholder = QLabel("📊 Graph will come here")
        graph_placeholder.setAlignment(Qt.AlignCenter)
        graph_placeholder.setStyleSheet("""
            color: gray;
            font-size: 18px;
            margin-top: 20px;
        """)

        main_layout.addWidget(graph_placeholder)

        self.setLayout(main_layout)