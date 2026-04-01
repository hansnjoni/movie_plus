import sys, os, requests, threading, time, json, webbrowser, re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS SUBSYSTEM CHECK ---
VOICE_READY = False
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except: pass

YT_READY = False
try:
    from youtubesearchpython import VideosSearch
    YT_READY = True
except: pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QActionGroup, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

# --- PROTOCOL: SIGNAL HANDLER ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()
    voice_status = pyqtSignal(str)

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #1a0033; }
QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QScrollArea { background-color: #1a0033; border: none; }
QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }
QFrame#MovieCard { background-color: #1a0000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
QFrame#MovieCard:hover { border: 2px solid #00ff00; background-color: #001a00; }
QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; font-family: 'Consolas'; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#VoiceBtn { background-color: #330033; color: #ff00ff; border: 1px solid #ff00ff; }
QPushButton#Listening { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
* { outline: none; }
"""

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 300)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix); layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        self.title = QLabel((item.get('title') or item.get('name'))[:18])
        self.title.setStyleSheet("color: white; font-size: 10px;"); layout.addWidget(self.title, alignment=Qt.AlignCenter)
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.launch_with_sentinel(item['id'], mtype, self.title.text()))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        rating = self.item.get('vote_average', 'N/A')
        date = self.item.get('release_date') or self.item.get('first_air_date') or 'Unknown'
        self.parent_app.signals.log_signal.emit(f"🔍 SENTINEL INTEL: {self.title.text()} | ⭐ {rating} | 📅 {date}")

class StarkCinemaSentinel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - The Sentinel V19.0")
        self.resize(1500, 920); self.setStyleSheet(STYLESHEET)
        
        self.pref_file = "neural_prefs.json"; self.prefs = self.load_prefs()
        self.current_source_idx = 0
        self.source_list = ["Alpha", "Bravo", "Gamma", "Delta", "Epsilon"]
        self.sources = {
            "Alpha": "vidsrc.me", "Bravo": "vidsrc.to", "Gamma": "vidsrc.cc", "Delta": "embed.su", "Epsilon": "vidsrc.xyz"
        }
        
        self.shown_ids = set(); self.task_counter = 0; self.current_mode = "movie"
        self.current_mid = None; self.current_title = None; self.current_mtype = None
        self.auto_pilot = False; self.social_omega = None
        
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.voice_status.connect(self.update_voice_ui)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()

    def load_prefs(self):
        if os.path.exists(self.pref_file):
            try:
                with open(self.pref_file, 'r') as f: return json.load(f)
            except: pass
        return {"action": 0, "comedy": 0, "horror": 0, "crime": 0}

    def save_prefs(self):
        with open(self.pref_file, 'w') as f: json.dump(self.prefs, f)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        btn_trend = QPushButton("🔥 FRESH TRENDING"); btn_trend.clicked.connect(self.run_fresh_trending); side_layout.addWidget(btn_trend)
        self.v_btn = QPushButton("🎙️ VOICE COMMAND"); self.v_btn.setObjectName("VoiceBtn")
        self.v_btn.clicked.connect(self.start_voice_thread); side_layout.addWidget(self.v_btn)
        
        side_layout.addWidget(QLabel("\n   NEURAL GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80)]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i, name=n.lower(): self.neural_genre_click(idx, name)); side_layout.addWidget(b)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(280)
        side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("The Sentinel is scouting links..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(10); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def neural_genre_click(self, idx, name):
        self.prefs[name] += 1; self.save_prefs()
        self.signals.log_signal.emit(f"🧠 NEURAL: Memory updated. {name.upper()} priority increased.")
        self.run_fresh_genre(idx)

    def launch_with_sentinel(self, mid, mtype, title):
        self.current_mid = mid; self.current_mtype = mtype; self.current_title = title
        self.signals.log_signal.emit(f"🛡️ SENTINEL: Scouting health for '{title}'...")
        threading.Thread(target=self.sentinel_worker, daemon=True).start()

    def sentinel_worker(self):
        # Neural Failover: Check Alpha and Bravo first
        for s_name in ["Alpha", "Bravo"]:
            url = f"https://vidsrc.me/embed/{self.current_mtype}?tmdb={self.current_mid}" if s_name == "Alpha" else f"https://vidsrc.to/embed/{self.current_mtype}/{self.current_mid}"
            try:
                if requests.head(url, timeout=1.5).status_code == 200:
                    self.signals.log_signal.emit(f"✅ SENTINEL: Source {s_name} is Healthy."); webbrowser.open(url); return
            except: continue
        self.signals.log_signal.emit("⚠️ SENTINEL: Primary sources blocked. Using Gamma Hail Mary."); webbrowser.open(f"https://vidsrc.cc/v2/embed/{self.current_mtype}/{self.current_mid}")

    def run_fresh_trending(self):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        top_genre = max(self.prefs, key=self.prefs.get); genre_ids = {"action": 28, "comedy": 35, "horror": 27, "crime": 80}
        url = f"https://api.themoviedb.org/3/discover/{self.current_mode}?sort_by=popularity.desc&primary_release_date.gte={six_mo}&with_genres={genre_ids[top_genre]}"
        self.start_thread(url)

    def run_fresh_genre(self, g_id):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&primary_release_date.gte={six_mo}&sort_by=popularity.desc")

    def process_command(self):
        cmd = self.search_bar.text().lower().strip()
        if cmd.startswith("play "): self.auto_pilot = True; self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd.replace('play ', '')}")
        else: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:60]):
                if t_id == self.task_counter:
                    self.executor.submit(self.img_worker, item, i+1, self.current_mode, t_id)
                    time.sleep(0.25)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            pix = QPixmap(); pix.loadFromData(requests.get(f"https://image.tmdb.org/t/p/w300{item['poster_path']}").content)
            self.signals.item_signal.emit(item, pix.scaled(155, 230, Qt.KeepAspectRatio), rank, mtype, tid)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)
            if self.auto_pilot and rank == 1:
                self.auto_pilot = False; self.launch_with_sentinel(item['id'], mtype, (item.get('title') or item.get('name')))

    def start_voice_thread(self):
        if VOICE_READY: threading.Thread(target=self.voice_worker, daemon=True).start()

    def voice_worker(self):
        self.signals.voice_status.emit("listening"); r = sr.Recognizer()
        with sr.Microphone() as src:
            try:
                q = r.recognize_google(r.listen(src, timeout=5)).lower()
                self.search_bar.setText(f"play {q}"); self.process_command()
            except: pass
        self.signals.voice_status.emit("idle")

    def update_voice_ui(self, status):
        self.v_btn.setObjectName("Listening" if status == "listening" else "VoiceBtn"); self.v_btn.setText("● LISTENING..." if status == "listening" else "🎙️ VOICE COMMAND"); self.setStyleSheet(STYLESHEET)

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit(); threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        menu = QMenu(); menu.addAction("👁️ SHOW").triggered.connect(self.show_normal); menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

    def show_normal(self): self.show(); self.raise_(); self.activateWindow()
    def clear_gallery(self): 
        self.shown_ids.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); win = StarkCinemaSentinel(); win.show(); sys.exit(app.exec_())
