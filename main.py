import queue
import sounddevice as sd
import vosk
import sys
import json
import datetime
import os
import glob
import google.generativeai as genai
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

# CONFIGURATION TO PUT YOUR API KEY OR CUSTOM MODEL

MODEL_PATH = "models/vosk-model-fr-0.22"
GEMINI_API_KEY = "PUT YOUR GEMINI API KEY HERE" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FOLDER = os.path.join(BASE_DIR, "recordings")
os.makedirs(SAVE_FOLDER, exist_ok=True)


if not os.path.exists(MODEL_PATH):
    messagebox.showerror("Error", f"Model not found at {MODEL_PATH}")
    sys.exit(1)


timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
transcript_path = os.path.join(SAVE_FOLDER, f"transcript_{timestamp}.md")
summary_path = os.path.join(SAVE_FOLDER, f"summary_{timestamp}.md")

q = queue.Queue()
model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, 16000)
recording = False
stream = None

def clean_text(text):
    text = text.strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if not text.endswith("."):
        text += "."
    return text

def audio_callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))


def get_latest_transcript():
    files = glob.glob(os.path.join(SAVE_FOLDER, "transcript_*.md"))
    if not files:
        return None
    return max(files, key=os.path.getctime)


genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

def summarize_with_gemini(file_path):
    with open(file_path, "r") as f:
        raw_text = f.read()
# YOU CAN CHANGE THE PROMPT TO YOUR NEEDS
    prompt = f"Summarize and organize this transcript into sections for me to study later in French, and after you finish translate it into Spanish:\n\n{raw_text}"
    response = gemini_model.generate_content(prompt)

    summary_text = response.text
    with open(summary_path, "w") as f:
        f.write(summary_text)

    return summary_text



def record_audio():
    global recording, stream
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while recording:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = clean_text(result.get("text", ""))
                if text:
                    transcript_box.insert(tk.END, f"{text}\n")
                    transcript_box.see(tk.END)
                    with open(transcript_path, "a") as f:
                        f.write(text + "\n\n")


def start_recording():
    global recording
    recording = True
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    threading.Thread(target=record_audio, daemon=True).start()

def stop_recording():
    global recording
    recording = False
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

    latest_file = get_latest_transcript()
    if latest_file:
        summary = summarize_with_gemini(latest_file)
        summary_box.delete(1.0, tk.END)
        summary_box.insert(tk.END, summary)
        summary_box.see(tk.END)
        messagebox.showinfo("Summary Saved", f"Summary saved to: {summary_path}")


# CHANGE THE WINDOW TITLE AND SIZE IF YOU WANT

root = tk.Tk()
root.title("Live Transcription")
root.geometry("900x700")

#Decided to leave this here so you can change the transparency of the window if you want
#root.attributes('-alpha', 0.9)  # 0.0 = fully transparent, 1.0 = fully opaque


# Transcript display
tk.Label(root, text=" Live Transcript:", font=("Arial", 14, "bold")).pack(anchor="w")
transcript_box = scrolledtext.ScrolledText(root, height=15, wrap=tk.WORD, font=("Arial", 12))
transcript_box.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

# Summary display
tk.Label(root, text=" AI Summary:", font=("Arial", 14, "bold")).pack(anchor="w")
summary_box = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD, font=("Arial", 12))
summary_box.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)

# Buttons
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)
start_button = tk.Button(btn_frame, text="Start Recording", command=start_recording, font=("Arial", 12), bg="green", fg="black")
start_button.pack(side=tk.LEFT, padx=10)
stop_button = tk.Button(btn_frame, text="Stop & Summarize", command=stop_recording, font=("Arial", 12), bg="red", fg="black")
stop_button.pack(side=tk.LEFT, padx=10)

root.mainloop()

