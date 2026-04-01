import sys
import os
import requests
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# --- IGNITION SETTINGS ---
# Paste the RAW GitHub link to your stark_cinema.py file here:
GITHUB_RAW_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/stark_cinema.py"

# The name of your main app file on your computer
MAIN_APP_NAME = "stark_cinema.py"

class UpdateThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        try:
            self.log_signal.emit("📡 ESTABLISHING UPLINK TO GITHUB...")
            
            # 1. Fetch the latest code from GitHub
            response = requests.get(GITHUB_RAW_URL, timeout=10)
            
            if response.status_code == 200:
                self.log_signal.emit("✅ UPLINK SECURED. REFLASHING ENGINE CYLINDERS...")
                
                # 2. Overwrite the local file with the fresh code
                with open(MAIN_APP_NAME, 'wb') as f:
                    f.write(response.content)
                    
                self.log_signal.emit("🚀 UPDATE COMPLETE. IGNITING MAIN ENGINE...")
            else:
                self.log_signal.emit(f"⚠️ GITHUB REJECTED CONNECTION ({response.status_code}). BOOTING FROM LOCAL CACHE...")
                
        except Exception as e:
            self.log_signal.emit("⚠️ NO INTERNET CONNECTION. BOOTING FROM LOCAL CACHE...")
        
        # Tell the UI we are done and ready to launch
        self.finished_signal.emit()

class StarkLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STARK IGNITION")
        self.setFixedSize(400, 250)
        self.setStyleSheet("background-color: #050505;")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # The Status Screen
        self.status_label = QLabel("SYSTEM STANDBY. READY FOR UPLINK.")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #00ffff; font-family: 'Consolas'; font-size: 12px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.status_label)
        
        # The Massive Ignition Button
        self.start_btn = QPushButton("START ENGINE")
        self.start_btn.setMinimumHeight(100)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #aa0000;
                color: white;
                font-family: 'Segoe UI';
                font-size: 28px;
                font-weight: bold;
                border: 3px solid #ff3333;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ff0000;
                border: 3px solid #ffffff;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #888888;
                border: 3px solid #555555;
            }
        """)
        self.start_btn.clicked.connect(self.trigger_ignition)
        layout.addWidget(self.start_btn)

    def trigger_ignition(self):
        # Lock the button so you can't double-click it
        self.start_btn.setEnabled(False)
        self.start_btn.setText("SYNCING...")
        self.start_btn.setStyleSheet("background-color: #b8860b; color: black; font-size: 24px; font-weight: bold; border-radius: 15px;")
        
        # Spin up the background thread so the UI doesn't freeze
        self.updater = UpdateThread()
        self.updater.log_signal.connect(self.update_status)
        self.updater.finished_signal.connect(self.launch_main_app)
        self.updater.start()

    def update_status(self, msg):
        self.status_label.setText(msg)

    def launch_main_app(self):
        # Check if the main app actually exists in the folder
        if os.path.exists(MAIN_APP_NAME):
            self.status_label.setText("FIRING...")
            
            # Open the main app using the exact same Python system running the launcher
            subprocess.Popen([sys.executable, MAIN_APP_NAME])
            
            # Kill the launcher instantly so only the main app remains on screen
            sys.exit()
        else:
            self.status_label.setText("💥 CRITICAL ERROR: MAIN APP FILE NOT FOUND!")
            self.status_label.setStyleSheet("color: #ff0000; font-family: 'Consolas'; font-size: 12px; font-weight: bold;")
            self.start_btn.setText("SYSTEM FAILURE")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StarkLauncher()
    win.show()
    sys.exit(app.exec_())
