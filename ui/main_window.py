import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IDS Dashboard")
        self.setGeometry(100, 100, 1200, 700)

        # Main container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # Sidebar
        self.sidebar = self.create_sidebar()
        main_layout.addLayout(self.sidebar, 1)

        # Stacked Views
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 4)

        # Views
        from ui.dashboard_view import DashboardView
        self.dashboard_view = DashboardView()
        self.alerts_view = self.create_label_view("Alerts View")
        self.traffic_view = self.create_label_view("Traffic View")
        self.settings_view = self.create_label_view("Settings View")

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.alerts_view)
        self.stack.addWidget(self.traffic_view)
        self.stack.addWidget(self.settings_view)

    def create_sidebar(self):
        layout = QVBoxLayout()

        title = QLabel("IDS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Buttons
        btn_dashboard = QPushButton("Dashboard")
        btn_alerts = QPushButton("Alerts")
        btn_traffic = QPushButton("Traffic")
        btn_settings = QPushButton("Settings")

        # Connect buttons
        btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        btn_alerts.clicked.connect(lambda: self.switch_page(1))
        btn_traffic.clicked.connect(lambda: self.switch_page(2))
        btn_settings.clicked.connect(lambda: self.switch_page(3))

        # Add buttons
        for btn in [btn_dashboard, btn_alerts, btn_traffic, btn_settings]:
            btn.setFixedHeight(40)
            layout.addWidget(btn)

        layout.addStretch()
        return layout

    def create_label_view(self, text):
        widget = QWidget()
        layout = QVBoxLayout()

        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")

        layout.addWidget(label)
        widget.setLayout(layout)

        return widget

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())