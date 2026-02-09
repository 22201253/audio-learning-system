"""
COMPLETE DYNAMIC ADMIN DASHBOARD
Features: Login/Logout, Register Teachers/Students, CRUD for Subjects/Lessons/Quizzes
Integrated with your backend at localhost:8001
"""

import reflex as rx
import httpx
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

API_URL = "https://audio-learning-system.onrender.com"

# ===================== MODELS =====================
class Subject(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    id: int
    name: str
    description: str = ""
    teacher_id: int = 0


class Lesson(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    id: int
    title: str
    content: str
    topic_id: int
    duration: str = "15 min"


class Quiz(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    id: int
    lesson_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str


class Student(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    id: int
    username: str
    email: str
    first_name: str
    surname: str = ""
    role: str


# ===================== STATE =====================

class State(rx.State):
    # Auth
    is_authenticated: bool = False
    current_user: dict = {}
    token: str = ""
    
    # UI State
    message: str = ""
    message_type: str = "info"  # info, success, error
    show_register: bool = False
    active_tab: str = "subjects"
    
    # Login Form
    login_username: str = ""
    login_password: str = ""
    
    # Register Form
    reg_first_name: str = ""
    reg_surname: str = ""
    reg_email: str = ""
    reg_username: str = ""
    reg_password: str = ""
    reg_role: str = "student"
    
    # Data
    subjects: List[Subject] = []
    lessons: List[Lesson] = []
    quizzes: List[Quiz] = []
    students: List[Student] = []
    
    # Subject Form
    subj_name: str = ""
    subj_desc: str = ""
    
    # Lesson Form
    lesson_subject_id: str = ""
    lesson_title: str = ""
    lesson_content: str = ""
    lesson_duration: str = "15 min"
    
    # Quiz Form
    quiz_lesson_id: str = ""
    quiz_question: str = ""
    quiz_a: str = ""
    quiz_b: str = ""
    quiz_c: str = ""
    quiz_d: str = ""
    quiz_correct: str = "A"
    
    # Stats
    total_subjects: int = 0
    total_lessons: int = 0
    total_quizzes: int = 0
    total_students: int = 0

    # ============ HELPER METHODS ============
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def set_message(self, msg: str, msg_type: str = "info"):
        self.message = msg
        self.message_type = msg_type
    
    def switch_tab(self, tab: str):
        self.active_tab = tab

    # ============ AUTHENTICATION ============
    
    async def login(self):
        if not self.login_username or not self.login_password:
            self.set_message("Please enter username and password", "error")
            return
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{API_URL}/auth/login",
                    json={
                        "username": self.login_username,
                        "password": self.login_password
                    },
                    timeout=10
                )
                
                if res.status_code == 200:
                    data = res.json()
                    self.token = data.get("access_token", "")
                    self.current_user = data.get("user", {})
                    
                    if self.current_user.get("role") == "teacher":
                        self.is_authenticated = True
                        self.set_message(f"Welcome, {self.current_user.get('first_name')}!", "success")
                        await self.load_all_data()
                    else:
                        self.set_message("Teacher access only", "error")
                else:
                    self.set_message("Invalid credentials", "error")
            except Exception as e:
                self.set_message(f"Login error: {str(e)}", "error")
    
    def logout(self):
        self.is_authenticated = False
        self.token = ""
        self.current_user = {}
        self.login_username = ""
        self.login_password = ""
        self.set_message("Logged out successfully", "info")
    
    async def register_user(self):
        if not all([self.reg_first_name, self.reg_username, self.reg_email, self.reg_password]):
            self.set_message("All fields required", "error")
            return
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{API_URL}/auth/register",
                    json={
                        "first_name": self.reg_first_name,
                        "surname": self.reg_surname,
                        "email": self.reg_email,
                        "username": self.reg_username,
                        "password": self.reg_password,
                        "role": self.reg_role
                    },
                    timeout=10
                )
                
                if res.status_code == 201:
                    self.set_message(f"✅ {self.reg_role.capitalize()} registered!", "success")
                    self.reg_first_name = ""
                    self.reg_surname = ""
                    self.reg_email = ""
                    self.reg_username = ""
                    self.reg_password = ""
                    self.show_register = False
                    await self.load_students()
                else:
                    error = res.json().get("detail", "Registration failed")
                    self.set_message(f"❌ {error}", "error")
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")

    # ============ DATA LOADING ============
    
    async def load_all_data(self):
        await self.load_subjects()
        await self.load_lessons()
        await self.load_quizzes()
        await self.load_students()
        self.update_stats()
    
    async def load_subjects(self):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{API_URL}/lessons/subjects", timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    self.subjects = [Subject(**item) for item in data]
            except Exception as e:
                print(f"Error loading subjects: {e}")
    
    async def load_lessons(self):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{API_URL}/lessons/", timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    self.lessons = [Lesson(**item) for item in data]
            except Exception as e:
                print(f"Error loading lessons: {e}")
    
    async def load_quizzes(self):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{API_URL}/quizzes/", timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    self.quizzes = [Quiz(**item) for item in data]
            except Exception as e:
                print(f"Error loading quizzes: {e}")
    
    async def load_students(self):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(
                    f"{API_URL}/auth/users?role=student",
                    headers=self.get_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    data = res.json()
                    self.students = [Student(**item) for item in data]
            except Exception as e:
                print(f"Error loading students: {e}")
    
    def update_stats(self):
        self.total_subjects = len(self.subjects)
        self.total_lessons = len(self.lessons)
        self.total_quizzes = len(self.quizzes)
        self.total_students = len(self.students)

    # ============ CREATE OPERATIONS ============
    
    async def create_subject(self):
        if not self.subj_name:
            self.set_message("Subject name required", "error")
            return
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{API_URL}/lessons/subjects",
                    json={"name": self.subj_name, "description": self.subj_desc},
                    headers=self.get_headers(),
                    timeout=10
                )
                
                if res.status_code == 201:
                    self.set_message(f"✅ Subject '{self.subj_name}' created!", "success")
                    self.subj_name = ""
                    self.subj_desc = ""
                    await self.load_subjects()
                    self.update_stats()
                else:
                    self.set_message("Failed to create subject", "error")
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")
    
    async def create_lesson(self):
        if not all([self.lesson_subject_id, self.lesson_title, self.lesson_content]):
            self.set_message("All lesson fields required", "error")
            return
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{API_URL}/lessons/",
                    json={
                        "topic_id": int(self.lesson_subject_id),
                        "title": self.lesson_title,
                        "content": self.lesson_content,
                        "duration": self.lesson_duration,
                        "order": 1
                    },
                    headers=self.get_headers(),
                    timeout=10
                )
                
                if res.status_code == 201:
                    self.set_message(f"✅ Lesson '{self.lesson_title}' created!", "success")
                    self.lesson_subject_id = ""
                    self.lesson_title = ""
                    self.lesson_content = ""
                    await self.load_lessons()
                    self.update_stats()
                else:
                    self.set_message("Failed to create lesson", "error")
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")
    
    async def create_quiz(self):
        if not all([self.quiz_lesson_id, self.quiz_question, self.quiz_a, 
                   self.quiz_b, self.quiz_c, self.quiz_d, self.quiz_correct]):
            self.set_message("All quiz fields required", "error")
            return
        
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{API_URL}/quizzes/",
                    json={
                        "lesson_id": int(self.quiz_lesson_id),
                        "question": self.quiz_question,
                        "option_a": self.quiz_a,
                        "option_b": self.quiz_b,
                        "option_c": self.quiz_c,
                        "option_d": self.quiz_d,
                        "correct_answer": self.quiz_correct
                    },
                    headers=self.get_headers(),
                    timeout=10
                )
                
                if res.status_code == 201:
                    self.set_message("✅ Quiz question created!", "success")
                    self.quiz_lesson_id = ""
                    self.quiz_question = ""
                    self.quiz_a = ""
                    self.quiz_b = ""
                    self.quiz_c = ""
                    self.quiz_d = ""
                    self.quiz_correct = "A"
                    await self.load_quizzes()
                    self.update_stats()
                else:
                    self.set_message("Failed to create quiz", "error")
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")

    # ============ DELETE OPERATIONS ============
    
    async def delete_subject(self, subject_id: int):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.delete(
                    f"{API_URL}/lessons/subjects/{subject_id}",
                    headers=self.get_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    self.set_message("🗑️ Subject deleted", "success")
                    await self.load_subjects()
                    self.update_stats()
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")
    
    async def delete_lesson(self, lesson_id: int):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.delete(
                    f"{API_URL}/lessons/{lesson_id}",
                    headers=self.get_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    self.set_message("🗑️ Lesson deleted", "success")
                    await self.load_lessons()
                    self.update_stats()
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")
    
    async def delete_quiz(self, quiz_id: int):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.delete(
                    f"{API_URL}/quizzes/{quiz_id}",
                    headers=self.get_headers(),
                    timeout=10
                )
                if res.status_code == 200:
                    self.set_message("🗑️ Quiz deleted", "success")
                    await self.load_quizzes()
                    self.update_stats()
            except Exception as e:
                self.set_message(f"Error: {str(e)}", "error")


# ===================== UI COMPONENTS =====================

def login_page():
    """Login page"""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("🎓 Admin Login", size="8", color="#667eea"),
                
                rx.cond(
                    ~State.show_register,
                    # Login Form
                    rx.vstack(
                        rx.input(
                            placeholder="Username",
                            on_change=State.set_login_username,
                            value=State.login_username,
                            width="100%"
                        ),
                        rx.input(
                            placeholder="Password",
                            type="password",
                            on_change=State.set_login_password,
                            value=State.login_password,
                            width="100%"
                        ),
                        rx.button(
                            "Login",
                            on_click=State.login,
                            color_scheme="blue",
                            width="100%",
                            size="3"
                        ),
                        rx.text(
                            "Need an account? ",
                            rx.text(
                                "Register here",
                                color="blue",
                                cursor="pointer",
                                on_click=State.set_show_register(True)
                            )
                        ),
                        spacing="4",
                        width="100%"
                    ),
                    
                    # Register Form
                    rx.vstack(
                        rx.heading("Register New Account", size="5"),
                        rx.input(
                            placeholder="First Name",
                            on_change=State.set_reg_first_name,
                            value=State.reg_first_name,
                            width="100%"
                        ),
                        rx.input(
                            placeholder="Surname (optional)",
                            on_change=State.set_reg_surname,
                            value=State.reg_surname,
                            width="100%"
                        ),
                        rx.input(
                            placeholder="Email",
                            on_change=State.set_reg_email,
                            value=State.reg_email,
                            width="100%"
                        ),
                        rx.input(
                            placeholder="Username",
                            on_change=State.set_reg_username,
                            value=State.reg_username,
                            width="100%"
                        ),
                        rx.input(
                            placeholder="Password",
                            type="password",
                            on_change=State.set_reg_password,
                            value=State.reg_password,
                            width="100%"
                        ),
                        rx.select(
                            ["student", "teacher"],
                            placeholder="Role",
                            on_change=State.set_reg_role,
                            value=State.reg_role,
                            width="100%"
                        ),
                        rx.button(
                            "Register",
                            on_click=State.register_user,
                            color_scheme="green",
                            width="100%",
                            size="3"
                        ),
                        rx.text(
                            "Already have an account? ",
                            rx.text(
                                "Login here",
                                color="blue",
                                cursor="pointer",
                                on_click=State.set_show_register(False)
                            )
                        ),
                        spacing="4",
                        width="100%"
                    )
                ),
                
                # Message Display
                rx.cond(
                    State.message != "",
                    rx.callout(
                        State.message,
                        icon="info",
                        color_scheme=rx.cond(
                            State.message_type == "error",
                            "red",
                            rx.cond(State.message_type == "success", "green", "blue")
                        ),
                        width="100%"
                    )
                ),
                
                rx.divider(),
                rx.text("Test: teacher1 / password123", size="2", color="gray"),
                
                spacing="5",
                width="100%"
            ),
            width="450px",
            padding="2em"
        ),
        height="100vh",
        background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    )


def stats_cards():
    """Dashboard statistics"""
    return rx.grid(
        rx.card(
            rx.vstack(
                rx.heading(State.total_subjects, size="8"),
                rx.text("Subjects", size="3"),
                align="center"
            ),
            bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color="white"
        ),
        rx.card(
            rx.vstack(
                rx.heading(State.total_lessons, size="8"),
                rx.text("Lessons", size="3"),
                align="center"
            ),
            bg="linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)",
            color="white"
        ),
        rx.card(
            rx.vstack(
                rx.heading(State.total_quizzes, size="8"),
                rx.text("Quizzes", size="3"),
                align="center"
            ),
            bg="linear-gradient(135deg, #f39c12 0%, #e67e22 100%)",
            color="white"
        ),
        rx.card(
            rx.vstack(
                rx.heading(State.total_students, size="8"),
                rx.text("Students", size="3"),
                align="center"
            ),
            bg="linear-gradient(135deg, #3498db 0%, #2980b9 100%)",
            color="white"
        ),
        columns="4",
        spacing="4",
        width="100%"
    )


def subjects_tab():
    """Subjects management"""
    return rx.vstack(
        rx.heading("📚 Subjects", size="6"),
        
        # Create Subject Form
        rx.card(
            rx.vstack(
                rx.heading("Create Subject", size="4"),
                rx.input(
                    placeholder="Subject Name",
                    on_change=State.set_subj_name,
                    value=State.subj_name,
                    width="100%"
                ),
                rx.text_area(
                    placeholder="Description (optional)",
                    on_change=State.set_subj_desc,
                    value=State.subj_desc,
                    width="100%",
                    rows="2"
                ),
                rx.button(
                    "Create Subject",
                    on_click=State.create_subject,
                    color_scheme="blue",
                    width="100%"
                ),
                spacing="3",
                width="100%"
            )
        ),
        
        rx.divider(),
        
        # Subjects List
        rx.cond(
            State.subjects.length() > 0,
            rx.grid(
                rx.foreach(
                    State.subjects,
                    lambda s: rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text(s.name, weight="bold", size="4"),
                                rx.spacer(),
                                rx.badge(f"ID: {s.id}")
                            ),
                            rx.text(s.description, color="gray", size="2"),
                            rx.button(
                                "Delete",
                                on_click=lambda: State.delete_subject(s.id),
                                color_scheme="red",
                                size="1"
                            ),
                            spacing="2"
                        )
                    )
                ),
                columns="3",
                spacing="3",
                width="100%"
            ),
            rx.text("No subjects yet", color="gray")
        ),
        
        spacing="4",
        width="100%"
    )


def lessons_tab():
    """Lessons management"""
    return rx.vstack(
        rx.heading("📖 Lessons", size="6"),
        
        # Create Lesson Form
        rx.card(
            rx.vstack(
                rx.heading("Create Lesson", size="4"),
                rx.input(
                    placeholder="Subject ID (e.g., 1)",
                    on_change=State.set_lesson_subject_id,
                    value=State.lesson_subject_id,
                    width="100%"
                ),
                rx.input(
                    placeholder="Lesson Title",
                    on_change=State.set_lesson_title,
                    value=State.lesson_title,
                    width="100%"
                ),
                rx.text_area(
                    placeholder="Lesson Content",
                    on_change=State.set_lesson_content,
                    value=State.lesson_content,
                    width="100%",
                    rows="4"
                ),
                rx.input(
                    placeholder="Duration (e.g., 15 min)",
                    on_change=State.set_lesson_duration,
                    value=State.lesson_duration,
                    width="100%"
                ),
                rx.button(
                    "Create Lesson",
                    on_click=State.create_lesson,
                    color_scheme="green",
                    width="100%"
                ),
                spacing="3",
                width="100%"
            )
        ),
        
        rx.divider(),
        
        # Lessons List
        rx.cond(
            State.lessons.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.lessons,
                    lambda l: rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.heading(l.title, size="4"),
                                rx.spacer(),
                                rx.badge(f"Subject: {l.topic_id}")
                            ),
                            rx.text(l.content[:100] + "...", color="gray", size="2"),
                            rx.text(f"⏱️ {l.duration}", size="2"),
                            rx.button(
                                "Delete",
                                on_click=lambda: State.delete_lesson(l.id),
                                color_scheme="red",
                                size="1"
                            ),
                            spacing="2"
                        )
                    )
                ),
                spacing="3",
                width="100%"
            ),
            rx.text("No lessons yet", color="gray")
        ),
        
        spacing="4",
        width="100%"
    )


def quizzes_tab():
    """Quizzes management"""
    return rx.vstack(
        rx.heading("❓ Quizzes", size="6"),
        
        # Create Quiz Form
        rx.card(
            rx.vstack(
                rx.heading("Create Quiz Question", size="4"),
                rx.input(
                    placeholder="Lesson ID (e.g., 1)",
                    on_change=State.set_quiz_lesson_id,
                    value=State.quiz_lesson_id,
                    width="100%"
                ),
                rx.text_area(
                    placeholder="Question",
                    on_change=State.set_quiz_question,
                    value=State.quiz_question,
                    width="100%",
                    rows="2"
                ),
                rx.grid(
                    rx.input(placeholder="Option A", on_change=State.set_quiz_a, value=State.quiz_a),
                    rx.input(placeholder="Option B", on_change=State.set_quiz_b, value=State.quiz_b),
                    rx.input(placeholder="Option C", on_change=State.set_quiz_c, value=State.quiz_c),
                    rx.input(placeholder="Option D", on_change=State.set_quiz_d, value=State.quiz_d),
                    columns="2",
                    spacing="2"
                ),
                rx.select(
                    ["A", "B", "C", "D"],
                    placeholder="Correct Answer",
                    on_change=State.set_quiz_correct,
                    value=State.quiz_correct,
                    width="100%"
                ),
                rx.button(
                    "Create Quiz",
                    on_click=State.create_quiz,
                    color_scheme="orange",
                    width="100%"
                ),
                spacing="3",
                width="100%"
            )
        ),
        
        rx.divider(),
        
        # Quizzes List
        rx.cond(
            State.quizzes.length() > 0,
            rx.vstack(
                rx.foreach(
                    State.quizzes,
                    lambda q: rx.card(
                        rx.vstack(
                            rx.text(q.question, weight="bold"),
                            rx.grid(
                                rx.text(f"A: {q.option_a}", size="2"),
                                rx.text(f"B: {q.option_b}", size="2"),
                                rx.text(f"C: {q.option_c}", size="2"),
                                rx.text(f"D: {q.option_d}", size="2"),
                                columns="2",
                                spacing="2"
                            ),
                            rx.hstack(
                                rx.badge(f"✓ {q.correct_answer}", color_scheme="green"),
                                rx.spacer(),
                                rx.button(
                                    "Delete",
                                    on_click=lambda: State.delete_quiz(q.id),
                                    color_scheme="red",
                                    size="1"
                                )
                            ),
                            spacing="2"
                        ),
                        bg="#fff9e6"
                    )
                ),
                spacing="3",
                width="100%"
            ),
            rx.text("No quizzes yet", color="gray")
        ),
        
        spacing="4",
        width="100%"
    )


def students_tab():
    """Students management"""
    return rx.vstack(
        rx.heading("👥 Students", size="6"),
        
        # Register Student Form
        rx.card(
            rx.vstack(
                rx.heading("Register New Student", size="4"),
                rx.grid(
                    rx.input(
                        placeholder="First Name",
                        on_change=State.set_reg_first_name,
                        value=State.reg_first_name
                    ),
                    rx.input(
                        placeholder="Surname",
                        on_change=State.set_reg_surname,
                        value=State.reg_surname
                    ),
                    columns="2",
                    spacing="2"
                ),
                rx.input(
                    placeholder="Email",
                    on_change=State.set_reg_email,
                    value=State.reg_email,
                    width="100%"
                ),
                rx.grid(
                    rx.input(
                        placeholder="Username",
                        on_change=State.set_reg_username,
                        value=State.reg_username
                    ),
                    rx.input(
                        placeholder="Password",
                        type="password",
                        on_change=State.set_reg_password,
                        value=State.reg_password
                    ),
                    columns="2",
                    spacing="2"
                ),
                rx.button(
                    "Register Student",
                    on_click=lambda: [State.set_reg_role("student"), State.register_user()],
                    color_scheme="purple",
                    width="100%"
                ),
                spacing="3",
                width="100%"
            )
        ),
        
        rx.divider(),
        
        # Students List
        rx.cond(
            State.students.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("ID"),
                        rx.table.column_header_cell("Name"),
                        rx.table.column_header_cell("Username"),
                        rx.table.column_header_cell("Email")
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        State.students,
                        lambda s: rx.table.row(
                            rx.table.cell(s.id),
                            rx.table.cell(f"{s.first_name} {s.surname}"),
                            rx.table.cell(s.username),
                            rx.table.cell(s.email)
                        )
                    )
                ),
                width="100%"
            ),
            rx.text("No students registered", color="gray")
        ),
        
        spacing="4",
        width="100%"
    )


def dashboard_page():
    """Main dashboard"""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading("🎓 Teacher Dashboard", size="8"),
            rx.spacer(),
            rx.button(
                "Logout",
                on_click=State.logout,
                color_scheme="red"
            ),
            width="100%",
            padding="20px",
            bg="white",
            border_radius="10px"
        ),
        
        # Message Display
        rx.cond(
            State.message != "",
            rx.callout(
                State.message,
                icon="info",
                color_scheme=rx.cond(
                    State.message_type == "error",
                    "red",
                    rx.cond(State.message_type == "success", "green", "blue")
                ),
                width="100%"
            )
        ),
        
        # Stats
        stats_cards(),
        
        # Tabs
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Subjects", value="subjects"),
                rx.tabs.trigger("Lessons", value="lessons"),
                rx.tabs.trigger("Quizzes", value="quizzes"),
                rx.tabs.trigger("Students", value="students")
            ),
            rx.tabs.content(subjects_tab(), value="subjects"),
            rx.tabs.content(lessons_tab(), value="lessons"),
            rx.tabs.content(quizzes_tab(), value="quizzes"),
            rx.tabs.content(students_tab(), value="students"),
            default_value="subjects",
            width="100%"
        ),
        
        spacing="4",
        padding="2em",
        width="100%",
        on_mount=State.load_all_data
    )


def index():
    """Main page with authentication"""
    return rx.cond(
        State.is_authenticated,
        dashboard_page(),
        login_page()
    )

# ===================== APP =====================

app = rx.App()
app.add_page(index, route="/", title="Admin Dashboard")