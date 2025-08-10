#!/usr/bin/env python3
"""
SatelliteProcessor - Main Application Entry Point
A desktop application for processing AMSR-2 satellite data
"""

import os
import sys
import pathlib
import tkinter as tk
from tkinter import messagebox
import sys


# Add this function after imports
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Add project root to path
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = pathlib.Path(sys._MEIPASS)
else:
    PROJECT_ROOT = pathlib.Path(__file__).parent

# Import our modules
from gui.login_window import LoginWindow
from gui.path_selector import PathSelector
from gui.main_window import MainWindow
from core.auth_manager import AuthManager
from core.path_manager import PathManager
from utils.file_manager import FileManager


class SatelliteProcessor:
    """Main application class that handles initialization and flow"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide root window initially

        # Initialize managers
        self.auth_manager = AuthManager()
        self.path_manager = PathManager()
        self.file_manager = FileManager()

        # Application state
        self.authenticated = False
        self.output_path_set = False

    def run(self):
        """Main application flow"""
        try:
            # Start the main loop first
            self.root.after(100, self.initialize_app)
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Application error: {str(e)}")
            self.cleanup_and_exit()

    def initialize_app(self):
        """Initialize app after mainloop starts"""
        try:
            # Step 1: Check and handle authentication
            if not self.check_authentication():
                self.show_login()
                return

            # Step 2: Check and handle output path
            if not self.check_output_path():
                self.show_path_selector()
                return

            # Step 3: Show main window
            self.show_main_window()

        except Exception as e:
            messagebox.showerror("Error", f"Initialization error: {str(e)}")
            self.cleanup_and_exit()

    def check_authentication(self):
        """Check if valid credentials exist"""
        if self.auth_manager.has_credentials():
            # Credentials exist, validate them
            try:
                username, password = self.auth_manager.get_credentials()
                # Here we'll validate with gportal
                # For now, assume valid if credentials exist
                self.authenticated = True
                return True
            except:
                return False
        return False

    def check_output_path(self):
        """Check if output path is set"""
        if self.path_manager.has_output_path():
            output_path = self.path_manager.get_output_path()
            if output_path and output_path.exists():
                self.output_path_set = True
                return True
        return False

    def show_login(self):
        """Show login window"""

        def on_login_complete():
            if hasattr(self, '_login_window') and self._login_window.login_successful:
                self.authenticated = True
                self.root.after(100, self.initialize_app)
            else:
                self.cleanup_and_exit()

        self._login_window = LoginWindow(self.root, self.auth_manager)
        self.root.wait_window(self._login_window.window)
        on_login_complete()

    def show_path_selector(self):
        """Show path selection window"""

        def on_path_complete():
            if hasattr(self, '_path_window') and self._path_window.path_selected:
                self.output_path_set = True
                self.root.after(100, self.initialize_app)
            else:
                self.cleanup_and_exit()

        self._path_window = PathSelector(self.root, self.path_manager)
        self.root.wait_window(self._path_window.window)
        on_path_complete()

    def show_main_window(self):
        """Show main application window"""
        # Clean up temp directory first
        self.file_manager.cleanup_temp()

        # Show main window
        self.root.deiconify()
        main_window = MainWindow(self.root, self.auth_manager, self.path_manager)
        self.root.mainloop()

    def cleanup_and_exit(self):
        """Clean up and exit application"""
        try:
            self.file_manager.cleanup_temp()
        except:
            pass
        self.root.quit()
        sys.exit(0)


def main():
    """Main entry point"""
    # Create necessary directories
    config_dir = PROJECT_ROOT / "config"
    temp_dir = PROJECT_ROOT / "temp"
    assets_dir = PROJECT_ROOT / "assets"

    config_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)
    assets_dir.mkdir(exist_ok=True)

    # Run application
    app = SatelliteProcessor()
    app.run()


if __name__ == "__main__":
    main()