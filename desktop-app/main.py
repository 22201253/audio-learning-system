import sys
import os
import uuid
import time
import queue
import threading
import requests
import speech_recognition as sr
from gtts import gTTS
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout,
    QWidget, QPushButton, QLabel, QTextEdit
)
from PySide6.QtCore import Qt

API_URL = "http://localhost:8001"


# ================= AUDIO ENGINE (STABLE) =================
class AudioPlayer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = queue.Queue()
        self.start()

    def run(self):
        import pygame
        pygame.mixer.init()

        while True:
            text = self.queue.get()
            if text is None:
                break

            try:
                filename = f"tts_{uuid.uuid4()}.mp3"
                gTTS(text=text, lang="en").save(filename)

                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                pygame.mixer.music.stop()
                os.remove(filename)

            except Exception as e:
                print("Audio error:", e)

    def speak(self, text):
        self.queue.put(text)


# ================= MAIN APP =================
class StudentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.audio = AudioPlayer()

        self.current_lesson = None
        self.current_quiz = []
        self.quiz_index = 0
        self.score = 0

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("🎓 Audio Learning System")
        self.setGeometry(120, 80, 900, 650)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setSpacing(18)
        layout.setContentsMargins(30, 30, 30, 30)

        # ===== TITLE =====
        title = QLabel("🎓 Audio Learning System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
            color: #2c3e50;
            padding: 15px;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Student Voice Learning App")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        layout.addWidget(subtitle)

        # ===== STATUS CARD =====
        self.status = QLabel("Ready to learn 🚀")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("""
            font-size: 16px;
            padding: 12px;
            background-color: #ecf0f1;
            border-radius: 10px;
        """)
        layout.addWidget(self.status)

        # ===== CONTENT CARD =====
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("""
            font-size: 16px;
            padding: 15px;
            border-radius: 12px;
            border: 2px solid #3498db;
            background-color: #ffffff;
        """)
        layout.addWidget(self.display, stretch=1)

        # ===== BUTTONS =====
        self.btn_lesson = QPushButton("📚 Start Lesson")
        self.btn_lesson.clicked.connect(self.play_lesson)
        self.btn_lesson.setStyleSheet(self.button_style("#3498db"))
        layout.addWidget(self.btn_lesson)

        self.btn_quiz = QPushButton("❓ Start Quiz")
        self.btn_quiz.clicked.connect(self.start_quiz)
        self.btn_quiz.setStyleSheet(self.button_style("#e74c3c"))
        layout.addWidget(self.btn_quiz)

        self.btn_voice = QPushButton("🎤 Answer with Voice")
        self.btn_voice.clicked.connect(self.voice_answer)
        self.btn_voice.setStyleSheet(self.button_style("#2ecc71"))
        layout.addWidget(self.btn_voice)

    def button_style(self, color):
        return f"""
            QPushButton {{
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                background-color: {color};
                color: white;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: #1abc9c;
            }}
        """

    # ================= LOGIC =================
    def play_lesson(self):
        try:
            self.status.setText("📡 Loading lesson...")
            res = requests.get(f"{API_URL}/lessons/")
            lessons = res.json()

            if not lessons:
                self.audio.speak("No lesson available")
                return

            self.current_lesson = lessons[0]
            title = self.current_lesson["title"]
            content = self.current_lesson["content"]

            self.display.setText(f"📖 {title}\n\n{content}")
            self.status.setText("🔊 Playing lesson...")

            self.audio.speak(f"Lesson title: {title}")
            self.audio.speak(content)
            self.audio.speak("Lesson completed. You can take the quiz now")

        except Exception as e:
            print(e)
            self.audio.speak("Error loading lesson")

    def start_quiz(self):
        if not self.current_lesson:
            self.audio.speak("Please take the lesson first")
            return

        try:
            lesson_id = self.current_lesson["id"]
            res = requests.get(f"{API_URL}/quizzes/lessons/{lesson_id}")
            self.current_quiz = res.json()

            if not self.current_quiz:
                self.audio.speak("No quiz available")
                return

            self.quiz_index = 0
            self.score = 0
            self.ask_question()

        except:
            self.audio.speak("Error loading quiz")

    def ask_question(self):
        if self.quiz_index >= len(self.current_quiz):
            total = len(self.current_quiz)
            percent = (self.score / total) * 100

            self.display.setText(
                f"🎯 Quiz Complete\n\nScore: {self.score}/{total}\nPercentage: {percent:.0f}%"
            )
            self.audio.speak(f"You scored {self.score} out of {total}")
            return

        q = self.current_quiz[self.quiz_index]

        self.display.setText(
            f"❓ Question {self.quiz_index + 1}\n\n"
            f"{q['question']}\n\n"
            f"A. {q['option_a']}\n"
            f"B. {q['option_b']}\n"
            f"C. {q['option_c']}\n"
            f"D. {q['option_d']}"
        )

        self.status.setText("🎤 Click voice button and answer")

        self.audio.speak(q["question"])
        self.audio.speak(f"A {q['option_a']}")
        self.audio.speak(f"B {q['option_b']}")
        self.audio.speak(f"C {q['option_c']}")
        self.audio.speak(f"D {q['option_d']}")

    def voice_answer(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.audio.speak("Speak your answer now")
                recognizer.adjust_for_ambient_noise(source, 1)
                audio = recognizer.listen(source, timeout=6)
                text = recognizer.recognize_google(audio).upper()

                if "A" in text:
                    self.check_answer("A")
                elif "B" in text:
                    self.check_answer("B")
                elif "C" in text:
                    self.check_answer("C")
                elif "D" in text:
                    self.check_answer("D")
                else:
                    self.audio.speak("Say A, B, C or D")

        except:
            self.audio.speak("I did not hear you")

    def check_answer(self, answer):
        q = self.current_quiz[self.quiz_index]
        correct = q["correct_answer"].upper()

        if answer == correct:
            self.score += 1
            self.audio.speak("Correct answer")
        else:
            self.audio.speak(f"Wrong. The correct answer is {correct}")

        self.quiz_index += 1
        self.ask_question()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentApp()
    window.show()
    sys.exit(app.exec())
