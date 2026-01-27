import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PySide6.QtCore import Qt
import pyttsx3
import requests

API_URL = "http://localhost:8001"

class StudentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.token = None
        self.tts_engine = pyttsx3.init()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Audio Learning System - Student App")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Title
        self.title = QLabel("🎓 Audio Learning System")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(self.title)
        
        # Status
        self.status = QLabel("Press 'Start' to begin learning")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size: 16px; padding: 10px;")
        layout.addWidget(self.status)
        
        # Lesson display
        self.lesson_text = QTextEdit()
        self.lesson_text.setReadOnly(True)
        self.lesson_text.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.lesson_text)
        
        # Buttons
        self.btn_start = QPushButton("▶️ Start Lesson")
        self.btn_start.clicked.connect(self.start_lesson)
        self.btn_start.setStyleSheet("font-size: 16px; padding: 15px;")
        layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹️ Stop")
        self.btn_stop.clicked.connect(self.stop_speaking)
        self.btn_stop.setStyleSheet("font-size: 16px; padding: 15px;")
        layout.addWidget(self.btn_stop)
    
    def speak(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()
    
    def start_lesson(self):
        try:
            # Get lessons from API
            response = requests.get(f"{API_URL}/lessons/")
            
            if response.status_code == 200:
                lessons = response.json()
                
                if lessons:
                    lesson = lessons[0]
                    self.lesson_text.setText(f"Title: {lesson['title']}\n\n{lesson['content']}")
                    self.status.setText("🔊 Playing lesson...")
                    self.speak(f"Lesson title: {lesson['title']}. {lesson['content']}")
                    self.status.setText("✅ Lesson completed!")
                else:
                    self.status.setText("❌ No lessons available!")
                    self.speak("No lessons available")
            else:
                self.status.setText("❌ Cannot connect to server!")
                self.speak("Cannot connect to server")
        except Exception as e:
            self.status.setText(f"❌ Error: {str(e)}")
            self.speak("An error occurred")
    
    def stop_speaking(self):
        self.tts_engine.stop()
        self.status.setText("⏸️ Stopped")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentApp()
    window.show()
    sys.exit(app.exec())