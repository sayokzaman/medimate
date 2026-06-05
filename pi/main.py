import os
import subprocess
import json
import wave
import pyaudio
import numpy as np
import ollama
from faster_whisper import WhisperModel
import openwakeword
from openwakeword.model import Model

# =====================================================================
# 🎛️ SYSTEM CONFIGURATION
# =====================================================================
AUDIO_FILE = "command_input.wav"
WHISPER_MODEL_SIZE = "tiny.en"       # Local STT
OLLAMA_MODEL = "gpt-oss:120b-cloud"  # Your cloud gateway

PIPER_PATH = os.path.expanduser("~/piper/piper/piper")
PIPER_MODEL = os.path.expanduser("~/piper/en_US-lessac-medium.onnx")
VOLUME_BOOST = "1.5"

# Audio Recording Settings for Real-time Streaming
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280  # openWakeWord requires exactly 1280 sample chunks (80ms)

# =====================================================================
# 🔄 INITS & LOADERS
# =====================================================================
print("🔄 Loading local STT (Faster-Whisper)...")
stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

print("👂 Initializing Wake Word Engine...")

oww_model = Model(
    wakeword_models=["./hey_mycroft.onnx"],
    inference_framework="onnx"
)

pyaudio_instance = pyaudio.PyAudio()
mic_stream = pyaudio_instance.open(
    format=FORMAT, channels=CHANNELS, rate=RATE, 
    input=True, frames_per_buffer=CHUNK
)

print("✅ System Fully Operational. Listening for 'Hey Medimate'...")

# =====================================================================
# 🛠️ HELPER PIPELINE FUNCTIONS
# =====================================================================
def speak_sentence(text):
    """Feeds text directly to Piper TTS with digital volume gain."""
    cleaned_text = text.strip()
    if not cleaned_text:
        return
    cmd = (
        f"echo {json.dumps(cleaned_text)} | "
        f"{PIPER_PATH} --model {PIPER_MODEL} --volume {VOLUME_BOOST} --output-raw | "
        f"aplay -r 22050 -f S16_LE -t raw"
    )
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def record_active_command(duration=5):
    """Records a fixed block window immediately after wake-word matches."""
    print("🎤 Capturing command...")
    frames = []
    # Read fresh audio data chunks from our open microphone stream
    for _ in range(0, int(RATE / CHUNK * duration)):
        frames.append(mic_stream.read(CHUNK, exception_on_overflow=False))
        
    # Write temporal audio block out to file for local transcription pass
    with wave.open(AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio_instance.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

def run_brain_pipeline():
    """Executes the transcription, cloud generation, and output loop."""
    # 1. Transcribe the captured audio block
    segments, _ = stt_model.transcribe(AUDIO_FILE, beam_size=1)
    user_text = "".join([segment.text for segment in segments]).strip()
    print(f"🗣️ User: {user_text}")
    
    if not user_text or len(user_text) < 3:
        print("⚠️ False activation or silent phrase. Re-arming.")
        return

    # 2. Call Ollama Cloud streaming
    print(f"☁️ Cloud Routing ({OLLAMA_MODEL})...")
    system_instruction = (
        "You are Medimate, a medical-focused smart assistant. Keep responses reassuring, "
        "extremely clear, and short (max 2 sentences). Avoid Markdown or bullet points."
        "DO NOT USE any kind of punctuation except comma, period and question mark, as your response will be fed to a TTS model."
    )
    
    stream = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {'role': 'system', 'content': system_instruction},
            {'role': 'user', 'content': user_text}
        ],
        stream=True
    )

    # 3. Dynamic Sentence TTS Streaming Loop
    current_sentence = ""
    print("🤖 Medimate: ", end="", flush=True)

    for chunk in stream:
        token = chunk['message']['content']
        print(token, end="", flush=True)
        current_sentence += token
        
        if any(p in token for p in ['.', '!', '?']):
            speak_sentence(current_sentence)
            current_sentence = ""
            
    if current_sentence.strip():
        speak_sentence(current_sentence)
    print("\n" + "-"*50)

# =====================================================================
# 🚀 CORE ENGINE STREAM LOOP
# =====================================================================
def start_ambient_assistant():
    while True:
        try:
            # Read standard 80ms chunk out of continuous audio buffer
            audio_data = mic_stream.read(CHUNK, exception_on_overflow=False)
            
            # Convert binary sound wave formats to flat floating numpy arrays
            int_data = np.frombuffer(audio_data, dtype=np.int16)
            
            # Feed data array directly to openWakeWord frame processor
            prediction = oww_model.predict(int_data)
            
            # Accessing prediction metric score for 'hey_mycroft' frame match
            for mdl, score in prediction.items():
                if score > 0.60:  # Confidence matching threshold (0.0 - 1.0)
                    print(f"\n🎉 Wake Word Triggered! (Score: {score:.2f})")
                    
                    # Wake up phrase spoken via local Piper loop
                    speak_sentence("Hi, I'm your Medimate assistant, ask me anything.")
                    
                    # Run the active pipeline interaction loop
                    record_active_command(duration=5)
                    run_brain_pipeline()

                    time.sleep(0.1) # Optional tiny pause to let hardware catch up
                    mic_stream.read(mic_stream.get_read_available(), exception_on_overflow=False)
                    
                    print("👂 Resetting ambient loop. Listening for 'Hey Medimate'...")
                    
        except KeyboardInterrupt:
            print("\nShutting down streaming listeners gracefully.")
            break
        except Exception as e:
            print(f"\nError in continuous stream loop: {e}")
            continue

    # Cleanup hardware state
    mic_stream.stop_stream()
    mic_stream.close()
    pyaudio_instance.terminate()

if __name__ == "__main__":
    start_ambient_assistant()
