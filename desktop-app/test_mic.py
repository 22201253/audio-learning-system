import speech_recognition as sr

print("Testing microphone...")

recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("🎤 Say something now!")
    recognizer.adjust_for_ambient_noise(source, duration=1)
    audio = recognizer.listen(source, timeout=10)
    
    try:
        text = recognizer.recognize_google(audio)
        print(f"✅ You said: {text}")
    except Exception as e:
        print(f"❌ Error: {e}")