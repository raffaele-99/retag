#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path

def get_last_modified():
    files = ["retag_gui.py", "retag_lib.py"]
    return max(os.path.getmtime(f) for f in files if os.path.exists(f))

def main():
    script_path = "retag_gui.py"
    python_bin = "./venv/bin/python"
    
    print(f"🚀 Starting Hot Reload for {script_path}")
    print("Watching for changes in retag_gui.py and retag_lib.py...")
    
    last_mtime = get_last_modified()
    process = subprocess.Popen([python_bin, script_path])
    
    try:
        while True:
            time.sleep(0.5)
            current_mtime = get_last_modified()
            
            if current_mtime > last_mtime:
                print("\n🔄 Change detected! Restarting...")
                process.terminate()
                process.wait()
                process = subprocess.Popen([python_bin, script_path])
                last_mtime = current_mtime
    except KeyboardInterrupt:
        print("\n👋 Stopping preview...")
        process.terminate()

if __name__ == "__main__":
    main()
