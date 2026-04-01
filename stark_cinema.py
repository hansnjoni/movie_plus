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
sys.excepthook = global_exception_handler

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"
FAVORITES_FILE = "favorites.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #02040a; }
QFrame#Sidebar { background-color: #080808; border-right: 1px solid #222; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; margin-right: 30px; }
QLineEdit:hover { border: 1px solid #00ff00; }

QWidget#GalleryContainer { background-color: #02040a; }
QScrollArea { border: none; background-color: #02040a; }

QFrame#MovieCard { 
    background-color: #1a0033; 
    border-radius: 12px; 
    border: 1px solid #330066;
    margin: 5px;
    padding: 10px;
}
QFrame#MovieCard:hover { border: 1px solid #00ff00; }

QPushButton { 
    background-color: #0f0f0f; 
    color: #ff3333; 
    border: 2px solid #aa0000; 
    border-radius: 10px; 
    padding: 8px; 
    font-weight: bold; 
}
QPushButton:hover { background-color: #111; color: #ffffff; border: 2px solid #00ff00; }
QPushButton#WatchBtn { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
QPushButton#FavBtn { background-color: #111; color: #ffcc00; border: 1px solid #444; font-size: 14px; }

QTextEdit#Console {
    background-color: #050505;
    color: #00ff00;
    border: 1px solid #330066;
    font-family: 'Consolas';
    font-size: 11px;
}
"""

class SignalHandler(QObject):
    log_signal = pyqtSignal(str)
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    clear_signal = pyqtSignal()

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Settings")
        self.setFixedSize(400, 300)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("API Read Access Token:"))
        self.token_input = QTextEdit()
        self.token_input.setPlainText(settings.get("token", ""))
        layout.addWidget(self.token_input)
        save = QPushButton("💾 SAVE SETTINGS")
        save.clicked.connect(self.accept)
        layout.addWidget(save)

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0  
        self.load_identity()
        self.load_history()
        self.load_favorites()
        
        self.signals = SignalHandler()
        self.signals.log_signal.connect(self.update_log)
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=15)
        
        self.resize(1400, 950)
        self.setStyleSheet(STYLESHEET)
        
        central = QWidget()
        self.main_layout = QHBoxLayout(central)
        self.setCentralWidget(central)
        
        # --- SIDEBAR ---
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        self.side_layout = QVBoxLayout(self.sidebar)
        
        self.logo_label = QLabel()
        if os.path.exists(LOGO_PATH):
            self.logo_label.setPixmap(QPixmap(LOGO_PATH).scaled(220, 150, Qt.KeepAspectRatio))
        else:
            self.logo_label.setText("STARK CINEMA")
            self.logo_label.setStyleSheet("font-size: 22px; color: #ff0000; padding: 20px;")
        self.side_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        btn_set = QPushButton("⚙️ SETTINGS")
        btn_set.clicked.connect(self.open_settings)
        self.side_layout.addWidget(btn_set)
        
        btn_favs = QPushButton("⭐ YOUR FAVORITES")
        btn_favs.setStyleSheet("color: #ffcc00; border-color: #ffcc00;")
        btn_favs.clicked.connect(self.display_favorites)
        self.side_layout.addWidget(btn_favs)
        
        btn_tr = QPushButton("🔥 TRENDING NOW")
        btn_tr.clicked.connect(self.run_trending)
        self.side_layout.addWidget(btn_tr)
        
        self.movie_radio = QRadioButton("Movies"); self.movie_radio.setChecked(True)
        self.movie_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.tv_radio = QRadioButton("TV Shows")
        self.tv_radio.clicked.connect(lambda: self.set_mode("tv"))
        self.side_layout.addWidget(self.movie_radio)
        self.side_layout.addWidget(self.tv_radio)

        self.side_layout.addWidget(QLabel("   GENRES"))
        genres = {"Action": 28, "Comedy": 35, "Horror": 27, "Crime": 80, "True Crime": "99,80"}
        for name, g_id in genres.items():
            b = QPushButton(name.upper())
            b.clicked.connect(lambda checked=False, idx=g_id: self.run_genre(idx))
            self.side_layout.addWidget(b)
        
        self.side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True)
        self.side_layout.addWidget(self.console)
        self.main_layout.addWidget(self.sidebar)
        
        # --- CONTENT ---
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search Stark Database...")
        self.search_input.returnPressed.connect(self.run_search)
        self.content_layout.addWidget(self.search_input)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.gallery_container = QWidget(); self.gallery_container.setObjectName("GalleryContainer")
        self.gallery_layout = QGridLayout(self.gallery_container)
        self.scroll.setWidget(self.gallery_container)
        self.content_layout.addWidget(self.scroll)
        self.main_layout.addWidget(self.content_area)
        
        self.run_trending()

    def load_identity(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f: self.settings = json.load(f)
        else: self.settings = {"token": STARK_TOKEN, "quarantine_days": 90}
        self.token = self.settings.get("token", STARK_TOKEN)

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.settings["token"] = dialog.token_input.toPlainText().strip()
            with open(SETTINGS_FILE, 'w') as f: json.dump(self.settings, f)
            self.token = self.settings["token"]

    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r') as f: self.favorites = json.load(f)
            except: self.favorites = []
        else: self.favorites = []

    def save_to_favorites(self, item):
        if item['id'] not in [f['id'] for f in self.favorites]:
            item['stark_media_type'] = self.current_mode
            self.favorites.append(item)
            with open(FAVORITES_FILE, 'w') as f: json.dump(self.favorites, f)
            self.update_log(f"⭐ Added: {item.get('title') or item.get('name')}")
        else: self.update_log("ℹ️ Already in favorites.")

    def display_favorites(self):
        self.update_log("📂 Opening Favorites Vault...")
        self.signals.clear_signal.emit()
        self.task_counter += 1
        for i, item in enumerate(self.favorites, 1):
            self.executor.submit(self.load_image_worker, item, i, item.get('stark_media_type', 'movie'), self.task_counter)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f: self.history = json.load(f)
            except: self.history = {}
        else: self.history = {}

    def update_log(self, msg):
        self.console.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def set_mode(self, mode):
        self.current_mode = mode; self.run_trending()

    def api_call(self, url):
        headers = {"Authorization": f"Bearer {self.token}"}
        try: return requests.get(url, headers=headers).json()
        except: return {}

    def run_trending(self):
        url = f"https://api.themoviedb.org/3/trending/{self.current_mode}/week"
        self.restart_belt(url)

    def run_genre(self, g_id):
        url = f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc"
        self.restart_belt(url)

    def run_search(self):
        query = self.search_input.text()
        url = f"https://api.themoviedb.org/3/search/{self.current_mode}?query={query}"
        self.restart_belt(url)

    def restart_belt(self, url):
        self.task_counter += 1
        self.signals.clear_signal.emit()
        threading.Thread(target=self.worker, args=(url, self.task_counter), daemon=True).start()

    def worker(self, url, task_id):
        res = self.api_call(url)
        results = res.get('results', [])
        q_days = self.settings.get("quarantine_days", 90)
        safe_date = datetime.now() - timedelta(days=q_days)
        count = 1
        for item in results:
            if self.task_counter != task_id: return
            r_date_str = item.get('release_date') or item.get('first_air_date') or ''
            try:
                if r_date_str:
                    r_date = datetime.strptime(r_date_str, '%Y-%m-%d')
                    if self.current_mode == "movie" and r_date > safe_date: continue
            except: continue
            self.executor.submit(self.load_image_worker, item, count, self.current_mode, task_id)
            count += 1
            time.sleep(0.05)

    def load_image_worker(self, item, rank, m_type, task_id):
        pix = QPixmap()
        if item.get('poster_path'):
            try:
                data = requests.get(f"https://image.tmdb.org/t/p/w200{item['poster_path']}").content
                img = QImage.fromData(data)
                pix = QPixmap.fromImage(img).scaled(150, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except: pass
        if self.task_counter == task_id:
            self.signals.item_signal.emit(item, pix, rank, m_type, task_id)

    def add_item_to_ui(self, item, pix, rank, m_type, task_id):
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix)
        p.setStyleSheet("border-radius: 8px; border: 1px solid #330066;")
        
        btn_row = QHBoxLayout()
        b_watch = QPushButton("WATCH"); b_watch.setObjectName("WatchBtn")
        b_watch.clicked.connect(lambda: self.launch(item, m_type))
        
        b_fav = QPushButton("⭐"); b_fav.setObjectName("FavBtn"); b_fav.setFixedWidth(40)
        b_fav.clicked.connect(lambda: self.save_to_favorites(item))
        
        btn_row.addWidget(b_watch); btn_row.addWidget(b_fav)
        l.addWidget(p, alignment=Qt.AlignCenter); l.addLayout(btn_row)
        self.gallery_layout.addWidget(f, (rank-1)//5, (rank-1)%5)

    def launch(self, item, m_type):
        ts = int(time.time())
        if m_type == "movie":
            u = f"https://vidsrc.me/embed/movie?tmdb={item['id']}&t={ts}"
        else:
            u = f"https://vidsrc.me/embed/tv?tmdb={item['id']}&season=1&episode=1&t={ts}"
        
        self.update_log("🎬 Force-Starting Chrome Trojan Horse...")
        
        # Hard-coded Chrome hunt
        chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
        try:
            webbrowser.get(chrome_path).open(u)
        except:
            webbrowser.open(u) # Edge fallback if chrome missing

    def clear_gallery(self):
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0); child.widget().deleteLater() if child.widget() else None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MoviePlusPro()
    win.show()
    sys.exit(app.exec_())
