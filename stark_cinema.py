import sys, os, requests, threading, time, json, webbrowser, re, subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS SUBSYSTEM INITIALIZATION ---
VOICE_ON = True 
VOICE_READY = False
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except: pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- PROTOCOL: SIGNAL HANDLER ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()
    voice_status = pyqtSignal(str)

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

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

class StarkCinemaApex(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - The Apex V24.0")
        self.resize(1500, 920)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a0033; }
            QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QScrollArea { background-color: #1a0033; border: none; }
            QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }
            QFrame#MovieCard { background-color: #1a0000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
            QFrame#MovieCard:hover { border: 2px solid #00ff00; background-color: #001a00; }
            QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; }
            QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
            QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
            QPushButton#LiveOn { background-color: #004400; color: #00ff00; border: 2px solid #00ff00; }
            QPushButton#LiveOff { background-color: #330000; color: #ff0000; border: 1px solid #ff0000; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        self.is_live_mode = False
        self.speak_lock = threading.Lock() 
        self.task_counter = 0; self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()
        self.speak("Apex Build synchronized. All tactical modules are integrated.")

    def speak(self, text):
        if not VOICE_ON: return
        def run_speech():
            with self.speak_lock: 
                cmd = f'PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def initiate_watch_protocol(self, item, mtype):
        title = item.get('title') or item.get('name')
        rel_date = item.get('release_date') or item.get('first_air_date')
        if rel_date and datetime.strptime(rel_date, '%Y-%m-%d') > datetime.now():
            self.speak(f"Negative Boss, {title} is still in theaters. Digital file not found.")
            return
        self.speak(f"Analyzing {title}.")
        threading.Thread(target=self.sentinel_worker, args=(item['id'], mtype, title), daemon=True).start()

    def sentinel_worker(self, mid, mtype, title):
        mirrors = [f"https://vidsrc.me/embed/{mtype}?tmdb={mid}", f"https://vidsrc.to/embed/{mtype}/{mid}"]
        for url in mirrors:
            try:
                if requests.head(url, timeout=1.5).status_code == 200:
                    self.speak("Link active. Opening browser.")
                    webbrowser.open(url); return
            except: continue
        self.speak("All mirrors are unresponsive for this title.")

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode:
            self.live_btn.setText("🎙️ LIVE MODE: ACTIVE"); self.live_btn.setObjectName("LiveOn")
            self.speak("Live link active. I'm listening.")
            threading.Thread(target=self.live_voice_loop, daemon=True).start()
        else:
            self.live_btn.setText("🎙️ LIVE MODE: STANDBY"); self.live_btn.setObjectName("LiveOff")
            self.speak("Live mode terminated.")
        self.setStyleSheet(self.styleSheet())

    def live_voice_loop(self):
        r = sr.Recognizer()
        while self.is_live_mode:
            if self.speak_lock.locked(): # Echo-Shield: Don't listen to the speaker output
                time.sleep(0.5); continue
            with sr.Microphone() as src:
                try:
                    audio = r.listen(src, timeout=3, phrase_time_limit=5)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"🗣️ Live Command: '{q}'")
                    if "stop" in q or "off" in q or "terminate" in q:
                        self.is_live_mode = False; break
                    self.speak(f"Searching for {q}.")
                    self.search_bar.setText(q); self.process_command()
                except: pass
            time.sleep(0.1)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        btn_trend = QPushButton("🔥 FRESH TRENDING"); btn_trend.clicked.connect(self.run_fresh_trending); side_layout.addWidget(btn_trend)
        
        self.live_btn = QPushButton("🎙️ LIVE MODE: STANDBY"); self.live_btn.setObjectName("LiveOff")
        self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        
        side_layout.addWidget(QLabel("\n   GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("TRUE CRIME", "80,99")]:
            b = QPushButton(n)
            b.clicked.connect(lambda ch, idx=i: self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={idx}&primary_release_date.gte={(datetime.now()-timedelta(days=180)).strftime('%Y-%m-%d')}"))
            side_layout.addWidget(b)
        
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(280)
        side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Live Link Monitoring..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(10); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def run_fresh_trending(self):
        six_mo = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?sort_by=popularity.desc&primary_release_date.gte={six_mo}")

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

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

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self); self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        menu = QMenu(); menu.addAction("👁️ SHOW").triggered.connect(self.show); menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False); win = StarkCinemaApex(); win.show(); sys.exit(app.exec_())
