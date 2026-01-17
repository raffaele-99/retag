#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from tkinter import ttk
import threading
import sys
from pathlib import Path
import queue
import retag_lib

class RedirectText(object):
    """Simple wrapper to redirect stdout/stderr to a tkinter widget"""
    def __init__(self, text_widget, queue):
        self.output = text_widget
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass


class RetagApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Retagger")
        self.root.geometry("600x500")

        # Variables
        self.folder_path = tk.StringVar()
        self.delimiter_var = tk.StringVar(value="/")
        self.set_album_artist_var = tk.BooleanVar(value=False)
        self.write_changes_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.log_queue = queue.Queue()

        self._create_widgets()
        self._check_queue()

    def _create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Directory Selection ---
        dir_frame = ttk.LabelFrame(main_frame, text="Directory", padding="5")
        dir_frame.pack(fill=tk.X, pady=5)

        dir_entry = ttk.Entry(dir_frame, textvariable=self.folder_path)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(dir_frame, text="Browse...", command=self._browse_directory)
        browse_btn.pack(side=tk.LEFT)

        # --- Options ---
        opts_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        opts_frame.pack(fill=tk.X, pady=5)

        # Delimiter
        ttk.Label(opts_frame, text="Delimiter:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(opts_frame, textvariable=self.delimiter_var, width=5).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        # Checkboxes
        ttk.Checkbutton(opts_frame, text="Set Album Artist to Main Artist", var=self.set_album_artist_var).grid(row=0, column=2, sticky=tk.W, padx=10, pady=2)
        
        # Write Mode (Red/bold to warn user)
        write_check = ttk.Checkbutton(opts_frame, text="Write Changes to Files", var=self.write_changes_var)
        write_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # --- Actions ---
        btn_frame = ttk.Frame(main_frame, padding="5")
        btn_frame.pack(fill=tk.X, pady=5)

        self.run_btn = ttk.Button(btn_frame, text="Start Processing", command=self._start_processing)
        self.run_btn.pack(side=tk.RIGHT)

        # --- Log Output ---
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _browse_directory(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def _log(self, message):
        self.log_queue.put(message + "\n")

    def _check_queue(self):
        """Poll the queue to update the UI from the thread safely"""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, msg)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        
        self.root.after(100, self._check_queue)

    def _start_processing(self):
        if self.is_running:
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
        self.run_btn.config(state='disabled')
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')
        
        mode_str = "WRITE MODE" if self.write_changes_var.get() else "DRY RUN"
        self._log(f"Starting scan in {mode_str}...")
        self._log(f"Target: {root_path}")
        self._log("-" * 40)

        # Run in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._process_thread, args=(root_path,))
        thread.start()

    def _process_thread(self, root_path):
        try:
            mp3s = retag_lib.get_mp3_files(root_path)
            if not mp3s:
                self._log("No .mp3 files found in directory.")
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
                scanned_count += 1
                # Update status bar occasionally or for every file if preferred, 
                # but direct TK access isn't thread safe. Use queue or just log result.
                
                try:
                    result = retag_lib.process_file(p, config)
                    
                    if result:
                        if result.error:
                             self._log(f"[Skipped] {p.name}: {result.error}")
                        elif result.changed:
                            changed_count += 1
                            self._log(f"[Change] {p.name}")
                            self._log(f"  Old: {result.old_artist} - {result.old_title}")
                            self._log(f"  New: {result.new_artist} - {result.new_title}")
                            self._log("")
                except Exception as e:
                     self._log(f"[Error] Processing {p.name}: {e}")

            self._log("-" * 40)
            self._log(f"Done. Scanned {scanned_count} files.")
            self._log(f"Files matched/changed: {changed_count}")

        except Exception as e:
            self._log(f"CRITICAL ERROR: {e}")
        
        finally:
            self._finish_processing()

    def _finish_processing(self):
        self.is_running = False
        # Schedule button re-enable on main thread
        self.root.after(0, lambda: self.run_btn.config(state='normal'))
        self.root.after(0, lambda: self.status_var.set("Processing complete."))


def main():
    root = tk.Tk()
    app = RetagApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
