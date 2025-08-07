"""
Main application window with function buttons
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import pathlib
'''
from gui.function_windows import (
    PolarCircleWindow,
    SingleStripWindow,
    Enhance8xWindow,
    PolarEnhanced8xWindow
)
'''
from gui.function_windows_server import (
    ServerPolarCircleWindow as PolarCircleWindow,
    ServerSingleStripWindow as SingleStripWindow,
    ServerEnhance8xWindow as Enhance8xWindow,
    ServerPolarEnhanced8xWindow as PolarEnhanced8xWindow
)
from utils.file_manager import FileManager


class MainWindow:
    """Main application window"""

    def __init__(self, root, auth_manager, path_manager):
        self.root = root
        self.auth_manager = auth_manager
        self.path_manager = path_manager
        self.file_manager = FileManager()

        # Set custom icon
        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Configure root window
        self.root.title("SatProcessor - Main Menu")
        self.root.geometry("600x600")
        self.root.resizable(False, False)

        # Center window
        self.center_window()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Create UI
        self.create_widgets()

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        """Create main window widgets"""
        # Title frame
        title_frame = tk.Frame(self.root, bg="#2c3e50")
        title_frame.pack(fill="x")

        # Title
        title_label = tk.Label(
            title_frame,
            text="SatProcessor",
            font=("Arial", 24, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=20)

        # Subtitle
        subtitle_label = tk.Label(
            title_frame,
            text="AMSR-2 Satellite Data Processing Tool",
            font=("Arial", 12),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        subtitle_label.pack(pady=(0, 20))

        # Main frame
        main_frame = tk.Frame(self.root, bg="#ecf0f1")
        main_frame.pack(fill="both", expand=True)

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=40)

        # Style for buttons
        style = ttk.Style()
        style.configure("Function.TButton", font=("Arial", 12), padding=10)

        # Function buttons
        buttons_data = [
            ("Polar Circle", "Create circular polar image", self.on_polar_circle),
            ("Single Strip", "Process single data strip", self.on_single_strip),
            ("8x Enhance", "Enhance quality 8x", self.on_enhance_8x),  # Removed "Coming Soon"
            ("8x Polar", "Enhanced polar circle", self.on_polar_8x),  # Removed "Coming Soon"
            ("Exit", "Close application", self.on_exit)
        ]

        for i, (text, tooltip, command) in enumerate(buttons_data):
            btn = ttk.Button(
                buttons_frame,
                text=text,
                command=command,
                style="Function.TButton",
                width=30
            )
            btn.pack(pady=10)

            # Add tooltip
            self.create_tooltip(btn, tooltip)

            # Disable placeholder functions
            if "Coming Soon" in tooltip:
                btn.config(state="disabled")

        # Status bar
        self.status_bar = tk.Label(
            main_frame,
            text=f"Output: {self.path_manager.get_output_path()}",
            bg="#34495e",
            fg="white",
            anchor="w",
            padx=10
        )
        self.status_bar.pack(side="bottom", fill="x")

    def create_tooltip(self, widget, text):
        """Create tooltip for widget"""

        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            label = tk.Label(
                tooltip,
                text=text,
                background="#333333",
                foreground="white",
                relief="solid",
                borderwidth=1,
                font=("Arial", 9)
            )
            label.pack()
            widget.tooltip = tooltip

        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def on_polar_circle(self):
        """Handle Polar Circle button click"""
        try:
            window = PolarCircleWindow(
                self.root,
                self.auth_manager,
                self.path_manager,
                self.file_manager
            )
            self.root.wait_window(window.window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Polar Circle window:\n{str(e)}")

    def on_single_strip(self):
        """Handle Single Strip button click"""
        try:
            window = SingleStripWindow(
                self.root,
                self.auth_manager,
                self.path_manager,
                self.file_manager
            )
            self.root.wait_window(window.window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Single Strip window:\n{str(e)}")

    def on_enhance_8x(self):
        """Handle 8x Enhance button click (placeholder)"""
        try:
            window = Enhance8xWindow(
                self.root,
                self.auth_manager,
                self.path_manager,
                self.file_manager
            )
            self.root.wait_window(window.window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open 8x Enhance window:\n{str(e)}")

    def on_polar_8x(self):
        """Handle 8x Polar button click (placeholder)"""
        try:
            window = PolarEnhanced8xWindow(
                self.root,
                self.auth_manager,
                self.path_manager,
                self.file_manager
            )
            self.root.wait_window(window.window)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open 8x Polar window:\n{str(e)}")
    '''
    def on_exit(self):
        """Handle Exit button click"""
        # Confirm exit
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            try:
                # Clean up temp files
                self.file_manager.cleanup_temp()
            except:
                pass
            finally:
                self.root.quit()
                sys.exit(0)
    '''
    def on_exit(self):
        """Handle Exit button click"""
        # Confirm exit
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            try:
                # Clean up temp files
                self.file_manager.cleanup_temp()

                # NEW: Cleanup server jobs
                from core.server_communicator import ServerCommunicator
                server_comm = ServerCommunicator(self.auth_manager)
                if server_comm.connect():
                    server_comm.cleanup_server_jobs()
                    server_comm.disconnect()

            except Exception as e:
                print(f"Error during cleanup: {e}")
            finally:
                self.root.quit()
                sys.exit(0)



    