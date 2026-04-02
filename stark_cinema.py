import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- PERSISTENCE: IDENTITY & WATCHED HISTORY ---
USER_DATA_FILE = "user_profile.json"
WATCH_HISTORY_FILE = "watched_episodes.json"

def load_data(file, default):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump(default, f)
        return default
    with open(file, 'r') as f: return json.load(f)

USER = load_data(USER_DATA_FILE, {"name": "Hans", "partner": "the little woman", "job": "Electrician/Plumber"})
WATCHED = load_data(WATCH_HISTORY_FILE, {}) # Structure: {"tv_id": ["S1E1", "S1E2"]}

def save_watched():
    with open(WATCH_HISTORY_FILE, 'w') as f: json.dump(WATCHED, f)

# --- STABLE INITIALIZATION ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                             QFrame, QTextEdit, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon, QFont

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Master Terminal")
        self.resize(1500, 950)
        self.current_mode = "movie"
        self.is_live_mode = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Full Dashboard Restored. TV and Movie modules are online, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        # --- STARK THEME ---
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #111; color: #ff0000; border: 1px solid #ff0000; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
            QLineEdit { background-color: #111; border: 1px solid #ff0000; color: #00ff00; padding: 10px; border-radius: 5px; }
            QTextEdit#Console { background-color: #000; color: #00ff00; font-family: 'Consolas'; font-size: 10px; border: 1px solid #333; }
            QComboBox { background-color: #111; color: #00ff00; border: 1px solid #ff0000; }
        """)

        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)

        # --- SIDEBAR (THE GENRE HUB) ---
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280)
        side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists("logo.png"):
            l = QLabel(); l.setPixmap(QPixmap("logo.png").scaled(240, 120, Qt.KeepAspectRatio)); side_layout.addWidget(l, alignment=Qt.AlignCenter)

        side_layout.addWidget(QLabel(" MODE SELECTION "))
        self.mode_toggle = QComboBox(); self.mode_toggle.addItems(["Movies", "TV Shows"])
        self.mode_toggle.currentTextChanged.connect(self.switch_mode); side_layout.addWidget(self.mode_toggle)

        side_layout.addWidget(QLabel("\n SYNDICATE GENRES "))
        genres = [("ACTION", 28), ("COMEDY", 35), ("CRIME", 80), ("TRUE CRIME", "80,99"), ("ADVENTURE", 12), ("HORROR", 27)]
        for name, g_id in genres:
            btn = QPushButton(name); btn.clicked.connect(lambda ch, idx=g_id: self.run_genre(idx)); side_layout.addWidget(btn)

        side_layout.addWidget(QLabel("\n COMMANDS "))
        self.live_btn = QPushButton("🎙️ TALK TO JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(200); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        # --- CONTENT AREA ---
        content = QWidget(); c_layout = QVBoxLayout(content)
        
        # Search Bar + Button
        search_row = QHBoxLayout()
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search manually or use JARVIS..."); search_row.addWidget(self.search_bar)
        self.search_btn = QPushButton("SEARCH"); self.search_btn.clicked.connect(self.process_command); search_row.addWidget(self.search_btn)
        c_layout.addLayout(search_row)

        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll)
        layout.addWidget(content)

    def switch_mode(self, text):
        self.current_mode = "movie" if text == "Movies" else "tv"
        self.run_fresh_trending()

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def initiate_watch_protocol(self, item, mtype):
        if mtype == "tv":
            self.show_episode_manager(item)
        else:
            url = f"https://vidsrc.me/embed/movie?tmdb={item['id']}"; webbrowser.open(url)

    def show_episode_manager(self, item):
        # Creates a quick popup for seasons/episodes
        self.manager = QMainWindow(); self.manager.setWindowTitle(f"Episodes: {item.get('name')}"); self.manager.resize(400, 600)
        self.manager.setStyleSheet("background: black; color: #00ff00;")
        scroll = QScrollArea(); widget = QWidget(); ep_layout = QVBoxLayout(widget)
        
        # Simple Logic: Fetch Season 1 (Expansion can be added later)
        h = {"Authorization": f"Bearer {STARK_TOKEN}"}
        res = requests.get(f"https://api.themoviedb.org/3/tv/{item['id']}/season/1", headers=h).json()
        
        for ep in res.get('episodes', []):
            row = QHBoxLayout(); tag = f"S1E{ep['episode_number']}"
            check = QCheckBox(); check.setChecked(tag in WATCHED.get(str(item['id']), []))
            check.stateChanged.connect(lambda state, tid=item['id'], t=tag: self.toggle_watched(tid, t, state))
            
            lbl = QLabel(f"{tag}: {ep['name']}"); lbl.setStyleSheet("color: white;")
            btn = QPushButton("PLAY"); btn.clicked.connect(lambda ch, e=ep['episode_number']: webbrowser.open(f"https://vidsrc.me/embed/tv?tmdb={item['id']}&season=1&episode={e}"))
            
            row.addWidget(check); row.addWidget(lbl); row.addStretch(); row.addWidget(btn)
            ep_layout.addLayout(row)
            
        scroll.setWidget(widget); scroll.setWidgetResizable(True); self.manager.setCentralWidget(scroll); self.manager.show()

    def toggle_watched(self, tv_id, tag, state):
        tid = str(tv_id)
        if tid not in WATCHED: WATCHED[tid] = []
        if state == 2: # Checked
            if tag not in WATCHED[tid]: WATCHED[tid].append(tag)
        else: # Unchecked
            if tag in WATCHED[tid]: WATCHED[tid].remove(tag)
        save_watched()

    # --- SHARED WORKER LOGIC ---
    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/{self.current_mode}?query={cmd}")

    def run_genre(self, g_id):
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")

    def run_fresh_trending(self):
        self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/day")

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

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        self.live_btn.setText("🎙️ JARVIS LISTENING" if self.is_live_mode else "🎙️ TALK TO JARVIS")
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 3500
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    audio = r.listen(src, timeout=5)
                    q = r.recognize_google(audio).lower()
                    if "play" in q or "search" in q:
                        target = q.replace("play", "").replace("search", "").strip()
                        self.signals.search_trigger.emit(target)
            except: continue

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(175, 330); self.setStyleSheet("border: 1px solid #ff0000; padding: 2px;")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl
