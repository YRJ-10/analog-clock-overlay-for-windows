import sys
import os
import ctypes
import winreg
import winsound
from PySide6.QtCore import Qt, QTimer, QTime, QDate, QLocale, QDateTime, QPoint
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTimeEdit, QSpinBox, QPushButton
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QFont, QCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.edit_mode = False
        self.ghost_mode = True
        self.color = QColor("white")
        self.base_opacity = 1.0
        self.glow_factor = 0
        self.last_hour = QTime.currentTime().hour()
        
        self.alarm_time = None
        self.last_alarm_triggered = None
        self.timer_end_time = None
        self.timer_1m_warned = False
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Initial size and position
        self.current_width = 160
        self.current_height = 160
        self.update_geometry()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.timer.start(16) # 60 FPS for smooth movement
        self.set_click_through(True)
        self.force_topmost()
        
        # Initialize Media Player for Voice Chimes
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        


    def play_beeps(self):
        self.beep_count = 0
        def do_beep():
            try: winsound.Beep(1000, 200)
            except: pass
            self.beep_count += 1
            if self.beep_count < 4:
                QTimer.singleShot(400, do_beep)
        do_beep()
        
    def play_voice_warning(self):
        try:
            audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "tersisa_1_menit.mp3")
            if os.path.exists(audio_path):
                self.player.setSource(QUrl.fromLocalFile(audio_path))
                self.player.play()
        except Exception:
            pass

    def open_alarm_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Alarm")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Atur Waktu Alarm:"))
        time_edit = QTimeEdit()
        if self.alarm_time:
            time_edit.setTime(self.alarm_time)
        else:
            time_edit.setTime(QTime.currentTime().addSecs(3600))
        layout.addWidget(time_edit)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_clear = QPushButton("Hapus")
        btn_cancel = QPushButton("Batal")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        def on_ok():
            self.alarm_time = time_edit.time()
            dialog.accept()
        def on_clear():
            self.alarm_time = None
            dialog.accept()
            
        btn_ok.clicked.connect(on_ok)
        btn_clear.clicked.connect(on_clear)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def open_timer_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Timer")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Atur Durasi Timer (menit):"))
        spin_box = QSpinBox()
        spin_box.setRange(1, 1440)
        spin_box.setValue(5)
        layout.addWidget(spin_box)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_clear = QPushButton("Hapus")
        btn_cancel = QPushButton("Batal")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        def on_ok():
            self.timer_end_time = QDateTime.currentDateTime().addSecs(spin_box.value() * 60)
            self.timer_1m_warned = False
            dialog.accept()
        def on_clear():
            self.timer_end_time = None
            dialog.accept()
            
        btn_ok.clicked.connect(on_ok)
        btn_clear.clicked.connect(on_clear)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def update_geometry(self):
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 0
        x = screen.width() - self.current_width - margin
        y = margin
        self.setGeometry(x, y, self.current_width, self.current_height)

    def on_timer_timeout(self):
        # 1. Update drawing
        self.update()
        
        # 2. Check for Hover (Auto-Fade)
        mouse_pos = QCursor.pos()
        if self.geometry().contains(mouse_pos):
            target_opacity = 0.2
        else:
            target_opacity = self.base_opacity
            
        # Smoothly transition opacity
        curr = self.windowOpacity()
        if abs(curr - target_opacity) > 0.05:
            self.setWindowOpacity(curr + (0.05 if target_opacity > curr else -0.05))
        else:
            self.setWindowOpacity(target_opacity)

        # 3. Check for Hourly Chime
        current_time = QTime.currentTime()
        if current_time.hour() != self.last_hour and current_time.minute() == 0:
            self.trigger_chime()
            self.last_hour = current_time.hour()
            
        # Check Timer
        if self.timer_end_time:
            now = QDateTime.currentDateTime()
            rem = now.msecsTo(self.timer_end_time)
            if rem <= 0:
                self.timer_end_time = None
                self.play_beeps()
            elif rem <= 60000 and not self.timer_1m_warned:
                self.timer_1m_warned = True
                self.play_voice_warning()

        # Check Alarm
        if self.alarm_time:
            if current_time.hour() == self.alarm_time.hour() and current_time.minute() == self.alarm_time.minute():
                if self.last_alarm_triggered != self.alarm_time:
                    self.last_alarm_triggered = self.alarm_time
                    self.play_beeps()
            
        # Fade out glow
        if self.glow_factor > 0:
            self.glow_factor -= 2

        # 4. Force topmost occasionally
        if not hasattr(self, 'frame_count'): self.frame_count = 0
        self.frame_count += 1
        if self.frame_count % 60 == 0:
            self.force_topmost()
            self.frame_count = 0

    def trigger_chime(self):
        self.glow_factor = 100
        current_hour = QTime.currentTime().hour()
        
        # Coba putar file audio MP3
        try:
            audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", f"jam_{current_hour}.mp3")
            if os.path.exists(audio_path):
                self.player.setSource(QUrl.fromLocalFile(audio_path))
                self.player.play()
            else:
                winsound.Beep(1000, 200)
        except Exception as e:
            try: winsound.Beep(1000, 200)
            except: pass

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

    def refresh_overlay(self):
        effective_ghost = not self.edit_mode and self.ghost_mode
        self.setWindowFlag(Qt.WindowTransparentForInput, effective_ghost)

        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.force_topmost()
        self.raise_()
        self.update()

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
        date_str = QLocale("id").toString(date, "d MMMM yyyy")

        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        def draw_elements(p, color, is_shadow=False, is_glow=False):
            offset = 2 if is_shadow else 0
            if is_shadow:
                p.translate(offset, offset)
            
            if is_glow:
                # Draw a glow ring
                glow_pen = QPen(color)
                glow_pen.setWidth(10)
                p.setPen(glow_pen)
                p.drawEllipse(-92, -92, 184, 184)
                return

            # outer circle
            pen = QPen(color)
            pen.setWidth(4)
            p.setPen(pen)
            p.drawEllipse(-90, -90, 180, 180)

            # Draw day/date
            p.save()
            p.setFont(QFont("Segoe UI", 14, QFont.Bold))
            p.setPen(color)
            day_str = QLocale("id").toString(date, "dddd").capitalize()
            # Elevated position to avoid 5 and 7 numbers
            p.drawText(-60, 4, 120, 24, Qt.AlignCenter, day_str)
            p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            p.drawText(-60, 27, 120, 15, Qt.AlignCenter, date_str)
            p.restore()

            # Draw Alarm Icon and Text
            p.save()
            p.setFont(QFont("Segoe UI Emoji", 14))
            p.setPen(color)
            p.drawText(-45, 30, 30, 30, Qt.AlignCenter, "🔔")
            if self.alarm_time:
                p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
                p.drawText(-55, 55, 50, 15, Qt.AlignCenter, self.alarm_time.toString("HH:mm"))
            p.restore()

            # Draw Timer Icon and Text
            p.save()
            p.setFont(QFont("Segoe UI Emoji", 14))
            p.setPen(color)
            p.drawText(15, 30, 30, 30, Qt.AlignCenter, "⏳")
            if self.timer_end_time:
                rem = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
                if rem > 0:
                    secs = rem // 1000
                    mins = secs // 60
                    secs = secs % 60
                    time_str = f"{mins:02}:{secs:02}"
                    p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
                    p.drawText(5, 55, 50, 15, Qt.AlignCenter, time_str)
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
            
            if is_shadow: p.translate(-offset, -offset)

        # 1. Draw Glow (if active)
        if self.glow_factor > 0:
            glow_color = QColor(self.color)
            glow_color.setAlpha(self.glow_factor)
            draw_elements(painter, glow_color, is_glow=True)

        # 2. Draw Shadow
        draw_elements(painter, QColor(0, 0, 0, 100), is_shadow=True)
        # 3. Draw Main Clock
        draw_elements(painter, self.color)

    def mousePressEvent(self, event):
        local_pos = event.position()
        cx = self.width() / 2
        cy = self.height() / 2
        scale = min(self.width(), self.height()) / 200.0
        nx = (local_pos.x() - cx) / scale
        ny = (local_pos.y() - cy) / scale
        
        is_alarm_area = -55 <= nx <= -15 and 30 <= ny <= 70
        is_timer_area = 5 <= nx <= 45 and 30 <= ny <= 70

        if event.button() == Qt.RightButton:
            if is_alarm_area:
                self.alarm_time = None
                self.update()
                event.accept()
                return
            if is_timer_area:
                self.timer_end_time = None
                self.update()
                event.accept()
                return

        if event.button() == Qt.LeftButton:
            if is_alarm_area:
                self.open_alarm_dialog()
                event.accept()
                return
            if is_timer_area:
                self.open_timer_dialog()
                event.accept()
                return

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

    menu.addAction("Refresh Clock").triggered.connect(clock_widget.refresh_overlay)
    menu.addSeparator()

    def toggle_edit():
        clock_widget.edit_mode = not clock_widget.edit_mode
        # If edit mode is ON, we MUST disable ghost mode to allow dragging
        effective_ghost = not clock_widget.edit_mode and clock_widget.ghost_mode
        clock_widget.set_click_through(effective_ghost)
        edit_action.setChecked(clock_widget.edit_mode)

    edit_action = menu.addAction("Edit Mode (Drag)")
    edit_action.setCheckable(True)
    edit_action.triggered.connect(toggle_edit)

    def toggle_ghost(checked):
        clock_widget.ghost_mode = checked
        if not clock_widget.edit_mode:
            clock_widget.set_click_through(checked)

    ghost_action = menu.addAction("Ghost Mode (Click-through)")
    ghost_action.setCheckable(True)
    ghost_action.setChecked(clock_widget.ghost_mode)
    ghost_action.triggered.connect(toggle_ghost)

    menu.addSeparator()

    color_menu = menu.addMenu("Theme Colors")
    def change_color(c):
        clock_widget.color = QColor(c)
        clock_widget.update()

    color_menu.addAction("Classic White").triggered.connect(lambda: change_color("white"))
    color_menu.addAction("Cyan Glow").triggered.connect(lambda: change_color("#00ffff"))
    color_menu.addAction("Luxury Gold").triggered.connect(lambda: change_color("#ffd700"))
    color_menu.addAction("Neon Pink").triggered.connect(lambda: change_color("#ff00ff"))
    color_menu.addAction("Emerald Green").triggered.connect(lambda: change_color("#50c878"))
    color_menu.addAction("Midnight Blue").triggered.connect(lambda: change_color("#191970"))

    scale_menu = menu.addMenu("Scale / Size")
    def change_scale(w, h):
        clock_widget.current_width = w
        clock_widget.current_height = h
        clock_widget.update_geometry()

    scale_menu.addAction("Tiny (100px)").triggered.connect(lambda: change_scale(100, 100))
    scale_menu.addAction("Small (160px)").triggered.connect(lambda: change_scale(160, 160))
    scale_menu.addAction("Medium (240px)").triggered.connect(lambda: change_scale(240, 240))
    scale_menu.addAction("Large (320px)").triggered.connect(lambda: change_scale(320, 320))

    opacity_menu = menu.addMenu("Base Opacity")
    def set_base_opacity(o):
        clock_widget.base_opacity = o
        clock_widget.setWindowOpacity(o)

    opacity_menu.addAction("100%").triggered.connect(lambda: set_base_opacity(1.0))
    opacity_menu.addAction("70%").triggered.connect(lambda: set_base_opacity(0.7))
    opacity_menu.addAction("40%").triggered.connect(lambda: set_base_opacity(0.4))

    menu.addSeparator()
    
    startup_action = menu.addAction("Run at Startup")
    startup_action.setCheckable(True)
    startup_action.setChecked(is_startup_enabled())
    startup_action.triggered.connect(toggle_startup)

    menu.addSeparator()
    menu.addAction("Exit").triggered.connect(app.quit)

    def show_menu_on_left_click(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            menu.popup(QCursor.pos())

    tray.setContextMenu(menu)
    tray.activated.connect(show_menu_on_left_click)
    tray.show()
    return tray

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = AnalogClock()
    tray = create_tray_icon(clock, app)
    sys.exit(app.exec())
