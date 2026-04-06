import sys, os, requests, threading, time, json, subprocess, re, webbrowser
from concurrent.futures import ThreadPoolExecutor

# === 🛑 THE MASTER BREAKER ===
# Set to True only on the fast PC. 
JARVIS_POWER_ENABLED = False

# --- 🔌 THE SAFETY CIRCUIT (STRICT SYNTAX) ---
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLineEdit, QPushButton, QScrollArea, QLabel, QGridLayout, 
                                 QFrame, QTextEdit, QCheckBox, QComboBox, QStackedWidget)
    from PyQt5.QtCore import Qt, pyqtSignal, QObject, QUrl
    from PyQt5.QtGui import QPixmap, QColor
    from PyQt5.QtWebEngineWidgets import QWebEngineView 
    from youtubesearchpython import VideosSearch 
    
    if JARVIS_POWER_ENABLED:
        import google.generativeai as genai
except ImportError as e:
    print(f"❌ [CRITICAL]: {e}. Run: pip install PyQt5 PyQtWebEngine youtube-search-python requests")
    sys.exit()

# --- 🧠 THE OMNI-ACTION AI CONFIG ---
if JARVIS_POWER_ENABLED:
    genai.configure(api_key="YOUR_API_KEY_HERE")
    model = genai.GenerativeModel('gemini-1.5-flash')
    SYSTEM_PROMPT = "You are JARVIS. Brief answers. Use [CMD: MUSIC|MOVIE|TV|KARAOKE|CALL | Query]."

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int, int, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal(); search_trigger = pyqtSignal(str, int, int)

class StarkCinemaSingularity(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Media Center - Definitive V106.0")
        self.resize(1600, 950)
        
        # Memory Banks
        self.history_file = "stark_history.json"
        self.playlist_file = "stark_playlist.json"
        self.history = self.load_data(self.history_file)
        self.contacts = {"little woman": "555-0101", "landlord": "555-0103", "supply house": "555-0104"}

        self.task_counter = 0; self.is_live_mode = False; self.is_speaking = False
        self.search_mode = "movie" 
        
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(m))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.init_ui()
        self.set_movie_mode() 
        self.start_tmdb_thread("https://api.themoviedb.org/3/trending/movie/day", 1, 1)

    def load_data(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "r") as f: return json.load(f)
        return []

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #000; color: #00FF00; }
            QFrame#Sidebar { background-color: #050505; border-right: 2px solid #FF0000; }
            QPushButton { background-color: #1a0000; color: #FF0000; border: 1px solid #FF0000; padding: 10px; font-weight: bold; }
            QPushButton:hover { border: 1px solid #00FF00; color: #00FF00; }
            QLineEdit { background-color: #111; color: #00FF00; border: 1px solid #FF0000; padding: 8px; }
            QComboBox { background-color: #111; color: #FF0000; border: 1px solid #FF0000; }
        """)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0,0,0,0)
        
        # SIDEBAR
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(300); side_layout = QVBoxLayout(self.sidebar)
        self.live_btn = QPushButton("🎙️ ACTIVATE JARVIS")
        self.live_btn.setEnabled(JARVIS_POWER_ENABLED)
        side_layout.addWidget(self.live_btn)
        self.console = QTextEdit(); self.console.setReadOnly(True); side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)

        # MAIN CONTENT
        self.content_area = QWidget(); self.c_layout = QVBoxLayout(self.content_area)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search..."); self.search_bar.returnPressed.connect(lambda: self.route_search(self.search_bar.text(), 1, 1))
        self.c_layout.addWidget(self.search_bar)
        
        # MASTER SELECTOR
        self.master_switch = QFrame(); ms_layout = QHBoxLayout(self.master_switch)
        for name, mode in [("🎬 MOVIES", self.set_movie_mode), ("📺 TV", self.set_tv_mode), ("🎵 MUSIC", self.set_music_mode)]:
            btn = QPushButton(name); btn.clicked.connect(mode); ms_layout.addWidget(btn)
        self.c_layout.addWidget(self.master_switch)

        # SUB-PANELS
        self.control_stack = QStackedWidget()
        self.movie_panel = QFrame(); mp_layout = QHBoxLayout(self.movie_panel)
        self.movie_genres = QComboBox(); self.movie_genres.addItem("SELECT GENRE...")
        for g in ["Action", "Comedy", "Crime", "Horror", "Western"]: self.movie_genres.addItem(g)
        self.movie_genres.currentIndexChanged.connect(lambda: self.genre_search())
        mp_layout.addWidget(self.movie_genres); self.control_stack.addWidget(self.movie_panel)

        self.music_panel = QFrame(); mup_layout = QHBoxLayout(self.music_panel)
        self.karaoke_btn = QCheckBox("🎤 KARAOKE MODE")
        playlist_btn = QPushButton("⭐ LOAD PLAYLIST"); playlist_btn.clicked.connect(self.load_playlist)
        mup_layout.addWidget(self.karaoke_btn); mup_layout.addWidget(playlist_btn)
        self.control_stack.addWidget(self.music_panel)

        self.c_layout.addWidget(self.control_stack)

        self.browser = QWebEngineView(); self.browser.hide(); self.c_layout.addWidget(self.browser)
        self.back_btn = QPushButton("⬅️ BACK TO GALLERY"); self.back_btn.hide(); self.back_btn.clicked.connect(self.show_gallery); self.c_layout.addWidget(self.back_btn)
        self.scroll = QScrollArea(); self.container = QWidget(); self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container); self.scroll.setWidgetResizable(True); self.c_layout.addWidget(self.scroll)
        layout.addWidget(self.content_area)

    # --- 📡 LOGIC GATES ---
    def set_movie_mode(self): self.search_mode = "movie"; self.control_stack.setCurrentIndex(0)
    def set_tv_mode(self): self.search_mode = "tv"; self.control_stack.setCurrentIndex(0)
    def set_music_mode(self): self.search_mode = "music"; self.control_stack.setCurrentIndex(1)

    def route_search(self, query, s, e):
        self.signals.clear_signal.emit()
        if self.search_mode == "music":
            suffix = " karaoke instrumental" if self.karaoke_btn.isChecked() else " song"
            threading.Thread(target=self.youtube_worker, args=(query + suffix, self.task_counter), daemon=True).start()
        else:
            self.start_tmdb_thread(f"https://api.themoviedb.org/3/search/multi?query={query}", s, e)

    def youtube_worker(self, query, t_id):
        self.task_counter += 1
        try:
            results = VideosSearch(query, limit=15).result()['result']
            for i, vid in enumerate(results):
                item = {'id': vid['id'], 'title': vid['title']}
                self.executor.submit(self.img_worker, item, vid['thumbnails'][0]['url'], i+1, self.task_counter, 1, 1, 'music')
        except: pass

    def img_worker(self, item, url, rank, tid, s, e, mtype):
        try:
            pix = QPixmap(); pix.loadFromData(requests.get(url).content)
            self.signals.item_signal.emit(item, pix, rank, mtype, tid, s, e)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid, s, e):
        if tid == self.task_counter:
            card = MovieCard(item, pix, mtype, self)
            self.grid.addWidget(card, (rank-1)//4, (rank-1)%4)

    def genre_search(self):
        g = self.movie_genres.currentText()
        if g != "SELECT GENRE...":
            self.signals.clear_signal.emit()
            self.start_tmdb_thread(f"https://api.themoviedb.org/3/search/multi?query={g}", 1, 1)

    def load_playlist(self):
        self.signals.clear_signal.emit(); tracks = self.load_data(self.playlist_file)
        for i, t in enumerate(tracks):
            url = f"https://img.youtube.com/vi/{t['id']}/hqdefault.jpg"
            self.executor.submit(self.img_worker, t, url, i+1, self.task_counter, 1, 1, 'music')

    def clear_gallery(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def show_gallery(self): self.browser.hide(); self.back_btn.hide(); self.scroll.show(); self.browser.setUrl(QUrl("about:blank"))

    def start_tmdb_thread(self, url, s, e):
        self.task_counter += 1; threading.Thread(target=self.tmdb_worker, args=(url, self.task_counter, s, e), daemon=True).start()

    def tmdb_worker(self, url, t_id, s, e):
        h = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"}
        try:
            res = requests.get(url, headers=h).json().get('results', [])
            for i, itm in enumerate(res[:20]):
                p = f"https://image.tmdb.org/t/p/w300{itm.get('poster_path')}"
                self.executor.submit(self.img_worker, itm, p, i+1, t_id, s, e, itm.get('media_type', 'movie'))
        except: pass

class MovieCard(QFrame):
    def __init__(self, item, pix, mtype, app):
        super().__init__(); self.app = app; self.mtype = mtype; self.tid = item['id']; self.title = item.get('title') or item.get('name')
        self.setFixedSize(180, 380); self.setStyleSheet("border: 1px solid #FF0000;")
        l = QVBoxLayout(self); img = QLabel(); img.setPixmap(pix.scaled(150, 220)); l.addWidget(img)
        t = QLabel(self.title[:30]); t.setWordWrap(True); l.addWidget(t)
        if mtype == 'music':
            btn_s = QPushButton("⭐ SAVE"); btn_s.clicked.connect(self.save); l.addWidget(btn_s)
        btn_p = QPushButton("WATCH/PLAY"); btn_p.clicked.connect(self.play); l.addWidget(btn_p)
        btn_c = QPushButton("📺 CAST"); btn_c.clicked.connect(self.cast); l.addWidget(btn_c)

    def save(self):
        p = self.app.load_data(self.app.playlist_file)
        if not any(x['id'] == self.tid for x in p):
            p.append({'id': self.tid, 'title': self.title}); json.dump(p, open(self.app.playlist_file, "w"))

    def play(self):
        if self.mtype == 'music': u = f"https://www.youtube.com/embed/{self.tid}?autoplay=1"
        else: u = f"https://vidsrc.me/embed/movie?tmdb={self.tid}"
        self.app.scroll.hide(); self.app.browser.setUrl(QUrl(u)); self.app.browser.show(); self.app.back_btn.show()

    def cast(self):
        u = f"https://www.youtube.com/watch?v={self.tid}" if self.mtype == 'music' else f"https://vidsrc.me/embed/movie?tmdb={self.tid}"
        webbrowser.open(u)

if __name__ == "__main__":
    a = QApplication(sys.argv); w = StarkCinemaSingularity(); w.show(); sys.exit(a.exec_())
