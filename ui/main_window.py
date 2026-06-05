import sys
import os
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont, QPainterPath


class AboutView(QWidget):
    """About page showing application information."""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # App title
        title = QLabel("🛡 IDS Dashboard")
        title.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel("Version 1.0.0")
        version.setStyleSheet("font-size: 18px; color: #a0a0b0; font-weight: bold;")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # Description
        desc = QLabel(
            "Intrusion Detection System Dashboard\n\n"
            "A comprehensive network security monitoring solution that detects\n"
            "and alerts on suspicious network activities in real-time.\n\n"
            "Features:\n"
            "• Real-time traffic monitoring\n"
            "• Alert management with severity levels\n"
            "• Protocol distribution analysis\n"
            "• Log management and export\n"
            "• Rule-based detection engine"
        )
        desc.setStyleSheet("font-size: 15px; color: #c0c0d0; background: #1e1e2f; border-radius: 12px; padding: 20px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Tech stack
        tech = QLabel(
            "Built with:\n"
            "• Python 3.11+\n"
            "• PySide6 (Qt6)\n"
            "• SQLite3\n"
            "• PyQtGraph"
        )
        tech.setStyleSheet("font-size: 13px; color: #a0a0b0; background: #1e1e2f; border-radius: 12px; padding: 15px;")
        tech.setAlignment(Qt.AlignCenter)
        layout.addWidget(tech)
        
        # Footer
        footer = QLabel("© 2025 IDS Dashboard | All Rights Reserved")
        footer.setStyleSheet("font-size: 12px; color: #6a6a7a;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
        
        layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IDS Dashboard")
        self.setGeometry(100, 100, 1200, 700)
        
        # CRITICAL: Set WM_CLASS for Ubuntu taskbar icon
        self.setWindowFilePath("IDS-Dashboard")
        self.setWindowIcon(self.load_icon())
        
        # Main container
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #12121f;")
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar_widget = self.create_sidebar()
        main_layout.addWidget(self.sidebar_widget, 0)

        # Thin divider line
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background-color: #2d2d3a;")
        main_layout.addWidget(divider)

        # Stacked Views
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #12121f;")
        main_layout.addWidget(self.stack, 1)

        # Views
        from ui.dashboard_view import DashboardView
        from ui.alerts_view import AlertsView
        from ui.settings_view import SettingsView
        from ui.logs_view import LogsView

        self.dashboard_view = DashboardView()
        self.alerts_view = AlertsView()
        self.about_view = AboutView()           # About page
        self.logs_view = LogsView()
        self.settings_view = SettingsView()

        self.stack.addWidget(self.dashboard_view)   # index 0
        self.stack.addWidget(self.alerts_view)      # index 1
        self.stack.addWidget(self.about_view)       # index 2
        self.stack.addWidget(self.logs_view)        # index 3
        self.stack.addWidget(self.settings_view)    # index 4

        self.nav_buttons = []
        self.switch_page(0)

    def load_icon(self):
        """Load icon from various possible locations."""
        base_path = Path(__file__).parent
        
        icon_paths = [
            base_path / "ui" / "icons" / "app_icon.png",
            base_path / "ui" / "icons" / "app_icon.ico",
            base_path / "ui" / "icons" / "ids_icon.png",
            base_path / "ui" / "icons" / "logo.png",
            base_path / "icons" / "app_icon.png",
            base_path / "app_icon.png",
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    print(f"✅ Icon found: {icon_path}")
                    return QIcon(pixmap)
        
        # Fallback: create a colored icon with "IDS" text
        print("⚠️ No icon file found. Creating fallback icon...")
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#2196f3")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "IDS")
        painter.end()
        
        return QIcon(pixmap)

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1e1e2f;")
        sidebar.setSizePolicy(
            sidebar.sizePolicy().horizontalPolicy(),
            sidebar.sizePolicy().verticalPolicy()
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo/title area (with icon)
        title_container = QWidget()
        title_container.setFixedHeight(70)
        title_container.setStyleSheet("background-color: #1e1e2f; border-bottom: 2px solid #2d2d3a;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(15, 0, 15, 0)
        title_layout.setAlignment(Qt.AlignCenter)

        # Add icon next to title
        icon_label = QLabel()
        icon = self.load_icon()
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(28, 28))
        icon_label.setStyleSheet("background: transparent;")
        title_layout.addWidget(icon_label)

        title = QLabel("IDS")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: white; background: transparent; border: none;")
        title_layout.addWidget(title)

        layout.addWidget(title_container)

        # Nav buttons with icons
        nav_items = [
            ("📊  Dashboard", 0),
            ("⚠️  Alerts",    1),
            ("📋  Logs",      3),
            ("⚙️  Settings",  4),
        ]

        self.nav_buttons = []
        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setFixedHeight(50)
            btn.setCheckable(True)
            btn.setStyleSheet(self._btn_style(False))
            btn.clicked.connect(lambda checked, i=idx: self.switch_page(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        # Add stretch to push About button and time to bottom
        layout.addStretch()

        # About button at the bottom with icon
        btn_about = QPushButton("ℹ️  About")
        btn_about.setFixedHeight(50)
        btn_about.setCheckable(True)
        btn_about.setStyleSheet(self._btn_style(False))
        btn_about.clicked.connect(lambda checked, i=2: self.switch_page(2))
        self.nav_buttons.append(btn_about)
        layout.addWidget(btn_about)

        # System time at the very bottom - 2 columns layout
        time_container = QWidget()
        time_container.setFixedHeight(80)
        time_container.setStyleSheet("background-color: #1a1a2a; border-top: 2px solid #2d2d3a;")
        
        # Main horizontal layout for 2 columns
        time_main_layout = QHBoxLayout(time_container)
        time_main_layout.setContentsMargins(10, 8, 10, 8)
        time_main_layout.setSpacing(10)
        
        # Column 1: Clock Icon (Left)
        clock_column = QVBoxLayout()
        clock_column.setAlignment(Qt.AlignCenter)
        
        clock_icon = QLabel("🕐")
        clock_icon.setStyleSheet("font-size: 28px; color: #4caf50; background: transparent;")
        clock_icon.setAlignment(Qt.AlignCenter)
        clock_column.addWidget(clock_icon)
        
        time_main_layout.addLayout(clock_column, 1)
        
        # Column 2: Time and Date (Right) - 2 rows
        datetime_column = QVBoxLayout()
        datetime_column.setAlignment(Qt.AlignCenter)
        datetime_column.setSpacing(5)
        
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            color: #4caf50; 
            font-size: 14px; 
            font-weight: bold; 
            background: transparent;
        """)
        datetime_column.addWidget(self.time_label)
        
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("""
            color: #2196f3; 
            font-size: 11px; 
            font-weight: bold; 
            background: transparent;
        """)
        datetime_column.addWidget(self.date_label)
        
        time_main_layout.addLayout(datetime_column, 2)
        
        layout.addWidget(time_container)

        # Timer to update time every second
        self.update_time()
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

        return sidebar

    def update_time(self):
        """Update the time and date display in sidebar."""
        current_time = datetime.now().strftime("%I:%M:%S %p")
        current_date = datetime.now().strftime("%b %d, %Y")
        self.time_label.setText(current_time)
        self.date_label.setText(current_date)

    def _btn_style(self, active):
        if active:
            return """
                QPushButton {
                    background-color: #2d2d3a;
                    color: white;
                    border: none;
                    border-left: 4px solid #4caf50;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 15px;
                    font-weight: bold;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                color: #c0c0d0;
                border: none;
                border-left: 4px solid transparent;
                text-align: left;
                padding-left: 20px;
                font-size: 15px;
                font-weight: bold;
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
    
    # Set application metadata
    app.setApplicationName("IDS Dashboard")
    app.setApplicationDisplayName("IDS Dashboard")
    app.setOrganizationName("IDS")
    app.setOrganizationDomain("ids.local")
    app.setDesktopFileName("ids-dashboard")
    
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    
    print("\n" + "="*50)
    print("IDS Dashboard Started")
    print("="*50)
    
    sys.exit(app.exec())