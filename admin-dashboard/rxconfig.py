import reflex as rx

config = rx.Config(
    app_name="admin_dashboard",

    # REQUIRED on Render
    host="0.0.0.0",
    port=8000,  # Render overrides with $PORT

    # Backend API (FastAPI service)
    backend_url="https://audio-learning-system.onrender.com",

    # Optional but OK
    deploy_url="https://audio-learning-admin.onrender.com",

    state_auto_setters=True,
)
