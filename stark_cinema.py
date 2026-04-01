import sys
import os
import requests
import threading
import time
import json
import webbrowser
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"

STYLESHEET = """
QMainWindow { background-color: #050000; }
QFrame#Sidebar { background-color: #0a0000; border-right: 2px solid #ff0000; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QScrollArea { background-color: #050000; border: none; }
QWidget#Gallery { background-color: #050000; } 
QFrame#MovieCard { background-color: #1a0000; border-radius: 12px; border: 2px solid #330000; padding: 8px; margin: 5px; }

QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; margin-bottom: 2px; }

/* 🟢 NEON GREEN HOVER */
QPushButton:hover, QLineEdit:hover { border: 2px solid #00ff00; color: #00ff00; }

QPushButton#WatchBtn { background-color: #002200; color: #00ff00; border: 2px solid #00ff00; }
QPushButton#WatchBtn:disabled { background-color: #111; color: #444; border: 1px solid #222; }

QRadioButton { color: #ff0000; font-weight: bold; }
QRadioButton:checked { color: #00ff00; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
"""

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()
    status_signal = pyqtSignal(str, bool) 

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STARK CINEMA - PRO V7.1")
        self.resize(1550, 950)
        self.setStyleSheet(STYLESHEET)
        
        self.task_counter = 0
        self.current_mode = "movie"
        self.watch_buttons = {} 
        self.executor = ThreadPoolExecutor(max_workers=30)
        
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{time.strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.status_signal.connect(self.update_button_ui)
        
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        
        self.logo = QLabel("STARK CINEMA")
        self.logo.setStyleSheet("font-size: 24px; margin: 20px; color: #ff0000;")
        side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_trend = QPushButton("🔥 TRENDING")
        btn_trend.clicked.connect(self.run_trending)
        side_layout.addWidget(btn_trend)
        
        # 🟢 GENRE BUTTONS - RESTORED
        side_layout.addWidget(QLabel("\n   MASTER GENRES"))
        genres = [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]
        for name, g_id in genres:
            b = QPushButton(name)
            b.clicked.connect(lambda checked=False, idx=g_id: self.run_genre(idx))
            side_layout.addWidget(b)
        
        # Mode Switch
        mode_box = QWidget()
        mode_l = QHBoxLayout(mode_box)
        self.m_radio = QRadioButton("Movies")
        self.m_radio.setChecked(True)
        self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV")
        self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        mode_l.addWidget(self.m_radio)
        mode_l.addWidget(self.t_radio)
        side_layout.addWidget(mode_box)

        btn_settings = QPushButton("⚙️ CLEAR SYSTEM CACHE")
        btn_settings.clicked.connect(self.clear_cache)
        side_layout.addWidget(btn_settings)

        side_layout.addStretch()
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(120)
        self.console.setObjectName("Console")
        side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        
        # Content
        content = QWidget()
        c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Stark Database...")
        self.search_bar.returnPressed.connect(self.run_search)
        c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container.setObjectName("Gallery")
        self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        c_layout.addWidget(self.scroll)
        layout.addWidget(content)
        
        self.run_trending()

    def set_mode(self, m):
        self.current_mode = m
        self.run_trending()

    def clear_gallery(self):
        self.watch_buttons.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

    def clear_cache(self):
        if os.path.exists(JASON_FILE):
            os.remove(JASON_FILE)
        self.signals.log_signal.emit("🧹 Cache Cleared. Re-scanning links...")
        self.run_trending()

    def run_trending(self):
        url = f"https://api.themoviedb.org/3/trending/{self.current_mode}/week"
        self.start_thread(url)

    def run_genre(self, g_id):
        url = f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc"
        self.start_thread(url)

    def run_search(self):
        query = self.search_bar.text().strip()
        if query:
            url = f"https://api.themoviedb.org/3/search/multi?query={query}"
            self.start_thread(url)

    def start_thread(self, url):
        self.task_counter += 1
        self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        h = {"Authorization": f"Bearer {STARK_TOKEN}"}
        try:
            res = requests.get(url, headers=h).json()
            results = res.get('results', [])
            limit_date = datetime.now() - timedelta(days=90)
            
            ui_count = 1
            for item in results:
                if t_id != self.task_counter:
                    return
                
                mtype = item.get('media_type', self.current_mode)
                if mtype not in ["movie", "tv"]:
                    continue

                d_str = item.get('release_date') or item.get('first_air_date') or '1900-01-01'
                try:
                    release_date = datetime.strptime(d_str, '%Y-%m-%d')
                except:
                    release_date = datetime.now()

                if release_date < limit_date:
                    self.executor.submit(self.img_worker, item, ui_count, mtype, t_id)
                    self.executor.submit(self.verify_link_worker, item['id'], mtype, t_id)
                    ui_count += 1
                    if ui_count > 40:
                        break
        except Exception as e:
            self.signals.log_signal.emit(f"⚠️ Engine Error: {str(e)}")

    def img_worker(self, item, rank, mtype, tid):
        if tid != self.task_counter:
            return
        try:
            path = item.get('poster_path')
            pix = QPixmap()
            if path:
                img_data = requests.get(f"https://image.tmdb.org/t/p/w200{path}", timeout=5).content
                pix.loadFromData(img_data)
            self.signals.item_signal.emit(item, pix.scaled(170, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, mtype, tid)
        except:
            pass

    def verify_link_worker(self, mid, mtype, tid):
        try:
            url = f"https://vidsrc.me/embed/{mtype}?tmdb={mid}"
            status = requests.head(url, timeout=2.0).status_code == 200
            self.signals.status_signal.emit(str(mid), status)
        except:
            self.signals.status_signal.emit(str(mid), False)

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid != self.task_counter:
            return
        
        f = QFrame()
        f.setObjectName("MovieCard")
        l = QVBoxLayout(f)
        
        p = QLabel()
        p.setPixmap(pix)
        l.addWidget(p, alignment=Qt.AlignCenter)
        
        title = (item.get('title') or item.get('name'))[:18]
        l.addWidget(QLabel(f"{title}..."))
        
        b = QPushButton("CHECKING...")
        b.setEnabled(False)
        mid = str(item['id'])
        self.watch_buttons[mid] = b 
        
        b.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{mtype}?tmdb={mid}"))
        l.addWidget(b)
        self.grid.addWidget(f, (rank-1)//5, (rank-1)%5)

    def update_button_ui(self, mid, is_available):
        if mid in self.watch_buttons:
            btn = self.watch_buttons[mid]
            if is_available:
                btn.setText("WATCH NOW")
                btn.setObjectName("WatchBtn") 
                btn.setEnabled(True)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            else:
                btn.setText("OFFLINE")
                btn.setStyleSheet("color: #444; border: 1px solid #222;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoviePlusPro()
    win.show()
    sys.exit(app.exec_())
