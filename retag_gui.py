#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import json
import os
import threading
import sys
from pathlib import Path
import queue
import retag_lib

# Configuration Setup
APP_NAME = "retagger"
def get_config_path():
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    config_dir = base / APP_NAME
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"

CONFIG_FILE = get_config_path()

def load_settings():
    defaults = {
        "appearance_mode": "dark",
        "last_directory": "",
        "delimiter": "/",
        "window_size": "700x600",
        "update_album_artist": False,
        "scan_subfolders": False
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                settings = json.load(f)
                return {**defaults, **settings}
        except:
            return defaults
    return defaults

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

class RedirectText(object):
    """Simple wrapper to redirect stdout/stderr to a tkinter widget"""
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass


class RetagApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        
        self.title("Retagger")
        self.geometry(self.settings.get("window_size", "700x600"))
        ctk.set_appearance_mode(self.settings.get("appearance_mode", "dark"))
        ctk.set_default_color_theme("blue")

        # Variables
        self.folder_path = tk.StringVar(value=self.settings.get("last_directory", ""))
        self.delimiter_var = tk.StringVar(value=self.settings.get("delimiter", "/"))
        self.set_album_artist_var = tk.BooleanVar(value=self.settings.get("update_album_artist", False))
        self.scan_subfolders_var = tk.BooleanVar(value=self.settings.get("scan_subfolders", False))
        self.write_changes_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.stop_requested = False
        self.log_queue = queue.Queue()

        self._create_widgets()
        self._check_queue()
        
        # Save settings on close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        # Update settings before saving
        self.settings["last_directory"] = self.folder_path.get()
        self.settings["delimiter"] = self.delimiter_var.get()
        self.settings["update_album_artist"] = self.set_album_artist_var.get()
        self.settings["scan_subfolders"] = self.scan_subfolders_var.get()
        self.settings["appearance_mode"] = ctk.get_appearance_mode().lower()
        self.settings["window_size"] = f"{self.winfo_width()}x{self.winfo_height()}"
        save_settings(self.settings)
        self.destroy()

    def _create_widgets(self):
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=60)
        header_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))
        
        header_label = ctk.CTkLabel(header_frame, text="Retagger", font=ctk.CTkFont(size=20, weight="bold"))
        header_label.pack(pady=15)

        # Appearance Toggle
        self.theme_btn = ctk.CTkButton(
            header_frame, 
            text="toggle dark/light",
            width=100,
            height=28,
            command=self._toggle_appearance_mode
        )
        self.theme_btn.place(relx=0.97, rely=0.5, anchor="e")

        # --- Main Controls ---
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        control_frame.grid_columnconfigure(1, weight=1)

        # Directory Selection
        ctk.CTkLabel(control_frame, text="Library Path:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.dir_entry = ctk.CTkEntry(control_frame, textvariable=self.folder_path, placeholder_text="Select music folder...")
        self.dir_entry.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
        
        browse_btn = ctk.CTkButton(control_frame, text="Browse Folder", command=self._browse_directory, width=120)
        browse_btn.grid(row=1, column=2, padx=15, pady=5)

        # Options
        options_subframe = ctk.CTkFrame(control_frame, fg_color="transparent")
        options_subframe.grid(row=2, column=0, columnspan=3, padx=10, pady=15, sticky="ew")

        ctk.CTkLabel(options_subframe, text="Delimiter:").grid(row=0, column=0, padx=(5, 2), pady=5, sticky="w")
        ctk.CTkEntry(options_subframe, textvariable=self.delimiter_var, width=50).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkCheckBox(options_subframe, text="Update Album Artist", variable=self.set_album_artist_var).grid(row=1, column=0, padx=5, pady=10, sticky="w")
        
        ctk.CTkCheckBox(options_subframe, text="Scan Subfolders", variable=self.scan_subfolders_var).grid(row=1, column=1, padx=5, pady=10, sticky="w")

        self.write_mode_switch = ctk.CTkSwitch(options_subframe, text="Write Mode (DANGEROUS)", variable=self.write_changes_var, progress_color="#ff4b4b")
        self.write_mode_switch.grid(row=1, column=2, padx=20, pady=10, sticky="w")

        # Action Button
        self.run_btn = ctk.CTkButton(control_frame, text="Start Processing", command=self._start_processing, height=40, font=ctk.CTkFont(weight="bold"))
        self.run_btn.grid(row=3, column=0, columnspan=3, padx=15, pady=(5, 15), sticky="ew")

        # --- Log Output ---
        log_container = ctk.CTkFrame(self)
        log_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        log_container.grid_columnconfigure(0, weight=1)
        log_container.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_container, text="Process Log", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.log_area = ctk.CTkTextbox(log_container, font=("monaco", 12))
        self.log_area.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

    def _browse_directory(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def _toggle_appearance_mode(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="toggle dark/light")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="toggle dark/light")

    def _log(self, message):
        self.log_queue.put(message + "\n")

    def _check_queue(self):
        """Poll the queue to update the UI from the thread safely"""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_area.insert(tk.END, msg)
            self.log_area.see(tk.END)
        
        self.after(100, self._check_queue)

    def _start_processing(self):
        if self.is_running:
            self.stop_requested = True
            self.run_btn.configure(state='disabled', text="Stopping...")
            return

        path_str = self.folder_path.get()
        if not path_str:
            messagebox.showwarning("Warning", "Please select a directory first.")
            return

        root_path = Path(path_str)
        if not root_path.exists():
            messagebox.showerror("Error", f"Path does not exist: {root_path}")
            return

        self.is_running = True
        self.stop_requested = False
        self.run_btn.configure(text="Stop Processing", fg_color="#ff4b4b", hover_color="#ff3333")
        self.log_area.delete("0.0", tk.END)
        
        mode_str = "WRITE MODE" if self.write_changes_var.get() else "DRY RUN"
        self._log(f"[START] Starting scan in {mode_str}...")
        self._log(f"  Target: {root_path}")
        self._log("-" * 50)

        # Run in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._process_thread, args=(root_path,))
        thread.start()

    def _process_thread(self, root_path):
        try:
            mp3s = retag_lib.get_mp3_files(root_path, recursive=self.scan_subfolders_var.get())
            if not mp3s:
                self._log(f"no .mp3 files found in target directory")
                if not self.scan_subfolders_var.get():
                    self._log(f"(maybe you forgot to enable 'Scan Subfolders'?)")
                self._finish_processing()
                return

            config = retag_lib.RetagConfig(
                delimiter=self.delimiter_var.get(),
                write=self.write_changes_var.get(),
                set_albumartist=self.set_album_artist_var.get(),
            )

            changed_count = 0
            scanned_count = 0
            total = len(mp3s)

            for p in mp3s:
                if self.stop_requested:
                    self._log("\n🛑 Stop requested by user.")
                    break
                    
                scanned_count += 1
                try:
                    result = retag_lib.process_file(p, config)
                    
                    if result:
                        if result.error:
                             self._log(f"[SKIP] {p.name}: {result.error}")
                        elif result.changed:
                            changed_count += 1
                            self._log(f"[CHANGE] {p.name}")
                            self._log(f"  Old: {result.old_artist} - {result.old_title}")
                            self._log(f"  New: {result.new_artist} - {result.new_title}")
                            self._log("")
                except Exception as e:
                     self._log(f"[ERROR] {p.name}: {e}")

            self._log("-" * 50)
            self._log(f"[DONE] Scanned {scanned_count} files")
            self._log(f"  Files matched/updated: {changed_count}")

        except Exception as e:
            self._log(f"[FATAL] {e}")
        
        finally:
            self._finish_processing()

    def _finish_processing(self):
        self.is_running = False
        self.stop_requested = False
        self.after(0, lambda: self.run_btn.configure(
            state='normal', 
            text="Start Processing",
            fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        ))


if __name__ == "__main__":
    app = RetagApp()
    app.mainloop()
