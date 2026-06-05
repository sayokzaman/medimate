import os
import subprocess
import json
import urllib.error
import urllib.request
from google import genai
from google.genai import types as genai_types
from dotenv import load_dotenv
import wave

load_dotenv()
import time
import ollama

# Allow tests to import this module without pulling in heavy/audio dependencies
# Set MEDIMATE_SKIP_INIT=1 to skip hardware and model initialization at import time
SKIP_INIT = bool(os.getenv("MEDIMATE_SKIP_INIT"))

if not SKIP_INIT:
    import pyaudio
    import numpy as np
    from faster_whisper import WhisperModel
    import openwakeword
    from openwakeword.model import Model

# =====================================================================
# 🎛️ SYSTEM CONFIGURATION
# =====================================================================
AUDIO_FILE = "command_input.wav"
WHISPER_MODEL_SIZE = "tiny.en"       # Local STT
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI = bool(GEMINI_API_KEY)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")  # Your cloud gateway
PULSE_DATA_URL = "https://lavender-monkey-657081.hostingersite.com/get_data.php"
MAX_MEMORY_MESSAGES = 10

PIPER_PATH = os.path.expanduser("~/piper/piper/piper")
PIPER_MODEL = os.path.expanduser("~/piper/en_US-lessac-medium.onnx")
VOLUME_BOOST = "1.5"
WAKEWORD_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hey_mycroft.onnx")

# Audio Recording Settings for Real-time Streaming
CHANNELS = 1
RATE = 16000
CHUNK = 1280  # openWakeWord requires exactly 1280 sample chunks (80ms)
SPEECH_RMS_THRESHOLD = 450
START_SPEECH_CHUNKS = 2
END_SILENCE_SECONDS = 3.0
MAX_COMMAND_SECONDS = 20
PRE_SPEECH_SECONDS = 0.4

# =====================================================================
# 🔄 INITS & LOADERS
# =====================================================================
if not SKIP_INIT:
    print("🔄 Loading local STT (Faster-Whisper)...")
    stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    print("👂 Initializing Wake Word Engine...")

    oww_model = Model(
        wakeword_models=[WAKEWORD_MODEL],
        inference_framework="onnx"
    )

    FORMAT = pyaudio.paInt16
    pyaudio_instance = pyaudio.PyAudio()
    mic_stream = pyaudio_instance.open(
        format=FORMAT, channels=CHANNELS, rate=RATE,
        input=True, frames_per_buffer=CHUNK
    )
    print("✅ System Fully Operational. Listening for 'Hey Medimate'...")
else:
    # Define placeholders so code that references these names does not crash at import
    FORMAT = None
    stt_model = None
    oww_model = None
    pyaudio_instance = None
    mic_stream = None

CONVERSATION_HISTORY = []
LAST_PATIENT_PULSE_CONTEXT = None
VOICE_MODE = "patient"

MODE_ACKNOWLEDGEMENTS = {
    "patient": "Patient mode is on. Ask me a health question whenever you are ready.",
    "doctor": "Doctor mode is on. You can ask about the patient's vitals and health information.",
}

# =====================================================================
# 🛠️ HELPER PIPELINE FUNCTIONS
# =====================================================================
def speak_sentence(text):
    """Feeds text directly to Piper TTS with digital volume gain."""
    cleaned_text = text.strip()
    if not cleaned_text:
        return

    if os.name == "nt":
        ps_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Volume = 100; "
            "$s.Speak([Console]::In.ReadToEnd())"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            input=cleaned_text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    cmd = (
        f"echo {json.dumps(cleaned_text)} | "
        f"{PIPER_PATH} --model {PIPER_MODEL} --volume {VOLUME_BOOST} --output-raw | "
        f"aplay -r 22050 -f S16_LE -t raw"
    )
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_rms(audio_data):
    """Returns the root mean square volume for a chunk of int16 PCM audio."""
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0
    return float(np.sqrt(np.mean(samples * samples)))

def get_latest_pulse_data(limit=5):
    """Fetches the latest pulse readings from the MediMate API."""
    try:
        with urllib.request.urlopen(PULSE_DATA_URL, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if payload.get("status") != "success":
            print("Pulse API returned an error response.")
            return {
                "device_status": "Unknown",
                "readings": []
            }

        readings = payload.get("data", [])[-limit:]
        print(f"Fetched {len(readings)} latest pulse readings.")

        pulse_values = []
        for item in readings:
            try:
                pulse_values.append(int(item.get("pulse", 0)))
            except (TypeError, ValueError):
                continue

        average_pulse = None
        if pulse_values:
            average_pulse = sum(pulse_values) / len(pulse_values)
            print(f"Average pulse: {average_pulse:.1f}")
        
        return {
            "device_status": payload.get("device_status", "Unknown"),
            "average_pulse": average_pulse,
            "readings": readings
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"Could not fetch pulse data: {e}")
        return {
            "device_status": "Unknown",
            "readings": []
        }

def format_pulse_context(pulse_snapshot):
    """Formats pulse data for the assistant model."""
    readings = pulse_snapshot.get("readings", [])
    if not readings:
        return "No recent pulse readings are available right now."

    rows = [
        f"Device status: {pulse_snapshot.get('device_status', 'Unknown')}.",
        "Latest 5 pulse readings, oldest to newest:"
    ]

    average_pulse = pulse_snapshot.get("average_pulse")
    if average_pulse is not None:
        rows.append(f"Average pulse from these readings: {average_pulse:.1f} BPM")

    for item in readings:
        rows.append(
            f"{item.get('created_at', 'unknown time')}: {item.get('pulse', 'unknown')} BPM"
        )

    return "\n".join(rows)

PULSE_DATA_TOOL = {
    "type": "function",
    "function": {
        "name": "get_latest_pulse_data",
        "description": (
            "Fetch the patient's latest 5 pulse readings, average pulse, and device status. "
            "Use this only when the user asks about the patient, the patient's pulse, heart rate, "
            "recent readings, sensor status, vitals, or whether the patient's current data looks okay."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def get_message_field(message, field_name, default=None):
    """Reads a field from either Ollama dict responses or SDK response objects."""
    if isinstance(message, dict):
        return message.get(field_name, default)
    return getattr(message, field_name, default)

def get_tool_call_function(tool_call):
    """Returns the function name and args from an Ollama tool call."""
    function_call = get_message_field(tool_call, "function", {})
    name = get_message_field(function_call, "name", "")
    arguments = get_message_field(function_call, "arguments", {}) or {}
    return name, arguments


def _build_genai_request(messages, tools):
    """Convert Ollama-style messages to GenAI (system_instruction, contents, tools)."""
    system_parts = []
    contents = []

    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "user")
        content = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""

        if role == "system":
            if content:
                system_parts.append(content)
            continue

        if role == "tool":
            tool_name = msg.get("tool_name", "") if isinstance(msg, dict) else getattr(msg, "tool_name", "")
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(
                    function_response=genai_types.FunctionResponse(name=tool_name, response={"result": content})
                )]
            ))
        elif role == "assistant":
            tool_calls = (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)) or []
            parts = []
            if content:
                parts.append(genai_types.Part(text=content))
            for tc in tool_calls:
                func = tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", {})
                name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "")
                args = func.get("arguments", {}) if isinstance(func, dict) else getattr(func, "arguments", {})
                parts.append(genai_types.Part(
                    function_call=genai_types.FunctionCall(name=name, args=args or {})
                ))
            if parts:
                contents.append(genai_types.Content(role="model", parts=parts))
        else:
            if content:
                contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=content)]))

    system_instruction = "\n\n".join(system_parts) if system_parts else None

    genai_tools = None
    if tools:
        declarations = []
        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            props = params.get("properties", {})
            schema_props = {
                k: genai_types.Schema(type=v.get("type", "string").upper())
                for k, v in props.items()
            }
            declarations.append(genai_types.FunctionDeclaration(
                name=func.get("name", ""),
                description=func.get("description", ""),
                parameters=genai_types.Schema(
                    type="OBJECT",
                    properties=schema_props,
                    required=params.get("required", [])
                ) if schema_props or params.get("required") else None
            ))
        genai_tools = [genai_types.Tool(function_declarations=declarations)]

    return system_instruction, contents, genai_tools


def call_gemini_chat(messages, model, stream=False, tools=None):
    """Call the Gemini API using the official google-genai SDK."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    system_instruction, contents, genai_tools = _build_genai_request(messages, tools)
    config = genai_types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=genai_tools,
    )

    try:
        if stream:
            def _stream():
                for chunk in client.models.generate_content_stream(
                    model=model, contents=contents, config=config
                ):
                    if chunk.candidates:
                        for part in chunk.candidates[0].content.parts:
                            if hasattr(part, "text") and part.text:
                                yield {"message": {"content": part.text}}
            return _stream()

        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )

        content_text = ""
        tool_calls = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    content_text += part.text
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "function": {"name": fc.name, "arguments": dict(fc.args) if fc.args else {}}
                    })

        message = {"role": "assistant", "content": content_text}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return {"message": message}

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise
        err = f"[Gemini call failed] {e}"
        if stream:
            return iter([{"message": {"content": err}}])
        return {"message": {"role": "assistant", "content": err}}


def cloud_chat(kwargs):
    """Route chat requests to Gemini when enabled, otherwise use Ollama SDK.
    `kwargs` should mirror the existing calls to `ollama.chat` in this file.
    """
    messages = kwargs.get("messages")
    stream = kwargs.get("stream", False)
    tools = kwargs.get("tools", None)

    if USE_GEMINI:
        try:
            gemini_result = call_gemini_chat(messages=messages, model=GEMINI_MODEL, stream=stream, tools=tools)
        except Exception as e:
            print(f"Gemini quota exceeded, falling back to Ollama... ({e.__class__.__name__})")
            return ollama.chat(**kwargs)

        if not stream:
            return gemini_result

        # Gemini streaming is lazy — the 429 fires during iteration, not here.
        # Wrap in a generator so Ollama takes over if Gemini fails mid-stream.
        def _stream_with_fallback():
            try:
                yield from gemini_result
            except Exception as e:
                print(f"Gemini stream failed, falling back to Ollama... ({e.__class__.__name__})")
                yield from ollama.chat(**kwargs)

        return _stream_with_fallback()

    return ollama.chat(**kwargs)

def normalize_spoken_command(text):
    """Normalizes transcribed speech so mode commands survive punctuation noise."""
    cleaned = "".join(
        ch.lower() if ch.isalnum() or ch.isspace() else " "
        for ch in text
    )
    return " ".join(cleaned.split())

def get_requested_voice_mode(user_text):
    """Detects spoken commands that switch between patient and doctor mode."""
    normalized = normalize_spoken_command(user_text)

    # Only treat short utterances as mode commands to avoid false positives
    if len(normalized.split()) > 8:
        return None

    if "doctor mode" in normalized:
        return "doctor"
    if "patient mode" in normalized:
        return "patient"
    return None

def build_system_instruction():
    """Builds the active assistant behavior for patient or doctor mode."""
    base_instruction = (
        "You are Medimate, a helpful voice assistant. "
        "Keep responses clear and short, max 2 sentences. "
        "Avoid Markdown or bullet points. "
        "DO NOT USE any kind of punctuation except comma, period and question mark, "
        "as your response will be fed to a TTS model. "
    )

    if VOICE_MODE == "doctor":
        return (
            base_instruction
            + "You are in doctor mode and speaking with a doctor or clinician. "
            + "The doctor may ask about the patient's health information, vitals, "
            + "heart rate, pulse readings, and sensor status. "
            + "Pulse sensor readings belong to the patient, not necessarily the person speaking. "
            + "Use the pulse data tool when the doctor asks for current or recent patient vitals."
        )

    return (
        base_instruction
        + "You are in patient mode. Answer any question the user asks, whether it is about health, "
        + "weather, general knowledge, or anything else. "
        + "For medical questions, do not diagnose, and recommend urgent care for emergency symptoms. "
        + "If the user asks for stored vitals, pulse data, or sensor data, "
        + "explain that those details are available in doctor mode."
    )

def remember_turn(user_text, assistant_text):
    """Stores a short rolling chat history across wake-word turns."""
    CONVERSATION_HISTORY.extend([
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text.strip()}
    ])

    if len(CONVERSATION_HISTORY) > MAX_MEMORY_MESSAGES:
        del CONVERSATION_HISTORY[:-MAX_MEMORY_MESSAGES]

def record_active_command():
    """Records until speech has started and then stopped for a short silence."""
    print("🎤 Listening for command...")
    frames = []
    pre_speech_frames = []
    speech_started = False
    speech_chunks = 0
    silent_chunks = 0

    chunks_per_second = RATE / CHUNK
    max_chunks = int(chunks_per_second * MAX_COMMAND_SECONDS)
    end_silence_chunks = int(chunks_per_second * END_SILENCE_SECONDS)
    pre_speech_chunks = int(chunks_per_second * PRE_SPEECH_SECONDS)

    # Read fresh audio chunks until the user stops speaking.
    for _ in range(max_chunks):
        audio_data = mic_stream.read(CHUNK, exception_on_overflow=False)
        is_speech = get_rms(audio_data) >= SPEECH_RMS_THRESHOLD

        if not speech_started:
            pre_speech_frames.append(audio_data)
            if len(pre_speech_frames) > pre_speech_chunks:
                pre_speech_frames.pop(0)

            if is_speech:
                speech_chunks += 1
                if speech_chunks >= START_SPEECH_CHUNKS:
                    speech_started = True
                    frames.extend(pre_speech_frames)
                    print("🎙️ Speech detected...")
            else:
                speech_chunks = 0
            continue

        frames.append(audio_data)

        if is_speech:
            silent_chunks = 0
        else:
            silent_chunks += 1
            if silent_chunks >= end_silence_chunks:
                print("✅ Speech ended. Processing...")
                break

    if not frames:
        print("⚠️ No speech detected. Re-arming.")
        return False

    # Write temporal audio block out to file for local transcription pass
    with wave.open(AUDIO_FILE, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio_instance.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return True

def run_brain_pipeline():
    """Executes the transcription, cloud generation, and output loop."""
    global LAST_PATIENT_PULSE_CONTEXT, VOICE_MODE

    # 1. Transcribe the captured audio block
    segments, _ = stt_model.transcribe(AUDIO_FILE, beam_size=1)
    user_text = "".join([segment.text for segment in segments]).strip()
    print(f"🗣️ User: {user_text}")
    
    if not user_text or len(user_text) < 3:
        print("⚠️ False activation or silent phrase. Re-arming.")
        return

    requested_mode = get_requested_voice_mode(user_text)
    if requested_mode:
        VOICE_MODE = requested_mode
        acknowledgement = MODE_ACKNOWLEDGEMENTS[VOICE_MODE]
        print(f"Mode switched to {VOICE_MODE}.")
        speak_sentence(acknowledgement)
        return

    # 2. Call Ollama Cloud streaming
    print(f"☁️ Cloud Routing ({OLLAMA_MODEL}) in {VOICE_MODE} mode...")
    system_instruction = build_system_instruction()
    active_tools = [PULSE_DATA_TOOL] if VOICE_MODE == "doctor" else None
    messages = [
        {'role': 'system', 'content': system_instruction}
    ]

    if VOICE_MODE == "doctor" and LAST_PATIENT_PULSE_CONTEXT:
        messages.append({
            'role': 'system',
            'content': (
                "Earlier patient pulse data remembered from this session:\n"
                + LAST_PATIENT_PULSE_CONTEXT
                + "\nUse this only as conversational memory. Call the tool again when the user asks for the latest readings."
            )
        })

    messages.extend(CONVERSATION_HISTORY)
    messages.append({'role': 'user', 'content': user_text})

    chat_kwargs = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }
    if active_tools:
        chat_kwargs["tools"] = active_tools

    tool_response = cloud_chat(chat_kwargs)

    assistant_message = get_message_field(tool_response, "message", {})
    messages.append(assistant_message)

    tool_calls = get_message_field(assistant_message, "tool_calls", []) or []
    for tool_call in tool_calls:
        tool_name, _ = get_tool_call_function(tool_call)

        if tool_name == "get_latest_pulse_data":
            pulse_snapshot = get_latest_pulse_data(limit=5)
            tool_result = format_pulse_context(pulse_snapshot)
            LAST_PATIENT_PULSE_CONTEXT = tool_result
        else:
            tool_result = "Unknown tool requested."

        messages.append({
            "role": "tool",
            "tool_name": tool_name,
            "content": tool_result
        })

    if tool_calls and active_tools:
        stream = cloud_chat({
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
        })
    else:
        direct_content = get_message_field(assistant_message, "content", "")
        if direct_content:
            stream = iter([{"message": {"content": direct_content}}])
        else:
            stream = cloud_chat({
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": True,
            })

    # 3. Dynamic Sentence TTS Streaming Loop
    current_sentence = ""
    assistant_text = ""
    print("🤖 Medimate: ", end="", flush=True)

    for chunk in stream:
        chunk_message = get_message_field(chunk, "message", {})
        token = get_message_field(chunk_message, "content", "") or ""
        if not token:
            continue

        print(token, end="", flush=True)
        assistant_text += token
        current_sentence += token
        
        if any(p in token for p in ['.', '!', '?']):
            speak_sentence(current_sentence)
            current_sentence = ""
            
    if current_sentence.strip():
        speak_sentence(current_sentence)

    if assistant_text.strip():
        remember_turn(user_text, assistant_text)

    print("\n" + "-"*50)

# =====================================================================
# 🚀 CORE ENGINE STREAM LOOP
# =====================================================================
def start_ambient_assistant():
    global VOICE_MODE

    has_greeted = False

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
                    
                    # Wake up phrase spoken once per process run.
                    if not has_greeted:
                        VOICE_MODE = "patient"
                        speak_sentence(
                            "Hi, I am in patient mode. Ask me anything, or say switch to doctor mode."
                        )
                        has_greeted = True
                    else:
                        speak_sentence("Listening.")

                    # Run the active pipeline interaction loop
                    if record_active_command():
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
