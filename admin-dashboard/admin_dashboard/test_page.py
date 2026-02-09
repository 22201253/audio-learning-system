# In your admin-dashboard, create a simple test page
import reflex as rx

def test_page():
    return rx.text("Hello World - If you see this, Reflex works!")

app = rx.App()
app.add_page(test_page, route="/test")