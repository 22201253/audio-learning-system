import reflex as rx
import httpx

API_URL = "http://localhost:8001"

class State(rx.State):
    username: str = ""
    password: str = ""
    is_logged_in: bool = False
    token: str = ""
    subjects_count: int = 0
    lessons_count: int = 0
    students_count: int = 0
    
    # Lesson creation
    lesson_title: str = ""
    lesson_content: str = ""
    
    # Quiz creation
    quiz_lesson_id: str = "1"
    quiz_question: str = ""
    quiz_option_a: str = ""
    quiz_option_b: str = ""
    quiz_option_c: str = ""
    quiz_option_d: str = ""
    quiz_correct: str = ""
    
    # Student progress
    students_progress: list = []
    show_progress: bool = False
    
    message: str = ""
    
    async def login(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/auth/login",
                    data={"username": self.username, "password": self.password}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.token = data["access_token"]
                    self.is_logged_in = True
                    await self.load_stats()
        except:
            self.message = "Cannot connect to backend!"
    
    def logout(self):
        self.is_logged_in = False
        self.token = ""
        self.show_progress = False
    
    async def load_stats(self):
        try:
            async with httpx.AsyncClient() as client:
                subjects = await client.get(f"{API_URL}/lessons/subjects")
                lessons = await client.get(f"{API_URL}/lessons/")
                students = await client.get(
                    f"{API_URL}/progress/all-students",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                
                if subjects.status_code == 200:
                    self.subjects_count = len(subjects.json())
                
                if lessons.status_code == 200:
                    self.lessons_count = len(lessons.json())
                
                if students.status_code == 200:
                    self.students_count = students.json()["total_students"]
        except:
            pass
    
    async def create_lesson(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/lessons/",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "topic_id": 1,
                        "title": self.lesson_title,
                        "content": self.lesson_content,
                        "duration_minutes": 15,
                        "order": 1,
                        "is_published": True
                    }
                )
                if response.status_code == 201:
                    self.message = "✅ Lesson created successfully!"
                    self.lesson_title = ""
                    self.lesson_content = ""
                    await self.load_stats()
        except:
            self.message = "❌ Error creating lesson!"
    
    async def create_quiz(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URL}/quizzes/",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "lesson_id": int(self.quiz_lesson_id),
                        "question": self.quiz_question,
                        "question_type": "multiple_choice",
                        "option_a": self.quiz_option_a,
                        "option_b": self.quiz_option_b,
                        "option_c": self.quiz_option_c,
                        "option_d": self.quiz_option_d,
                        "correct_answer": self.quiz_correct,
                        "explanation": "",
                        "order": 1
                    }
                )
                if response.status_code == 201:
                    self.message = "✅ Quiz created successfully!"
                    self.quiz_question = ""
                    self.quiz_option_a = ""
                    self.quiz_option_b = ""
                    self.quiz_option_c = ""
                    self.quiz_option_d = ""
                    self.quiz_correct = ""
        except:
            self.message = "❌ Error creating quiz!"
    
    async def load_students_progress(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_URL}/progress/all-students",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    self.students_progress = data.get("students", [])
                    self.show_progress = True
                    self.message = f"✅ Loaded progress for {len(self.students_progress)} students!"
        except:
            self.message = "❌ Error loading progress!"


def login_page():
    return rx.center(
        rx.vstack(
            rx.heading("🎓 Audio Learning System", size="9"),
            rx.heading("Teacher Dashboard", size="5", color="gray"),
            rx.input(placeholder="Username", on_change=State.set_username, width="300px"),
            rx.input(placeholder="Password", type="password", on_change=State.set_password, width="300px"),
            rx.button("Login", on_click=State.login, width="300px", size="3"),
            rx.text(State.message, color="red"),
            spacing="4"
        ),
        height="100vh"
    )


def dashboard():
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading("📚 Teacher Dashboard", size="8"),
            rx.spacer(),
            rx.button("Logout", on_click=State.logout, color_scheme="red"),
            width="100%",
            padding="20px"
        ),
        
        # Stats Cards
        rx.hstack(
            rx.card(rx.vstack(rx.heading(State.subjects_count, size="7"), rx.text("Subjects"), align="center")),
            rx.card(rx.vstack(rx.heading(State.lessons_count, size="7"), rx.text("Lessons"), align="center")),
            rx.card(rx.vstack(rx.heading(State.students_count, size="7"), rx.text("Students"), align="center")),
            spacing="4",
            width="100%"
        ),
        
        # Create Lesson Section
        rx.card(
            rx.vstack(
                rx.heading("📝 Create New Lesson", size="6"),
                rx.input(
                    placeholder="Lesson Title (e.g., Introduction to Fractions)",
                    on_change=State.set_lesson_title,
                    value=State.lesson_title,
                    width="100%"
                ),
                rx.text_area(
                    placeholder="Lesson Content (TTS will read this to students)...",
                    on_change=State.set_lesson_content,
                    value=State.lesson_content,
                    width="100%",
                    height="150px"
                ),
                rx.button("Create Lesson", on_click=State.create_lesson, width="100%", color_scheme="green"),
                spacing="3",
                width="100%"
            ),
            width="100%"
        ),
        
        # Create Quiz Section
        rx.card(
            rx.vstack(
                rx.heading("❓ Create Quiz Question", size="6"),
                rx.input(placeholder="Lesson ID (e.g., 1)", on_change=State.set_quiz_lesson_id, value=State.quiz_lesson_id, width="100%"),
                rx.input(placeholder="Question", on_change=State.set_quiz_question, value=State.quiz_question, width="100%"),
                rx.input(placeholder="Option A", on_change=State.set_quiz_option_a, value=State.quiz_option_a, width="100%"),
                rx.input(placeholder="Option B", on_change=State.set_quiz_option_b, value=State.quiz_option_b, width="100%"),
                rx.input(placeholder="Option C", on_change=State.set_quiz_option_c, value=State.quiz_option_c, width="100%"),
                rx.input(placeholder="Option D", on_change=State.set_quiz_option_d, value=State.quiz_option_d, width="100%"),
                rx.input(placeholder="Correct Answer (A, B, C, or D)", on_change=State.set_quiz_correct, value=State.quiz_correct, width="100%"),
                rx.button("Create Quiz", on_click=State.create_quiz, width="100%", color_scheme="blue"),
                spacing="3",
                width="100%"
            ),
            width="100%"
        ),
        
        # Student Progress Section
        rx.card(
            rx.vstack(
                rx.heading("📊 View Student Progress", size="6"),
                rx.button(
                    "Load Students Progress",
                    on_click=State.load_students_progress,
                    width="100%",
                    color_scheme="purple"
                ),
                rx.cond(
                    State.show_progress,
                    rx.vstack(
                        rx.heading(f"Total Students: {State.students_count}", size="4", color="blue"),
                        rx.divider(),
                        rx.text("Students enrolled in the system", size="2", color="gray"),
                        spacing="3",
                        width="100%"
                    )
                ),
                spacing="3",
                width="100%"
            ),
            width="100%"
        ),
        
        # Message
        rx.cond(
            State.message != "",
            rx.callout(State.message, size="2")
        ),
        
        spacing="5",
        padding="20px",
        width="100%",
        max_width="900px"
    )


def index():
    return rx.cond(State.is_logged_in, dashboard(), login_page())


app = rx.App()
app.add_page(index)
