import os
from gtts import gTTS

# Buat folder 'audio' jika belum ada
audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)

angka_ke_huruf = {
    0: "dua belas", 1: "satu", 2: "dua", 3: "tiga", 4: "empat", 5: "lima",
    6: "enam", 7: "tujuh", 8: "delapan", 9: "sembilan", 10: "sepuluh",
    11: "sebelas", 12: "dua belas", 13: "tiga belas", 14: "empat belas",
    15: "lima belas", 16: "enam belas", 17: "tujuh belas", 18: "delapan belas",
    19: "sembilan belas", 20: "dua puluh", 21: "dua puluh satu",
    22: "dua puluh dua", 23: "dua puluh tiga", 24: "dua puluh empat"
}

print("Mulai mengunduh suara dari Google TTS...")

# Mengenerate file untuk jam 0 sampai 24
for hour in range(0, 25):
    hour_word = angka_ke_huruf[hour]
    text = f"Jam {hour_word}"
    filename = os.path.join(audio_dir, f"jam_{hour}.mp3")
    
    print(f"Membuat {filename} -> '{text}'")
    tts = gTTS(text=text, lang="id", slow=False)
    tts.save(filename)

print("\nBerhasil! Semua file audio telah dibuat di folder 'audio'.")
