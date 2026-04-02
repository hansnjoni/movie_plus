import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- JARVIS IDENTITY ---
USER_DATA_FILE = "user_profile.json"
DEFAULT_PROFILE = {"name": "Hans", "partner": "the little woman", "job": "Electrician/Plumber"}

def load_profile():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f: json.dump(DEFAULT_PROFILE, f)
        return DEFAULT_PROFILE
    with open(USER_DATA_FILE, 'r') as f: return json.load(f)

USER = load_profile()

# --- STABLE INITIALIZATION ---
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
        self.setWindowTitle(f"Stark Cinema - JARVIS Intelligence V64.1")
        self.resize(1400, 900); self.is_live_mode = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.speak(f"Cast database synced. I can now identify actors for you, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 3500
        while self.is_live_mode:
            if self.speak_lock.locked(): time.sleep(1); continue
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.6)
                    audio = r.listen(src, timeout=5, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"🗣️ {USER['name']}: {q}")

                    # --- HOLLYWOOD INTEL PROTOCOL ---
                    if "who is in" in q or "who played in" in q:
                        movie = q.replace("who is in", "").replace("who played in", "").strip()
                        self.speak(f"Scanning the cast list for {movie}.")
                        self.fetch_cast(movie); continue

                    if "what movies is" in q or "what movies has" in q:
                        actor = q.replace("what movies is", "").replace("what movies has", "").replace("in", "").strip()
                        self.speak(f"Searching for films featuring {actor}.")
                        self.trigger_search(actor); continue

                    # --- STANDARD COMMANDS ---
                    if any(x in q for x in ["play", "find", "search", "stream"]):
                        target = q.replace("play", "").replace("find", "").replace("search", "").strip()
                        self.signals.search_trigger.emit(target); break
                    
                    if "stop" in q: self.is_live_mode = False; self.speak("Shutting down."); return
            except: continue

    def fetch_cast(self, movie_name):
        # This searches the movie first to get the ID, then grabs the cast
        h = {"Authorization": f"Bearer {STARK_TOKEN}"}
        search = requests.get(f"https://api.themoviedb.org/3/search/movie?query={movie_name}", headers=h).json()
        if search['results']:
            m_id = search['results'][0]['id']
            credits = requests.get(f"https://api.themoviedb.org/3/movie/{m_id}/credits", headers=h).json()
            cast = [member['name'] for member in credits['cast'][:5]]
            self.speak(f"The lead actors are {', '.join(cast)}.")
            self.signals.log_signal.emit(f"🎬 CAST: {', '.join(cast)}")

    def initiate_watch_protocol(self, item, mtype):
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"; webbrowser.open(url)

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={cmd}")

    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/all/day")

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setFixedWidth(260); self.sidebar.setStyleSheet("background: black; border-right: 2px solid red;")
        side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        self.console = QTextEdit(); self.console.setStyleSheet("background: black; color: #00ff00;"); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content); self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search movies or actors..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid == self.task_counter: 
            card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

    def start_thread(self, url): self.task_counter += 1; self.signals.clear_signal.emit(); threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:25]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, item.get('media_type', 'movie'), t_id); time.sleep(0.05)
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        try:
            p_path = item.get('poster_path') or item.get('profile_path') # Added profile_path for actors!
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{p_path}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, mtype, tid)
        except: pass

    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(170, 320); self.setStyleSheet("border: 1px solid red; color: white;")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = item.get('title') or item.get('name'); layout.addWidget(QLabel(t[:15]))
        btn = QPushButton("WATCH"); btn.clicked.connect(lambda: app.initiate_watch_protocol(item, mtype)); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
