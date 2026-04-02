import sys, os, requests, threading, time, json, webbrowser, re, subprocess, shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

# --- JARVIS 3.14.3 MASTER INITIALIZATION ---
VOICE_ON = True 
VOICE_READY = False
MIC_INVENTORY = []

# V42 & V51: Hardware Signal Probe & Auto-Pilot initialization
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            MIC_INVENTORY.append({"id": i, "name": dev['name']})
except Exception:
    VOICE_READY = False

# THE STARK KEY
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- SIGNAL HANDLER ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()
    search_trigger = pyqtSignal(str)

# --- V41: MOVIE CARD WITH STARK SCORE ---
class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 300)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix); layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        
        title = item.get('title') or item.get('name') or "Unknown"
        self.title_lbl = QLabel(title[:18]); self.title_lbl.setStyleSheet("color: white; font-size: 10px;")
        layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        
        self.btn = QPushButton("WATCH")
        self.btn.clicked.connect(lambda: parent_app.initiate_watch_protocol(item, mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        # V41: Stark Score Calculation on Hover
        pop = self.item.get('popularity', 0); vote = self.item.get('vote_average', 0)
        score = round((vote * 0.7) + (min(pop/100, 3)), 1)
        self.parent_app.signals.log_signal.emit(f"⭐ STARK SCORE: {score}/10 | {self.item.get('title') or self.item.get('name')}")

# --- THE MASTER CHASSIS ---
class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Singularity Omnibus V60.0")
        self.resize(1500, 920)
        
        # V52: Syndicate Stealth UI (Black/Red/Green)
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QScrollArea { background-color: #050505; border: none; }
            QWidget#Gallery { background-color: #000000; }
            QFrame#MovieCard { background-color: #000000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
            QFrame#MovieCard:hover { border: 2px solid #00ff00; }
            QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; }
            QPushButton { 
                background-color: #000000; color: #ff0000; border: 2px solid #ff0000; 
                border-radius: 8px; padding: 10px; font-weight: bold; 
            }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; background-color: #001100; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        self.is_live_mode = False; self.auto_pilot = False
        self.speak_lock = threading.Lock(); self.task_counter = 0; self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=15)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()
        
        # V53: Disk Space Report
        try:
            total, used, free = shutil.disk_usage("C:")
            self.signals.log_signal.emit(f"💾 DISK GUARD: {free // (2**30)} GB Free on C: Drive.")
        except: pass

        # V42: Startup Hardware Probe
        if VOICE_READY and MIC_INVENTORY:
            self.signals.log_signal.emit(f"✅ HUD: Found {len(MIC_INVENTORY)} microphones.")
            for mic in MIC_INVENTORY: self.signals.log_signal.emit(f"📡 MIC DETECTED: {mic['name']}")
            self.speak("Omnibus build online. All ears, Boss.")
        else:
            self.signals.log_signal.emit("❌ HUD ERROR: Microphone link offline. 'Plus Plus' (C++) Forge required.")
            self.speak("Voice link is offline, Boss. Check the HUD.")

    def speak(self, text):
        if not VOICE_ON: return
        def run_speech():
            with self.speak_lock: 
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    # V41: Cerebral Intent Mapping
    def handle_intent(self, q):
        def match(a, b): return SequenceMatcher(None, a, b).ratio() > 0.7
        if "comedy" in q or "laugh" in q or match(q, "something funny"):
            self.speak("Accessing comedy archives."); self.run_genre(35); return True
        if "scary" in q or "horror" in q:
            self.speak("Initializing horror protocol."); self.run_genre(27); return True
        if "girlfriend" in q or "true crime" in q:
            self.speak("Finding something for the syndicate."); self.run_genre("80,99"); return True
        return False

    def toggle_live_mode(self):
        if not VOICE_READY:
            self.signals.log_signal.emit("❌ HUD: Live Mode Blocked. Hardware Link missing.")
            return
        self.is_live_mode = not self.is_live_mode
        self.live_btn.setText(f"🎙️ LIVE MODE: {'ACTIVE' if self.is_live_mode else 'OFF'}")
        if self.is_live_mode:
            self.signals.log_signal.emit("📡 HUD: Intent Engine Hot. Speak clearly.")
            threading.Thread(target=self.live_voice_loop, daemon=True).start()
        else: self.speak("Going to standby.")

    # V43 & V51: Visual HUD & Mic Auto-Pilot
    def live_voice_loop(self):
        r = sr.Recognizer(); r.dynamic_energy_threshold = True
        while self.is_live_mode:
            if self.speak_lock.locked(): time.sleep(0.5); continue
            # V51: Auto-Pilot cycles through mics
            for mic in MIC_INVENTORY:
                try:
                    with sr.Microphone(device_index=mic['id']) as src:
                        self.signals.log_signal.emit("🎤 HUD: Listening...")
                        r.adjust_for_ambient_noise(src, duration=0.4)
                        audio = r.listen(src, timeout=5, phrase_time_limit=10)
                        q = r.recognize_google(audio).lower()
                        # V43: Real-Time HUD Transcription
                        self.signals.log_signal.emit(f"🗣️ YOU SAID: \"{q}\"")
                        if "stop" in q: self.is_live_mode = False; return
                        if self.handle_intent(q): break
                        self.auto_pilot = "play" in q
                        target = q.replace("play", "").replace("movie", "").strip()
                        self.signals.search_trigger.emit(target)
                        break
                except: continue
            time.sleep(0.1)

    def trigger_search(self, query):
        self.search_bar.setText(query); self.process_command()

    def initiate_watch_protocol(self, item, mtype):
        title = item.get('title') or item.get('name')
        self.speak(f"Opening {title}.")
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"
        webbrowser.open(url)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        self.live_btn = QPushButton("🎙️ LIVE MODE: OFF"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        
        side_layout.addWidget(QLabel("\n   SYNDICATE GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i: self.run_genre(idx)); side_layout.addWidget(b)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(280)
        side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Speak or type movie name..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(10); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def run_genre(self, g_id):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&primary_release_date.gte={six_mo}")

    def run_fresh_trending(self):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?sort_by=popularity.desc&primary_release_date.gte={six_mo}")

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            # V41: CAM-Shield theater rip detection
            title = (item.get('title') or item.get('name')).lower()
            if any(x in title for x in ["cam", "hdcam", "ts"]): 
                self.signals.log_signal.emit(f"⚠️ CAM-SHIELD: Low quality detected for {title}.")
            
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)
            if self.auto_pilot and rank == 1: self.auto_pilot = False; self.initiate_watch_protocol(item, mtype)

    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        menu = QMenu(); menu.addAction("👁️ SHOW").triggered.connect(self.show); menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:60]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, self.current_mode, t_id); time.sleep(0.1)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            pix = QPixmap(); pix.loadFromData(requests.get(f"https://image.tmdb.org/t/p/w300{item['poster_path']}").content)
            self.signals.item_signal.emit(item, pix.scaled(155, 230, Qt.KeepAspectRatio), rank, mtype, tid)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
