#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path

def get_last_modified():
    files = [
        "src/retagger/gui.py",
        "src/retagger/core.py",
        "src/retagger/__main__.py"
    ]
    return max(os.path.getmtime(f) for f in files if os.path.exists(f))

def main():
    script_path = "src/retagger/gui.py"
    python_bin = "./venv/bin/python"
    
    print(f"🚀 Starting Hot Reload for {script_path}")
    print("Watching for changes in src/retagger/...")
    
    last_mtime = get_last_modified()
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    process = subprocess.Popen([python_bin, script_path], env=env)
    
    try:
        while True:
            time.sleep(0.5)
            current_mtime = get_last_modified()
            
            if current_mtime > last_mtime:
                print("\n🔄 Change detected! Restarting...")
                process.terminate()
                process.wait()
                process = subprocess.Popen([python_bin, script_path], env=env)
                last_mtime = current_mtime
    except KeyboardInterrupt:
        print("\n👋 Stopping preview...")
        process.terminate()

if __name__ == "__main__":
    main()
