import sys, os, requests, threading, time, json, webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QScrollArea, 
                             QLabel, QGridLayout, QFrame, QRadioButton, QTextEdit, 
                             QSystemTrayIcon, QMenu, QAction, QStyle, QActionGroup)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QIcon

# --- STARK PROTOCOL: THE BRAIN V11.0 ---
class SignalHandler(QObject):
    item_signal = pyqtSignal(dict, QPixmap, int, str, int)
    log_signal = pyqtSignal(str); clear_signal = pyqtSignal()

STARK_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlYjhlNjk5OGE0MGVhYmY0YmZjODg0NGI1YWJmNjM0OCIsIm5iZiI6MTc3MDk1NDE2NC40MjQsInN1YiI6IjY5OGU5ZGI0MTYxYmU0NzBjODJmMzBhYSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.7vRC52l-A-wHieUWk65LelT8dLFYMD70kxas_p5qWu4"
JASON_FILE = "status_cache.json"
LOGO_PATH = "logo.png"

STYLESHEET = """
QMainWindow { background-color: #1a0033; }
QFrame#Sidebar { background-color: #0f001a; border-right: 2px solid #ff0000; }
QLabel { color: #ff0000; font-family: 'Segoe UI'; font-weight: bold; }
QScrollArea { background-color: #1a0033; border: none; }
QWidget#Gallery { background-color: #2e004b; padding-right: 10px; }
QFrame#MovieCard { background-color: #1a0000; border-radius: 10px; border: 2px solid #ff0000; padding: 5px; margin: 2px; }
QLineEdit { background-color: #111; border: 1px solid #ff0000; border-radius: 5px; color: white; padding: 12px; }
QPushButton { background-color: #111; color: #ff3333; border: 1px solid #aa0000; border-radius: 8px; padding: 8px; font-weight: bold; }
QPushButton:hover { border: 1px solid #00ff00; color: #00ff00; }
QPushButton#WatchBtn { background-color: #006600; color: #00ff00; border: 1px solid #00ff00; outline: none; }
QTextEdit#Console { background-color: #000; color: #00ff00; border: 1px solid #ff0000; font-family: 'Consolas'; font-size: 11px; }
* { outline: none; }
"""

class MoviePlusPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stark Cinema - The Brain V11.0")
        self.resize(1500, 920); self.setStyleSheet(STYLESHEET)
        
        # --- THE ARSENAL (18 SOURCES) ---
        self.current_source = "Alpha"
        self.sources = {
            "Alpha": "vidsrc.me", "Bravo": "vidsrc.to", "Gamma": "vidsrc.cc",
            "Delta": "embed.su", "Epsilon": "vidsrc.xyz", "Zeta": "vidsrc.pro",
            "Eta": "vidsrc.icu", "Theta": "autoembed.to", "Iota": "vidlink.pro",
            "Kappa": "2embed.cc", "Lambda": "vidsrc.in", "Mu": "superembed.me",
            "Nu": "movieapi.club", "Xi": "db-gdrive", "Omicron": "vidsrcme.ru",
            "Pi": "vidplay.online", "Rho": "moviesapi.club", "Sigma": "vidsrc.net"
        }
        
        self.shown_ids = set(); self.task_counter = 0; self.current_mode = "movie"
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.signals = SignalHandler()
        self.signals.item_signal.connect(self.add_item_to_ui)
        self.signals.log_signal.connect(lambda m: self.console.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}"))
        self.signals.clear_signal.connect(self.clear_gallery)
        
        self.setup_tray(); self.init_ui()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.tray_menu = QMenu()
        self.arsenal_menu = self.tray_menu.addMenu("📁 SOURCE ARSENAL")
        self.source_group = QActionGroup(self)
        for s_name in self.sources.keys():
            act = QAction(f"Source {s_name}", self, checkable=True)
            if s_name == self.current_source: act.setChecked(True)
            act.triggered.connect(lambda ch, name=s_name: self.set_source(name))
            self.arsenal_menu.addAction(act); self.source_group.addAction(act)
        self.tray_menu.addAction("👁️ SHOW GALLERY").triggered.connect(self.show_normal)
        self.tray_menu.addAction("❌ EXIT").triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(self.tray_menu); self.tray_icon.activated.connect(self.on_tray_activated); self.tray_icon.show()

    def set_source(self, name):
        self.current_source = name
        self.signals.log_signal.emit(f"🧠 Intelligence Update: Switched to {name}")
        if hasattr(self, 'current_mid') and self.current_mid: 
            self.launch_movie(self.current_mid, self.current_mtype)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: self.show_normal()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central); layout = QHBoxLayout(central); layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(260); side_layout = QVBoxLayout(self.sidebar)
        if os.path.exists(LOGO_PATH):
            self.logo = QLabel(); self.logo.setPixmap(QPixmap(LOGO_PATH).scaled(220, 120, Qt.KeepAspectRatio)); side_layout.addWidget(self.logo, alignment=Qt.AlignCenter)
        btn_trend = QPushButton("🔥 TRENDING"); btn_trend.clicked.connect(self.run_trending); side_layout.addWidget(btn_trend)
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True); self.console.setFixedHeight(150); side_layout.addStretch(); side_layout.addWidget(self.console); layout.addWidget(self.sidebar)
        content = QWidget(); c_layout = QVBoxLayout(content); self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Search Intelligence..."); self.search_bar.returnPressed.connect(self.run_search); c_layout.addWidget(self.search_bar)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.container = QWidget(); self.container.setObjectName("Gallery"); self.grid = QGridLayout(self.container); self.grid.setSpacing(8); self.scroll.setWidget(self.container); c_layout.addWidget(self.scroll); layout.addWidget(content); self.run_trending()

    def launch_movie(self, mid, mtype):
        self.current_mid = mid; self.current_mtype = mtype
        urls = {
            "Alpha": f"https://vidsrc.me/embed/{mtype}?tmdb={mid}",
            "Bravo": f"https://vidsrc.to/embed/{mtype}/{mid}",
            "Gamma": f"https://vidsrc.cc/v2/embed/{mtype}/{mid}",
            "Delta": f"https://embed.su/embed/{mtype}/{mid}",
            "Epsilon": f"https://vidsrc.xyz/embed/{mtype}/{mid}",
            "Zeta": f"https://vidsrc.pro/embed/{mtype}/{mid}",
            "Eta": f"https://vidsrc.icu/embed/{mtype}/{mid}",
            "Theta": f"https://autoembed.to/{mtype}/tmdb/{mid}",
            "Iota": f"https://vidlink.pro/embed/{mtype}/{mid}",
            "Kappa": f"https://www.2embed.cc/embed/{mid}",
            "Lambda": f"https://vidsrc.in/embed/{mtype}/{mid}",
            "Mu": f"https://superembed.me/{mtype}/{mid}",
            "Nu": f"https://movieapi.club/{mtype}/{mid}",
            "Xi": f"https://databasegdriveplayer.co/player.php?type={mtype}&tmdb={mid}",
            "Omicron": f"https://vidsrcme.ru/embed/{mtype}?tmdb={mid}",
            "Pi": f"https://vidplay.online/embed/{mtype}/{mid}",
            "Rho": f"https://moviesapi.club/{mtype}/{mid}",
            "Sigma": f"https://vidsrc.net/embed/{mtype}/{mid}"
        }
        self.signals.log_signal.emit(f"🎬 Intelligence: Launching via {self.current_source}...")
        webbrowser.open(urls.get(self.current_source, urls["Alpha"]))

    def show_normal(self): self.show(); self.raise_(); self.activateWindow()
    def clear_gallery(self): 
        self.shown_ids.clear()
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w: w.deleteLater()

    def start_thread(self, url):
        self.task_counter += 1; self.signals.clear_signal.emit()
        threading.Thread(target=self.fetch_worker, args=(url, self.task_counter), daemon=True).start()

    def fetch_worker(self, url, t_id):
        try:
            h = {"Authorization": f"Bearer {STARK_TOKEN}"}
            count = 1; page = 1
            while count <= 60 and page <= 10:
                p_url = f"{url}{'&' if '?' in url else '?'}page={page}"
                res = requests.get(p_url, headers=h).json().get('results', [])
                for item in res:
                    if t_id != self.task_counter: return
                    if str(item['id']) in self.shown_ids: continue
                    self.shown_ids.add(str(item['id']))
                    self.executor.submit(self.img_worker, item, count, self.current_mode, t_id)
                    count += 1
                    time.sleep(0.25) # Conveyor Belt Protocol
                page += 1
        except: pass

    def img_worker(self, item, rank, mtype, tid):
        if tid != self.task_counter: return
        try:
            url = f"https://image.tmdb.org/t/p/w300{item['poster_path']}"
            data = requests.get(url, timeout=5).content; pix = QPixmap(); pix.loadFromData(data)
            self.signals.item_signal.emit(item, pix.scaled(155, 230, Qt.KeepAspectRatio, Qt.SmoothTransformation), rank, mtype, tid)
        except: pass

    def add_item_to_ui(self, item, pix, rank, mtype, tid):
        if tid != self.task_counter: return
        f = QFrame(); f.setObjectName("MovieCard"); l = QVBoxLayout(f)
        p = QLabel(); p.setPixmap(pix); l.addWidget(p, alignment=Qt.AlignCenter)
        title = (item.get('title') or item.get('name'))[:20]
        l.addWidget(QLabel(title), alignment=Qt.AlignCenter)
        b = QPushButton("WATCH"); b.setObjectName("WatchBtn")
        b.clicked.connect(lambda: self.launch_movie(item['id'], mtype))
        l.addWidget(b); self.grid.addWidget(f, (rank-1)//5, (rank-1)%5, alignment=Qt.AlignCenter)

    def run_trending(self): self.start_thread(f"https://api.themoviedb.org/3/trending/{self.current_mode}/week")
    def run_search(self):
        q = self.search_bar.text().strip()
        if q: self.start_thread(f"https://api.themoviedb.org/3/search/multi?query={q}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = MoviePlusPro(); win.show(); sys.exit(app.exec_())
