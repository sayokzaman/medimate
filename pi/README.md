# 🩺 MediMate: Pi Core Deployment & Setup Guide

This guide outlines how to configure a pristine system to run the MediMate Ambient Audio Voice Core using **Python 3.13+** on a Raspberry Pi (or Linux-based ARM64 environment).

## 🚀 Setup Checklist

### Step 1: Install System Audio Packages

Before setting up your Python workspace, your operating system needs hardware sound abstraction drivers. Run the following command in your terminal:

```bash
sudo apt-get update && sudo apt-get install -y portaudio19-dev python3-dev libgomp1 aplay

```

### Step 2: Initialize Your Virtual Environment

Navigate to your project's Pi workspace directory, create an isolated virtual environment, and activate it:

```bash
cd /path/to/medimate/pi
python3 -m venv .
source bin/activate

```

### Step 3: Upgrade System Package Tools

Ensure your internal environment installation tools are completely up to date to properly build wheel packages for modern Python versions:

```bash
pip install --upgrade pip setuptools wheel

```

### Step 4: Install the Python Package Framework

Because `openwakeword` natively requests dependencies that break on Python 3.13 (`tflite-runtime`), we must install it **separately** by ignoring its core dependencies and providing the ONNX alternatives manually.

**1. Install openwakeword without standard dependencies:**

```bash
pip install openwakeword==0.6.0 --no-deps

```

**2. Manually install its required safe libraries:**

```bash
pip install onnxruntime tqdm scipy scikit-learn requests

```

**3. Install the remaining frozen project requirements:**
Make sure your `requirements.txt` contains `pyaudio`, `numpy`, `faster-whisper`, and `ollama`, then run:

```bash
pip install -r requirements.txt

```

### Step 5: Inject the Missing ONNX Feature Models

Since we bypassed the default `openwakeword` installation routine, we need to manually place the speech-processing and wake-word neural network models directly into the internal virtual environment folder structure where the script expects them.

Run this block of commands to automatically generate the paths and download the official pre-compiled assets:

```bash
# 1. Create the environment internal resource directory
mkdir -p ./lib/python3.13/site-packages/openwakeword/resources/models/

# 2. Download the Mel-Spectrogram Pre-processor Model
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx -O ./lib/python3.13/site-packages/openwakeword/resources/models/melspectrogram.onnx

# 3. Download the Audio Embedding Vector Engine Model
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx -O ./lib/python3.13/site-packages/openwakeword/resources/models/embedding_model.onnx

# 4. Download your active target Wake Word Model into your project folder
wget https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/hey_mycroft_v0.1.onnx -O hey_mycroft.onnx

```

### Step 6: Verify Configuration Health

Before starting up the full microphone stream loop, run this quick diagnostic inline test snippet to ensure all background microservices are linking together seamlessly without throwing errors:

```bash
python -c 'import openwakeword; import faster_whisper; import pyaudio; import ollama; print("🚀 ENVIRONMENT FULLY STABILIZED")'

```

*If it returns the rocket message, you are entirely good to go.*

---

## 🏃 Execution

To run your smart assistant in production or debugging mode, ensure your workspace environment is active and run:

```bash
python main.py

```

---

## 🛠️ Code Maintenance Blueprint (For `main.py`)

To prevent script crashes due to absolute hardware path tracking differences across filesystems, ensure your `main.py` utilizes absolute fallback bindings:

1. **The Missing Import Fix:** Verify that `import time` is explicitly added at the absolute top of `main.py` so the hardware loop micro-pauses do not fail.
2. **Absolute Wake Word Reference:** Confirm your `Model` initialization uses Python's path utility to read your local `hey_mycroft.onnx` file cleanly:
```python
import os

abs_model_path = os.path.abspath("./hey_mycroft.onnx")
oww_model = Model(
    wakeword_models=[abs_model_path],
    inference_framework="onnx"
)

```
