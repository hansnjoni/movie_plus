import sys, os, requests, threading, time, json, webbrowser, re, subprocess, shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

# --- JARVIS 3.12.0 STABLE INITIALIZATION ---
VOICE_ON = True 
VOICE_READY = False
MIC_INVENTORY = []

# V63.2: Enhanced Hardware Probe & 3.12 Audio Link
try:
    import speech_recognition as sr
    import pyaudio
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            MIC_INVENTORY.append({"id": i, "name": dev['name']})
    VOICE_READY = True if MIC_INVENTORY else False
except Exception:
    VOICE_READY = False

# THE STARK KEY (TMDB Access)
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()
    search_trigger = pyqtSignal(str)

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard")
        self.setFixedSize(170, 320)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix)
        layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        title = item.get('title') or item.get('name') or "Unknown"
        self.title_lbl = QLabel(title[:20]); self.title_lbl.setStyleSheet("color: white; font-size: 10px;")
        layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.initiate_watch_protocol(item, mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        pop = self.item.get('popularity', 0); vote = self.item.get('vote_average', 0)
        score = round((vote * 0.7) + (min(pop/100, 3)), 1)
        name = self.item.get('title') or self.item.get('name')
        self.parent_app.signals.log_signal.emit(f"⭐ STARK SCORE: {score}/10 | {name}")

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Omnibus V63.2 (Final)")
        self.resize(1400, 900)
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QScrollArea { background-color: #050505; border: none; }
            QWidget#Gallery { background-color: #000000; }
            QFrame#MovieCard { background-color: #000000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
            QFrame#MovieCard:hover { border: 2px solid #00ff00; }
            QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; }
            QPushButton { background-color: #000000; color: #ff0000; border: 2px solid #ff0000; border-radius: 8px; padding: 10px; font-weight: bold; }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; background-color: #001100; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        self.is_live_mode = False; self.auto_pilot = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.current_mode = "movie"; self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.setup_tray(); self.run_
        
