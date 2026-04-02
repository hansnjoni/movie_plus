import sys, os, requests, threading, time, json, webbrowser, subprocess, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- THE CEREBRAL VAULT ---
MEMORY_DIR = "jarvis_memory"
if not os.path.exists(MEMORY_DIR): os.makedirs(MEMORY_DIR)

def save_vault(filename, data):
    with open(os.path.join(MEMORY_DIR, filename), 'w') as f:
        json.dump(data, f, indent=4)

def load_vault(filename, default):
    path = os.path.join(MEMORY_DIR, filename)
    if not os.path.exists(path): save_vault(filename, default); return default
    with open(path, 'r') as f: return json.load(f)

# Load Intelligence Layers
USER = load_vault("user_profile.json", {"name": "Hans", "interests": {}, "birthday": "04-02"})
INTEL = load_vault("intelligence_vault.json", {"actors": [], "facts": [], "sessions": []})

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                             QFrame, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Proactive Assistant V70.0")
        self.resize(1500, 950); self.is_live_mode = False; self.speak_lock = threading.Lock()
        self.task_counter = 0; self.executor = ThreadPoolExecutor(max_workers=10); self.signals = SignalHandler()
        
        self.signals.item_signal.connect(self.add_item_to_ui); self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery); self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        
        # --- BIRTHDAY & STARTUP LOGIC ---
        today = datetime.now().strftime("%m-%d")
        if today == USER.get('birthday'):
            self.speak(f"Happy Birthday, {USER['name']}. I've prepared the theater for your special day.")
        else:
            self.speak(f"Assistant online. Analyzing your world, {USER['name']}.")

    def speak(self, text):
        def run_speech():
            with self.speak_lock:
                cmd = f'PowerShell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text.replace("'", "")}\');"'
                subprocess.run(cmd, shell=True)
        threading.Thread(target=run_speech, daemon=True).start()

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 4200
        while self.is_live_mode:
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=1.0)
                    audio = r.listen(src, timeout=None, phrase_time_limit=12)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"YOU: {q}")
                    
                    # --- PASSIVE LEARNING ENGINE ---
                    if any(x in q for x in ["passed away", "died", "born", "starred", "loved", "liked"]):
                        INTEL['facts'].append({"text": q, "time": str(datetime.now())})
                        save_vault("intelligence_vault.json", INTEL)
                        self.signals.log_signal.emit("🧠 [SYSTEM]: Passive Intelligence Gathered.")

                    # --- PROACTIVE RECALL ---
                    if "what do you know" in q:
                        if INTEL['facts']:
                            recent = INTEL['facts'][-1]['text']
                            self.speak(f"I've recorded that {recent}. I'm learning more every day.")
                        else:
                            self.speak("I'm still observing. Tell me more about your interests.")
                        continue

                    # --- COMMANDS ---
                    if any(x in q for x in ["play", "find", "search"]):
                        target = q.replace("play", "").replace("find", "").replace("search", "").strip()
                        self.signals.search_trigger.emit(target); break
            except: continue

    def initiate_watch_protocol(self, item, mtype):
        # LOGGING INTEREST AUTOMATICALLY
        genre = item.get('genre_ids', [0])[0]
        USER['interests'][str(genre)] = USER['interests'].get(str(genre), 0) + 1
        save_vault("user_profile.json", USER)
        
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"
        webbrowser.open(url)
        self.speak(f"Launching {item.get('title') or item.get('name')}. I'll remember you liked this.")

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #050505; }
            QFrame#Sidebar { background-color: #000000; border-right: 2px solid #ff0000; }
            QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #111; color: #ff0000; border: 1px solid #ff0000; padding: 12px; font-weight: bold; }
            QPushButton:hover { border: 2px solid #00ff00; color: #00ff00; }
            QLineEdit { background-color: #000; border: 2px solid #ff0000; color: #00ff00; padding: 12px; }
            QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #333; font-family: 'Consolas'; }
        """)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        side_layout.addWidget(QLabel("\n INTELLIGENCE DATA "))
        self.stat_lbl = QLabel(f"Profiles: {len(INTEL['facts'])} Items"); side_layout.addWidget(self.stat_lbl)
        side_layout.addStretch(); self.console = QTextEdit(); self.console.setFixedHeight(250); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("The assistant is listening..."); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); c_layout.addWidget(self.scroll); layout.addWidget(content)

    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

    def trigger_search(self, query): self.search_bar.setText(query); self.process_command()

    def process_command(self):
        cmd = self.search_bar.text().strip()
        if cmd: self.start_thread(f"https://api.themoviedb.org/3/search/movie?query={cmd}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:25]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, "movie", t_id); time.sleep(0.05)
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
        btn = QPushButton("WATCH"); btn.clicked.connect(lambda: app.initiate_watch_protocol(item, mtype)); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
