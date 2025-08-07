"""
Login window for gportal authentication
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pathlib


class LoginWindow:
    """Login window for gportal authentication"""

    def __init__(self, parent, auth_manager):
        self.parent = parent
        self.auth_manager = auth_manager
        self.login_successful = False

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("SatProcessor - Login")
        self.window.geometry("400x250")
        self.window.resizable(False, False)

        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")

        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (250 // 2)
        self.window.geometry(f"400x250+{x}+{y}")

        # Prevent closing
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Create UI
        self.create_widgets()

    def create_widgets(self):
        """Create login form widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="GPORTAL Authentication",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # Info label
        info_label = tk.Label(
            self.window,
            text="Please enter your GPORTAL credentials",
            font=("Arial", 10)
        )
        info_label.pack(pady=5)

        # Form frame
        form_frame = ttk.Frame(self.window)
        form_frame.pack(pady=20, padx=50, fill="both")

        # Username
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky="e", pady=5)
        self.username_entry = ttk.Entry(form_frame, width=25)
        self.username_entry.grid(row=0, column=1, pady=5, padx=10)

        # Password
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky="e", pady=5)
        self.password_entry = ttk.Entry(form_frame, width=25, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=10)

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=10)

        # Login button
        self.login_button = ttk.Button(
            button_frame,
            text="Login",
            command=self.on_login,
            width=15
        )
        self.login_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="blue"
        )
        self.status_label.pack(pady=5)

        # Focus on username
        self.username_entry.focus()

        # Bind Enter key
        self.window.bind('<Return>', lambda e: self.on_login())

    def on_login(self):
        """Handle login button click"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password")
            return

        # Disable form
        self.set_form_enabled(False)
        self.status_label.config(text="Authenticating...", fg="blue")

        # Run authentication in thread
        thread = threading.Thread(
            target=self.authenticate,
            args=(username, password)
        )
        thread.daemon = True
        thread.start()

    def authenticate(self, username, password):
        """Authenticate with gportal (runs in thread)"""
        try:
            # Test authentication
            success = self.auth_manager.test_credentials(username, password)

            if success:
                # Save credentials
                self.auth_manager.save_credentials(username, password)

                # Update UI in main thread
                self.window.after(0, self.on_login_success)
            else:
                self.window.after(0, self.on_login_failed, "Invalid credentials")

        except Exception as e:
            self.window.after(0, self.on_login_failed, str(e))

    def on_login_success(self):
        """Handle successful login"""
        self.login_successful = True
        self.status_label.config(text="Login successful!", fg="green")
        self.window.after(500, self.window.destroy)

    def on_login_failed(self, error_msg):
        """Handle failed login"""
        self.set_form_enabled(True)
        self.status_label.config(text=f"Login failed: {error_msg}", fg="red")
        self.password_entry.delete(0, tk.END)
        self.password_entry.focus()

    def set_form_enabled(self, enabled):
        """Enable/disable form controls"""
        state = "normal" if enabled else "disabled"
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.login_button.config(state=state)

    def on_cancel(self):
        """Handle cancel button click"""
        self.login_successful = False
        self.window.destroy()