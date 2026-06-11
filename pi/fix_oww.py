import os
import urllib.request
import openwakeword

# Dynamically locate the openwakeword installation inside your .venv
model_dir = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
os.makedirs(model_dir, exist_ok=True)

# Corrected URLs pointing to the 'master' branch
files = {
    "melspectrogram.onnx": "https://raw.githubusercontent.com/dscripka/openWakeWord/master/openwakeword/resources/models/melspectrogram.onnx",
    "embedding_model.onnx": "https://raw.githubusercontent.com/dscripka/openWakeWord/master/openwakeword/resources/models/embedding_model.onnx"
}

print("🛠️ Patching OpenWakeWord internal models...")

for filename, url in files.items():
    filepath = os.path.join(model_dir, filename)
    if not os.path.exists(filepath):
        print(f"⬇️ Downloading {filename} (this might take a moment)...")
        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"✅ Saved {filename}!")
        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
    else:
        print(f"✅ {filename} already exists.")
        
print("🚀 Patch complete! You can now run main.py")