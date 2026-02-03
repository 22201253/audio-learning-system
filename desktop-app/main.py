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
    QWidget, QPushButton, QLabel, QTextEdit, QSlider, QCheckBox, QListWidget
    )
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor

API_URL = "http://localhost:8001"
DB_FILE = "offline_lessons.db"

# ================= QMETA AI CONFIGURATION =================
QMETA_API_KEY = "qm-Q2LCqsz6scwV0C1Nz6MIU"  # Replace with your actual Qmeta API key
QMETA_API_URL = "https://api.qmeta.ai/v1/chat/completions"
QMETA_MODEL = "qmeta-llama-3.1-70b-instruct"


# ================= QMETA VOICE COMMAND PROCESSOR =================
class QmetaVoiceProcessor:
    """
    Intelligent voice command processor using Qmeta AI
    Handles natural language understanding for voice commands
    """
    
    @staticmethod
    def get_intent(command_text):
        """
        Use Qmeta AI to interpret voice command
        Returns intent dictionary with action and parameters
        """
        try:
            response = requests.post(
                QMETA_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {QMETA_API_KEY}"
                },
                json={
                    "model": QMETA_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a voice command interpreter for an accessible education app for visually impaired students.
Analyze the user's voice command and return ONLY a JSON object with these fields:
{
    "intent": "one of: load_subjects, select_subject, start_lesson, take_quiz, answer_question, pause_audio, resume_audio, stop_audio, repeat_content, next_question, help, increase_speed, decrease_speed, toggle_mode, exit_app, unknown",
    "subject": "subject name if mentioned (math, science, history, english, computer, etc.) or null",
    "answer": "A, B, C, or D if answering a quiz question, or null",
    "speed_change": "number for speed adjustment (e.g., 0.1 for increase, -0.1 for decrease) or null",
    "subject_number": "number if user says 'select subject 1' etc., or null",
    "confidence": "high, medium, or low"
}
Return ONLY valid JSON, no other text or markdown.

Examples:
- "select math" → {"intent": "select_subject", "subject": "math", "answer": null, "speed_change": null, "subject_number": null, "confidence": "high"}
- "start the lesson" → {"intent": "start_lesson", "subject": null, "answer": null, "speed_change": null, "subject_number": null, "confidence": "high"}
- "my answer is B" → {"intent": "answer_question", "subject": null, "answer": "B", "speed_change": null, "subject_number": null, "confidence": "high"}
- "select subject 2" → {"intent": "select_subject", "subject": null, "answer": null, "speed_change": null, "subject_number": 2, "confidence": "high"}
- "speak faster" → {"intent": "increase_speed", "subject": null, "answer": null, "speed_change": 0.2, "subject_number": null, "confidence": "high"}"""
                        },
                        {
                            "role": "user",
                            "content": f"Analyze this command: \"{command_text}\""
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 200
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content'].strip()
                
                # Extract JSON from response
                json_str = content
                if '{' in content:
                    json_str = content[content.index('{'):content.rindex('}')+1]
                
                intent = json.loads(json_str)
                intent['original_command'] = command_text
                print(f"🤖 Qmeta Intent: {intent}")
                return intent
            else:
                print(f"❌ Qmeta API error: {response.status_code}")
                return QmetaVoiceProcessor._fallback_intent(command_text)
                
        except Exception as e:
            print(f"❌ Qmeta AI error: {e}")
            # Use fallback intent recognition
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
            "confidence": "low",
            "original_command": command
        }
        
        # Subject detection
        subjects = ["math", "science", "history", "english", "computer", "physics", "chemistry", "biology"]
        for subj in subjects:
            if subj in command_lower:
                intent["subject"] = subj
                break
        
        # Subject number detection (e.g., "select subject 1")
        import re
        subject_num_match = re.search(r'subject\s+(\d+)', command_lower)
        if subject_num_match:
            intent["subject_number"] = int(subject_num_match.group(1))
        
        # Answer detection
        for letter in ['a', 'b', 'c', 'd']:
            if f"answer {letter}" in command_lower or f"option {letter}" in command_lower or f" {letter} " in command_lower:
                intent["answer"] = letter.upper()
                intent["intent"] = "answer_question"
                return intent
        
        # Intent detection
        if "load subject" in command_lower or "show subject" in command_lower or "list subject" in command_lower:
            intent["intent"] = "load_subjects"
        elif "select" in command_lower or "choose" in command_lower or "pick" in command_lower:
            intent["intent"] = "select_subject"
        elif "start lesson" in command_lower or "play lesson" in command_lower or "begin lesson" in command_lower:
            intent["intent"] = "start_lesson"
        elif "take quiz" in command_lower or "start quiz" in command_lower or "begin quiz" in command_lower:
            intent["intent"] = "take_quiz"
        elif "pause" in command_lower:
            intent["intent"] = "pause_audio"
        elif "resume" in command_lower or "continue" in command_lower or "play" in command_lower:
            intent["intent"] = "resume_audio"
        elif "stop" in command_lower:
            intent["intent"] = "stop_audio"
        elif "repeat" in command_lower or "say again" in command_lower:
            intent["intent"] = "repeat_content"
        elif "next" in command_lower:
            intent["intent"] = "next_question"
        elif "help" in command_lower or "what can i say" in command_lower or "commands" in command_lower:
            intent["intent"] = "help"
        elif "faster" in command_lower or "speed up" in command_lower or "increase speed" in command_lower:
            intent["intent"] = "increase_speed"
            intent["speed_change"] = 0.2
        elif "slower" in command_lower or "slow down" in command_lower or "decrease speed" in command_lower:
            intent["intent"] = "decrease_speed"
            intent["speed_change"] = -0.2
        elif "online" in command_lower and "mode" in command_lower:
            intent["intent"] = "toggle_mode"
        elif "offline" in command_lower and "mode" in command_lower:
            intent["intent"] = "toggle_mode"
        elif "exit" in command_lower or "quit" in command_lower or "close" in command_lower:
            intent["intent"] = "exit_app"
        
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
        """Repeat the last spoken text"""
        if self.last_spoken:
            self.speak(self.last_spoken)


# ================= MAIN APP WITH FULL VOICE CONTROL =================
class StudentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.audio = AudioPlayer()
        self.storage = OfflineStorage()
        
        self.selected_subject_id = None
        self.selected_subject_name = None
        self.current_lesson = None
        self.current_quiz = []
        self.quiz_index = 0
        self.score = 0
        self.online_mode = True
        self.voice_nav_active = False
        self.command_queue = queue.Queue()
        self.subjects_list = []  # Store loaded subjects
        self.is_listening = False  # Track listening state
        
        self.setup_ui()
        
        # Welcome message for visually impaired users
        welcome_msg = """Welcome to the Audio Learning System. 
        This system is fully voice controlled for accessibility.  
        Say load subjects to begin."""
        
        self.audio.speak(welcome_msg)
    
    def setup_ui(self):
        self.setWindowTitle("🎓 Audio Learning System")
        self.setGeometry(90, 60, 800, 500)
        
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)
        
        # Title
        title = QLabel("🎓 Audio Learning System - Voice Controlled")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #667eea, stop:1 #764ba2); padding: 20px; border-radius: 15px;")
        main_layout.addWidget(title)
        
        # Voice Status Indicator
        self.voice_indicator = QLabel("🎤 VOICE: ACTIVE - Listening for commands...")
        self.voice_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voice_indicator.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px; background: #2ecc71; color: white; border-radius: 10px;")
        main_layout.addWidget(self.voice_indicator)
        
        # Controls
        controls = QHBoxLayout()
        
        self.online_checkbox = QCheckBox("🌐 Online Mode")
        self.online_checkbox.setChecked(True)
        self.online_checkbox.stateChanged.connect(self.toggle_mode)
        self.online_checkbox.setStyleSheet("font-size: 14px; font-weight: bold;")
        controls.addWidget(self.online_checkbox)
        
        self.voice_nav_checkbox = QCheckBox("🎤 Voice Commands")
        self.voice_nav_checkbox.setChecked(True)  # ON by default
        self.voice_nav_checkbox.stateChanged.connect(self.toggle_voice_navigation)
        self.voice_nav_checkbox.setStyleSheet("font-size: 14px; font-weight: bold;")
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
        self.speed_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        controls.addWidget(self.speed_label)
        controls.addStretch()
        
        main_layout.addLayout(controls)
        
        # Status
        self.status = QLabel("🎤 Say 'Load Subjects' or click the button to begin")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("font-size: 16px; padding: 12px; background: #d5f4e6; border-radius: 10px; border: 2px solid #2ecc71;")
        main_layout.addWidget(self.status)
        
        # Subject List
        subjects_layout = QHBoxLayout()
        subjects_layout.addWidget(QLabel("📚 Available Subjects:"))
        
        self.subject_list = QListWidget()
        self.subject_list.itemClicked.connect(self.subject_selected)
        self.subject_list.setMaximumHeight(100)
        self.subject_list.setStyleSheet("font-size: 16px;")
        subjects_layout.addWidget(self.subject_list)
        
        btn_load_subjects = QPushButton("🔄 Load Subjects (or say 'load subjects')")
        btn_load_subjects.clicked.connect(self.load_subjects)
        btn_load_subjects.setStyleSheet("padding: 10px; background: #3498db; color: white; border-radius: 5px; font-size: 14px;")
        subjects_layout.addWidget(btn_load_subjects)
        
        main_layout.addLayout(subjects_layout)
        
        # Display
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("font-size: 20px; padding: 20px; border-radius: 12px; border: 3px solid #3498db;")
        main_layout.addWidget(self.display, stretch=1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_lesson = QPushButton("📚 Start Lesson (say 'start lesson')")
        self.btn_lesson.clicked.connect(self.play_lesson)
        self.btn_lesson.setStyleSheet("font-size: 15px; padding: 12px; background: #3498db; color: white; border-radius: 10px;")
        btn_layout.addWidget(self.btn_lesson)
        
        self.btn_quiz = QPushButton("❓ Start Quiz (say 'take quiz')")
        self.btn_quiz.clicked.connect(self.start_quiz)
        self.btn_quiz.setStyleSheet("font-size: 15px; padding: 12px; background: #e74c3c; color: white; border-radius: 10px;")
        btn_layout.addWidget(self.btn_quiz)
        
        main_layout.addLayout(btn_layout)
        
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
        
        # Voice help button
        btn_help = QPushButton("❓ Voice Commands Help (say 'help')")
        btn_help.clicked.connect(self.show_voice_help)
        btn_help.setStyleSheet("font-size: 15px; padding: 12px; background: #34495e; color: white; border-radius: 10px;")
        main_layout.addWidget(btn_help)
        
        # Quiz answer buttons (for when voice is disabled)
        quiz_answer_layout = QHBoxLayout()
        
        self.btn_answer_a = QPushButton("A")
        self.btn_answer_a.clicked.connect(lambda: self.check_answer('A'))
        self.btn_answer_a.setStyleSheet("font-size: 18px; padding: 15px; background: #3498db; color: white; border-radius: 8px; font-weight: bold;")
        quiz_answer_layout.addWidget(self.btn_answer_a)
        
        self.btn_answer_b = QPushButton("B")
        self.btn_answer_b.clicked.connect(lambda: self.check_answer('B'))
        self.btn_answer_b.setStyleSheet("font-size: 18px; padding: 15px; background: #3498db; color: white; border-radius: 8px; font-weight: bold;")
        quiz_answer_layout.addWidget(self.btn_answer_b)
        
        self.btn_answer_c = QPushButton("C")
        self.btn_answer_c.clicked.connect(lambda: self.check_answer('C'))
        self.btn_answer_c.setStyleSheet("font-size: 18px; padding: 15px; background: #3498db; color: white; border-radius: 8px; font-weight: bold;")
        quiz_answer_layout.addWidget(self.btn_answer_c)
        
        self.btn_answer_d = QPushButton("D")
        self.btn_answer_d.clicked.connect(lambda: self.check_answer('D'))
        self.btn_answer_d.setStyleSheet("font-size: 18px; padding: 15px; background: #3498db; color: white; border-radius: 8px; font-weight: bold;")
        quiz_answer_layout.addWidget(self.btn_answer_d)
        
        main_layout.addLayout(quiz_answer_layout)
        
        # Auto-start voice navigation
        self.toggle_voice_navigation(Qt.CheckState.Checked.value)
    
    def toggle_mode(self, state):
        self.online_mode = state == Qt.CheckState.Checked.value
        mode = "Online" if self.online_mode else "Offline"
        if self.voice_nav_active:
            self.audio.speak(f"Switched to {mode} mode")
        self.status.setText(f"📡 Mode: {mode}")
    
    def change_speed(self, value):
        speed = value / 10.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.audio.set_speed(speed)
    
    def load_subjects(self):
        try:
            if self.online_mode:
                self.status.setText("🔄 Loading subjects from server...")
                QApplication.processEvents()
                
                res = requests.get(f"{API_URL}/lessons/subjects", timeout=5)
                subjects = res.json()
                
                # Save offline
                for subj in subjects:
                    self.storage.save_subject(subj['id'], subj['name'], subj.get('description', ''))
            else:
                subjects = self.storage.get_subjects()
            
            self.subjects_list = subjects
            self.subject_list.clear()
            
            for idx, subj in enumerate(subjects, 1):
                self.subject_list.addItem(f"{idx}. {subj['name']} (ID: {subj['id']})")
            
            self.status.setText(f"✅ {len(subjects)} subjects loaded")
            
            # Announce subjects with numbers only if voice is active
            if self.voice_nav_active:
                subject_names = ", ".join([f"number {idx}, {subj['name']}" for idx, subj in enumerate(subjects, 1)])
                self.audio.speak(f"{len(subjects)} subjects loaded. {subject_names}. Say select followed by subject name or number.")
            
        except Exception as e:
            print(f"Error: {e}")
            self.status.setText("❌ Error loading subjects. Check connection.")
            if self.voice_nav_active:
                self.audio.speak("Error loading subjects. Please check your connection and try again.")
    
    def subject_selected(self, item):
        # Extract ID from item text
        text = item.text()
        subject_id = int(text.split("ID: ")[1].split(")")[0])
        subject_name = text.split(".")[1].split(" (ID:")[0].strip()
        
        self.select_subject_by_id(subject_id, subject_name)
    
    def select_subject_by_id(self, subject_id, subject_name):
        """Select subject by ID and name"""
        self.selected_subject_id = subject_id
        self.selected_subject_name = subject_name
        
        self.status.setText(f"📚 Loading {subject_name} lessons...")
        QApplication.processEvents()

        try:
            if self.online_mode:
                res = requests.get(f"{API_URL}/lessons/by-subject/{subject_id}", timeout=10)
                data = res.json()
                lessons = data.get('lessons', [])
                
                # Save offline
                for lesson in lessons:
                    self.storage.save_lesson(lesson['id'], subject_id, lesson['title'], lesson['content'])
            else:
                lessons = self.storage.get_lessons_by_subject(subject_id)
            
            if lessons:
                self.current_lesson = lessons[0]
                self.status.setText(f"✅ {subject_name}: {len(lessons)} lessons available")
                if self.voice_nav_active:
                    self.audio.speak(f"{subject_name} selected. {len(lessons)} lessons available. Say start lesson to begin, or say take quiz to test your knowledge.")
                self.show_lesson_preview()
            else:
                self.status.setText(f"❌ No lessons for {subject_name}")
                if self.voice_nav_active:
                    self.audio.speak(f"No lessons available for {subject_name}")
        except Exception as e:
            print(f"Error: {e}")
            if self.voice_nav_active:
                self.audio.speak("Error loading lessons. Please try again.")
    
    def select_subject_by_name(self, subject_name):
        """Select subject by name (from voice command)"""
        subject_name_lower = subject_name.lower()
        
        for subj in self.subjects_list:
            if subject_name_lower in subj['name'].lower():
                self.select_subject_by_id(subj['id'], subj['name'])
                return
        
        if self.voice_nav_active:
            self.audio.speak(f"Subject {subject_name} not found. Please say load subjects first.")
    
    def select_subject_by_number(self, number):
        """Select subject by number (from voice command)"""
        if 1 <= number <= len(self.subjects_list):
            subj = self.subjects_list[number - 1]
            self.select_subject_by_id(subj['id'], subj['name'])
        else:
            if self.voice_nav_active:
                self.audio.speak(f"Subject number {number} not found. Please choose a number between 1 and {len(self.subjects_list)}.")
    
    def show_lesson_preview(self):
        if self.current_lesson:
            title = self.current_lesson['title']
            content = self.current_lesson['content']
            preview = content[:200] + "..." if len(content) > 200 else content
            
            html = f"""
            <div style='padding: 10px;'>
                <h3 style='color: #2c3e50;'>📖 {title}</h3>
                <p style='font-size: 16px; color: #7f8c8d; line-height: 1.6;'>{preview}</p>
                <p style='font-size: 14px; color: #95a5a6; font-style: italic;'>Say 'start lesson' to begin</p>
            </div>
            """
            self.display.setHtml(html)
    
    def play_lesson(self):
        if not self.current_lesson:
            if self.voice_nav_active:
                self.audio.speak("Please select a subject first. Say load subjects.")
            else:
                self.status.setText("❌ Please select a subject first")
            return
        
        title = self.current_lesson['title']
        content = self.current_lesson['content']
        
        
        html = f"""
        <div style='padding: 10px;'>
            <h2 style='color: #2c3e50; border-bottom: 3px solid #3498db;'>📖 {title}</h2>
            <p style='font-size: 14px; line-height: 1.5;'>{content}</p>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText("🔊 Playing lesson..." if self.voice_nav_active else "✅ Lesson displayed")
        QApplication.processEvents()

        if self.voice_nav_active:
            self.audio.speak(f"Lesson title: {title}. {content}")
            time.sleep(0.1)
            self.audio.speak("Lesson completed. Say take quiz to test your knowledge, or say repeat to hear the lesson again.")
            self.status.setText("✅ Lesson completed! Say 'take quiz' or click the quiz button")
        else:
            self.status.setText("✅ Lesson displayed. Click 'Start Quiz' when ready.")
    
    def start_quiz(self):
        if not self.current_lesson:
            if self.voice_nav_active:
                self.audio.speak("Please take a lesson first. Say start lesson.")
            else:
                self.status.setText("❌ Please complete a lesson first")
            return
        
        try:
            lesson_id = self.current_lesson['id']
            
            self.status.setText("🔄 Loading quiz...")
            QApplication.processEvents()
            
            if self.online_mode:
                res = requests.get(f"{API_URL}/quizzes/lessons/{lesson_id}", timeout=10)
                self.current_quiz = res.json()
                
                for quiz in self.current_quiz:
                    quiz['lesson_id'] = lesson_id
                    self.storage.save_quiz(quiz)
            else:
                self.current_quiz = self.storage.get_quizzes(lesson_id)
            
            if self.current_quiz:
                self.quiz_index = 0
                self.score = 0
                self.status.setText(f"📝 Quiz started: {len(self.current_quiz)} questions")
                if self.voice_nav_active:
                    self.audio.speak(f"Quiz has {len(self.current_quiz)} questions. Answer by saying A, B, C, or D.")
                    time.sleep(0.1)
                self.ask_question()
            else:
                if self.voice_nav_active:
                    self.audio.speak("No quiz available for this lesson.")
                self.status.setText("❌ No quiz available")
        except Exception as e:
            print(f"Quiz error: {e}")
            if self.voice_nav_active:
                self.audio.speak("Error loading quiz. Please try again.")
    
    def ask_question(self):
        if self.quiz_index >= len(self.current_quiz):
            self.show_results()
            return
        
        q = self.current_quiz[self.quiz_index]
        
        html = f"""
        <div style='padding: 10px;'>
            <h3 style='color: #e74c3c;'>❓ Question {self.quiz_index + 1} of {len(self.current_quiz)}</h3>
            <p style='font-size: 22px; font-weight: bold; margin: 20px 0;'>{q['question']}</p>
            <ul style='font-size: 20px; line-height: 2.2; list-style: none;'>
                <li><strong style='color: #e74c3c;'>A.</strong> {q['option_a']}</li>
                <li><strong style='color: #e74c3c;'>B.</strong> {q['option_b']}</li>
                <li><strong style='color: #e74c3c;'>C.</strong> {q['option_c']}</li>
                <li><strong style='color: #e74c3c;'>D.</strong> {q['option_d']}</li>
            </ul>
            <p style='font-size: 16px; color: #7f8c8d; margin-top: 20px;'>{"Say A, B, C, or D to answer" if self.voice_nav_active else "Select an answer or use voice"}</p>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText(f"Question {self.quiz_index + 1}/{len(self.current_quiz)} - {'Say your answer (A, B, C, or D)' if self.voice_nav_active else 'Ready for answer'}")
        QApplication.processEvents()
        
        if self.voice_nav_active:
            self.audio.speak(f"Question {self.quiz_index + 1}.")
            self.audio.speak(q['question'])
            self.audio.speak(f"Option A: {q['option_a']}")
            self.audio.speak(f"Option B: {q['option_b']}")
            self.audio.speak(f"Option C: {q['option_c']}")
            self.audio.speak(f"Option D: {q['option_d']}")
            self.audio.speak("Say A, B, C, or D to answer")

    def check_answer(self, answer):
        if not self.current_quiz or self.quiz_index >= len(self.current_quiz):
            return
            
        q = self.current_quiz[self.quiz_index]
        correct = q['correct_answer'].upper()
        
        answer = answer.upper()
        
        if answer == correct:
            self.score += 1
            if self.voice_nav_active:
                self.audio.speak(f"Correct! The answer is {correct}.")
            self.status.setText(f"✅ Correct! Score: {self.score}/{self.quiz_index + 1}")
        else:
            correct_text = q[f'option_{correct.lower()}']
            if self.voice_nav_active:
                self.audio.speak(f"Incorrect. The correct answer is {correct}: {correct_text}")
            self.status.setText(f"❌ Incorrect. Correct answer: {correct}")
        
        time.sleep(0.1 if self.voice_nav_active else 0)
        self.quiz_index += 1
        
        if self.quiz_index < len(self.current_quiz):
            if self.voice_nav_active:
                self.audio.speak("Next question.")
                time.sleep(0.1)
        
        self.ask_question()

    def show_results(self):
        total = len(self.current_quiz)
        percent = (self.score / total) * 100
        passed = percent >= 70
        
        html = f"""
        <div style='text-align: center; padding: 30px;'>
            <h1 style='color: {'#2ecc71' if passed else '#e74c3c'};'>🎯 Quiz Completed!</h1>
            <h2 style='margin: 20px 0;'>Score: {self.score} out of {total}</h2>
            <h2 style='margin: 20px 0;'>Percentage: {percent:.0f}%</h2>
            <h3 style='color: {'#2ecc71' if passed else '#e74c3c'}; font-size: 28px;'>
                {'✅ YOU PASSED!' if passed else '❌ PLEASE TRY AGAIN'}
            </h3>
            <p style='font-size: 16px; margin-top: 30px;'>{"Say 'take quiz' to try again or 'start lesson' to review" if self.voice_nav_active else "Click buttons to continue"}</p>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText(f"Quiz Complete: {self.score}/{total} ({percent:.0f}%)")
        
        if self.voice_nav_active:
            self.audio.speak(f"Quiz complete! You scored {self.score} out of {total}. That is {percent:.0f} percent.")
            time.sleep(0.1)
            
            if passed:
                self.audio.speak("Congratulations! You passed the quiz!")
            else:
                self.audio.speak("Please review the lesson and try again.")
        
        # Save progress
        try:
            lesson_id = self.current_lesson['id']
            self.storage.save_progress(lesson_id, self.score, total)
        except:
            pass

    def toggle_voice_navigation(self, state):
        is_checked = (state == Qt.CheckState.Checked.value or state == True)
        
        if is_checked:
            self.voice_nav_active = True
            
            if not hasattr(self, 'command_timer'):
                self.command_timer = QTimer()
                self.command_timer.timeout.connect(self.process_voice_commands)
            
            self.start_voice_navigation() 
            self.command_timer.start(100)  # Check every 100ms
            
            self.voice_indicator.setText("🎤 VOICE: ACTIVE - Listening for commands...")
            self.voice_indicator.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px; background: #2ecc71; color: white; border-radius: 10px;")
            self.audio.speak("Hello Student")
        else:
            self.voice_nav_active = False
            
            if hasattr(self, 'command_timer') and self.command_timer.isActive():
                self.command_timer.stop()
            
            self.voice_indicator.setText("🎤 VOICE: INACTIVE")
            self.voice_indicator.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px; background: #95a5a6; color: white; border-radius: 10px;")
            self.audio.speak("Voice commands deactivated")

    def start_voice_navigation(self):
        """Start continuous voice recognition with Qmeta AI processing"""
        def _listen():
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 4000
            recognizer.dynamic_energy_threshold = True
            
            while self.voice_nav_active:
                try:
                    with sr.Microphone() as source:
                        if not self.is_listening:
                            self.is_listening = True
                            print("🎤 Listening...")
                        
                        recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        
                        try:
                            command_text = recognizer.recognize_google(audio)
                            print(f"🗣️ Heard: {command_text}")
                            
                            # Process with Qmeta AI
                            intent = QmetaVoiceProcessor.get_intent(command_text)
                            self.command_queue.put(intent)
                            
                        except sr.UnknownValueError:
                            pass  # Couldn't understand, keep listening
                        except sr.RequestError as e:
                            print(f"Recognition error: {e}")
                            
                except sr.WaitTimeoutError:
                    pass  # No speech detected, continue
                except Exception as e:
                    print(f"Listen error: {e}")
                    time.sleep(0.1)
                
                time.sleep(0.1)
            
            self.is_listening = False
    
        threading.Thread(target=_listen, daemon=True).start()

    def process_voice_commands(self):
        """Process commands from the queue using Qmeta AI intents"""
        try:
            while not self.command_queue.empty():
                intent = self.command_queue.get_nowait()
                
                print(f"📋 Processing intent: {intent}")
                
                command = intent.get('intent')
                
                # Update voice indicator
                self.voice_indicator.setText(f"🎤 Command: {intent.get('original_command', 'Processing...')}")
                QApplication.processEvents()
                
                # Route commands
                if command == "load_subjects":
                    self.load_subjects()
                    
                elif command == "select_subject":
                    if intent.get('subject_number'):
                        self.select_subject_by_number(intent['subject_number'])
                    elif intent.get('subject'):
                        self.select_subject_by_name(intent['subject'])
                    else:
                        self.audio.speak("Please specify a subject name or number")
                        
                elif command == "start_lesson":
                    self.play_lesson()
                    
                elif command == "take_quiz":
                    self.start_quiz()
                    
                elif command == "answer_question":
                    if intent.get('answer'):
                        self.check_answer(intent['answer'])
                    else:
                        self.audio.speak("Please say A, B, C, or D")
                        
                elif command == "pause_audio":
                    self.audio.pause()
                    self.audio.speak("Paused")
                    
                elif command == "resume_audio":
                    self.audio.resume()
                    self.audio.speak("Resumed")
                    
                elif command == "stop_audio":
                    self.audio.stop()
                    self.audio.speak("Stopped")
                    
                elif command == "repeat_content":
                    self.audio.repeat_last()
                    
                elif command == "next_question":
                    if self.current_quiz and self.quiz_index < len(self.current_quiz):
                        self.audio.speak("Please answer the current question first")
                    else:
                        self.audio.speak("No active quiz")
                        
                elif command == "help":
                    self.show_voice_help()
                    
                elif command == "increase_speed":
                    current_value = self.speed_slider.value()
                    self.speed_slider.setValue(min(20, current_value + 2))
                    self.audio.speak(f"Speed increased to {self.speed_label.text()}")
                    
                elif command == "decrease_speed":
                    current_value = self.speed_slider.value()
                    self.speed_slider.setValue(max(5, current_value - 2))
                    self.audio.speak(f"Speed decreased to {self.speed_label.text()}")
                    
                elif command == "toggle_mode":
                    self.online_checkbox.setChecked(not self.online_mode)
                    
                elif command == "exit_app":
                    self.audio.speak("Goodbye!")
                    time.sleep(0.5)
                    self.close()
                    
                else:
                    self.audio.speak("Command not recognized. Try Again.")
                
                # Reset indicator after 2 seconds
                QTimer.singleShot(2000, lambda: self.voice_indicator.setText("🎤 VOICE: ACTIVE - Listening for commands..."))
                
        except Exception as e:
            print(f"Command processing error: {e}")

    def show_voice_help(self):
        """Show and speak voice command help"""
        help_text = """
        Voice Commands Available:
        
        Navigation:
        Say 'load subjects' to load all subjects.
        Say 'select' followed by subject name or number, for example, select math, or select subject 1.
        Say 'start lesson' to begin the current lesson.
        Say 'take quiz' to start the quiz.
        
        Quiz:
        Say 'A', 'B', 'C', or 'D' to answer questions.
        Say 'repeat' to hear the last content again.
        
        Playback:
        Say 'pause' to pause audio.
        Say 'resume' to continue audio.
        Say 'stop' to stop audio.
        Say 'faster' or 'slower' to adjust speed.
        
        General:
        Say 'help' for this message.
        Say 'online mode' or 'offline mode' to switch.
        Say 'exit' to close the application.
        """
        
        html = f"""
        <div style='padding: 20px; background: #ecf0f1; border-radius: 10px;'>
            <h2 style='color: #2c3e50; text-align: center;'>🎤 Voice Commands Help</h2>
            <div style='font-size: 16px; line-height: 1.8;'>
                <h3 style='color: #3498db;'>📍 Navigation:</h3>
                <ul>
                    <li>Say <strong>"load subjects"</strong> to load all subjects</li>
                    <li>Say <strong>"select math"</strong> or <strong>"select subject 1"</strong></li>
                    <li>Say <strong>"start lesson"</strong> to begin</li>
                    <li>Say <strong>"take quiz"</strong> to start quiz</li>
                </ul>
                
                <h3 style='color: #e74c3c;'>❓ Quiz:</h3>
                <ul>
                    <li>Say <strong>"A"</strong>, <strong>"B"</strong>, <strong>"C"</strong>, or <strong>"D"</strong> to answer</li>
                    <li>Say <strong>"repeat"</strong> to hear again</li>
                </ul>
                
                <h3 style='color: #f39c12;'>🎚️ Playback:</h3>
                <ul>
                    <li>Say <strong>"pause"</strong>, <strong>"resume"</strong>, <strong>"stop"</strong></li>
                    <li>Say <strong>"faster"</strong> or <strong>"slower"</strong></li>
                </ul>
                
                <h3 style='color: #9b59b6;'>⚙️ General:</h3>
                <ul>
                    <li>Say <strong>"help"</strong> for this message</li>
                    <li>Say <strong>"exit"</strong> to close app</li>
                </ul>
            </div>
        </div>
        """
        
        self.display.setHtml(html)
        self.status.setText("📖 Showing voice commands help")
        
        # Speak the help text only if voice is active
        if self.voice_nav_active:
            self.audio.speak(help_text)

    def closeEvent(self, event):
        """Clean shutdown"""
        self.voice_nav_active = False
        self.audio.queue.put(None)
        self.storage.conn.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style for better visibility
    app.setStyle('Fusion')
    
    window = StudentApp()
    window.show()
    sys.exit(app.exec())