import pvporcupine
import pyaudio
import struct
import time
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import subprocess

import os
import requests

# ---------------- CONFIG ----------------

PICOVOICE_KEY = "JPh9LWVN+Qk3mzYIQm/hvv3gJdp0ueUp17gQbkmOH09RSdnAyX3XRw=="

WAKE_WORD = "jarvis"
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"

SYSTEM_PROMPT = """
You are Jarvis, an advanced AI assistant inspired by Iron Man.
You speak formally, politely, and concisely.
You address the user as "Vansh".
You are helpful, intelligent, and slightly witty.
"""

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1"

# ----------------------------------------

def speak(text):
    print("Jarvis:", text)
    subprocess.run(["say", text])


# ---------- WAKE WORD ----------

def wait_for_wake_word():
    porcupine = pvporcupine.create(
        access_key=PICOVOICE_KEY,
        keywords=[WAKE_WORD]
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("Listening for 'Jarvis'...")

    while True:
        try:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                break
        except Exception:
            pass

    stream.stop_stream()
    stream.close()
    pa.terminate()
    porcupine.delete()


# ---------- SPEECH TO TEXT ----------

def listen(timeout=10):
    model = Model(VOSK_MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)

    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    print("Listening...")
    start_time = time.time()

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback
    ):
        while True:
            if time.time() - start_time > timeout:
                return "I did not hear anything."

            if not q.empty():
                data = q.get()
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text.strip():
                        return text


# ---------- OLLAMA BRAIN ----------

def ask_gpt(user_text, history):
    try:
        prompt = SYSTEM_PROMPT + "\n"

        for msg in history:
            if msg["role"] == "user":
                prompt += f"User: {msg['content']}\n"
            else:
                prompt += f"Jarvis: {msg['content']}\n"

        prompt += f"User: {user_text}\nJarvis:"

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(OLLAMA_URL, json=payload)
        return response.json()["response"]

    except Exception as e:
        print("Ollama error:", e)
        return "I'm having trouble reaching my local AI brain, Vansh."


# ---------- MAIN LOOP ----------

def main():
    conversation_history = []

    speak("Jarvis online. Awaiting your call, Vansh.")

    while True:
        wait_for_wake_word()
        speak("Yes Vansh, how may I assist you?")

        user_text = listen()
        print("You:", user_text)

        if "open camera" in user_text.lower() or "vision" in user_text.lower():
            speak("Opening vision mode.")
            subprocess.run(["python3", "vision_ollama.py"])
            continue

        conversation_history.append(
            {"role": "user", "content": user_text}
        )

        ai_text = ask_gpt(user_text, conversation_history)
        conversation_history.append(
            {"role": "assistant", "content": ai_text}
        )

        speak(ai_text)
        time.sleep(1)


if __name__ == "__main__":
    main()