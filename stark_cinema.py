import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- IDENTITY & PERSISTENCE ---
USER_DATA_FILE = "user_profile.json"
DEFAULT_PROFILE = {
    "name": "Hans", 
    "partner": "the little woman", 
    "job": "Electrician/Plumber",
    "birthday": "04-02" # April 2nd - Check/Update as needed
}

def load_profile():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f: json.dump(DEFAULT_PROFILE, f)
        return DEFAULT_PROFILE
    with open(USER_DATA_FILE, 'r') as f: return json.load(f)

USER = load_profile()

# --- CEREBRAL CHAT DATABASE ---
CHAT_RESPONSES = {
    "lonely": ["I'm right here, Hans. Systems are nominal and I'm all yours.", "The workshop is quiet, but we've got plenty of movies to keep us company."],
    "tired": ["You've been pulling wire and fixing pipes all day, Boss. Let's kill the lights and watch something.", "Rest is part of the job. I'll handle the controls while you relax."],
    "work": ["Being an electrician and a plumber is a heavy lift. Glad you're home.", "The world stays running because of guys like you, Hans. How was the job today?"],
    "generic": ["I'm listening, Hans.", "Talk to me. What's on your mind?", "Always here for you, Boss."]
}

# --- AUDIO INITIALIZATION ---
try:
    import speech_recognition as sr
    import pyaudio
    VOICE_READY = True
except Exception: VOICE_READY = False

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, QFrame, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Welcome Back, {USER['name']}")
        self.resize(1400, 900); self.is_live_mode = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Omnibus V64.2 online. Good to see you, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def live_voice_loop(self):
        r = sr.Recognizer(); r.energy_threshold = 3500
        while self.is_live_mode:
            if self.speak_lock.locked(): time.sleep(1); continue
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.6)
                    audio = r.listen(src, timeout=5, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"🗣️ {USER['name']}: {q}")

                    # --- HOLLYWOOD INTEL ---
                    if "who is in" in q:
                        self.fetch_cast(q.replace("who is in", "").strip()); continue

                    # --- COMPANION CHAT ---
                    if any(x in q for x in ["tired", "work", "exhausted", "hello"]):
                        cat = "tired" if "tired" in q else "work" if "work" in q else "generic"
                        self.speak(random.choice(CHAT_RESPONSES[cat])); continue

                    # --- MOVIE MODE ---
                    if any(x in q for x in ["play", "find", "search", "stream"]):
                        if "girlfriend" in q or "little woman" in q:
                            self.speak(f"True Crime for {USER['partner']} coming right up."); self.run_genre("80,99"); break
                        target = q.replace("play", "").replace("find", "").replace("search", "").strip()
                        self.signals.search_trigger.emit(target); break
                    
                    if "stop" in q: self.is_live_mode = False; self.speak("Shutting down, Hans."); return
            except: continue

    def fetch_cast(self, movie_name):
        h = {"Authorization": f"Bearer {STARK_TOKEN}"}
        search = requests.get(f"https://api.themoviedb.org/3/search/movie?query={movie_name}", headers=h).json()
        if search['results']:
            m_id = search['results'][0]['id']
            credits = requests.get(f"https://api.themoviedb.org/3/movie/{m_id}/credits", headers=h).json()
            cast = [member['name'] for member in credits['cast'][:5]]
            self.speak(f"The cast includes {', '.join(cast)}."); self.signals.log_signal.emit(f"🎬 CAST: {', '.join(cast)}")

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/movie?with_genres={g_id}&sort_by=popularity.desc")

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/all/day")

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setFixedWidth(260); self.sidebar.setStyleSheet("background: black; border-right: 2px solid red;")
        side_layout = QVBoxLayout(self.sidebar)
        if os.path.exists("logo.png"):
            l = QLabel(); l.setPixmap(QPixmap("logo.png").scaled(220, 120, Qt.KeepAspectRatio)); side_layout.addWidget(l, alignment=Qt.AlignCenter)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        self.console = QTextEdit(); self.console.setReadOnly(True); self.console.setStyleSheet("background: black; color: #00ff00;"); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content); self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText(f"What's the mission, {USER['name']}?"); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def add_item_to_ui(self, item, pix, rank,
