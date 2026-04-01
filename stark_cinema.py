import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

# --- PROTOCOL: SIGNAL HANDLER ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

# --- MASTER SPECS ---
STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #1a0033; }
QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }

/* PURPLE BACKGROUND - TIGHTENED PADDING */
QScrollArea { background-color: #1a0033; border: none; }
QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }

/* STARK RED MOVIE CARDS - SLIMMED FOR 5-COLUMN FIT */
QFrame#MovieCard { 
    background-color: #1a0000; 
    border-radius: 10px; 
    border: 2px solid #ff0000; 
    padding: 5px; 
    margin: 2px; 
}

/* UI ELEMENTS */
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #006600; color: #00ff00; border: 1px solid #00ff00; outline: none; }

QRadioButton { color: #ff0000; font-weight: bold; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }

* { outline: none; }
"""

def get_jason():
    if os.path.exists(JASON_FILE):
        try:
            with open(JASON_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_to_jason(m_id, status):
    mem = get_jason()
    mem[str(m_id)] = {"status": status, "last_checked": str(datetime.now().date())}
    with open(JASON_FILE, 'w', encoding='utf-8') as f: json.dump(mem, f)

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - Master V8.5 Verified")
        self.resize(1500, 920); self.setStyleSheet(STYLESHEET)
        
        self.settings = {"token": STARK_TOKEN, "timeout": 1.2}
        self.current_mid = None; self.current_mtype = None; self.current_source = "Alpha"
        self.shown_ids = set(); self.task_counter = 0; self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{time.strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.setup_tray()
        self.init_ui()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.tray_menu = QMenu()
        self.switch_action = QAction("⚡ SWITCH SOURCE", self)
        self.switch_action.triggered.connect(self.toggle_source_from_tray)
        self.tray_menu.addAction(self.switch_action)
        self.tray_menu.addAction("👁️ SHOW GALLERY").triggered.connect(self.show_normal)
        self.tray_menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: 
            self.show_normal()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260)
        side_layout = QVBoxLayout(self.sidebar)
        
        if os.path.exists(LOGO_PATH):
            self.logo = QLabel(); self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio))
            side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending)
        side_layout.addWidget(btn_trend)
        
        rc = QWidget(); rl = QHBoxLayout(rc)
        self.m_radio = QRadioButton("Movies"); self.m_radio.setChecked(True)
        self.m_radio.clicked.connect(lambda: self.set_mode("movie"))
        self.t_radio = QRadioButton("TV"); self.t_radio.clicked.connect(lambda: self.set_mode("tv"))
        rl.addWidget(self.m_radio); rl.addWidget(self.t_radio); side_layout.addWidget(rc)

        side_layout.addWidget(QLabel("\n   GENRES"))
        for n, i in [("ACTION", 28), ("COMEDY", 35), ("HORROR", 27), ("CRIME", 80), ("TRUE CRIME", "80,99")]:
            b = QPushButton(n); b.clicked.connect(lambda ch, idx=i: self.run_genre(idx))
            side_layout.addWidget(b)
        
        side_layout.addStretch()
        self.console = QTextEdit(); self.console.setObjectName("Console")
        self.console.setReadOnly(True); self.console.setFixedHeight(120)
        side_layout.addWidget(self.console)
        layout.addWidget(self.sidebar)
        
        content = QWidget(); c_layout = QVBoxLayout(content); c_layout.setContentsMargins(10, 10, 10, 10)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search...")
        self.search_bar.returnPressed.connect(self.run_search)
        c_layout.addWidget(self.search_bar)
        
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.container = QWidget(); self.container.setObjectName("Gallery")
        self.grid = QGridLayout(self.container); self.grid.setSpacing(8)
        self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll)
        layout.addWidget(content); self.run_trending()

    def show_normal(self): 
        self.show(); self.raise_(); self.activateWindow()

    def set_mode(self, m): 
        self.current_mode = m; self.run_trending()

    def clear_gallery(self): 
        self.shown_ids.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def run_trending(self): 
        self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")

    def run_genre(self, g_id): 
        self.start_thread(f"https://api.themoviedb.org/3/discover/{self.current_mode}?with_genres={g_id}&sort_by=popularity.desc")

    def run_search(self):
        q = self.search_bar.text().strip()
        if q: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}")

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            mem = get_jason(); count = 1; page = 1; is_search = "search" in url
            while count <= 60 and page <= 40:
                conn = "&" if "?" in url else "?"
                p_url = f"{url}{conn}page={page}"
                res = requests.get(p_url, headers=h).json(); raw = res.get('results', [])
                if not raw: break
                for item in raw:
                    if t_id != self.task_counter: return
                    mid = str(item['id'])
                    if mid in self.shown_ids or (not is_search and 16 in item.get('genre_ids', [])): continue
                    mtype = item.get('media_type', self.current_mode)
                    if self.recon_verify(mid, mtype, mem):
                        self.shown_ids.add(mid)
                        self.executor.submit(self.img_worker, item, count, mtype, t_id)
                        count += 1
                        time.sleep(0.25) # CONVEYOR BELT DELAY
                        if count > 60: break
                page += 1
        except: pass

    def recon_verify(self, mid, mtype, mem):
        if mid in mem and mem[mid]['status'] == "Available": return True
        for s in [f"https://vidsrc.me/embed/{mtype}?tmdb={mid}", f"https://vidsrc.to/embed/{mtype}/{mid}"]:
            try:
                if requests.head(s, timeout=1.2).status_code == 200:
                    save_to_jason(mid, "Available"); return True
            except: continue
        return False

    def img_worker(self, item, rank, mtype, tid):
        if tid != self.task_counter: return
        try:
            url = f"https://image.tmdb.org/t/p/w300{item['poster_path']}"
            data = requests.get(url, timeout=5).content; pix = QPixmap()
            pix.loadFromData(data)
            # PRECISION FIT: 155px width
            self.signals.item_signal.emit(item, pix.scaled(155, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, mtype, tid)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        title = (item.get('title') or item.get('name'))[:20]
        t_lbl = QLabel(title); t_lbl.setStyleSheet("color:white; font-size:9px;")
        l.addWidget(t_lbl, alignment=Qt.AlignCenter)
        b = QPushButton("WATCH"); b.setObjectName("WatchBtn")
        b.clicked.connect(lambda: self.launch_movie(item['id'], mtype))
        l.addWidget(b); self.grid.addWidget(f, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)

    def launch_movie(self, mid, mtype):
        self.current_mid = mid; self.current_mtype = mtype
        url = f"https://vidsrc.me/embed/{mtype}?tmdb={mid}" if self.current_source == "Alpha" else f"https://vidsrc.to/embed/{mtype}/{mid}"
        webbrowser.open(url)

    def toggle_source_from_tray(self):
        if not self.current_mid: return
        self.current_source = "Bravo" if self.current_source == "Alpha" else "Alpha"
        self.switch_action.setText(f"⚡ SWITCH SOURCE ({self.current_source})")
        self.launch_movie(self.current_mid, self.current_mtype)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = MoviePlusPro()
    win.show()
    sys.exit(app.exec_())
