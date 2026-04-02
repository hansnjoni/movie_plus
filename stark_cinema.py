import sys, os, requests, threading, time, json, webbrowser, re, subprocess, shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

# --- JARVIS 3.12.0 STABLE INITIALIZATION ---
VOICE_ON = True 
VOICE_READY = False
MIC_INVENTORY = []

try:
    import speech_recognition as sr
    import pyaudio
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            MIC_INVENTORY.append({"id": i, "name": dev['name']})
    VOICE_READY = True if MIC_INVENTORY else False
except Exception:
    VOICE_READY = False

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QTextEdit, 
                             QSystemTrayIcon, QMenu, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str)
    clear_signal = pyqtSignal()
    search_trigger = pyqtSignal(str)

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, parent_app):
        super().__init__()
        self.setObjectName("MovieCard"); self.setFixedSize(170, 320)
        self.item = item; self.parent_app = parent_app; self.mtype = mtype
        layout = QVBoxLayout(self)
        self.poster = QLabel(); self.poster.setPixmap(pix)
        layout.addWidget(self.poster, alignment=Qt.AlignCenter)
        title = item.get('title') or item.get('name') or "Unknown"
        self.title_lbl = QLabel(title[:20]); self.title_lbl.setStyleSheet("color: white; font-size: 10px;")
        layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        self.btn = QPushButton("WATCH"); self.btn.clicked.connect(lambda: parent_app.initiate_watch_protocol(item, mtype))
        layout.addWidget(self.btn)

    def enterEvent(self, event):
        pop = self.item.get('popularity', 0); vote = self.item.get('vote_average', 0)
        score = round((vote * 0.7) + (min(pop/100, 3)), 1)
        name = self.item.get('title') or self.item.get('name')
        self.parent_app.signals.log_signal.emit(f"⭐ STARK SCORE: {score}/10 | {name}")

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Omnibus V63.5")
        self.resize(1400, 900)
        
        if os.path.exists("logo.png"):
            self.setWindowIcon(QIcon("logo.png"))

        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QScrollArea { background-color: #050505; border: none; }
            QWidget#Gallery { background-color: #000000; }
            QFrame#MovieCard { background-color: #000000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; }
            QFrame#MovieCard:hover { border: 2px solid #00ff00; }
            QLineEdit { background-color: #111; border: 2px solid #ff0000; border-radius: 8px; color: #00ff00; padding: 12px; }
            QPushButton { background-color: #000000; color: #ff0000; border: 2px solid #ff0000; border-radius: 8px; padding: 10px; font-weight: bold; }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; background-color: #001100; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
        """)
        
        self.is_live_mode = False; self.auto_pilot = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.current_mode = "movie"; self.executor = ThreadPoolExecutor(max_workers=10)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.setup_tray(); self.run_fresh_trending()
        
        if VOICE_READY:
            self.speak("Omnibus build online. All ears, Boss.")
        else:
            self.signals.log_signal.emit("❌ HUD ERROR: Microphone link offline.")

    def speak(self, text):
        if not VOICE_ON: return
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def live_voice_loop(self):
        r = sr.Recognizer(); r.energy_threshold = 4000
        while self.is_live_mode:
            if self.speak_lock.locked(): time.sleep(1); continue
            for mic in MIC_INVENTORY:
                try:
                    with sr.Microphone(device_index=mic['id']) as src:
                        r.adjust_for_ambient_noise(src, duration=0.6)
                        audio = r.listen(src, timeout=4, phrase_time_limit=8)
                        q = r.recognize_google(audio).lower()
                        self.signals.log_signal.emit(f"🗣️ YOU: {q}")
                        
                        if "stop" in q:
                            self.is_live_mode = False; self.speak("Going to standby."); return
                        if "who are you" in q or "your name" in q:
                            self.speak("I am JARVIS. Ready for your command."); break
                        if "horror" in q: self.run_genre(27); break
                        if "comedy" in q: self.run_genre(35); break
                        if "true crime" in q or "girlfriend" in q: 
                            self.speak("Accessing True Crime archives."); self.run_genre("80,99"); break
                        
                        self.auto_pilot = "play" in q
                        target = q.replace("play", "").replace("movie", "").strip()
                        if target: self.signals.search_trigger.emit(target)
                        break
                except: continue
            time.sleep(0.5)

    def toggle_live_mode(self):
        if not VOICE_READY: return
        self.is_live_mode = not self.is_live_mode
        self.live_btn.setText(f"🎙️ LIVE MODE: {'ACTIVE' if self.is_live_mode else 'OFF'}")
        if self.is_live_mode:
            self.signals.log_signal.emit("📡 Intent Engine Hot.")
            threading.Thread(target=self.live_voice_loop, daemon=True).start()
        else: self.speak("Standby.")

    def initiate_watch_protocol(self, item, mtype):
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"
        webbrowser.open(url)

    def trigger_search(self, query):
        self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

    def run_genre(self, g_id):
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")

    def run_fresh_trending(self):
        self.start_thread(f"https://api.themoviedb.org/3/trending/all/day")

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists("logo.png"):
            logo_label = QLabel(); logo_label.setPixmap(QPixmap("logo.png").scaled(220, 120, Qt.KeepAspectRatio))
            side_layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        side_layout.addWidget(QLabel(" COMMAND CENTER "))
        self.live_btn = QPushButton("🎙️ LIVE MODE: OFF"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        side_layout.addWidget(QLabel("\n SYNDICATE MODULES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("TRUE CRIME", "80,99")]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i: self.run_genre(idx)); side_layout.addWidget(b)
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(250)
        side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content); self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Identify target..."); self.search_bar.returnPressed.connect(self.process_command); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)
            if self.auto_pilot and rank == 1: self.auto_pilot = False; self.initiate_watch_protocol(item, mtype)

    def clear_gallery(self): 
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:25]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, item.get('media_type', 'movie'), t_id); time.sleep(0.05)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225, Qt.KeepAspectRatio), rank, mtype, tid)
        except: pass

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists("logo.png"): self.tray_icon.setIcon(QIcon("logo.png"))
        menu = QMenu()
        menu.addAction("👁️ SHOW").triggered.connect(self.show); menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(menu); self.tray_icon.show()

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
