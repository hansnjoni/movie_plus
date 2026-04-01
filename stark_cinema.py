import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
SETTINGS_FILE = "settings.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #050000; }
QFrame#Sidebar { background-color: #0a0000; border-right: 2px solid #ff0000; }
QRadioButton { color: #ff0000; font-weight: bold; font-size: 14px; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 8px; border: 2px solid #aa0000; background: #000; }
QRadioButton::indicator:checked { background-color: #00ff00; border: 2px solid #ffffff; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QScrollArea { background-color: #050000; border: none; }
QWidget#Gallery { background-color: #050000; } 

/* RECALIBRATED BRIGHTER CARDS */
QFrame#MovieCard { 
    background-color: #3a0000; 
    border-radius: 10px; 
    border: 2px solid #ff0000; 
    padding: 8px;
    margin: 2px;
}

QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #006600; color: #00ff00; border: 1px solid #00ff00; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
"""

def get_jason():
    if os.path.exists(JASON_FILE):
        try:
            with open(JASON_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_to_jason(m_id, status):
    mem = get_jason()
    mem[str(m_id)] = {"status": status, "last_checked": str(datetime.now().date())}
    with open(JASON_FILE, 'w') as f: json.dump(mem, f)

class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.task_counter = 0; self.current_mode = "movie"
        self.settings = json.load(open(SETTINGS_FILE)) if os.path.exists(SETTINGS_FILE) else {"token": STARK_TOKEN}
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{time.strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        self.executor = ThreadPoolExecutor(max_workers=25); self.shown_ids = set(); self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Stark Cinema - Perfect 5 Build"); self.resize(1400, 950); self.setStyleSheet(STYLESHEET)
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central)
        
        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260); side_layout = QVBoxLayout(self.sidebar)
        if os.path.exists(LOGO_PATH):
            self.logo = QLabel(); self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
            side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending); side_layout.addWidget(btn_trend)
        rc = QWidget(); rl = QHBoxLayout(rc)
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True); self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV"); self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        rl.addWidget(self.m_radio); rl.addWidget(self.t_radio); side_layout.addWidget(rc)

        side_layout.addWidget(QLabel("\n   GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i: self.run_genre(idx)); side_layout.addWidget(b)
        side_layout.addStretch(); self.console = QTextEdit(); self.console.setReadOnly(True); self.console.setFixedHeight(120); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        
        # Content
        content = QWidget(); c_layout = QVBoxLayout(content)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search..."); self.search_bar.returnPressed.connect(self.run_search); c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.container = QWidget(); self.container.setObjectName("Gallery")
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(15) # Space between movies
        self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content); self.run_trending()

    def set_mode(self, m): self.current_mode = m; self.run_trending()
    def clear_gallery(self): 
        self.shown_ids.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_genre(self, g_id): self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")
    def run_search(self):
        q = self.search_bar.text().strip()
        if q: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}; mem = get_jason(); count = 1; page = 1; is_search = "search" in url
            while count <= 60 and page <= 35:
                conn = "&" if "?" in url else "?"
                p_url = f"{url}{conn}page={page}"
                res = requests.get(p_url, headers=h).json(); raw = res.get('results', [])
                if not raw: break
                for item in raw:
                    if t_id != self.task_counter: return
                    mid = str(item['id'])
                    if mid in self.shown_ids or (not is_search and 16 in item.get('genre_ids', [])): continue
                    mtype = item.get('media_type', self.current_mode)
                    if self.recon_jump(mid, mtype, mem):
                        self.shown_ids.add(mid); self.executor.submit(self.img_worker, item, count, mtype, t_id); count += 1
                        if count > 60: break
                page += 1
        except: pass

    def recon_jump(self, mid, mtype, mem):
        if mid in mem and mem[mid]['status'] == "Available": return True
        sources = [f"https://vidsrc.me/embed/{mtype}?tmdb={mid}", f"https://vidsrc.to/embed/{mtype}/{mid}"]
        for s in sources:
            try:
                if requests.head(s, timeout=0.8).status_code == 200:
                    save_to_jason(mid, "Available"); return True
            except: continue
        return False

    def img_worker(self, item, rank, mtype, tid):
        if tid != self.task_counter: return
        try:
            url = f"https://image.tmdb.org/t/p/w300{item['poster_path']}"
            data = requests.get(url).content; pix = QPixmap(); pix.loadFromData(data)
            # SHRINKING SCALE TO 180 TO FIT ALL 5
            self.signals.item_signal.emit(item, pix.scaled(180, 270, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, mtype, tid)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        title = (item.get('title') or item.get('name'))[:20]
        t_lbl = QLabel(title); t_lbl.setStyleSheet("color:white; font-size:10px;"); l.addWidget(t_lbl, alignment=Qt.AlignCenter)
        b = QPushButton("WATCH"); b.setObjectName("WatchBtn")
        b.clicked.connect(lambda: webbrowser.open(f"https://vidsrc.me/embed/{mtype}?tmdb={item['id']}"))
        l.addWidget(b); self.grid.addWidget(f, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = MoviePlusPro(); win.show(); sys.exit(app.exec_())
