import sys
import os
import ctypes
import winreg
from PySide6.QtCore import Qt, QTimer, QTime, QDate, QLocale, QDateTime
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QFont

class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.edit_mode = False
        self.color = QColor("white")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Get screen geometry to place the clock exactly at the top right
        screen = QApplication.primaryScreen().availableGeometry()
        width, height = 160, 160
        margin = 0
        x = screen.width() - width - margin
        y = margin
        self.setGeometry(x, y, width, height)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.timer.start(16) # 60 FPS for smooth movement
        self.set_click_through(True)
        self.force_topmost()

    def on_timer_timeout(self):
        self.update()
        # Only force topmost occasionally (e.g., every 60 frames ~ 1 sec)
        if not hasattr(self, 'frame_count'): self.frame_count = 0
        self.frame_count += 1
        if self.frame_count % 60 == 0:
            self.force_topmost()
            self.frame_count = 0

    def force_topmost(self):
        """ Force the window to stay on top using Win32 API as a fallback. """
        if os.name == 'nt':
            # Win32 Constants
            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            
            # Use ctypes to call SetWindowPos periodically to ensure it's not hidden
            ctypes.windll.user32.SetWindowPos(self.winId(), HWND_TOPMOST, 0, 0, 0, 0, 
                                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        else:
            self.raise_()

    def set_click_through(self, enabled):
        if enabled:
            self.setWindowFlag(Qt.WindowTransparentForInput, True)
        else:
            self.setWindowFlag(Qt.WindowTransparentForInput, False)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        
        # Smooth time calculation
        time = QDateTime.currentDateTime().time()
        msec = time.msec()
        sec = time.second()
        minute = time.minute()
        hour = time.hour()
        
        date = QDate.currentDate()
        date_str = QLocale(QLocale.English).toString(date, "d MMMM yyyy")

        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        def draw_elements(p, color, is_shadow=False):
            offset = 2 if is_shadow else 0
            if is_shadow:
                p.translate(offset, offset)

            # outer circle
            pen = QPen(color)
            pen.setWidth(4)
            p.setPen(pen)
            p.drawEllipse(-90, -90, 180, 180)

            # Draw day/date
            p.save()
            p.setFont(QFont("Segoe UI", 8, QFont.Normal))
            p.setPen(color)
            day_str = QLocale(QLocale.English).toString(date, "dddd")
            # Elevated position to avoid 5 and 7 numbers
            p.drawText(-50, 10, 100, 15, Qt.AlignCenter, day_str)
            p.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
            p.drawText(-50, 25, 100, 20, Qt.AlignCenter, date_str)
            p.restore()

            # graphics (numbers)
            p.setFont(QFont("Segoe UI", 16, QFont.Bold))
            for i in range(1, 13):
                p.save()
                p.rotate(30.0 * i)
                p.translate(0, -68)
                p.rotate(-30.0 * i)
                p.drawText(-20, -20, 40, 40, Qt.AlignCenter, str(i))
                p.restore()

            # hour hand
            p.save()
            p.rotate(30.0 * ((hour % 12) + minute / 60.0 + sec / 3600.0))
            p.drawLine(0, 0, 0, -40)
            p.restore()

            # minutes hand
            p.save()
            p.rotate(6.0 * (minute + sec / 60.0 + msec / 60000.0))
            p.drawLine(0, 0, 0, -60)
            p.restore()

            # second hand
            pen.setWidth(1)
            p.setPen(pen)
            p.save()
            # Back to discrete "tick-tock" movement for seconds
            p.rotate(6.0 * sec)
            p.drawLine(0, 0, 0, -75)
            p.restore()
            
            if is_shadow:
                p.translate(-offset, -offset)

        # Draw Shadow first
        draw_elements(painter, QColor(0, 0, 0, 100), is_shadow=True)
        # Draw Main Clock
        draw_elements(painter, self.color)

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.edit_mode and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

def get_resource_path(relative_path):
    """ Memastikan path file benar saat di-run sebagai script maupun EXE """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def create_tray_icon(clock_widget, app):
    # Startup management
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "AnalogClockOverlay"
    
    def is_startup_enabled():
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False

    def toggle_startup(checked):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
            if checked:
                # Get the absolute path of the current script or executable
                if getattr(sys, 'frozen', False):
                    path = sys.executable
                else:
                    python_exe = sys.executable
                    script_path = os.path.abspath(sys.argv[0])
                    path = f'"{python_exe}" "{script_path}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to set startup: {e}")

    # logo
    icon_path = get_resource_path("icon.png")
    
    if os.path.exists(icon_path):
        tray_icon = QIcon(QPixmap(icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        # trycon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setBrush(QColor("cyan"))
        p.drawEllipse(10, 10, 44, 44)
        p.end()
        tray_icon = QIcon(pixmap)
    
    tray = QSystemTrayIcon(tray_icon, app)
    menu = QMenu()
    
    def toggle_edit():
        clock_widget.edit_mode = not clock_widget.edit_mode
        clock_widget.set_click_through(not clock_widget.edit_mode)
        edit_action.setChecked(clock_widget.edit_mode)

    edit_action = menu.addAction("Edit Mode (Drag)")
    edit_action.setCheckable(True)
    edit_action.triggered.connect(toggle_edit)

    color_menu = menu.addMenu("Color")
    def change_color(c):
        clock_widget.color = QColor(c)
        clock_widget.update()

    color_menu.addAction("White").triggered.connect(lambda: change_color("white"))
    color_menu.addAction("Cyan").triggered.connect(lambda: change_color("cyan"))
    color_menu.addAction("Gold").triggered.connect(lambda: change_color("gold"))

    opacity_menu = menu.addMenu("Opacity")
    opacity_menu.addAction("100%").triggered.connect(lambda: clock_widget.setWindowOpacity(1.0))
    opacity_menu.addAction("70%").triggered.connect(lambda: clock_widget.setWindowOpacity(0.7))
    opacity_menu.addAction("40%").triggered.connect(lambda: clock_widget.setWindowOpacity(0.4))

    menu.addSeparator()
    
    startup_action = menu.addAction("Run at Startup")
    startup_action.setCheckable(True)
    startup_action.setChecked(is_startup_enabled())
    startup_action.triggered.connect(toggle_startup)

    menu.addSeparator()
    menu.addAction("Exit").triggered.connect(app.quit)
    
    tray.setContextMenu(menu)
    tray.show()
    return tray

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = AnalogClock()
    tray = create_tray_icon(clock, app)
    sys.exit(app.exec())