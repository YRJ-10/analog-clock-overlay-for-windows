import sys
import os
import ctypes
from ctypes import wintypes
import winreg
import json
import winsound
from PySide6.QtCore import Qt, QTimer, QTime, QDate, QLocale, QDateTime, QPoint, QRect
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTimeEdit, QSpinBox, QPushButton, QLineEdit
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QFont, QCursor, QRegion
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

def get_notes_path():
    if hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "notes.json")

def load_notes_data():
    path = get_notes_path()
    default_data = {"show_notes": True, "notes": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {
                        "show_notes": data.get("show_notes", True),
                        "notes": data.get("notes", []) if isinstance(data.get("notes"), list) else []
                    }
                elif isinstance(data, list):
                    return {"show_notes": True, "notes": data}
        except Exception:
            return default_data
    return default_data

def save_notes_data(data):
    path = get_notes_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

class NotesClickOverlay(QWidget):
    """
    Companion window interaktif untuk floating notes.
    Hanya menerima klik kiri 2x (double click):
    - Pada [+] -> buka dialog tambah catatan
    - Pada checkbox [ ] -> hapus catatan (selesai/done)
    Semua klik lain dan area lain tembus langsung ke background.
    """
    def __init__(self, notes_overlay):
        super().__init__()
        self.notes_overlay = notes_overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, event):
        # Alpha 1 agar OS Windows bisa mendeteksi klik
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def update_geometry(self):
        if not self.notes_overlay.visible_enabled or not self.notes_overlay.isVisible():
            self.hide()
            return
        self.setGeometry(self.notes_overlay.geometry())

        # Masking presisi:
        # 1. Tombol [+]
        # 2. Kotak checklist [ ] (untuk selesaikan/hapus)
        # 3. Area teks catatan (untuk double-click lihat teks panjang lengkap)
        mask = QRegion()
        # Area tombol [+]
        mask = mask.united(QRegion(QRect(self.width() - 32, 2, 28, 22)))

        if not self.notes_overlay.notes:
            mask = mask.united(QRegion(QRect(8, 26, self.width() - 16, 20)))
        else:
            for i in range(len(self.notes_overlay.notes)):
                row_y = 25 + i * 22
                # Checkbox [ ]
                mask = mask.united(QRegion(QRect(6, row_y + 2, 22, 18)))
                # Note text
                mask = mask.united(QRegion(QRect(28, row_y, self.width() - 34, 20)))

        self.setMask(mask)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            x = pos.x()
            y = pos.y()

            # 1. Double click pada [+] (kanan atas) atau jika catatan kosong
            if (x >= self.width() - 32 and y <= 24) or (not self.notes_overlay.notes and y > 24):
                self.open_add_dialog()
                event.accept()
                return

            # 2. Baris catatan
            if y > 24:
                item_idx = int((y - 25) // 22)
                if 0 <= item_idx < len(self.notes_overlay.notes):
                    # Checkbox: x <= 28 -> Hapus (selesai)
                    if x <= 28:
                        self.notes_overlay.notes.pop(item_idx)
                        self.notes_overlay.save()
                        self.notes_overlay.update_geometry()
                        self.notes_overlay.update()
                        event.accept()
                        return
                    # Teks: x > 28 -> Tampilkan teks panjang lengkap (Detail dialog)
                    else:
                        self.open_detail_dialog(item_idx)
                        event.accept()
                        return

        super().mouseDoubleClickEvent(event)

    def open_add_dialog(self):
        dialog = QDialog(self.notes_overlay.clock)
        dialog.setWindowTitle("Tambah Catatan Prioritas")
        dialog.setFixedWidth(320)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Tulis Catatan Prioritas:"))
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Ketik catatan lalu Enter...")
        layout.addWidget(line_edit)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Tambah")
        btn_cancel = QPushButton("Batal")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        def on_ok():
            text = line_edit.text().strip()
            if text:
                self.notes_overlay.notes.append(text)
                self.notes_overlay.save()
                self.notes_overlay.update_geometry()
                self.notes_overlay.update()
            dialog.accept()

        btn_ok.clicked.connect(on_ok)
        line_edit.returnPressed.connect(on_ok)
        btn_cancel.clicked.connect(dialog.reject)
        line_edit.setFocus()
        dialog.exec()

    def open_detail_dialog(self, item_idx):
        if not (0 <= item_idx < len(self.notes_overlay.notes)):
            return
        current_text = self.notes_overlay.notes[item_idx]

        dialog = QDialog(self.notes_overlay.clock)
        dialog.setWindowTitle("Detail Catatan Prioritas")
        dialog.setFixedWidth(340)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Isi Lengkap Catatan:"))
        
        line_edit = QLineEdit(current_text)
        layout.addWidget(line_edit)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Simpan")
        btn_delete = QPushButton("Hapus")
        btn_close = QPushButton("Tutup")
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        def on_save():
            new_text = line_edit.text().strip()
            if new_text:
                self.notes_overlay.notes[item_idx] = new_text
                self.notes_overlay.save()
                self.notes_overlay.update_geometry()
                self.notes_overlay.update()
            dialog.accept()

        def on_delete():
            self.notes_overlay.notes.pop(item_idx)
            self.notes_overlay.save()
            self.notes_overlay.update_geometry()
            self.notes_overlay.update()
            dialog.accept()

        btn_save.clicked.connect(on_save)
        line_edit.returnPressed.connect(on_save)
        btn_delete.clicked.connect(on_delete)
        btn_close.clicked.connect(dialog.reject)
        line_edit.setFocus()
        dialog.exec()

class NotesOverlay(QWidget):
    """
    Jendela visual untuk floating notes / priority todo list.
    100% ghost (WS_EX_TRANSPARENT) sehingga teks dan background tidak menghalangi klik ke desktop.
    """
    def __init__(self, clock):
        super().__init__()
        self.clock = clock
        data = load_notes_data()
        self.notes = data["notes"]
        self.visible_enabled = data["show_notes"]
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.WindowTransparentForInput, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowOpacity(0.85)

        self.click_overlay = NotesClickOverlay(self)

    def save(self):
        save_notes_data({"show_notes": self.visible_enabled, "notes": self.notes})

    def set_visible_enabled(self, enabled):
        self.visible_enabled = enabled
        self.save()

    def update_geometry(self):
        if not self.visible_enabled:
            self.hide()
            self.click_overlay.hide()
            return

        w = max(160, self.clock.width())
        content_rows = max(1, len(self.notes))
        h = 24 + (content_rows * 22) + 8

        x = int(self.clock.x() + (self.clock.width() - w) / 2.0)
        y = int(self.clock.y() + self.clock.height() + 6)

        self.setGeometry(x, y, w, h)
        if self.clock.isVisible():
            self.show()
            self.click_overlay.update_geometry()
            self.click_overlay.show()
        self.update()

    def update_hover(self, mouse_pos):
        if not self.isVisible():
            return
        # Notes hover opacity: tidak seradikal jam (0.45 saat di-hover, 0.85 normal)
        if self.geometry().contains(mouse_pos):
            target = 0.45
        else:
            target = 0.85

        curr = self.windowOpacity()
        diff = target - curr
        if abs(diff) > 0.03:
            self.setWindowOpacity(curr + (0.05 if diff > 0 else -0.05))
        else:
            self.setWindowOpacity(target)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Background: dark translucent glass minimalis
        bg_rect = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(QColor(18, 18, 22, 210))
        p.drawRoundedRect(bg_rect, 7, 7)

        # Header: PRIORITAS & [+] button
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        p.setPen(QColor(220, 220, 225, 200))
        p.drawText(10, 4, self.width() - 40, 18, Qt.AlignLeft | Qt.AlignVCenter, "PRIORITAS")

        # [+] icon
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(self.width() - 25, 3, 18, 18, Qt.AlignCenter, "+")

        # Divider line
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawLine(8, 23, self.width() - 8, 23)

        # Items
        if not self.notes:
            p.setFont(QFont("Segoe UI", 7, QFont.Normal))
            p.setPen(QColor(180, 180, 190, 140))
            p.drawText(10, 26, self.width() - 20, 22, Qt.AlignLeft | Qt.AlignVCenter, "Klik 2x [+] untuk tambah")
        else:
            for i, note in enumerate(self.notes):
                row_y = 25 + i * 22

                # Checkbox square [ ]
                p.setPen(QPen(QColor(200, 200, 210, 180), 1.2))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(10, row_y + 4, 12, 12, 3, 3)

                # Text note
                p.setFont(QFont("Segoe UI", 8, QFont.Normal))
                p.setPen(QColor(240, 240, 245))
                metrics = p.fontMetrics()
                available_w = self.width() - 32
                elided = metrics.elidedText(note, Qt.ElideRight, available_w)
                p.drawText(28, row_y, available_w, 20, Qt.AlignLeft | Qt.AlignVCenter, elided)

class IconOverlay(QWidget):
    """
    Jendela interaktif mini transparan yang menempel persis di atas ikon Timer & Alarm.
    Memungkinkan kedua ikon menerima klik (double-click dan right-click) sementara
    jendela jam utama tetap 100% tembus klik (WS_EX_TRANSPARENT).
    """
    def __init__(self, clock):
        super().__init__()
        self.clock = clock
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, event):
        # Alpha 1 hampir tidak terlihat oleh mata, namun cukup bagi OS untuk mendeteksi klik
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def update_geometry(self):
        cx = self.clock.width() / 2.0
        cy = self.clock.height() / 2.0
        scale = min(self.clock.width(), self.clock.height()) / 200.0

        # Koordinat ikon:
        # Alarm: x=[-22 .. -2], y=[-52 .. -32], text sampai y=-16
        # Timer: x=[2 .. 22], y=[-52 .. -32], text sampai y=-16
        w = max(1, int(52 * scale))
        h = max(1, int(42 * scale))
        left = int(self.clock.x() + cx - (w / 2.0))
        top = int(self.clock.y() + cy - (56 * scale))

        self.setGeometry(left, top, w, h)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.position().x() < self.width() / 2.0:
                self.clock.open_alarm_dialog()
            else:
                self.clock.open_timer_dialog()
            event.accept()

    def mousePressEvent(self, event):
        # Klik kanan untuk membatalkan / mereset
        if event.button() == Qt.RightButton:
            if event.position().x() < self.width() / 2.0:
                self.clock.alarm_time = None
                self.clock.update()
            else:
                self.clock.timer_end_time = None
                self.clock.update()
            event.accept()
        # Klik kiri satu kali sengaja diabaikan (tidak membuka popup)

class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.edit_mode = False
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
        self.icon_overlay = IconOverlay(self)
        self.notes_overlay = NotesOverlay(self)
        self.set_click_through(True)
        self.force_topmost()
        
        # Initialize Media Player for Voice Chimes
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        
        # Separate Media Player for Alarm/Timer sounds (avoids conflict with hourly chime)
        self.alarm_player = QMediaPlayer()
        self.alarm_audio_output = QAudioOutput()
        self.alarm_player.setAudioOutput(self.alarm_audio_output)
        self.alarm_audio_output.setVolume(1.0)
        


    def play_beeps(self):
        try:
            audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "alarm.wav")
            if os.path.exists(audio_path):
                self.alarm_player.setSource(QUrl.fromLocalFile(audio_path))
                self.alarm_player.play()
            else:
                self.beep_count = 0
                def do_beep():
                    try: winsound.Beep(1000, 200)
                    except: pass
                    self.beep_count += 1
                    if self.beep_count < 4:
                        QTimer.singleShot(400, do_beep)
                do_beep()
        except Exception:
            pass
        
    def play_voice_warning(self):
        try:
            audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio", "tersisa_1_menit.mp3")
            if os.path.exists(audio_path):
                self.alarm_player.setSource(QUrl.fromLocalFile(audio_path))
                self.alarm_player.play()
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
        if hasattr(self, 'icon_overlay'):
            self.icon_overlay.update_geometry()
        if hasattr(self, 'notes_overlay'):
            self.notes_overlay.update_geometry()

    def on_timer_timeout(self):
        # 1. Update drawing
        self.update()
        
        # 2. Check for Hover (Auto-Fade)
        mouse_pos = QCursor.pos()
        if self.geometry().contains(mouse_pos):
            target_opacity = 0.05
        else:
            target_opacity = self.base_opacity
            
        # Smoothly transition opacity
        curr = self.windowOpacity()
        diff = target_opacity - curr
        if abs(diff) > 0.02:
            self.setWindowOpacity(curr + (0.05 if diff > 0 else -0.05))
        else:
            self.setWindowOpacity(target_opacity)

        if hasattr(self, 'notes_overlay'):
            self.notes_overlay.update_hover(mouse_pos)

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
            alarm_key = f"{self.alarm_time.hour()}:{self.alarm_time.minute()}"
            now_key = f"{current_time.hour()}:{current_time.minute()}"
            if now_key == alarm_key and self.last_alarm_triggered != alarm_key:
                self.last_alarm_triggered = alarm_key
                self.play_beeps()
                # Auto-clear alarm display after firing
                self.alarm_time = None
            
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
            if hasattr(self, 'icon_overlay'):
                ctypes.windll.user32.SetWindowPos(self.icon_overlay.winId(), HWND_TOPMOST, 0, 0, 0, 0,
                                                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
            if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled and self.notes_overlay.isVisible():
                ctypes.windll.user32.SetWindowPos(self.notes_overlay.winId(), HWND_TOPMOST, 0, 0, 0, 0,
                                                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
                ctypes.windll.user32.SetWindowPos(self.notes_overlay.click_overlay.winId(), HWND_TOPMOST, 0, 0, 0, 0,
                                                 SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        else:
            self.raise_()
            if hasattr(self, 'icon_overlay'):
                self.icon_overlay.raise_()
            if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled:
                self.notes_overlay.raise_()
                self.notes_overlay.click_overlay.raise_()

    def refresh_overlay(self):
        self.set_click_through(not self.edit_mode)

        if self.isMinimized():
            self.showNormal()
            if hasattr(self, 'icon_overlay'):
                self.icon_overlay.showNormal()
            if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled:
                self.notes_overlay.showNormal()
                self.notes_overlay.click_overlay.showNormal()
        else:
            self.show()
            if hasattr(self, 'icon_overlay'):
                self.icon_overlay.show()
            if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled:
                self.notes_overlay.show()
                self.notes_overlay.click_overlay.show()

        self.force_topmost()
        self.raise_()
        self.update()
        if hasattr(self, 'icon_overlay'):
            self.icon_overlay.update_geometry()
            self.icon_overlay.raise_()
        if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled:
            self.notes_overlay.update_geometry()
            self.notes_overlay.raise_()
            self.notes_overlay.click_overlay.raise_()

    def set_click_through(self, enabled):
        if enabled:
            self.setWindowFlag(Qt.WindowTransparentForInput, True)
        else:
            self.setWindowFlag(Qt.WindowTransparentForInput, False)
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'icon_overlay'):
            self.icon_overlay.update_geometry()
            self.icon_overlay.show()
        if hasattr(self, 'notes_overlay') and self.notes_overlay.visible_enabled:
            self.notes_overlay.update_geometry()
            self.notes_overlay.show()
            self.notes_overlay.click_overlay.show()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'icon_overlay'):
            self.icon_overlay.hide()
        if hasattr(self, 'notes_overlay'):
            self.notes_overlay.hide()
            self.notes_overlay.click_overlay.hide()

    def closeEvent(self, event):
        if hasattr(self, 'icon_overlay'):
            self.icon_overlay.close()
        if hasattr(self, 'notes_overlay'):
            self.notes_overlay.close()
            self.notes_overlay.click_overlay.close()
        super().closeEvent(event)

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
            alarm_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color.name()}" d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>'''
            from PySide6.QtCore import QByteArray, QRectF
            alarm_renderer = QSvgRenderer(QByteArray(alarm_svg.encode('utf-8')))
            alarm_renderer.render(p, QRectF(-22, -52, 20, 20))
            
            if self.alarm_time:
                p.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
                p.setPen(color)
                p.drawText(-32, -30, 40, 14, Qt.AlignCenter, self.alarm_time.toString("HH:mm"))
            p.restore()

            # Draw Timer Icon and Text
            p.save()
            timer_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color.name()}" d="M6 2v6h.01L6 8.01 10 12l-4 4 .01.01H6V22h12v-5.99h-.01L18 16l-4-4 4-3.99-.01-.01H18V2H6zm10 14.5V20H8v-3.5l4-4 4 4zm-4-5l-4-4V4h8v3.5l-4 4z"/></svg>'''
            timer_renderer = QSvgRenderer(QByteArray(timer_svg.encode('utf-8')))
            timer_renderer.render(p, QRectF(2, -52, 20, 20))
            
            if self.timer_end_time:
                rem = QDateTime.currentDateTime().msecsTo(self.timer_end_time)
                if rem > 0:
                    secs = rem // 1000
                    mins = secs // 60
                    secs = secs % 60
                    time_str = f"{mins:02}:{secs:02}"
                    p.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
                    p.setPen(color)
                    p.drawText(-6, -30, 40, 14, Qt.AlignCenter, time_str)
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
        # Drag in edit mode
        if self.edit_mode and event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.edit_mode and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            if hasattr(self, 'icon_overlay'):
                self.icon_overlay.update_geometry()
            if hasattr(self, 'notes_overlay'):
                self.notes_overlay.update_geometry()
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
    
    def toggle_notes(checked):
        clock_widget.notes_overlay.set_visible_enabled(checked)
        if checked:
            clock_widget.notes_overlay.update_geometry()
            clock_widget.notes_overlay.show()
            clock_widget.notes_overlay.click_overlay.show()
            clock_widget.notes_overlay.raise_()
            clock_widget.notes_overlay.click_overlay.raise_()
        else:
            clock_widget.notes_overlay.hide()
            clock_widget.notes_overlay.click_overlay.hide()

    notes_action = menu.addAction("Show Priority Notes")
    notes_action.setCheckable(True)
    notes_action.setChecked(clock_widget.notes_overlay.visible_enabled)
    notes_action.triggered.connect(toggle_notes)
    
    menu.addSeparator()

    def toggle_edit():
        clock_widget.edit_mode = not clock_widget.edit_mode
        # Saat Edit Mode aktif, disable click-through agar jam bisa digeser
        clock_widget.set_click_through(not clock_widget.edit_mode)
        edit_action.setChecked(clock_widget.edit_mode)

    edit_action = menu.addAction("Edit Mode (Drag)")
    edit_action.setCheckable(True)
    edit_action.triggered.connect(toggle_edit)

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
