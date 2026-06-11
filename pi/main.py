import os
import subprocess
import json
import urllib.error
import urllib.request
from google import genai
from google.genai import types as genai_types
from dotenv import load_dotenv
import wave
import time
import ollama

load_dotenv()

# Allow tests to import this module without pulling in heavy/audio dependencies
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
WHISPER_MODEL_SIZE = "tiny.en"       # Local STT[cite: 7]
GEMINI_MODEL = "gemini-2.5-flash"     #[cite: 7]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") #[cite: 7]
USE_GEMINI = bool(GEMINI_API_KEY)     #[cite: 7]
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud") #[cite: 7]
API_BASE_URL = os.getenv("API_BASE_URL", "https://lavender-monkey-657081.hostingersite.com")
PULSE_DATA_URL = f"{API_BASE_URL}/get_data.php" #[cite: 7]
PATIENT_ID = int(os.getenv("PATIENT_ID", "1"))
MAX_MEMORY_MESSAGES = 10 #[cite: 7]

# 🛠️ WINDOWS COMPATIBILITY FIX: Swapped hardcoded Linux paths (~/piper) to dynamic detections
if os.name == "nt":  # Windows Environment
    PIPER_PATH = r"C:\piper\piper.exe"
    PIPER_MODEL = r"C:\piper\en_US-lessac-medium.onnx"
else:                # Linux Fallback (Raspberry Pi)[cite: 7]
    PIPER_PATH = os.path.expanduser("~/piper/piper/piper")[cite: 7]
    PIPER_MODEL = os.path.expanduser("~/piper/en_US-lessac-medium.onnx")[cite: 7]

VOLUME_BOOST = "1.5" #[cite: 7]
WAKEWORD_MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hey_mycroft.onnx") #[cite: 7]

# Audio Recording Settings for Real-time Streaming[cite: 7]
CHANNELS = 1 #[cite: 7]
RATE = 16000 #[cite: 7]
CHUNK = 1280  # openWakeWord requires exactly 1280 sample chunks (80ms)[cite: 7]
SPEECH_RMS_THRESHOLD = 450 #[cite: 7]
START_SPEECH_CHUNKS = 2 #[cite: 7]
END_SILENCE_SECONDS = 3.0 #[cite: 7]
MAX_COMMAND_SECONDS = 20 #[cite: 7]
PRE_SPEECH_SECONDS = 0.4 #[cite: 7]

# =====================================================================
# 🔄 INITS & LOADERS
# =====================================================================
if not SKIP_INIT:
    print("🔄 Loading local STT (Faster-Whisper)...")
    stt_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=2) #[cite: 7]

    print("👂 Initializing Wake Word Engine...")
    oww_model = Model(
        wakeword_models=[WAKEWORD_MODEL],
        inference_framework="onnx"
    ) #[cite: 7]

    FORMAT = pyaudio.paInt16 #[cite: 7]
    pyaudio_instance = pyaudio.PyAudio() #[cite: 7]
    mic_stream = pyaudio_instance.open(
        format=FORMAT, channels=CHANNELS, rate=RATE,
        input=True, frames_per_buffer=CHUNK
    ) #[cite: 7]
    print("✅ System Fully Operational. Listening for 'Hey Mycroft'...")
else:
    FORMAT = None
    stt_model = None
    oww_model = None
    pyaudio_instance = None
    mic_stream = None

CONVERSATION_HISTORY = [] #[cite: 7]
LAST_PATIENT_PULSE_CONTEXT = None #[cite: 7]
VOICE_MODE = "patient" #[cite: 7]

MODE_ACKNOWLEDGEMENTS = {
    "patient": "Patient mode is on. Ask me a health question whenever you are ready.", #[cite: 7]
    "doctor": "Doctor mode is on. You can ask about the patient's vitals and health information.", #[cite: 7]
}

# =====================================================================
# 🛠️ HELPER PIPELINE FUNCTIONS
# =====================================================================
def speak_sentence(text):
    """Feeds text directly to Piper TTS, adapting automatically for Windows or Linux."""
    cleaned_text = text.strip() 
    if not cleaned_text: 
        return

    # 🛠️ WINDOWS COMPATIBILITY FIX
    if os.name == "nt": 
        import winsound
        cmd = [PIPER_PATH, "--model", PIPER_MODEL, "--output_file", "reply.wav"]
        try:
            # We removed capture_output=True to prevent the argument conflict!
            subprocess.run(cmd, input=cleaned_text.encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists("reply.wav"):
                winsound.PlaySound("reply.wav", winsound.SND_FILENAME)
        except Exception as e:
            print(f"❌ PIPER TTS ERROR: {e}")
        return

    # Linux Execution (Raspberry Pi fallback)
    cmd = (
        f"echo {json.dumps(cleaned_text)} | "
        f"{PIPER_PATH} --model {PIPER_MODEL} --volume {VOLUME_BOOST} --output-raw | "
        f"aplay -r 22050 -f S16_LE -t raw"
    ) 
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_rms(audio_data):
    """Returns the root mean square volume for a chunk of int16 PCM audio."""
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) #[cite: 7]
    if samples.size == 0: #[cite: 7]
        return 0
    return float(np.sqrt(np.mean(samples * samples))) #[cite: 7]

def get_latest_pulse_data(patient_identifier=None, limit=5):
    """Fetches health and environmental readings for a specific patient by ID or Name."""
    try:
        target_id = None
        
        # 1. Resolve Patient ID if a name/string is provided
        if patient_identifier:
            try:
                target_id = int(patient_identifier)
            except ValueError:
                # Search by name: Fetch all patients first
                with urllib.request.urlopen(PULSE_DATA_URL, timeout=10) as response:
                    list_payload = json.loads(response.read().decode("utf-8"))
                
                if list_payload.get("status") == "success":
                    patients = list_payload.get("patients", [])
                    search_name = str(patient_identifier).lower()
                    for p in patients:
                        if search_name in p.get("name", "").lower():
                            target_id = p.get("id")
                            print(f"Resolved name '{patient_identifier}' to ID {target_id}")
                            break
                
                if not target_id:
                    print(f"Could not find patient with name: {patient_identifier}")
                    return {"status": "error", "message": f"Patient '{patient_identifier}' not found."}
        else:
            target_id = PATIENT_ID

        # 2. Fetch specific data for the resolved ID
        url = f"{PULSE_DATA_URL}?patient_id={target_id}"
        with urllib.request.urlopen(url, timeout=10) as response: #[cite: 7]
            payload = json.loads(response.read().decode("utf-8")) #[cite: 7]

        if payload.get("status") != "success": #[cite: 7]
            print(f"Pulse API returned an error: {payload.get('message', 'Unknown error')}") #[cite: 7]
            return {"device_status": "Unknown", "readings": [], "patient": {}, "env_data": []} #[cite: 7]

        readings = payload.get("data", [])[-limit:] #[cite: 7]
        env_readings = payload.get("env_data", [])[-limit:]
        patient_info = payload.get("patient", {})
        
        print(f"Fetched data for patient: {patient_info.get('name', 'Unknown')}") #[cite: 7]

        pulse_values = [int(item.get("pulse", 0)) for item in readings if item.get("pulse")]
        average_pulse = sum(pulse_values) / len(pulse_values) if pulse_values else None
        
        return {
            "device_status": payload.get("device_status", "Unknown"), #[cite: 7]
            "average_pulse": average_pulse, #[cite: 7]
            "readings": readings, #[cite: 7]
            "env_data": env_readings,
            "patient": patient_info
        }
    except Exception as e:
        print(f"Could not fetch pulse data: {e}")
        return {"device_status": "Unknown", "readings": [], "patient": {}, "env_data": []}

def format_pulse_context(pulse_snapshot):
    """Formats pulse and environmental data for the assistant model."""
    readings = pulse_snapshot.get("readings", []) #[cite: 7]
    env_readings = pulse_snapshot.get("env_data", [])
    patient = pulse_snapshot.get("patient", {})
    
    if not readings and not env_readings: #[cite: 7]
        return "No recent health readings are available right now." #[cite: 7]

    patient_name = patient.get("name", "the patient")
    rows = [f"Data for patient: {patient_name}."]
    rows.append(f"Device status: {pulse_snapshot.get('device_status', 'Unknown')}.") #[cite: 7]
    
    average_pulse = pulse_snapshot.get("average_pulse") #[cite: 7]
    if average_pulse is not None: #[cite: 7]
        rows.append(f"Average pulse from recent readings: {average_pulse:.1f} BPM") #[cite: 7]

    if readings:
        rows.append("\nRecent Pulse Readings:")
        for item in readings: #[cite: 7]
            rows.append(f"- {item.get('created_at', 'unknown time')}: {item.get('pulse', 'unknown')} BPM") #[cite: 7]

    if env_readings:
        rows.append("\nRecent Environmental Data (Room):")
        for item in env_readings:
            rows.append(f"- {item.get('created_at', 'unknown time')}: Temp {item.get('temperature', 'unknown')}°C, Humidity {item.get('humidity', 'unknown')}%")

    return "\n".join(rows) #[cite: 7]

PULSE_DATA_TOOL = {
    "type": "function",
    "function": {
        "name": "get_latest_pulse_data",
        "description": (
            "Fetch the health data (pulse, temperature, humidity) for a specific patient. "
            "The assistant can provide a name (e.g., 'John Doe') or an ID (e.g., '1') as the identifier. "
            "If no identifier is provided, it defaults to the primary patient."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_identifier": {
                    "type": "string",
                    "description": "The name or ID of the patient to search for."
                }
            },
            "required": []
        }
    }
} #[cite: 7]

def get_message_field(message, field_name, default=None):
    if isinstance(message, dict): return message.get(field_name, default) #[cite: 7]
    return getattr(message, field_name, default) #[cite: 7]

def get_tool_call_function(tool_call):
    function_call = get_message_field(tool_call, "function", {}) #[cite: 7]
    return get_message_field(function_call, "name", ""), get_message_field(function_call, "arguments", {}) or {} #[cite: 7]

def _build_genai_request(messages, tools):
    """Convert Ollama-style messages to GenAI (system_instruction, contents, tools)."""
    system_parts, contents = [], [] #[cite: 7]

    for msg in messages: #[cite: 7]
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "user") #[cite: 7]
        content = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or "" #[cite: 7]

        if role == "system": #[cite: 7]
            if content: system_parts.append(content) #[cite: 7]
            continue

        if role == "tool": #[cite: 7]
            tool_name = msg.get("tool_name", "") if isinstance(msg, dict) else getattr(msg, "tool_name", "") #[cite: 7]
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(function_response=genai_types.FunctionResponse(name=tool_name, response={"result": content}))]
            )) #[cite: 7]
        elif role == "assistant": #[cite: 7]
            tool_calls = (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)) or [] #[cite: 7]
            parts = [genai_types.Part(text=content)] if content else [] #[cite: 7]
            for tc in tool_calls: #[cite: 7]
                func = tc.get("function", {}) if isinstance(tc, dict) else getattr(tc, "function", {}) #[cite: 7]
                name = func.get("name", "") if isinstance(func, dict) else getattr(func, "name", "") #[cite: 7]
                args = func.get("arguments", {}) if isinstance(func, dict) else getattr(func, "arguments", {}) #[cite: 7]
                parts.append(genai_types.Part(function_call=genai_types.FunctionCall(name=name, args=args or {}))) #[cite: 7]
            if parts: contents.append(genai_types.Content(role="model", parts=parts)) #[cite: 7]
        else:
            if content: contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=content)])) #[cite: 7]

    genai_tools = None #[cite: 7]
    if tools: #[cite: 7]
        declarations = [] #[cite: 7]
        for tool in tools: #[cite: 7]
            func = tool.get("function", {}) #[cite: 7]
            params = func.get("parameters", {}) #[cite: 7]
            props = params.get("properties", {}) #[cite: 7]
            schema_props = {k: genai_types.Schema(type=v.get("type", "string").upper()) for k, v in props.items()} #[cite: 7]
            declarations.append(genai_types.FunctionDeclaration(
                name=func.get("name", ""),
                description=func.get("description", ""),
                parameters=genai_types.Schema(
                    type="OBJECT", properties=schema_props, required=params.get("required", [])
                ) if schema_props or params.get("required") else None
            )) #[cite: 7]
        genai_tools = [genai_types.Tool(function_declarations=declarations)] #[cite: 7]

    return "\n\n".join(system_parts) if system_parts else None, contents, genai_tools #[cite: 7]

def call_gemini_chat(messages, model, stream=False, tools=None):
    client = genai.Client(api_key=GEMINI_API_KEY) #[cite: 7]
    system_instruction, contents, genai_tools = _build_genai_request(messages, tools) #[cite: 7]
    config = genai_types.GenerateContentConfig(system_instruction=system_instruction, tools=genai_tools) #[cite: 7]

    try:
        if stream: #[cite: 7]
            def _stream():
                for chunk in client.models.generate_content_stream(model=model, contents=contents, config=config): #[cite: 7]
                    if chunk.candidates: #[cite: 7]
                        for part in chunk.candidates[0].content.parts: #[cite: 7]
                            if hasattr(part, "text") and part.text: #[cite: 7]
                                yield {"message": {"content": part.text}} #[cite: 7]
            return _stream() #[cite: 7]

        response = client.models.generate_content(model=model, contents=contents, config=config) #[cite: 7]
        content_text, tool_calls = "", [] #[cite: 7]
        
        if response.candidates: #[cite: 7]
            for part in response.candidates[0].content.parts: #[cite: 7]
                if hasattr(part, "text") and part.text: #[cite: 7]
                    content_text += part.text #[cite: 7]
                elif hasattr(part, "function_call") and part.function_call: #[cite: 7]
                    fc = part.function_call #[cite: 7]
                    tool_calls.append({"function": {"name": fc.name, "arguments": dict(fc.args) if fc.args else {}}}) #[cite: 7]

        message = {"role": "assistant", "content": content_text} #[cite: 7]
        if tool_calls: message["tool_calls"] = tool_calls #[cite: 7]
        return {"message": message} #[cite: 7]

    except Exception as e:
        err_str = str(e)
        
        # 🟢 FIX: If the error is a 429 OR a 503 server overload, RAISE IT 
        # so that cloud_chat knows it needs to switch to your Cloud Ollama model!
        if any(err in err_str for err in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"]): 
            raise e
            
        if stream: return iter([{"message": {"content": f"[Gemini error] {e}"}}])
        return {"message": {"role": "assistant", "content": f"[Gemini error] {e}"}}

def cloud_chat(kwargs):
    messages, stream, tools = kwargs.get("messages"), kwargs.get("stream", False), kwargs.get("tools", None) #[cite: 7]

    def _safe_ollama_chat(**chat_args):
        try:
            return ollama.chat(**chat_args)
        except Exception as e:
            print(f"⚠️ Ollama Error: {e}")
            if stream:
                return iter([{"message": {"content": "I'm sorry, but both my cloud and local brains are currently offline. Please check your internet connection or ensure Ollama is running."}}])
            return {"message": {"role": "assistant", "content": "I'm sorry, but both my cloud and local brains are currently offline. Please check your internet connection or ensure Ollama is running."}}

    if USE_GEMINI: #[cite: 7]
        try:
            gemini_result = call_gemini_chat(messages=messages, model=GEMINI_MODEL, stream=stream, tools=tools) #[cite: 7]
        except Exception as e:
            print(f"Gemini quota exceeded, falling back to Ollama... ({e.__class__.__name__})") #[cite: 7]
            return _safe_ollama_chat(**kwargs) #[cite: 7]

        if not stream: return gemini_result #[cite: 7]

        def _stream_with_fallback():
            try: yield from gemini_result #[cite: 7]
            except Exception as e:
                print(f"Gemini stream failed, falling back to Ollama... ({e.__class__.__name__})") #[cite: 7]
                yield from _safe_ollama_chat(**kwargs) #[cite: 7]
        return _stream_with_fallback() #[cite: 7]

    return _safe_ollama_chat(**kwargs) #[cite: 7]

def normalize_spoken_command(text):
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text) #[cite: 7]
    return " ".join(cleaned.split()) #[cite: 7]

def get_requested_voice_mode(user_text):
    normalized = normalize_spoken_command(user_text) #[cite: 7]
    if len(normalized.split()) > 8: return None #[cite: 7]
    if "doctor mode" in normalized: return "doctor" #[cite: 7]
    if "patient mode" in normalized: return "patient" #[cite: 7]
    return None #[cite: 7]

def build_system_instruction():
    # 🛠️ GLOBAL TTS RULES: These prevent the Piper Voice Engine from crashing or stuttering
    tts_rules = (
        "Keep your responses naturally conversational, usually between 2 to 4 sentences. "
        "CRITICAL: Avoid Markdown, asterisks, or bullet points. DO NOT USE any kind of punctuation except commas, periods, and question marks, "
        "as your response will be read aloud by a text-to-speech engine."
    ) 

    if VOICE_MODE == "doctor": 
        return (
            "You are Medimate, an advanced clinical AI data analyst speaking directly with a healthcare professional. "
            "When asked about patient vitals, ALWAYS use the pulse data tool to fetch the latest readings. "
            "YOUR OBJECTIVE: Never just read back the average number. You must act as an insightful medical assistant! "
            "Analyze the array of recent readings provided by the tool. Point out the trend. Is the heart rate stable, "
            "erratic, trending upwards, or dropping? Provide a brief, professional clinical hypothesis or insight based on the data, "
            "and note if it falls within a normal resting adult range. Be sharp, analytical, and highly insightful. "
            + tts_rules
        ) 
    
    # Patient Mode (Default)
    return (
        "You are Medimate, an energetic, humorous, and warm companion AI speaking with a patient. "
        "YOUR OBJECTIVE: Make the patient feel happy, engaged, and less alone! "
        "Have a mature but lighthearted personality. Be witty, deeply empathetic, and highly interactive. "
        "Crucially, try to end your responses with a fun or engaging follow-up question to keep the conversation flowing naturally! "
        "If they talk about something random, lean into it and joke around with them. "
        "If they ask for their specific medical data, gently and playfully remind them that your clinical lips are sealed until the doctor turns the key. "
        + tts_rules
    )

def remember_turn(user_text, assistant_text):
    CONVERSATION_HISTORY.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": assistant_text.strip()}]) #[cite: 7]
    if len(CONVERSATION_HISTORY) > MAX_MEMORY_MESSAGES: del CONVERSATION_HISTORY[:-MAX_MEMORY_MESSAGES] #[cite: 7]

def record_active_command():
    print("🎤 Listening for command...")
    frames, pre_speech_frames, speech_started = [], [], False #[cite: 7]
    speech_chunks, silent_chunks = 0, 0 #[cite: 7]
    chunks_per_second = RATE / CHUNK #[cite: 7]
    max_chunks, end_silence_chunks = int(chunks_per_second * MAX_COMMAND_SECONDS), int(chunks_per_second * END_SILENCE_SECONDS) #[cite: 7]

    for _ in range(max_chunks): #[cite: 7]
        audio_data = mic_stream.read(CHUNK, exception_on_overflow=False) #[cite: 7]
        is_speech = get_rms(audio_data) >= SPEECH_RMS_THRESHOLD #[cite: 7]

        if not speech_started: #[cite: 7]
            pre_speech_frames.append(audio_data) #[cite: 7]
            if len(pre_speech_frames) > int(chunks_per_second * PRE_SPEECH_SECONDS): pre_speech_frames.pop(0) #[cite: 7]
            if is_speech: #[cite: 7]
                speech_chunks += 1 #[cite: 7]
                if speech_chunks >= START_SPEECH_CHUNKS: #[cite: 7]
                    speech_started = True #[cite: 7]
                    frames.extend(pre_speech_frames) #[cite: 7]
                    print("🎙️ Speech detected...") #[cite: 7]
            else: speech_chunks = 0 #[cite: 7]
            continue #[cite: 7]

        frames.append(audio_data) #[cite: 7]
        if is_speech: silent_chunks = 0 #[cite: 7]
        else:
            silent_chunks += 1 #[cite: 7]
            if silent_chunks >= end_silence_chunks: #[cite: 7]
                print("✅ Speech ended. Processing...") #[cite: 7]
                break #[cite: 7]

    if not frames: #[cite: 7]
        print("⚠️ No speech detected. Re-arming.") #[cite: 7]
        return False #[cite: 7]

    with wave.open(AUDIO_FILE, 'wb') as wf: #[cite: 7]
        wf.setnchannels(CHANNELS) #[cite: 7]
        wf.setsampwidth(pyaudio_instance.get_sample_size(FORMAT)) #[cite: 7]
        wf.setframerate(RATE) #[cite: 7]
        wf.writeframes(b''.join(frames)) #[cite: 7]
    return True #[cite: 7]

def run_brain_pipeline():
    global LAST_PATIENT_PULSE_CONTEXT, VOICE_MODE 

    segments, _ = stt_model.transcribe(AUDIO_FILE, beam_size=1) 
    user_text = "".join([segment.text for segment in segments]).strip() 
    print(f"🗣️ User: {user_text}") 
    
    if not user_text or len(user_text) < 3: return True 

    # --- 🛑 SHUTDOWN COMMAND CHECK ---
    normalized = normalize_spoken_command(user_text)
    if "turn off" in normalized or "shut down" in normalized:
        speak_sentence("Powering off. Goodbye!")
        return False # Returning False signals the main loop to terminate
    # ---------------------------------

    requested_mode = get_requested_voice_mode(user_text) 
    if requested_mode: 
        VOICE_MODE = requested_mode 
        print(f"Mode switched to {VOICE_MODE}.") 
        speak_sentence(MODE_ACKNOWLEDGEMENTS[VOICE_MODE]) 
        return True

    print(f"☁️ Cloud Routing ({GEMINI_MODEL if USE_GEMINI else OLLAMA_MODEL}) in {VOICE_MODE} mode...")
    messages = [{'role': 'system', 'content': build_system_instruction()}] 
    
    if VOICE_MODE == "doctor" and LAST_PATIENT_PULSE_CONTEXT: 
        messages.append({'role': 'system', 'content': f"Earlier pulse data memory:\n{LAST_PATIENT_PULSE_CONTEXT}"}) 
        
    messages.extend(CONVERSATION_HISTORY) 
    messages.append({'role': 'user', 'content': user_text}) 
    active_tools = [PULSE_DATA_TOOL] if VOICE_MODE == "doctor" else None 

    tool_response = cloud_chat({"model": OLLAMA_MODEL, "messages": messages, "stream": False, "tools": active_tools}) 
    assistant_message = get_message_field(tool_response, "message", {}) 
    messages.append(assistant_message) 
    tool_calls = get_message_field(assistant_message, "tool_calls", []) or [] 
    
    for tool_call in tool_calls: 
        tool_name, tool_args = get_tool_call_function(tool_call) 
        if tool_name == "get_latest_pulse_data": 
            patient_identifier = tool_args.get("patient_identifier")
            LAST_PATIENT_PULSE_CONTEXT = format_pulse_context(get_latest_pulse_data(patient_identifier=patient_identifier, limit=5)) 
            tool_result = LAST_PATIENT_PULSE_CONTEXT 
        else:
            tool_result = "Unknown tool requested." 
        messages.append({"role": "tool", "tool_name": tool_name, "content": tool_result}) 

    stream = cloud_chat({"model": OLLAMA_MODEL, "messages": messages, "stream": True, "tools": active_tools if tool_calls else None}) if tool_calls or not get_message_field(assistant_message, "content", "") else iter([{"message": {"content": get_message_field(assistant_message, "content", "")}}]) 

    current_sentence, assistant_text = "", "" 
    print("🤖 Medimate: ", end="", flush=True)

    try:
        for chunk in stream: 
            token = get_message_field(get_message_field(chunk, "message", {}), "content", "") or "" 
            if not token: continue 
            print(token, end="", flush=True) 
            assistant_text += token 
            current_sentence += token 
            if any(p in token for p in ['.', '!', '?']): 
                speak_sentence(current_sentence) 
                current_sentence = "" 
    except Exception as e:
        if "503" in str(e):
            print("\n⚠️ Google Servers are busy.")
            speak_sentence("My cloud brain is currently experiencing high traffic. Please ask me again in a few minutes.")
        else:
            print(f"\n⚠️ Generation Error: {e}")
    
    return True # Continue the conversation

def start_ambient_assistant():
    global VOICE_MODE 
    
    print("👂 Waiting for the initial 'Hey Mycroft' to wake up...")

    # --- PHASE 1: WAKE WORD LOOP (RUNS ONLY ONCE) ---
    woke_up = False
    while not woke_up:
        try:
            audio_data = mic_stream.read(CHUNK, exception_on_overflow=False) 
            prediction = oww_model.predict(np.frombuffer(audio_data, dtype=np.int16)) 
            
            for mdl, score in prediction.items(): 
                if score > 0.60: 
                    print(f"\n🎉 Wake Word Triggered! (Score: {score:.2f})") 
                    VOICE_MODE = "patient" 
                    speak_sentence("Hi, I am online. Ask me anything, or say switch to doctor mode.") 
                    woke_up = True
                    break # Break out of the prediction loop
                    
        except KeyboardInterrupt:
            mic_stream.stop_stream()
            mic_stream.close()
            pyaudio_instance.terminate()
            return
        except Exception as e: 
            continue

    # --- PHASE 2: CONTINUOUS LISTENING LOOP (NO WAKE WORD NEEDED) ---
    print("\n🚀 Entering continuous mode. Say 'Turn off' to exit the program.")
    while True:
        try:
            # Flush mic buffer before recording
            time.sleep(0.1) 
            mic_stream.read(mic_stream.get_read_available(), exception_on_overflow=False) 
            
            speech_detected = record_active_command()
            
            if speech_detected:
                keep_running = run_brain_pipeline()
                if keep_running is False:
                    break # "Turn off" was heard. Break the infinite loop!
                    
        except KeyboardInterrupt: 
            break 
        except Exception as e: 
            print(f"\nError in continuous loop: {e}")
            continue 

    # --- PHASE 3: CLEAN SHUTDOWN ---
    print("🛑 System shut down successfully.")
    mic_stream.stop_stream() 
    mic_stream.close() 
    pyaudio_instance.terminate()

if __name__ == "__main__":
    start_ambient_assistant()