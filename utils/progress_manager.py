import tkinter as tk
from tkinter import ttk
import threading
import time


class ProgressBarManager:
    """Manages time-based progress bars"""

    def __init__(self, progress_bar, status_label, duration_minutes=20):
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.duration_seconds = duration_minutes * 60
        self.running = False
        self.thread = None

    def start_progress(self, task_name="Processing"):
        """Start the progress bar animation"""
        if self.running:
            return

        self.running = True
        self.progress_bar['value'] = 0
        self.progress_bar.pack(pady=10, padx=20, fill="x")

        self.thread = threading.Thread(target=self._update_progress, args=(task_name,))
        self.thread.daemon = True
        self.thread.start()

    def stop_progress(self):
        """Stop the progress bar"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self.progress_bar.pack_forget()

    def _update_progress(self, task_name):
        """Update progress in background thread"""
        start_time = time.time()

        while self.running:
            elapsed = time.time() - start_time
            progress = min(95, (elapsed / self.duration_seconds) * 100)  # Max 95% until manual completion

            remaining_minutes = max(0, (self.duration_seconds - elapsed) / 60)

            # Update UI in main thread
            if self.progress_bar.winfo_exists():
                self.progress_bar.after(0, lambda: self.progress_bar.config(value=progress))

            if self.status_label.winfo_exists():
                self.status_label.after(0, lambda: self.status_label.config(
                    text=f"{task_name}... Est. {remaining_minutes:.0f} min remaining",
                    fg="blue"
                ))

            time.sleep(1)

            if elapsed >= self.duration_seconds:
                break

    def complete_progress(self, message="Complete!"):
        """Complete the progress bar"""
        self.running = False
        if self.progress_bar.winfo_exists():
            self.progress_bar.config(value=100)
        if self.status_label.winfo_exists():
            self.status_label.config(text=message, fg="green")

        # Hide progress bar after 2 seconds
        self.progress_bar.after(2000, self.stop_progress)