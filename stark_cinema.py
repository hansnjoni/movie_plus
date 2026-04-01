import sys, os, requests, threading, time, json, webbrowser, re, subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS SUBSYSTEM INITIALIZATION ---
VOICE_ON = True  # Set to False to mute JARVIS
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

# --- SIGNAL HANDLER PROTOCOL ---
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
"""

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 300)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix); layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        self.title_str = (item.get('title') or item.get('name'))[:18]
        self.title_lbl = QLabel(self.title_str); self.title_lbl.setStyleSheet("color: white; font-size: 10px;"); layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.initiate_watch_protocol(item, mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        rating = self.item.get('vote_average', 'N/A')
        date = self.item.get('release_date') or self.item.get('first_air_date') or 'Unknown'
        summary = self.item.get('overview', 'No data.')[:140] + "..."
        self.parent_app.signals.log_signal.emit(f"🔍 INTEL: {self.title_str} | ⭐ {rating} | 📅 {date}\n📝 {summary}")

class StarkCinemaMaster(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Singularity V21.0")
        self.resize(1500, 920); self.setStyleSheet(STYLESHEET)
        
        self.pref_file = "neural_prefs.json"; self.prefs = self.load_prefs()
        self.current_source_idx = 0; self.social_omega = None
        self.source_list = ["Alpha", "Bravo", "Gamma", "Delta", "Epsilon"]
        
        self.shown_ids = set(); self.task_counter = 0; self.current_mode = "movie"
        self.current_mid = None; self.current_title = None; self.current_mtype = None
        
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.voice_status.connect(self.update_voice_ui)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()
        self.speak("Systems Integrated. All tactical modules online.")

    def load_prefs(self):
        if os.path.exists(self.pref_file):
            try:
                with open(self.pref_file, 'r') as f: return json.load(f)
            except: pass
        return {"action": 0, "comedy": 0, "horror": 0, "crime": 0}

    def speak(self, text):
        if not VOICE_ON: return
        cmd = f'PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\');"'
        threading.Thread(target=lambda: subprocess.run(cmd, shell=True), daemon=True).start()

    def initiate_watch_protocol(self, item, mtype):
        self.current_mid = item['id']; self.current_mtype = mtype
        self.current_title = item.get('title') or item.get('name')
        
        # Freshness Check
        rel_date = item.get('release_date') or item.get('first_air_date')
        if rel_date and datetime.strptime(rel_date, '%Y-%m-%d') > datetime.now():
            self.speak(f"Warning Boss, {self.current_title} is not out on video file yet.")
            return

        self.speak(f"Scouting link health for {self.current_title}.")
        threading.Thread(target=self.sentinel_worker, daemon=True).start()

    def sentinel_worker(self):
        test_urls = [
            f"https://vidsrc.me/embed/{self.current_mtype}?tmdb={self.current_mid}",
            f"https://vidsrc.to/embed/{self.current_mtype}/{self.current_mid}",
            f"https://vidsrc.cc/v2/embed/{self.current_mtype}/{self.current_mid}"
        ]
        for url in test_urls:
            try:
                if requests.head(url, timeout=1.5).status_code == 200:
                    self.speak("Link secured. Enjoy the show.")
                    webbrowser.open(url); return
            except: continue
        self.speak("I'm sorry Boss, the mirrors are unresponsive.")

    def run_fresh_trending(self):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        top_g = max(self.prefs, key=self.prefs.get)
        g_ids = {"action": 28, "comedy": 35, "horror": 27, "crime": 80}
        url = f"https://api.themoviedb.org/3/discover/{self.current_mode}?sort_by=popularity.desc&primary_release_date.gte={six_mo}&with_genres={g_ids[top_g]}"
        self.start_thread(url)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        btn_trend = QPushButton("🔥 FRESH TRENDING"); btn_trend.clicked.connect(self.run_fresh_trending); side_layout.addWidget(btn_trend)
        self.v_btn = QPushButton("🎙️ VOICE COMMAND"); self.v_btn.setObjectName("VoiceBtn")
        self.v_btn.clicked.connect(self.start_voice_thread); side_layout.addWidget(self.v_btn)
        
        side_layout.addWidget(QLabel("\n   NEURAL GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80)]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i, name=n.lower(): self.run_fresh_genre(idx, name)); side_layout.addWidget(b)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(280)
        side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search or use taskbar commands..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(10); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def run_fresh_genre(self, g_id, name):
        self.prefs[name] += 1
        with open(self.pref_file, 'w') as f: json.dump(self.prefs, f)
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&primary_release_date.gte={six_mo}&sort_by=popularity.desc")

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        menu = QMenu()
        
        # Taskbar Command Center
        asst = menu.addMenu("🎙️ ASSISTANT")
        asst.addAction("🎤 Voice Search").triggered.connect(self.start_voice_thread)
        asst.addAction("🔄 Repair Link").triggered.connect(self.sentinel_worker)
        
        disc = menu.addMenu("🔥 DISCOVERY")
        disc.addAction("Trending (Last 6mo)").triggered.connect(self.run_fresh_trending)
        
        menu.addSeparator()
        menu.addAction("👁️ SHOW").triggered.connect(self.show_normal)
        menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

    def start_voice_thread(self):
        if VOICE_READY: threading.Thread(target=self.voice_worker, daemon=True).start()
        else: self.speak("Ears offline, Boss.")

    def voice_worker(self):
        self.signals.voice_status.emit("listening"); r = sr.Recognizer()
        with sr.Microphone() as src:
            try:
                q = r.recognize_google(r.listen(src, timeout=5)).lower()
                if "fix" in q or "broken" in q: self.sentinel_worker()
                else: self.search_bar.setText(f"play {q}"); self.process_command()
            except: pass
        self.signals.voice_status.emit("idle")

    def update_voice_ui(self, status):
        self.v_btn.setObjectName("Listening" if status == "listening" else "VoiceBtn")
        self.v_btn.setText("● LISTENING..." if status == "listening" else "🎙️ VOICE COMMAND"); self.setStyleSheet(STYLESHEET)

    def process_command(self):
        cmd = self.search_bar.text().lower().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd.replace('play ', '')}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

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

    def show_normal(self): self.show(); self.raise_(); self.activateWindow()
    def clear_gallery(self): 
        self.shown_ids.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); win = StarkCinemaMaster(); win.show(); sys.exit(app.exec_())
