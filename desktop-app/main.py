import sys
import os
import uuid
import time
import queue
import threading
import requests
import speech_recognition as sr
import json
import sqlite3
from PySide6.QtCore import Qt
import pygame 
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
from pathlib import Path
from gtts import gTTS
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QTextEdit, QSlider, QCheckBox, QListWidget, QLineEdit
    )
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor

API_URL = "http://localhost:8001"
DB_FILE = "offline_lessons.db"

# ================= QMETA AI CONFIGURATION =================
QMETA_API_KEY = "qm-Q2LCqsz6scwV0C1Nz6MIU"
QMETA_API_URL = "https://api.qmeta.ai/v1/chat/completions"
QMETA_MODEL = "qmeta-llama-3.1-70b-instruct"


# ================= QMETA VOICE COMMAND PROCESSOR =================
class QmetaVoiceProcessor:
    """Intelligent voice command processor with reliable fallback"""
    
    @staticmethod
    def get_intent(command_text):
        """Interpret voice command using fallback logic (Qmeta AI disabled for reliability)"""
        # Use fallback directly for reliability
        return QmetaVoiceProcessor._fallback_intent(command_text)
    
    @staticmethod
    def _fallback_intent(command):
        """Fallback intent recognition using keyword matching"""
        command_lower = command.lower()
        
        intent = {
            "intent": "unknown",
            "subject": None,
            "answer": None,
            "speed_change": None,
            "subject_number": None,
            "confidence": "medium",
            "original_command": command
        }
        
        # Subject detection - IMPROVED
        subjects = ["math", "mathematics", "science", "history", "english", "computer", "physics", "chemistry", "biology"]
        for subj in subjects:
            if subj in command_lower:
                intent["subject"] = subj
                intent["intent"] = "select_subject"
                intent["confidence"] = "high"
                return intent
        
        # Subject number detection
        import re
        subject_num_match = re.search(r'(?:subject\s+)?(\d+)', command_lower)
        if subject_num_match and ("select" in command_lower or "choose" in command_lower or "subject" in command_lower):
            intent["subject_number"] = int(subject_num_match.group(1))
            intent["intent"] = "select_subject"
            intent["confidence"] = "high"
            return intent
        
        # Answer detection - IMPROVED
        for letter in ['a', 'b', 'c', 'd']:
            patterns = [
                f"answer {letter}",
                f"option {letter}",
                f"select {letter}",
                f"choose {letter}",
                f" {letter} ",
                f"^{letter}$"
            ]
            for pattern in patterns:
                if re.search(pattern, command_lower):
                    intent["answer"] = letter.upper()
                    intent["intent"] = "answer_question"
                    intent["confidence"] = "high"
                    return intent
        
        # Intent detection
        if "repeat" in command_lower:
            if "lesson" in command_lower:
                intent["intent"] = "repeat_lesson"
            elif "question" in command_lower:
                intent["intent"] = "repeat_question"
            else:
                intent["intent"] = "repeat_content"
            intent["confidence"] = "high"
        elif "start quiz" in command_lower or "take quiz" in command_lower or "quiz" in command_lower:
            intent["intent"] = "take_quiz"
            intent["confidence"] = "high"
        elif "start lesson" in command_lower or "play lesson" in command_lower:
            intent["intent"] = "start_lesson"
            intent["confidence"] = "high"
        elif "select" in command_lower or "choose" in command_lower:
            intent["intent"] = "select_subject"
            intent["confidence"] = "medium"
        elif "pause" in command_lower:
            intent["intent"] = "pause_audio"
            intent["confidence"] = "high"
        elif "resume" in command_lower or "continue" in command_lower or "play" in command_lower:
            intent["intent"] = "resume_audio"
            intent["confidence"] = "high"
        elif "stop" in command_lower:
            intent["intent"] = "stop_audio"
            intent["confidence"] = "high"
        elif "help" in command_lower:
            intent["intent"] = "help"
            intent["confidence"] = "high"
        elif "faster" in command_lower or "speed up" in command_lower:
            intent["intent"] = "increase_speed"
            intent["speed_change"] = 0.2
            intent["confidence"] = "high"
        elif "slower" in command_lower or "slow down" in command_lower:
            intent["intent"] = "decrease_speed"
            intent["speed_change"] = -0.2
            intent["confidence"] = "high"
        elif "exit" in command_lower or "quit" in command_lower or "close" in command_lower:
            intent["intent"] = "exit_app"
            intent["confidence"] = "high"
        
        return intent


# ================= OFFLINE DATABASE =================
class OfflineStorage:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.setup_db()
    
    def setup_db(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY,
                subject_id INTEGER,
                title TEXT,
                content TEXT,
                FOREIGN KEY (subject_id) REFERENCES subjects (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY,
                lesson_id INTEGER,
                question TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_answer TEXT,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER,
                score INTEGER,
                total_questions INTEGER,
                percentage REAL,
                synced BOOLEAN DEFAULT 0,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            )
        """)
        
        self.conn.commit()
    
    def save_subject(self, subject_id, name, description):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO subjects (id, name, description) VALUES (?, ?, ?)",
                      (subject_id, name, description))
        self.conn.commit()
    
    def save_lesson(self, lesson_id, subject_id, title, content):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO lessons (id, subject_id, title, content) VALUES (?, ?, ?, ?)",
                      (lesson_id, subject_id, title, content))
        self.conn.commit()
    
    def save_quiz(self, quiz):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO quizzes 
            (id, lesson_id, question, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (quiz['id'], quiz['lesson_id'], quiz['question'], quiz['option_a'],
              quiz['option_b'], quiz['option_c'], quiz['option_d'], quiz['correct_answer']))
        self.conn.commit()
    
    def get_subjects(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description FROM subjects")
        return [{"id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]
    
    def get_lessons_by_subject(self, subject_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, content FROM lessons WHERE subject_id = ?", (subject_id,))
        return [{"id": row[0], "title": row[1], "content": row[2]} for row in cursor.fetchall()]
    
    def get_quizzes(self, lesson_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_answer
            FROM quizzes WHERE lesson_id = ?
        """, (lesson_id,))
        return [
            {
                "id": row[0], "question": row[1], "option_a": row[2],
                "option_b": row[3], "option_c": row[4], "option_d": row[5],
                "correct_answer": row[6]
            }
            for row in cursor.fetchall()
        ]
    
    def save_progress(self, lesson_id, score, total):
        cursor = self.conn.cursor()
        percentage = (score / total) * 100 if total > 0 else 0
        cursor.execute("INSERT INTO progress (lesson_id, score, total_questions, percentage, synced) VALUES (?, ?, ?, ?, 0)",
                      (lesson_id, score, total, percentage))
        self.conn.commit()
        return cursor.lastrowid


# ================= AUDIO ENGINE =================
class AudioPlayer(QObject):
    word_highlight = Signal(str)
    playback_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.paused = False
        self.stopped = False
        self.speed = 1.0
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()
        self.last_spoken = ""
    
    def _run(self):
        import pygame
        pygame.mixer.init()
        
        while True:
            text = self.queue.get()
            if text is None:
                break
            
            self.stopped = False
            self.paused = False
            self.last_spoken = text
            
            try:
                filename = f"tts_{uuid.uuid4()}.mp3"
                slow = self.speed < 0.8
                gTTS(text=text, lang="en", slow=slow).save(filename)
                
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                
                sound = pygame.mixer.Sound(filename)
                sound.play()
                
                while pygame.mixer.get_busy():
                    if self.stopped:
                        pygame.mixer.stop()
                        break
                    if self.paused:
                        pygame.mixer.pause()
                        while self.paused and not self.stopped:
                            time.sleep(0.1)
                        if not self.stopped:
                            pygame.mixer.unpause()
                    time.sleep(0.1)
                
                time.sleep(0.1)
                try:
                    os.remove(filename)
                except:
                    pass
                
                self.playback_finished.emit()
            except Exception as e:
                print(f"Audio error: {e}")
    
    def speak(self, text):
        self.queue.put(text)
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def stop(self):
        self.stopped = True
    
    def set_speed(self, speed):
        self.speed = max(0.5, min(2.0, speed))
    
    def repeat_last(self):
        if self.last_spoken:
            self.speak(self.last_spoken)


# ================= LOGIN SCREEN =================
class LoginScreen(QWidget):
    login_success = Signal(dict, str)  # user_data, access_token
    
    def __init__(self):
        super().__init__()
        self.audio = AudioPlayer()
        self.setup_ui()
        
        # Auto-announce login screen
        QTimer.singleShot(500, lambda: self.audio.speak("Welcome to Audio Learning System. Please enter your username and password to login."))
    
    def setup_ui(self):
        self.setWindowTitle("🔐 Login - Audio Learning System")
        self.setGeometry(300, 200, 500, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔐 Audio Learning System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: white; 
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2); 
            padding: 30px; 
            border-radius: 15px;
            margin-bottom: 20px;
        """)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Login Required")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 16px; color: #555; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Username
        username_label = QLabel("Username:")
        username_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            padding: 12px; 
            font-size: 16px; 
            border: 2px solid #ddd; 
            border-radius: 8px;
            margin-bottom: 15px;
        """)
        self.username_input.returnPressed.connect(self.login)
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            padding: 12px; 
            font-size: 16px; 
            border: 2px solid #ddd; 
            border-radius: 8px;
            margin-bottom: 20px;
        """)
        self.password_input.returnPressed.connect(self.login)
        layout.addWidget(self.password_input)
        
        # Status
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("font-size: 14px; padding: 10px; color: #e74c3c;")
        layout.addWidget(self.status)
        
        # Login Button
        self.login_btn = QPushButton("🔓 Login")
        self.login_btn.clicked.connect(self.login)
        self.login_btn.setStyleSheet("""
            QPushButton {
                padding: 15px; 
                font-size: 18px; 
                font-weight: bold; 
                background: #2ecc71; 
                color: white; 
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background: #27ae60;
            }
            QPushButton:pressed {
                background: #229954;
            }
        """)
        layout.addWidget(self.login_btn)
        
        layout.addStretch()
        
        # Focus on username
        self.username_input.setFocus()
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status.setText("⚠️ Please enter both username and password")
            self.audio.speak("Please enter both username and password.")
            return
        
        self.status.setText("🔄 Logging in...")
        self.login_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            # Call login API
            response = requests.post(
                f"{API_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data['access_token']
                user_data = data['user']
                
                self.status.setText (f"✅ Welcome, {user_data['first_name']}!")
                self.audio.speak(f"Login successful")
                
                # Emit success signal
                QTimer.singleShot(1500, lambda: self.login_success.emit(user_data, access_token))
                
            else:
                error_msg = "Invalid username or password"
                self.status.setText(f"❌ {error_msg}")
                self.audio.speak(error_msg)
                self.login_btn.setEnabled(True)
                
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to server. Please check your connection."
            self.status.setText(f"❌ {error_msg}")
            self.audio.speak(error_msg)
            self.login_btn.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Login failed: {str(e)}"
            self.status.setText(f"❌ {error_msg}")
            self.audio.speak("Login failed. Please try again.")
            self.login_btn.setEnabled(True)
            print(f"Login error: {e}")


# ================= MAIN APP =================
class StudentApp(QMainWindow):
    def __init__(self, user_data, access_token):
        super().__init__()
        
        self.user_data = user_data
        self.access_token = access_token
        
        self.audio = AudioPlayer()
        self.storage = OfflineStorage()
        
        self.selected_subject_id = None
        self.selected_subject_name = None
        self.current_lesson = None
        self.current_quiz = []
        self.quiz_index = 0
        self.score = 0
        self.online_mode = True
        self.voice_nav_active = True
        self.command_queue = queue.Queue()
        self.subjects_list = []
        self.is_listening = False
        self.app_state = "initial"
        
        self.setup_ui()
        
        # AUTO-LOAD ON LAUNCH
        QTimer.singleShot(1000, self.auto_load_on_launch)
    
    def get_headers(self):
        """Return authorization headers for API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def auto_load_on_launch(self):
        """Automatically load subjects and lessons on app launch"""
        welcome = f"Welcome {self.user_data['first_name']}. Loading subjects and lessons. Please wait."
        self.audio.speak(welcome)
        self.status.setText("🔄 Auto-loading subjects and lessons...")
        
        QTimer.singleShot(2000, self.load_subjects)
    
    def setup_ui(self):
        self.setWindowTitle("🎓 Audio Learning System")
        self.setGeometry(90, 60, 800, 500)
        
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)
        
        # Title with user info
        title = QLabel(f"🎓 Audio Learning System - {self.user_data['first_name']} ({self.user_data['role'].title()})")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2); padding: 20px; border-radius: 15px;")
        main_layout.addWidget(title)
        
        # Voice Status
        self.voice_indicator = QLabel("🎤 VOICE: ACTIVE - Listening...")
        self.voice_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_indicator.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px; background: #2ecc71; color: white; border-radius: 10px;")
        main_layout.addWidget(self.voice_indicator)
        
        # Controls
        controls = QHBoxLayout()
        
        self.online_checkbox = QCheckBox("🌐 Online Mode")
        self.online_checkbox.setChecked(True)
        self.online_checkbox.stateChanged.connect(self.toggle_mode)
        controls.addWidget(self.online_checkbox)
        
        self.voice_nav_checkbox = QCheckBox("🎤 Voice Commands")
        self.voice_nav_checkbox.setChecked(True)
        self.voice_nav_checkbox.stateChanged.connect(self.toggle_voice_navigation)
        controls.addWidget(self.voice_nav_checkbox)
        
        controls.addWidget(QLabel("🎚️ Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(5)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.change_speed)
        self.speed_slider.setMaximumWidth(200)
        controls.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("1.0x")
        controls.addWidget(self.speed_label)
        controls.addStretch()


        # Logout Button
        self.btn_logout = QPushButton("🚪 Logout")
        self.btn_logout.clicked.connect(self.logout)
        self.btn_logout.setStyleSheet("""
            QPushButton {
                padding: 5px 15px; 
                background: #e67e22; 
                color: white; 
                border-radius: 5px; 
                font-weight: bold;
            }
            QPushButton:hover { background: #d35400; }
        """)
        controls.addWidget(self.btn_logout)
        
        main_layout.addLayout(controls)
        
        # Status
        self.status = QLabel("🎤 Initializing...")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("font-size: 16px; padding: 12px; background: #d5f4e6; border-radius: 10px;")
        main_layout.addWidget(self.status)
        
        # Subject List
        subjects_layout = QHBoxLayout()
        subjects_layout.addWidget(QLabel("📚 Subjects:"))
        
        self.subject_list = QListWidget()
        self.subject_list.itemClicked.connect(self.subject_selected)
        self.subject_list.setMaximumHeight(100)
        subjects_layout.addWidget(self.subject_list)
        
        main_layout.addLayout(subjects_layout)


        # Display
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("font-size: 20px; padding: 20px; border-radius: 12px;")
        main_layout.addWidget(self.display, stretch=1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_lesson = QPushButton("📚 Start Lesson")
        self.btn_lesson.clicked.connect(self.play_lesson)
        self.btn_lesson.setStyleSheet("padding: 12px; background: #3498db; color: white; border-radius: 10px;")
        btn_layout.addWidget(self.btn_lesson)
        
        self.btn_quiz = QPushButton("❓ Start Quiz")
        self.btn_quiz.clicked.connect(self.start_quiz)
        self.btn_quiz.setStyleSheet("padding: 12px; background: #e74c3c; color: white; border-radius: 10px;")
        btn_layout.addWidget(self.btn_quiz)
        
        main_layout.addLayout(btn_layout)
        
        # Answer buttons
        quiz_layout = QHBoxLayout()
        for letter in ['A', 'B', 'C', 'D']:
            btn = QPushButton(letter)
            btn.clicked.connect(lambda checked, l=letter: self.check_answer(l))
            btn.setStyleSheet("padding: 15px; background: #3498db; color: white; border-radius: 8px; font-size: 18px; font-weight: bold;")
            quiz_layout.addWidget(btn)
        main_layout.addLayout(quiz_layout)
        
        # Playback controls
        playback = QHBoxLayout()
        
        btn_pause = QPushButton("⏸️ Pause")
        btn_pause.clicked.connect(self.audio.pause)
        btn_pause.setStyleSheet("padding: 10px; background: #f39c12; color: white; border-radius: 5px;")
        playback.addWidget(btn_pause)
        
        btn_resume = QPushButton("▶️ Resume")
        btn_resume.clicked.connect(self.audio.resume)
        btn_resume.setStyleSheet("padding: 10px; background: #27ae60; color: white; border-radius: 5px;")
        playback.addWidget(btn_resume)
        
        btn_stop = QPushButton("⏹️ Stop")
        btn_stop.clicked.connect(self.audio.stop)
        btn_stop.setStyleSheet("padding: 10px; background: #95a5a6; color: white; border-radius: 5px;")
        playback.addWidget(btn_stop)
        
        btn_repeat = QPushButton("🔁 Repeat Last")
        btn_repeat.clicked.connect(self.audio.repeat_last)
        btn_repeat.setStyleSheet("padding: 10px; background: #9b59b6; color: white; border-radius: 5px;")
        playback.addWidget(btn_repeat)
        
        main_layout.addLayout(playback)
        
        # Start voice navigation
        self.toggle_voice_navigation(Qt.CheckState.Checked.value)

    def toggle_mode(self, state):
        self.online_mode = state == Qt.CheckState.Checked.value
        mode = "Online" if self.online_mode else "Offline"
        self.status.setText(f"📡 Mode: {mode}")
    
    def change_speed(self, value):
        speed = value / 10.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.audio.set_speed(speed)
    
    def load_subjects(self):
        """Load subjects and lessons"""
        try:
            self.status.setText("🔄 Loading subjects and lessons...")
            QApplication.processEvents()
            
            if self.online_mode:
                # Load subjects (no auth required)
                res = requests.get(f"{API_URL}/lessons/subjects", timeout=10)
                subjects = res.json()
                
                for subj in subjects:
                    self.storage.save_subject(subj['id'], subj['name'], subj.get('description', ''))
                
                # Load ALL lessons
                lessons_res = requests.get(f"{API_URL}/lessons/", timeout=10)
                all_lessons = lessons_res.json()
                
                for lesson in all_lessons:
                    self.storage.save_lesson(
                        lesson['id'],
                        lesson['topic_id'],
                        lesson['title'],
                        lesson['content']
                    )
            else:
                subjects = self.storage.get_subjects()
            
            self.subjects_list = subjects
            self.subject_list.clear()
            
            for idx, subj in enumerate(subjects, 1):
                self.subject_list.addItem(f"{idx}. {subj['name']} (ID: {subj['id']})")
            
            self.app_state = "subjects_loaded"
            self.status.setText(f"✅ {len(subjects)} subjects loaded")
            
            # READ SUBJECTS ALOUD
            subject_names = ". ".join([f"{idx}, {subj['name']}" for idx, subj in enumerate(subjects, 1)])
            announcement = f"{len(subjects)} subjects available. {subject_names}. Please say the subject name to select it, or say repeat to hear the subjects again."
            
            self.audio.speak(announcement)
            
        except Exception as e:
            print(f"Error loading subjects: {e}")
            self.status.setText(f"❌ Error: {str(e)}")
            self.audio.speak("Error loading subjects. Please check connection.")
    
    def subject_selected(self, item):
        text = item.text()
        subject_id = int(text.split("ID: ")[1].split(")")[0])
        subject_name = text.split(".")[1].split(" (ID:")[0].strip()
        self.select_subject_by_id(subject_id, subject_name)
    
    def select_subject_by_id(self, subject_id, subject_name):
        """Select subject and load lessons"""
        self.selected_subject_id = subject_id
        self.selected_subject_name = subject_name
        self.app_state = "subject_selected"
        
        self.status.setText(f"📚 Loading {subject_name} lessons...")
        QApplication.processEvents()
        
        try:
            if self.online_mode:
                res = requests.get(f"{API_URL}/lessons/", timeout=10)
                all_lessons = res.json()
                lessons = [l for l in all_lessons if l['topic_id'] == subject_id]
                
                for lesson in lessons:
                    self.storage.save_lesson(lesson['id'], subject_id, lesson['title'], lesson['content'])
            else:
                lessons = self.storage.get_lessons_by_subject(subject_id)
            
            if lessons:
                self.current_lesson = lessons[0]
                self.status.setText(f"✅ {subject_name}: {len(lessons)} lessons")
                
                self.audio.speak(f"{subject_name} selected. Starting lesson.")
                QTimer.singleShot(2000, self.play_lesson)
            else:
                self.status.setText(f"❌ No lessons for {subject_name}")
                self.audio.speak(f"No lessons available for {subject_name}. Please select another subject.")
                
        except Exception as e:
            print(f"Error loading lessons: {e}")
            self.status.setText(f"❌ Error: {str(e)}")
            self.audio.speak("Error loading lessons. Please try again.")
    
    def select_subject_by_name(self, subject_name):
        """Select subject by name from voice"""
        subject_name_lower = subject_name.lower()
        
        for subj in self.subjects_list:
            if subject_name_lower in subj['name'].lower():
                self.select_subject_by_id(subj['id'], subj['name'])
                return
        
        self.audio.speak(f"Subject {subject_name} not found.")
    
    def select_subject_by_number(self, number):
        """Select subject by number from voice"""
        if 1 <= number <= len(self.subjects_list):
            subj = self.subjects_list[number - 1]
            self.select_subject_by_id(subj['id'], subj['name'])
        else:
            self.audio.speak(f"Subject number {number} not found.")
    
    def play_lesson(self):
        """Read lesson aloud"""
        if not self.current_lesson:
            self.audio.speak("Please select a subject first.")
            return
        
        self.app_state = "lesson_playing"
        
        title = self.current_lesson['title']
        content = self.current_lesson['content']
        
        html = f"""
        <div style='padding: 10px;'>
            <h2 style='color: #2c3e50;'>📖 {title}</h2>
            <p style='font-size: 18px; line-height: 1.6;'>{content}</p>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText("🔊 Playing lesson...")
        QApplication.processEvents()
        
        self.audio.speak(f"Lesson title: {title}.")
        self.audio.speak(content)
        
        prompt = "Lesson complete. Say start quiz to take the quiz, or say repeat lesson to listen again."
        QTimer.singleShot(len(content) * 50, lambda: self.audio.speak(prompt))
        QTimer.singleShot(len(content) * 50, lambda: self.status.setText("✅ Lesson complete! Say 'start quiz' or 'repeat lesson'"))
    
    def start_quiz(self):
        """Start quiz"""
        if not self.current_lesson:
            self.audio.speak("Please complete a lesson first.")
            return
        
        try:
            lesson_id = self.current_lesson['id']
            self.status.setText("🔄 Loading quiz...")
            QApplication.processEvents()
            
            if self.online_mode:
                res = requests.get(f"{API_URL}/quizzes/", timeout=10)
                all_quizzes = res.json()
                self.current_quiz = [q for q in all_quizzes if q['lesson_id'] == lesson_id]
                
                for quiz in self.current_quiz:
                    self.storage.save_quiz(quiz)
            else:
                self.current_quiz = self.storage.get_quizzes(lesson_id)
            
            if self.current_quiz:
                self.quiz_index = 0
                self.score = 0
                self.app_state = "quiz_active"
                self.status.setText(f"📝 Quiz: {len(self.current_quiz)} questions")
                
                self.audio.speak(f"Quiz started. {len(self.current_quiz)} questions.")
                QTimer.singleShot(2000, self.ask_question)
            else:
                self.audio.speak("No quiz available for this lesson.")
                
        except Exception as e:
            print(f"Quiz error: {e}")
            self.audio.speak("Error loading quiz.")
    
    def ask_question(self):
        """Read question and options aloud"""
        if self.quiz_index >= len(self.current_quiz):
            self.show_results()
            return
        
        q = self.current_quiz[self.quiz_index]
        
        html = f"""
        <div style='padding: 10px;'>
            <h3 style='color: #e74c3c;'>Question {self.quiz_index + 1}/{len(self.current_quiz)}</h3>
            <p style='font-size: 22px; font-weight: bold; margin: 20px 0;'>{q['question']}</p>
            <ul style='font-size: 20px; line-height: 2.2; list-style: none;'>
                <li><strong>A.</strong> {q['option_a']}</li>
                <li><strong>B.</strong> {q['option_b']}</li>
                <li><strong>C.</strong> {q['option_c']}</li>
                <li><strong>D.</strong> {q['option_d']}</li>
            </ul>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText(f"Question {self.quiz_index + 1}/{len(self.current_quiz)}")
        QApplication.processEvents()
        
        self.audio.speak(f"Question {self.quiz_index + 1}.")
        self.audio.speak(q['question'])
        self.audio.speak(f"Option A: {q['option_a']}")
        self.audio.speak(f"Option B: {q['option_b']}")
        self.audio.speak(f"Option C: {q['option_c']}")
        self.audio.speak(f"Option D: {q['option_d']}")
        self.audio.speak("Say your answer now, or say repeat question to hear it again.")
    
    def check_answer(self, answer):
        """Check answer and move to next question"""
        if not self.current_quiz or self.quiz_index >= len(self.current_quiz):
            return
        
        q = self.current_quiz[self.quiz_index]
        correct = q['correct_answer'].upper()
        answer = answer.upper()
        
        if answer == correct:
            self.score += 1
            self.audio.speak(f"Correct! The answer is {correct}.")
            self.status.setText(f"✅ Correct! Score: {self.score}/{self.quiz_index + 1}")
        else:
            self.audio.speak(f"Incorrect. The correct answer is {correct}.")
            self.status.setText(f"❌ Wrong. Correct: {correct}")
        
        self.quiz_index += 1
        
        if self.quiz_index < len(self.current_quiz):
            QTimer.singleShot(2000, self.ask_question)
        else:
            QTimer.singleShot(2000, self.show_results)
    
    def show_results(self):
        """Show quiz results"""
        total = len(self.current_quiz)
        percent = (self.score / total) * 100 if total > 0 else 0
        passed = percent >= 70
        
        html = f"""
        <div style='text-align: center; padding: 30px;'>
            <h1 style='color: {'#2ecc71' if passed else '#e74c3c'};'>Quiz Complete!</h1>
            <h2>Score: {self.score}/{total}</h2>
            <h2>Percentage: {percent:.0f}%</h2>
            <h3>{'✅ PASSED!' if passed else '❌ TRY AGAIN'}</h3>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText(f"Quiz Complete: {self.score}/{total}")
        self.app_state = "quiz_completed"
        
        result = f"Quiz complete! You scored {self.score} out of {total}. That is {percent:.0f} percent."
        
        if passed:
            result += " Congratulations! You passed!"
        else:
            result += " Please review the lesson and try again."
        
        self.audio.speak(result)
        
        try:
            self.storage.save_progress(self.current_lesson['id'], self.score, total)
        except:
            pass
    
    def toggle_voice_navigation(self, state):
        """Enable/disable voice commands"""
        is_checked = (state == Qt.CheckState.Checked.value or state == True)
        
        if is_checked:
            self.voice_nav_active = True
            
            if not hasattr(self, 'command_timer'):
                self.command_timer = QTimer()
                self.command_timer.timeout.connect(self.process_voice_commands)
            
            self.start_voice_navigation()
            self.command_timer.start(100)
            
            self.voice_indicator.setText("🎤 VOICE: ACTIVE")
            self.voice_indicator.setStyleSheet("padding: 15px; background: #2ecc71; color: white; border-radius: 10px; font-size: 18px; font-weight: bold;")
        else:
            self.voice_nav_active = False
            
            if hasattr(self, 'command_timer'):
                self.command_timer.stop()
            
            self.voice_indicator.setText("🎤 VOICE: OFF")
            self.voice_indicator.setStyleSheet("padding: 15px; background: #95a5a6; color: white; border-radius: 10px; font-size: 18px; font-weight: bold;")
    
    def logout(self):
        """Log out and return to login screen"""
        self.audio.speak("Logged out.")
        self.close() # Closes the main window
        # Create and show a new login screen
        self.login_scr = LoginScreen()
        self.login_scr.login_success.connect(self.on_login_success_callback)
        self.login_scr.show()

    def on_login_success_callback(self, user_data, access_token):
        """Helper to restart app after logout"""
        self.login_scr.close()
        self.new_window = StudentApp(user_data, access_token)
        self.new_window.show()


    def start_voice_navigation(self):
        """Start continuous voice recognition"""
        def _listen():
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 4000
            recognizer.dynamic_energy_threshold = True
            
            while self.voice_nav_active:
                try:
                    with sr.Microphone() as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        
                        try:
                            command_text = recognizer.recognize_google(audio)
                            print(f"🗣️ Heard: {command_text}")
                            
                            intent = QmetaVoiceProcessor.get_intent(command_text)
                            self.command_queue.put(intent)
                            
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError as e:
                            print(f"Recognition error: {e}")
                            
                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    print(f"Listen error: {e}")
                    time.sleep(0.1)
                
                time.sleep(0.1)
        
        threading.Thread(target=_listen, daemon=True).start()
    
    def process_voice_commands(self):
        """Process voice commands"""
        try:
            while not self.command_queue.empty():
                intent = self.command_queue.get_nowait()
                command = intent.get('intent')
                
                print(f"📋 Processing: {command}")
                
                if command == "select_subject":
                    if intent.get('subject_number'):
                        self.select_subject_by_number(intent['subject_number'])
                    elif intent.get('subject'):
                        self.select_subject_by_name(intent['subject'])
                
                elif command == "start_lesson":
                    self.play_lesson()
                
                elif command == "take_quiz":
                    self.start_quiz()
                
                elif command == "answer_question":
                    if intent.get('answer'):
                        self.check_answer(intent['answer'])
                
                elif command == "repeat_content" or command == "repeat_lesson":
                    if self.app_state == "subjects_loaded":
                        self.load_subjects()
                    elif self.app_state == "lesson_playing":
                        self.play_lesson()
                    else:
                        self.audio.repeat_last()
                
                elif command == "repeat_question":
                    if self.app_state == "quiz_active":
                        self.ask_question()
                    else:
                        self.audio.repeat_last()
                
                elif command == "pause_audio":
                    self.audio.pause()
                
                elif command == "resume_audio":
                    self.audio.resume()
                
                elif command == "stop_audio":
                    self.audio.stop()
                
                elif command == "increase_speed":
                    current = self.speed_slider.value()
                    self.speed_slider.setValue(min(20, current + 2))
                
                elif command == "decrease_speed":
                    current = self.speed_slider.value()
                    self.speed_slider.setValue(max(5, current - 2))
                
                elif command == "exit_app":
                    self.audio.speak("Goodbye!")
                    time.sleep(1)
                    self.close()
        
        except Exception as e:
            print(f"Command error: {e}")
    
    def closeEvent(self, event):
        self.voice_nav_active = False
        self.audio.queue.put(None)
        self.storage.conn.close()
        event.accept()

# ================= MAIN APPLICATION =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Show login screen first
    login_screen = LoginScreen()
    
    def on_login_success(user_data, access_token):
        """Called when login succeeds"""
        login_screen.close()
        
        # Show main app
        main_window = StudentApp(user_data, access_token)
        main_window.show()
    
    login_screen.login_success.connect(on_login_success)
    login_screen.show()
    
    sys.exit(app.exec())