import sys
import os
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QFont

class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.edit_mode = False
        self.color = QColor("white")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Get screen geometry to place the clock at top right
        screen = QApplication.primaryScreen().availableGeometry()
        width, height = 160, 160
        margin = 10
        x = screen.width() - width - margin
        y = margin
        self.setGeometry(x, y, width, height)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)
        self.set_click_through(True)

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
        time = QTime.currentTime()

        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # outer circle
        pen = QPen(self.color)
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawEllipse(-90, -90, 180, 180)

        # font
        font = QFont("Segoe UI", 16, QFont.Bold)
        painter.setFont(font)

        # graphics
        for i in range(1, 13):
            painter.save()
            painter.rotate(30.0 * i)
            painter.translate(0, -68)
            painter.rotate(-30.0 * i)
            painter.drawText(-20, -20, 40, 40, Qt.AlignCenter, str(i))
            painter.restore()

        # hour
        painter.save()
        painter.rotate(30.0 * ((time.hour() + time.minute() / 60.0)))
        painter.drawLine(0, 0, 0, -40)
        painter.restore()

        # minutes
        painter.save()
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawLine(0, 0, 0, -60)
        painter.restore()

        # second
        pen.setWidth(1)
        painter.setPen(pen)
        painter.save()
        painter.rotate(6.0 * time.second())
        painter.drawLine(0, 0, 0, -75)
        painter.restore()

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