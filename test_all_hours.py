import sys
import os
from PySide6.QtCore import QCoreApplication, QUrl, QTimer, QObject
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class AudioTester(QObject):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.current_hour = 1
        self.audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
        
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        print("\n=== Memulai Tes Pengucapan MP3 Jam 1 s.d. 24 (Google TTS) ===")
        print("Tekan Ctrl + C di terminal untuk menghentikan tes.\n")
        
        # Mulai setelah jeda singkat
        QTimer.singleShot(500, self.play_next)

    def play_next(self):
        if self.current_hour > 24:
            print("\nTes selesai!")
            QCoreApplication.quit()
            return
            
        audio_path = os.path.join(self.audio_dir, f"jam_{self.current_hour}.mp3")
        print(f"Memutar -> jam_{self.current_hour}.mp3")
        
        if os.path.exists(audio_path):
            self.player.setSource(QUrl.fromLocalFile(audio_path))
            self.player.play()
        else:
            print(f"File tidak ditemukan: {audio_path}")
            self.current_hour += 1
            QTimer.singleShot(500, self.play_next)

    def on_media_status_changed(self, status):
        # Saat MP3 selesai diputar, lanjut ke angka berikutnya setelah jeda 1.2 detik
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.current_hour += 1
            QTimer.singleShot(1200, self.play_next)

if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
    tester = AudioTester()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nTes dihentikan pengguna.")
