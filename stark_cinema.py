import sys, os, requests, threading, time, json, webbrowser, re, subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS CONFIGURATION ---
VOICE_ON = True  # SET TO FALSE TO MUTE THE ASSISTANT
VOICE_READY = False
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except: pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()
    voice_status = pyqtSignal(str)

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

class StarkCinemaV20(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - V20.1")
        self.resize(1500, 920)
        
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.init_ui()
        self.speak("Systems Integrated. Architect Build 20.1 Online.")

    def speak(self, text):
        if not VOICE_ON: return
        # Uses built-in Windows voice - NO DOWNLOAD REQUIRED
        cmd = f'PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\');"'
        threading.Thread(target=lambda: subprocess.run(cmd, shell=True), daemon=True).start()

    def initiate_watch_protocol(self, item, mtype):
        title = item.get('title') or item.get('name')
        self.speak(f"Analyzing links for {title}.")
        # (Sentinel check logic continues here...)
        webbrowser.open(f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}")

    def init_ui(self):
        # (UI creation code as per previous V20.0 build...)
        pass # Re-insert the UI code from V20.0 here

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaV20(); win.show(); sys.exit(app.exec_())
