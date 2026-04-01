import sys
import os
import requests
import threading
import time
import json
import zipfile
import io
import traceback
import webbrowser
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QCheckBox, QRadioButton, 
                             QButtonGroup, QDialog, QComboBox, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
from concurrent.futures import ThreadPoolExecutor

# --- CATCH SILENT CRASHES ---
def global_exception_handler(exc_type, exc_value, exc_traceback):
    print("\n💥 CRITICAL SYSTEM FAILURE CAUGHT 💥")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("--------------------------------------------------\n")
sys.excepthook = global_exception_handler

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

LOGO_PATH = "logo.png"

# 🟢 STYLESHEET UPDATED: Global Neon Green Hover Applied
STYLESHEET = """
QMainWindow { background-color: #02040a; }
QFrame#Sidebar { background-color: #080808; border-right: 1px solid #222; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; margin-right: 30px; }
QTextEdit#Console { background-color: #050505; color: #00ff00; border: 1px solid #330066; border-radius: 5px; font-family: 'Consolas', monospace; font-size: 11px; padding: 5px; margin-top: 10px; }

QWidget#GalleryContainer { background-color: #02040a; }
QScrollArea { border: none; background-color: #02040a; }
QFrame#MovieCard { background-color: #1a0033; border-radius: 12px; border: 1px solid #330066; margin: 5px; padding: 10px; min-width: 170px; max-width: 170px; }

/* 🟢 ALL BUTTONS - INITIAL STATE */
QPushButton { background-color: #0f0f0f; color: #ff3333; border: 2px solid #aa0000; border-radius: 10px; padding: 8px; font-weight: bold; }

/* 🟢 WATCH BUTTONS - INITIAL STATE */
QPushButton#WatchBtn { background-color: #008800; color: white; border: 2px solid #00ff00; }

/* 🟢 THE "MASTER HOVER" - ALL BUTTONS LIGHT UP NEON GREEN */
QPushButton:hover, QPushButton#WatchBtn:hover, QLineEdit:hover { 
    background-color: #111; 
    color: #ffffff; 
    border: 2px solid #00ff00; 
}
QRadioButton { color: #888; font-weight: bold; }
QRadioButton:checked { color: #00ff00; }
"""

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0  
        self.load_identity()
        
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        self.resize(1400, 950)
        self.setStyleSheet(STYLESHEET)
        
        central = QWidget()
        self.main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)
        
        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        self.side_layout = QVBoxLayout(self.sidebar)
        
        self.logo_display = QLabel("STARK CINEMA")
        self.logo_display.setStyleSheet("font-size: 22px; color: #ff0000; padding: 20px;")
        self.side_layout.addWidget(self.logo_display, alignment=Qt.AlignCenter)
        
        btn_tr = QPushButton("⭐ TRENDING NOW"); btn_tr.clicked.connect(self.run_trending)
        self.side_layout.addWidget(btn_tr)
        
        self.movie_radio = QRadioButton("Movies"); self.movie_radio.setChecked(True)
        self.movie_radio.clicked.connect(lambda: self.set_mode_stark("movie"))
        self.tv_radio = QRadioButton("TV Shows"); self.tv_radio.clicked.connect(lambda: self.set_mode_stark("tv"))
        
        self.side_layout.addWidget(self.movie_radio)
        self.side_layout.addWidget(self.tv_radio)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True)
        self.side_layout.addWidget(self.console)
        
        self.main_layout.addWidget(self.sidebar)
        
        # Content
        self.content_area = QWidget(); self.content_layout = QVBoxLayout(self.content_area)
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search Database...")
        self.search_input.returnPressed.connect(self.run_search)
        self.content_layout.addWidget(self.search_input)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.gallery_container = QWidget(); self.gallery_layout = QGridLayout(self.gallery_container)
        self.scroll.setWidget(self.gallery_container)
        self.content_layout.addWidget(self.scroll)
        self.main_layout.addWidget(self.content_area)
        
        self.run_trending()

    def load_identity(self):
        user = os.getlogin().lower()
        self.token = STARK_TOKEN if "stark" in user else ""

    def update_log(self, msg): self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def set_mode_stark(self, mode):
        self.current_mode = mode
        self.run_trending()

    def api_call(self, url):
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try: return requests.get(url, headers=headers, timeout=10).json()
        except: return {}

    def run_trending(self):
        url = f"https://api.themoviedb.org/3/trending/{self.current_mode}/week"
        self.restart_belt(url)

    def run_search(self):
        query = self.search_input.text()
        url = f"https://api.themoviedb.org/3/search/{self.current_mode}?query={query}"
        self.restart_belt(url)

    def restart_belt(self, url):
        self.task_counter += 1
        self.clear_gallery()
        threading.Thread(target=self.conveyor_belt_worker, args=(url, self.task_counter), daemon=True).start()

    def conveyor_belt_worker(self, url, task_id):
        res = self.api_call(url)
        results = res.get('results', [])
        limit_date = datetime.now() - timedelta(days=90)
        
        for i, item in enumerate(results, 1):
            if task_id != self.task_counter: return
            r_date_str = item.get('release_date') or item.get('first_air_date') or '1900-01-01'
            r_date = datetime.strptime(r_date_str, '%Y-%m-%d')
            
            if r_date < limit_date:
                self.signals.item_signal.emit(item, QPixmap(), i, self.current_mode, task_id)

    def add_item_to_ui(self, item, pix, rank, m_type, task_id):
        if task_id != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        title = item.get('title') or item.get('name')
        b = QPushButton(f"WATCH {title[:15]}..."); b.setObjectName("WatchBtn")
        b.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{m_type}?tmdb={item['id']}"))
        l.addWidget(QLabel(title)); l.addWidget(b)
        self.gallery_layout.addWidget(f, (rank-1)//5, (rank-1)%5)

    def clear_gallery(self):
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoviePlusPro()
    win.show()
    sys.exit(app.exec_())
