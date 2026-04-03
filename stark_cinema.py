import sys, os, requests, threading, time, json, webbrowser, subprocess, re
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai

# --- 🧪 THE BRAIN & SCREEN IMPORTS ---
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                                 QFrame, QTextEdit)
    from PyQt5.QtCore import Qt, pyqtSignal, QObject, QUrl
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtWebEngineWidgets import QWebEngineView # The 'TV Screen' component
except ImportError:
    print("❌ [CRITICAL]: Missing PyQtWebEngine. Run: pip install PyQtWebEngine")
    input("Press Enter to close...")
    sys.exit()

# --- 🧠 THE LIVE BRAIN CONFIG ---
GEMINI_API_KEY = "AIzaSyDhKiyDBdicvNAdhQzET1b9W4vsotmfrAw" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = (
    "You are JARVIS. You are having a live conversation with Hans. "
    "Hans is an electrician, plumber, and rockhound. Today is April 2nd, his birthday. "
    "Keep responses conversational, witty, and concise. You remember everything we built."
)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int, int, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str, int, int)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Stark Cinema - Singularity V100.0")
        self.resize(1600, 950)
        
        self.task_counter = 0; self.is_live_mode = False; self.is_speaking = False
        self.chat_session = model.start_chat(history=[]) 
        self.executor = ThreadPoolExecutor(max_workers=20); self.signals = SignalHandler()
        
        # Wiring the logic gates
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.signals.search_trigger.connect(self.trigger_search)
        
        self.init_ui(); self.run_fresh_trending()
        self.signals.log_signal.emit("⚡ [SYSTEM READY]: Happy Birthday, Hans. Let's get to work.")

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #000; }
            QFrame#Sidebar { background-color: #050505; border-right: 2px solid #FF0000; }
            QLabel { color: #FF0000; font-family: 'Segoe UI'; font-weight: bold; }
            QPushButton { background-color: #1a0000; color: #FF0000; border: 1px solid #FF0000; padding: 12px; }
            QLineEdit { background-color: #111; color: #00FF00; border: 1px solid #FF0000; padding: 10px; }
            QTextEdit#Console { background-color: #000; color: #00FF00; font-family: 'Consolas'; font-size: 10px; }
        """)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        
        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(280); side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS"); self.live_btn.clicked.connect(self.toggle_live_mode); side_layout.addWidget(self.live_btn)
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        # Main View Area
        self.content_stack = QWidget(); self.c_layout = QVBoxLayout(self.content_stack)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Voice monitoring active..."); self.c_layout.addWidget(self.search_bar)
        
        # The Video Player (Hidden by default)
        self.browser = QWebEngineView(); self.browser.hide(); self.c_layout.addWidget(self.browser)
        self.back_btn = QPushButton("⬅️ BACK TO GALLERY"); self.back_btn.hide(); self.back_btn.clicked.connect(self.show_gallery); self.c_layout.addWidget(self.back_btn)

        # The Gallery Area
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container); self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True)
        self.c_layout.addWidget(self.scroll); layout.addWidget(self.content_stack)

    # --- 🎥 MOVIE LOGIC ---
    def play_movie(self, mtype, tid):
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={tid}"
        self.scroll.hide(); self.browser.setUrl(QUrl(url)); self.browser.show(); self.back_btn.show()

    def show_gallery(self):
        self.browser.hide(); self.back_btn.hide(); self.scroll.show(); self.browser.setUrl(QUrl("about:blank"))

    # --- 🧠 BRAIN LOGIC ---
    def get_ai_response(self, text):
        try:
            response = self.chat_session.send_message(f"{SYSTEM_PROMPT}\n\nHans: {text}")
            return response.text
        except: return "Connection lost, Hans."

    def speak(self, text):
        self.signals.log_signal.emit(f"JARVIS: {text}")
        def run_speech():
            self.is_speaking = True
            clean_text = text.replace("'", "").replace('"', "")
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", 
                          f"$s = New-Object -ComObject SAPI.SpVoice; $s.Priority = 2; $s.Speak('{clean_text}')"])
            self.is_speaking = False
        threading.Thread(target=run_speech, daemon=True).start()

    def live_voice_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer(); r.energy_threshold = 3500; r.phrase_threshold = 0.4
        while self.is_live_mode:
            if self.is_speaking: time.sleep(0.1); continue
            try:
                with sr.Microphone() as src:
                    audio = r.listen(src, timeout=None, phrase_time_limit=10)
                    q = r.recognize_google(audio).lower()
                    self.signals.log_signal.emit(f"HANS: {q}")
                    
                    if any(x in q for x in ["play", "watch", "find", "search"]):
                        target = re.sub(r'play|watch|find|search|season \d+|episode \d+', '', q).strip()
                        self.signals.search_trigger.emit(target, 1, 1)
                        self.speak(f"Scanning for {target}.")
                    else:
                        answer = self.get_ai_response(q)
                        self.speak(answer)
            except: continue

    # --- 🎞️ DATA SCRAPING ---
    def trigger_search(self, q, s, e): self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}", s, e)
    def start_thread(self, url, s, e):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter, s, e), daemon=True).start()
    def fetch_worker(self, url, t_id, s, e):
        try:
            h = {"Authorization": f"Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"}
            res = requests.get(url, headers=h).json().get('results', [])
            for i, item in enumerate(res[:20]):
                if t_id == self.task_counter: self.executor.submit(self.img_worker, item, i+1, t_id, s, e, item.get('media_type', 'movie'))
        except: pass
    def img_worker(self, item, rank, tid, s, e, mtype):
        try:
            raw = requests.get(f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}").content
            pix = QPixmap(); pix.loadFromData(raw)
            self.signals.item_signal.emit(item, pix.scaled(150, 225), rank, mtype, tid, s, e)
        except: pass
    def add_item_to_ui(self, item, pix, rank, mtype, tid, s, e):
        if tid == self.task_counter: card = MovieCard(item, pix, mtype, self); self.grid.addWidget(card, (rank-1)//5, (rank-1)%5)
    def clear_gallery(self):
        while self.grid.count():
            child = self.grid.takeAt(0);
            if child.widget(): child.widget().deleteLater()
    def run_fresh_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/all/day", 1, 1)
    def toggle_live_mode(self):
        self.is_live_mode = not self.is_live_mode
        if self.is_live_mode: threading.Thread(target=self.live_voice_loop, daemon=True).start()

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.setFixedSize(175, 330); self.app = app
        self.setStyleSheet("QFrame { border: 1px solid #FF0000; background-color: #000; }")
        layout = QVBoxLayout(self); lbl = QLabel(); lbl.setPixmap(pix); layout.addWidget(lbl)
        t = (item.get('name') or item.get('title'))[:15]; layout.addWidget(QLabel(t))
        btn = QPushButton("WATCH"); btn.clicked.connect(lambda: self.app.play_movie(mtype, item['id'])); layout.addWidget(btn)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StarkCinemaSingularity(); win.show(); sys.exit(app.exec_())
