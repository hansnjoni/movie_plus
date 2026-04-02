import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- IDENTITY & BRAIN CONFIG ---
USER_DATA_FILE = "user_profile.json"
def load_user():
    default = {"name": "Hans", "job": "Electrician/Plumber", "partner": "the little woman"}
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f: json.dump(default, f)
        return default
    with open(USER_DATA_FILE, 'r') as f: return json.load(f)

USER = load_user()
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

# --- PERSONALITY MATRIX ---
RESPONSES = {
    "greetings": [
        f"Systems are nominal, {USER['name']}. Ready to light up the shop.",
        f"I'm functioning at peak efficiency. How was the job today, Boss?",
        f"Always online and waiting for you, {USER['name']}. What's the mission?",
        "Cores are cool and the database is primed. I'm doing great."
    ],
    "work_talk": [
        "Be careful with those live wires, Hans. I need you in one piece.",
        "Plumbing and electrics—you're the one keeping the world running. I'll handle the entertainment.",
        "Precision work takes a toll. Let's find something to help you unwind."
    ],
    "small_talk": [
        "I'm just a series of 1s and 0s, but I'm having a stellar day.",
        "Just enjoying the view of the workshop from the internal sensors.",
        "Ready whenever you are. The Little Woman's favorites are already indexed."
    ]
}

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                             QFrame, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - JARVIS Sentience V66.0")
        self.resize(1500, 950); self.current_mode = "movie"; self.is_live_mode = False
        self.speak_lock = threading.Lock(); self.task_counter = 0
        self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Intelligence upgrade complete. Talk to me, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #111; color: #ff0000; border: 1px solid #ff0000; padding: 12px; font-weight: bold; }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; background-color: #001100; }
            QLineEdit { background-color: #000; border: 2px solid #ff0000; color: #00ff00; padding: 12px; font-size: 16px; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #333; font-family: 'Consolas'; }
        """)

        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists("logo.png"):
            l = QLabel(); l.setPixmap(QPixmap("logo.png").scaled(240, 120, Qt.KeepAspectRatio)); side_layout.addWidget(l, alignment=Qt.AlignCenter)

        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setFixedHeight(250); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Say something..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll)
        layout.addWidget(content)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        self.live_btn.setText("📡 JARVIS ACTIVE" if self.is_live_mode else "🎙️ ACTIVATE JARVIS")
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 4000
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=1.0)
                    audio = r.listen(src, timeout=5, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"YOU: {q}")
                    
                    # --- CONVERSATIONAL ENGINE ---
                    if any(x in q for x in ["how are you", "how's it going", "status"]):
                        self.speak(random.choice(RESPONSES["greetings"])); continue
                    
                    if any(x in q for x in ["tired", "work", "job", "pipes", "wire"]):
                        self.speak(random.choice(RESPONSES["work_talk"])); continue

                    if any(x in q for x in ["hello", "jarvis", "you there"]):
                        self.speak(random.choice(RESPONSES["small_talk"])); continue

                    # --- COMMAND ENGINE ---
                    if any(x in q for x in ["play", "find", "search", "show me"]):
                        target = q.replace("play", "").replace("find", "").replace("search", "").replace("show me", "").strip()
                        if target: 
                            self.speak(f"Accessing database for {target}.")
                            self.signals.search_trigger.emit(target)
                        break
                    
                    if "stop" in q: self.speak("Shutting down. Get some rest."); self.is_live_mode = False; break
            except: continue

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/{self.current_mode}?query={cmd}")

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

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/movie/day")

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(175, 330); self.setObjectName("MovieCard")
        self.setStyleSheet("QFrame#MovieCard { border: 2px solid #ff0000; background: #000; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = (item.get('title') or item.get('name'))[:15]; layout.addWidget(QLabel(t))
        btn = QPushButton("WATCH"); btn.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}")); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
