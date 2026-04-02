import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- DIAGNOSTIC START ---
print("--- [STARTING JARVIS CORE V65.1] ---")

# --- PERSISTENCE ---
USER_DATA_FILE = "user_profile.json"
WATCH_HISTORY_FILE = "watched_episodes.json"

def load_data(file, default):
    try:
        if not os.path.exists(file):
            with open(file, 'w') as f: json.dump(default, f)
            return default
        with open(file, 'r') as f: return json.load(f)
    except: return default

USER = load_data(USER_DATA_FILE, {"name": "Hans", "partner": "the little woman", "job": "Electrician/Plumber"})
WATCHED = load_data(WATCH_HISTORY_FILE, {})

# --- LIBRARY CHECK ---
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                                 QFrame, QTextEdit, QComboBox, QCheckBox)
    from PyQt5.QtCore import Qt, pyqtSignal, QObject
    from PyQt5.QtGui import QPixmap, QIcon, QFont
    print("✅ UI MODULES: ONLINE")
except Exception as e:
    print(f"❌ UI ERROR: {e}")
    input("Press Enter to exit...")
    sys.exit()

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(175, 330); self.setObjectName("MovieCard")
        self.setStyleSheet("QFrame#MovieCard { border: 2px solid #ff0000; background: #000; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = item.get('title') or item.get('name'); layout.addWidget(QLabel(t[:15]))
        btn = QPushButton("SELECT"); btn.clicked.connect(lambda: app.initiate_watch_protocol(item, mtype)); layout.addWidget(btn)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Master Terminal [USER: {USER['name']}]")
        self.resize(1500, 950); self.current_mode = "movie"; self.is_live_mode = False
        self.task_counter = 0; self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        print("🚀 GUI INITIALIZED")

    def speak(self, text):
        def run_speech():
            cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
            subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-weight: bold; }
            QPushButton { background-color: #111; color: #ff0000; border: 1px solid #ff0000; padding: 10px; }
            QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
            QLineEdit { background-color: #111; border: 1px solid #ff0000; color: #00ff00; padding: 10px; }
            QTextEdit#Console { background-color: #000; color: #00ff00; font-family: 'Consolas'; border: 1px solid #333; }
        """)

        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists("logo.png"):
            l = QLabel(); l.setPixmap(QPixmap("logo.png").scaled(240, 120, Qt.KeepAspectRatio)); side_layout.addWidget(l, alignment=Qt.AlignCenter)

        side_layout.addWidget(QLabel(" MODE "))
        self.mode_toggle = QComboBox(); self.mode_toggle.addItems(["Movies", "TV Shows"]); self.mode_toggle.currentTextChanged.connect(self.switch_mode); side_layout.addWidget(self.mode_toggle)

        side_layout.addWidget(QLabel("\n GENRES "))
        for name, g_id in [("ACTION", 28), ("COMEDY", 35), ("CRIME", 80), ("TRUE CRIME", "80,99"), ("HORROR", 27)]:
            btn = QPushButton(name); btn.clicked.connect(lambda ch, idx=g_id: self.run_genre(idx)); side_layout.addWidget(btn)

        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(200); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        content = QWidget(); c_layout = QVBoxLayout(content)
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search..."); search_row.addWidget(self.search_bar)
        self.search_btn = QPushButton("GO"); self.search_btn.clicked.connect(self.process_command); search_row.addWidget(self.search_btn)
        c_layout.addLayout(search_row)

        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll)
        layout.addWidget(content)

    def switch_mode(self, text):
        self.current_mode = "movie" if text == "Movies" else "tv"; self.run_fresh_trending()

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def initiate_watch_protocol(self, item, mtype):
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"; webbrowser.open(url)

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip(); 
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/{self.current_mode}?query={cmd}")

    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/day")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:25]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, self.current_mode, t_id); time.sleep(0.05)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, mtype, tid)
        except: pass

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        win = StarkCinemaSingularity()
        win.show()
        print("--- [HUD ACTIVE] ---")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"🔥 CRITICAL STARTUP ERROR: {e}")
        input("Press Enter to close...")
