"""
Path selection window for output directory
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pathlib
import sys


class PathSelector:
    """Window for selecting output directory"""

    def __init__(self, parent, path_manager):
        self.parent = parent
        self.path_manager = path_manager
        self.path_selected = False

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("SatProcessor - Select Output Directory")
        self.window.geometry("500x280")
        self.window.resizable(False, False)

        try:
            if getattr(sys, 'frozen', False):
                icon_path = pathlib.Path(sys._MEIPASS) / "assets" / "satellite_icon.ico"
            else:
                icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.window.winfo_screenheight() // 2) - (280 // 2)
        self.window.geometry(f"500x280+{x}+{y}")

        # Prevent closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Create UI
        self.create_widgets()

    def create_widgets(self):
        """Create path selection widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Select Output Directory",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # Info label
        info_label = tk.Label(
            self.window,
            text="Choose where to save processed satellite data",
            font=("Arial", 10)
        )
        info_label.pack(pady=5)

        # Path frame
        path_frame = ttk.Frame(self.window)
        path_frame.pack(pady=20, padx=20, fill="x")

        # Path entry
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(
            path_frame,
            textvariable=self.path_var,
            width=40,
            state="readonly"
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Browse button
        browse_button = ttk.Button(
            path_frame,
            text="Browse...",
            command=self.on_browse,
            width=12
        )
        browse_button.pack(side="right")

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # OK button
        self.ok_button = ttk.Button(
            button_frame,
            text="OK",
            command=self.on_ok,
            width=15,
            state="disabled"
        )
        self.ok_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

    def on_browse(self):
        """Handle browse button click"""
        # Get initial directory
        initial_dir = pathlib.Path.home()

        # Show directory dialog
        selected_dir = filedialog.askdirectory(
            parent=self.window,
            title="Select Output Directory",
            initialdir=initial_dir
        )

        if selected_dir:
            self.path_var.set(selected_dir)
            self.ok_button.config(state="normal")

    def on_ok(self):
        """Handle OK button click"""
        selected_path = self.path_var.get()

        if not selected_path:
            messagebox.showwarning("No Path", "Please select an output directory")
            return

        try:
            # Create output directory
            base_path = pathlib.Path(selected_path)
            output_dir = base_path / "SatData"

            # Try to create directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save path
            self.path_manager.save_output_path(output_dir)

            # Success
            self.path_selected = True
            messagebox.showinfo(
                "Success",
                f"Output directory created:\n{output_dir}"
            )
            self.window.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to create output directory:\n{str(e)}"
            )

    def on_cancel(self):
        """Handle cancel button click"""
        self.path_selected = False
        self.window.destroy()