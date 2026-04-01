import sys
import webbrowser
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QAlignmentFlag
from PyQt5.QtGui import QFont

class StarkCinema(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STARK CINEMA - ENGINE TEST")
        self.setGeometry(100, 100, 800, 600)
        self.initUI()

    def initUI(self):
        # Main Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Title Label
        self.title = QLabel("STARK CINEMA DASHBOARD")
        self.title.setFont(QFont('Arial', 24))
        self.title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title)

        # The "Test Fire" Button
        self.btn = QPushButton("TEST STREAM: CLICK TO PLAY")
        self.btn.setMinimumHeight(100)
        self.btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn.clicked.connect(self.play_test_movie)
        self.layout.addWidget(self.btn)

    def play_test_movie(self):
        # This uses your default browser (Chrome) to play the movie
        # I'm using a generic test ID here
        url = "https://vidsrc.to/embed/movie/tt0111161" 
        print(f"Ignition! Opening: {url}")
        webbrowser.open(url)

if __name__ == "__main__":
    # This is the "Ignition Switch" we talked about
    app = QApplication(sys.argv)
    
    # Check if the engine is actually firing
    print("--- STARK CINEMA ENGINE STARTING ---")
    
    window = StarkCinema()
    window.show()
    
    print("--- WINDOW SHOULD BE VISIBLE NOW ---")
    sys.exit(app.exec_())
