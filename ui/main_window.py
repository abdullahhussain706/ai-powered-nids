import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IDS Dashboard")
        self.setGeometry(100, 100, 1200, 700)

        # Main container
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #12121f;")
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)  # ✅ no outer padding
        main_layout.setSpacing(0)                    # ✅ no gap between sidebar & content

        # Sidebar — wrapped in QWidget so stretch works correctly
        self.sidebar_widget = self.create_sidebar()
        main_layout.addWidget(self.sidebar_widget, 0)  # fixed width, no stretch

        # Thin divider line
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #2d2d3a;")
        main_layout.addWidget(divider)

        # Stacked Views — takes all remaining space
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #12121f;")
        main_layout.addWidget(self.stack, 1)           # ✅ stretch=1, fills rest

        # Views
        from ui.dashboard_view import DashboardView
        from ui.alerts_view import AlertsView

        self.dashboard_view = DashboardView()
        self.alerts_view = AlertsView()
        self.traffic_view = self.create_label_view("Traffic View")
        self.settings_view = self.create_label_view("Settings View")

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.alerts_view)
        self.stack.addWidget(self.traffic_view)
        self.stack.addWidget(self.settings_view)

        self.nav_buttons = []
        self.switch_page(0)  # default to dashboard

    def create_sidebar(self):
        # ✅ QWidget wrap — sidebar has fixed width, proper sizing
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background-color: #1e1e2f;")
        sidebar.setSizePolicy(
            sidebar.sizePolicy().horizontalPolicy(),
            sidebar.sizePolicy().verticalPolicy()
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo/title area
        title_container = QWidget()
        title_container.setFixedHeight(60)
        title_container.setStyleSheet("background-color: #1e1e2f; border-bottom: 1px solid #2d2d3a;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(12, 0, 12, 0)
        title_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("🛡 IDS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; background: transparent; border: none;")
        title_layout.addWidget(title)
        layout.addWidget(title_container)

        # Nav buttons
        nav_items = [
            ("🏠  Dashboard", 0),
            ("🔔  Alerts",    1),
            ("📶  Traffic",   2),
            ("⚙️  Settings",  3),
        ]

        self.nav_buttons = []
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setFixedHeight(44)
            btn.setCheckable(True)
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        return sidebar

    def _btn_style(self, active):
        if active:
            return """
                QPushButton {
                    background-color: #2d2d3a;
                    color: white;
                    border: none;
                    border-left: 3px solid #4caf50;
                    text-align: left;
                    padding-left: 18px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                color: #a0a0b0;
                border: none;
                border-left: 3px solid transparent;
                text-align: left;
                padding-left: 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2d2d3a;
                color: white;
            }
        """

    def create_label_view(self, text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: white;")
        layout.addWidget(label)
        return widget

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setStyleSheet(self._btn_style(i == index))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())