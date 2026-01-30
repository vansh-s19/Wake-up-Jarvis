import pyttsx3
import cv2
import easyocr
import requests
import time

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"   # or mistral, phi3, etc

reader = easyocr.Reader(['en'])
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Jarvis Vision + Ollama started")
print("Press Q to quit")

last_sent = ""
last_ocr_time = 0
OCR_INTERVAL = 2  # seconds
detected_text = ""

def ask_ollama(text):
    prompt = f"""
You are Jarvis, an AI vision assistant.
The following text was read from my camera:

{text}

Explain what this means in simple words.
"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    r = requests.post(OLLAMA_URL, json=payload)
    return r.json()["response"]

while True:
    ret, frame = cap.read()
    if not ret:
        break

    current_time = time.time()
    if current_time - last_ocr_time > OCR_INTERVAL:
        results = reader.readtext(frame)
        detected_text = " ".join([text for (_, text, _) in results])
        last_ocr_time = current_time

    # Draw boxes
    for (bbox, text, conf) in results:
        (tl, tr, br, bl) = bbox
        tl = tuple(map(int, tl))
        br = tuple(map(int, br))
        cv2.rectangle(frame, tl, br, (0,255,0), 2)
        cv2.putText(frame, text, tl, cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, (0,0,255), 2)

    cv2.imshow("Jarvis Vision", frame)

    # Send to Ollama only if new text
    if detected_text and detected_text != last_sent and len(detected_text) > 10:
        print("\n[OCR]", detected_text)
        reply = ask_ollama(detected_text)
        print("[Jarvis]", reply)
        speak(reply)
        last_sent = detected_text

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()