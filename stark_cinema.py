import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
SETTINGS_FILE = "settings.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #050000; }
QFrame#Sidebar { background-color: #0a0000; border-right: 2px solid #ff0000; }
QRadioButton { color: #ff0000; font-weight: bold; font-size: 14px; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 8px; border: 2px solid #aa0000; background: #000; }
QRadioButton::indicator:checked { background-color: #00ff00; border: 2px solid #ffffff; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QScrollArea { background-color: #050000; border: none; }
QWidget#Gallery { background-color: #050000; } 
QFrame#MovieCard { background-color: #3a0000; border-radius: 10px; border: 2px solid #ff0000; padding: 10px; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #006600; color: #00ff00; border: 1px solid #00ff00; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
"""

def get_jason():
    if os.path.exists(JASON_FILE):
        try:
            with open(JASON_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_to_jason(m_id, status):
    mem = get_jason()
    mem[str(m_id)] = {"status": status, "last_checked": str(datetime.now().date())}
    with open(JASON_FILE, 'w') as f: json.dump(mem, f)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0; self.current_mode = "movie"
        self.settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {"token": STARK_TOKEN}
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{time.strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.executor = ThreadPoolExecutor(max_workers=25); self.shown_ids = set(); self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Stark Cinema - Redundant Core v6.0"); self.resize(1400, 950); self.setStyleSheet(STYLESHEET)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260); side_layout = QVBoxLayout(self.sidebar)
        if os.path.exists(LOGO_PATH):
            self.logo = QLabel(); self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
            side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending); side_layout.addWidget(btn_trend)
        rc = QWidget(); rl = QHBoxLayout(rc)
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True); self.m_radio.clicked.connect(lambda: self.
