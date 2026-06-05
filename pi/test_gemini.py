import os
import importlib
from unittest.mock import patch, Mock

# Ensure example env is set for module reload
os.environ.setdefault("GEMINI_API_KEY", "testkey")
os.environ.setdefault("GEMINI_ENDPOINT", "https://example.com/gemini")

import main
importlib.reload(main)

def fake_post(url, headers=None, json=None, timeout=None):
    mock_resp = Mock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {"message": {"content": "Test response from Gemini"}}
    return mock_resp

with patch('requests.post', fake_post):
    res = main.call_gemini_chat(messages=[{"role":"user","content":"Hello"}], model="gemini-test", stream=False)
    content = res.get("message", {}).get("content", "")
    print("GEMINI RESPONSE:", content)
    if "Test response from Gemini" in content:
        print("PASS")
        raise SystemExit(0)
    else:
        print("FAIL")
        raise SystemExit(2)
