"""
Modified function windows for server-based processing
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
import time
from pathlib import Path
import pathlib

from utils.validators import DateValidator
from core.server_communicator import ServerCommunicator
from core.gportal_client import GPortalClient
from utils.progress_manager import ProgressBarManager


class ServerBaseFunctionWindow:
    """Base class for server-based function windows"""

    def __init__(self, parent, auth_manager, path_manager, file_manager, title):
        self.parent = parent
        self.auth_manager = auth_manager
        self.path_manager = path_manager
        self.file_manager = file_manager

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"SatProcessor - {title}")
        self.window.resizable(False, False)
        '''
        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")
        '''
        # Prevent parent interaction
        self.window.transient(parent)
        self.window.grab_set()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initialize server communicator
        self.server_comm = ServerCommunicator(auth_manager)
        self.current_job_id = None

        # Progress bar manager
        self.progress_manager = None

        # ADD THIS LINE - Initialize gportal client for file searching
        self.gportal_client = GPortalClient(auth_manager)

    def center_window(self, width=600, height=400):
        """Center the window on screen"""
        self.window.geometry(f"{width}x{height}")
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def on_close(self):
        """Handle window close"""
        if hasattr(self, 'server_comm'):
            # Only cleanup if we have an active job
            if hasattr(self, 'current_job_id') and self.current_job_id:
                print(f"Cleaning up job: {self.current_job_id}")
            self.server_comm.disconnect()
        self.window.destroy()

    def show_progress(self, message):
        """Show progress message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message, fg="blue")
            self.window.update()

    def show_error(self, message):
        """Show error message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"Error: {message}", fg="red")
        messagebox.showerror("Error", message)


    def show_success(self, message):
        """Show success message"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message, fg="green")
        messagebox.showinfo("Success", message)

    def submit_job_to_server(self, function: str, parameters: dict):
        """Submit job to server and monitor progress"""
        try:
            # Set up progress manager with different durations for different functions
            durations = {
                'polar_circle': 15,  # 15 minutes
                'single_strip': 2,  # 2 minutes
                'enhance_8x': 33,  # 18 minutes
                'polar_enhanced_8x': 140  # 25 minutes
            }

            duration = durations.get(function, 20)
            self.progress_manager = ProgressBarManager(
                self.progress_bar,
                self.status_label,
                duration_minutes=duration
            )

            # Start progress bar
            self.progress_manager.start_progress("Processing on server")

            # Connect to server
            if not self.server_comm.connect():
                self.progress_manager.stop_progress()
                self.show_error("Failed to connect to server")
                return

            # Submit job
            job_id = self.server_comm.submit_job(function, parameters)

            if not job_id:
                self.progress_manager.stop_progress()
                self.show_error("Failed to submit job")
                return

            self.current_job_id = job_id

            # Monitor job progress
            def progress_callback(status):
                pass  # We're using time-based progress, not real progress

            # Wait for completion
            final_status = self.server_comm.wait_for_job(
                job_id, timeout=36000, progress_callback=progress_callback
            )

            if not final_status:
                self.progress_manager.stop_progress()
                self.show_error("Job timed out")
                return

            if final_status['status'] == 'completed':
                # Complete progress bar
                self.progress_manager.complete_progress("Downloading results...")

                # Download results
                output_base = self.path_manager.get_output_path()
                job_output_dir = output_base / job_id

                success = self.server_comm.download_results(job_id, job_output_dir)

                if success:
                    self.progress_manager.complete_progress("Processing complete!")
                    self.show_success(f"Processing complete!\nResults saved to:\n{job_output_dir}")
                    self.server_comm.cleanup_job(job_id)
                else:
                    self.progress_manager.stop_progress()
                    self.show_error("Failed to download results")
            else:
                self.progress_manager.stop_progress()
                self.show_error("Job failed on server")

        except Exception as e:
            if self.progress_manager:
                self.progress_manager.stop_progress()
            self.show_error(f"Server processing failed: {str(e)}")
        finally:
            # Re-enable controls
            self.window.after(0, self.enable_controls)


class ServerPolarCircleWindow(ServerBaseFunctionWindow):
    """Window for server-based polar circle creation"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "Polar Circle (Server)")
        self.center_window(500, 400)
        self.create_widgets()
        '''
        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")
        '''
    def create_widgets(self):
        """Create polar circle widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Create Circular Polar Image (Server Processing)",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # Form frame
        form_frame = ttk.Frame(self.window)
        form_frame.pack(pady=20, padx=50)

        # Date input
        ttk.Label(form_frame, text="Date (MM/DD/YYYY):").grid(row=0, column=0, sticky="e", pady=10)
        self.date_entry = ttk.Entry(form_frame, width=20)
        self.date_entry.grid(row=0, column=1, pady=10, padx=10)

        # Set today's date as default
        today = datetime.date.today()
        self.date_entry.insert(0, today.strftime("%m/%d/%Y"))

        # Orbit type selection
        ttk.Label(form_frame, text="Orbit Type:").grid(row=1, column=0, sticky="e", pady=10)

        orbit_frame = ttk.Frame(form_frame)
        orbit_frame.grid(row=1, column=1, pady=10, padx=10, sticky="w")

        self.orbit_var = tk.StringVar(value="A")

        ttk.Radiobutton(
            orbit_frame,
            text="Ascending",
            variable=self.orbit_var,
            value="A"
        ).pack(side="left", padx=5)

        ttk.Radiobutton(
            orbit_frame,
            text="Descending",
            variable=self.orbit_var,
            value="D"
        ).pack(side="left", padx=5)

        # Pole selection
        ttk.Label(form_frame, text="Pole:").grid(row=2, column=0, sticky="e", pady=10)

        pole_frame = ttk.Frame(form_frame)
        pole_frame.grid(row=2, column=1, pady=10, padx=10, sticky="w")

        self.pole_var = tk.StringVar(value="N")

        ttk.Radiobutton(
            pole_frame,
            text="North",
            variable=self.pole_var,
            value="N"
        ).pack(side="left", padx=5)

        ttk.Radiobutton(
            pole_frame,
            text="South",
            variable=self.pole_var,
            value="S"
        ).pack(side="left", padx=5)

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="Process on Server",
            command=self.on_process,
            width=15
        )
        self.process_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_close,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='determinate',
            maximum=100
        )

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and select options",
            font=("Arial", 9),
            fg="black"
        )
        self.status_label.pack(pady=10)

    def on_process(self):
        """Handle process button click"""
        # Get inputs
        date_str = self.date_entry.get().strip()
        orbit_type = self.orbit_var.get()
        pole = self.pole_var.get()

        # Validate date
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Disable controls
        self.process_button.config(state="disabled")
        self.date_entry.config(state="disabled")

        # Prepare parameters
        parameters = {
            'date': date_obj.strftime("%Y-%m-%d"),
            'orbit_type': orbit_type,
            'pole': pole
        }

        # Process in thread
        thread = threading.Thread(
            target=self.submit_job_to_server,
            args=('polar_circle', parameters)
        )
        thread.daemon = True
        thread.start()

    def enable_controls(self):
        """Re-enable form controls"""
        self.process_button.config(state="normal")
        self.date_entry.config(state="normal")


class ServerSingleStripWindow(ServerBaseFunctionWindow):
    """Window for server-based single strip processing"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "Single Strip (Server)")
        self.center_window(600, 500)
        self.available_files = []
        self.create_widgets()
        '''
        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")
        '''
    def create_widgets(self):
        """Create single strip widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Process Single Data Strip (Server Processing)",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # Date frame
        date_frame = ttk.Frame(self.window)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Date (MM/DD/YYYY):").pack(side="left", padx=5)
        self.date_entry = ttk.Entry(date_frame, width=20)
        self.date_entry.pack(side="left", padx=5)

        # Set today's date as default
        today = datetime.date.today()
        self.date_entry.insert(0, today.strftime("%m/%d/%Y"))

        # Check button
        self.check_button = ttk.Button(
            date_frame,
            text="Check Files",
            command=self.on_check_files,
            width=12
        )
        self.check_button.pack(side="left", padx=5)

        # Files frame
        files_frame = ttk.LabelFrame(self.window, text="Available Files", padding=10)
        files_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Listbox with scrollbar
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.files_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            font=("Courier", 9)
        )
        self.files_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.files_listbox.yview)

        # Selection info
        self.selection_label = ttk.Label(files_frame, text="Select a file to process")
        self.selection_label.pack(pady=5)

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="Process on Server",
            command=self.on_process,
            width=15,
            state="disabled"
        )
        self.process_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_close,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='determinate',
            maximum=100
        )

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and select options",
            font=("Arial", 9),
            fg="black"
        )
        self.status_label.pack(pady=10)

        # Bind selection event
        self.files_listbox.bind('<<ListboxSelect>>', self.on_file_selected)

    def on_check_files(self):
        """Check available files for the date"""
        # Get date
        date_str = self.date_entry.get().strip()

        # Validate date
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Disable controls
        self.check_button.config(state="disabled")
        self.date_entry.config(state="disabled")

        # Check in thread
        thread = threading.Thread(
            target=self.check_files_thread,
            args=(date_obj,)
        )
        thread.daemon = True
        thread.start()

    def check_files_thread(self, date_obj):
        """Check files in thread"""
        try:
            # Update status
            self.window.after(0, self.show_progress, "Checking available files...")

            # Convert date
            date_str = date_obj.strftime("%Y-%m-%d")

            # Get all files for date using GPORTAL
            all_files = self.gportal_client.list_files_for_date(date_str)

            if not all_files:
                self.window.after(0, self.show_error, "No files available for this date")
                return

            # Update listbox
            self.window.after(0, self.update_files_list, all_files)

        except Exception as e:
            self.window.after(0, self.show_error, f"Failed to check files: {str(e)}")

        finally:
            # Re-enable controls
            self.window.after(0, lambda: self.check_button.config(state="normal"))
            self.window.after(0, lambda: self.date_entry.config(state="normal"))

    def update_files_list(self, files):
        """Update files listbox"""
        self.available_files = files
        self.files_listbox.delete(0, tk.END)

        for i, file_info in enumerate(files):
            display_text = f"{i + 1:3d}. {file_info['name']}"
            self.files_listbox.insert(tk.END, display_text)

        self.status_label.config(text=f"Found {len(files)} files", fg="green")
        self.selection_label.config(text="Select a file to process")

    def on_file_selected(self, event):
        """Handle file selection"""
        selection = self.files_listbox.curselection()
        if selection:
            index = selection[0]
            file_info = self.available_files[index]
            self.selection_label.config(text=f"Selected: {file_info['name']}")
            self.process_button.config(state="normal")
        else:
            self.process_button.config(state="disabled")

    def on_process(self):
        """Process selected file"""
        selection = self.files_listbox.curselection()
        if not selection:
            self.show_error("Please select a file")
            return

        index = selection[0]
        file_info = self.available_files[index]

        # Get date
        date_str = self.date_entry.get().strip()
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Disable controls
        self.process_button.config(state="disabled")
        self.files_listbox.config(state="disabled")

        # Prepare parameters
        parameters = {
            'date': date_obj.strftime("%Y-%m-%d"),
            'file_index': index,
            'file_name': file_info['name']
        }

        # Process in thread
        thread = threading.Thread(
            target=self.submit_job_to_server,
            args=('single_strip', parameters)
        )
        thread.daemon = True
        thread.start()

    def enable_controls(self):
        """Re-enable controls"""
        self.process_button.config(state="normal")
        self.files_listbox.config(state="normal")

# Similar implementations for Enhance8x and PolarEnhanced8x windows
# These would follow the same pattern but with appropriate parameters

"""
Server-based enhanced (8x) function windows
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
from pathlib import Path

from utils.validators import DateValidator
from core.server_communicator import ServerCommunicator


class ServerEnhance8xWindow(ServerBaseFunctionWindow):
    """Window for server-based 8x enhancement of single strip"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "8x Enhancement (Server)")
        self.center_window(600, 700)
        self.available_files = []
        self.create_widgets()

        '''
        icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
        if icon_path.exists():
            self.window.iconbitmap(str(icon_path))
        '''

    def create_widgets(self):
        """Create 8x enhancement widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="8x Quality Enhancement (Server GPU Processing)",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # GPU info
        gpu_label = tk.Label(
            self.window,
            text="This function requires GPU processing on server",
            font=("Arial", 10, "italic"),
            fg="blue"
        )
        gpu_label.pack(pady=5)

        # Date frame
        date_frame = ttk.Frame(self.window)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Date (MM/DD/YYYY):").pack(side="left", padx=5)
        self.date_entry = ttk.Entry(date_frame, width=20)
        self.date_entry.pack(side="left", padx=5)

        # Set today's date as default
        today = datetime.date.today()
        self.date_entry.insert(0, today.strftime("%m/%d/%Y"))

        # Check button
        self.check_button = ttk.Button(
            date_frame,
            text="Check Files",
            command=self.on_check_files,
            width=12
        )
        self.check_button.pack(side="left", padx=5)

        # Files frame
        files_frame = ttk.LabelFrame(self.window, text="Available Files", padding=10)
        files_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Listbox with scrollbar
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.files_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            font=("Courier", 9)
        )
        self.files_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.files_listbox.yview)

        # Selection info
        self.selection_label = ttk.Label(files_frame, text="Select a file to enhance")
        self.selection_label.pack(pady=5)

        # Processing options
        options_frame = ttk.LabelFrame(self.window, text="Enhancement Options", padding=10)
        options_frame.pack(pady=10, padx=20, fill="x")

        self.percentile_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Apply 1-99 percentile filter for better contrast",
            variable=self.percentile_var
        ).pack(anchor="w")

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="Enhance 8x on Server",
            command=self.on_process,
            width=20,
            state="disabled"
        )
        self.process_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_close,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='determinate',
            maximum=100
        )

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and select options",
            font=("Arial", 9),
            fg="black"
        )
        self.status_label.pack(pady=10)

        # Bind selection event
        self.files_listbox.bind('<<ListboxSelect>>', self.on_file_selected)

    def on_check_files(self):
        """Check available files on server"""
        date_str = self.date_entry.get().strip()

        # Validate date
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Disable controls
        self.check_button.config(state="disabled")
        self.date_entry.config(state="disabled")

        # Check files in thread
        thread = threading.Thread(
            target=self._check_files_thread,
            args=(date_obj,)
        )
        thread.daemon = True
        thread.start()

    def _check_files_thread(self, date_obj):
        """Check files on server (runs in thread)"""
        try:
            self.window.after(0, self.show_progress, "Checking available files...")

            # Convert date and use real GPORTAL search
            date_str = date_obj.strftime("%Y-%m-%d")
            all_files = self.gportal_client.list_files_for_date(date_str)

            if not all_files:
                self.window.after(0, self.show_error, "No files available for this date")
                return

            self.window.after(0, self.update_files_list, all_files)

        except Exception as e:
            self.window.after(0, self.show_error, f"Failed to check files: {str(e)}")
        finally:
            self.window.after(0, lambda: self.check_button.config(state="normal"))
            self.window.after(0, lambda: self.date_entry.config(state="normal"))

    def update_files_list(self, files):
        """Update files listbox"""
        self.available_files = files
        self.files_listbox.delete(0, tk.END)

        for i, file_info in enumerate(files):
            display_text = f"{i + 1:3d}. {file_info['name']}"
            self.files_listbox.insert(tk.END, display_text)

        self.status_label.config(text=f"Found {len(files)} files", fg="green")
        self.selection_label.config(text="Select a file to enhance")

    def on_file_selected(self, event):
        """Handle file selection"""
        selection = self.files_listbox.curselection()
        if selection:
            index = selection[0]
            file_info = self.available_files[index]
            self.selection_label.config(text=f"Selected: {file_info['name']}")
            self.process_button.config(state="normal")
        else:
            self.process_button.config(state="disabled")

    def on_process(self):
        """Process selected file with 8x enhancement"""
        selection = self.files_listbox.curselection()
        if not selection:
            self.show_error("Please select a file")
            return

        index = selection[0]
        file_info = self.available_files[index]

        # Get date
        date_str = self.date_entry.get().strip()
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Disable controls
        self.process_button.config(state="disabled")
        self.files_listbox.config(state="disabled")

        # Prepare parameters
        parameters = {
            'date': date_obj.strftime("%Y-%m-%d"),
            'file_index': index,
            'file_name': file_info['name'],
            'percentile_filter': self.percentile_var.get()
        }

        # Process in thread
        thread = threading.Thread(
            target=self.submit_job_to_server,
            args=('enhance_8x', parameters)
        )
        thread.daemon = True
        thread.start()

    def enable_controls(self):
        """Re-enable controls"""
        self.process_button.config(state="normal")
        self.files_listbox.config(state="normal")


class ServerPolarEnhanced8xWindow(ServerBaseFunctionWindow):
    """Window for server-based 8x enhanced polar circle"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "8x Enhanced Polar (Server)")
        self.center_window(500, 600)
        self.create_widgets()
        '''
        try:
            icon_path = pathlib.Path(__file__).parent.parent / "assets" / "satellite_icon.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"Could not load icon: {e}")
        '''

    def create_widgets(self):
        """Create 8x enhanced polar widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="8x Enhanced Polar Circle (Server GPU Processing)",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        # GPU warning
        gpu_label = tk.Label(
            self.window,
            text="⚠️ This is the most GPU-intensive function\nProcessing may take 10-30 minutes",
            font=("Arial", 10, "italic"),
            fg="red"
        )
        gpu_label.pack(pady=5)

        # Form frame
        form_frame = ttk.Frame(self.window)
        form_frame.pack(pady=20, padx=50)

        # Date input
        ttk.Label(form_frame, text="Date (MM/DD/YYYY):").grid(row=0, column=0, sticky="e", pady=10)
        self.date_entry = ttk.Entry(form_frame, width=20)
        self.date_entry.grid(row=0, column=1, pady=10, padx=10)

        # Set today's date
        today = datetime.date.today()
        self.date_entry.insert(0, today.strftime("%m/%d/%Y"))

        # Orbit type selection
        ttk.Label(form_frame, text="Orbit Type:").grid(row=1, column=0, sticky="e", pady=10)

        orbit_frame = ttk.Frame(form_frame)
        orbit_frame.grid(row=1, column=1, pady=10, padx=10, sticky="w")

        self.orbit_var = tk.StringVar(value="A")

        ttk.Radiobutton(
            orbit_frame,
            text="Ascending",
            variable=self.orbit_var,
            value="A"
        ).pack(side="left", padx=5)

        ttk.Radiobutton(
            orbit_frame,
            text="Descending",
            variable=self.orbit_var,
            value="D"
        ).pack(side="left", padx=5)

        # Pole selection
        ttk.Label(form_frame, text="Pole:").grid(row=2, column=0, sticky="e", pady=10)

        pole_frame = ttk.Frame(form_frame)
        pole_frame.grid(row=2, column=1, pady=10, padx=10, sticky="w")

        self.pole_var = tk.StringVar(value="N")

        ttk.Radiobutton(
            pole_frame,
            text="North",
            variable=self.pole_var,
            value="N"
        ).pack(side="left", padx=5)

        ttk.Radiobutton(
            pole_frame,
            text="South",
            variable=self.pole_var,
            value="S"
        ).pack(side="left", padx=5)

        # Processing info
        info_frame = ttk.LabelFrame(self.window, text="Processing Information", padding=10)
        info_frame.pack(pady=10, padx=20, fill="x")

        info_text = """• Downloads all satellite passes for the day
• Enhances each pass to 8x resolution
• Creates 14400×14400 pixel polar projection
• Output grid resolution: 1.25 km"""

        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w")

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="Process on Server",
            command=self.on_process,
            width=20
        )
        self.process_button.pack(side="left", padx=5)

        # Cancel button
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_close,
            width=15
        )
        cancel_button.pack(side="left", padx=5)

        # Progress bar (hidden initially)
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode='determinate',
            maximum=100
        )

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and select options",
            font=("Arial", 9),
            fg="black"
        )
        self.status_label.pack(pady=10)

    def on_process(self):
        """Process 8x enhanced polar circle"""
        # Get inputs
        date_str = self.date_entry.get().strip()
        orbit_type = self.orbit_var.get()
        pole = self.pole_var.get()

        # Validate date
        validator = DateValidator()
        is_valid, error_msg, date_obj = validator.validate_date(date_str)

        if not is_valid:
            self.show_error(error_msg)
            return

        # Warn about processing time
        result = messagebox.askyesno(
            "Long Processing Time",
            "This function may take 10-30 minutes to complete.\n\n"
            "The application will notify you when finished.\n\n"
            "Continue?",
            icon="warning"
        )

        if not result:
            return

        # Disable controls
        self.process_button.config(state="disabled")
        self.date_entry.config(state="disabled")

        # Prepare parameters
        parameters = {
            'date': date_obj.strftime("%Y-%m-%d"),
            'orbit_type': orbit_type,
            'pole': pole
        }

        # Process in thread
        thread = threading.Thread(
            target=self.submit_job_to_server,
            args=('polar_enhanced_8x', parameters)
        )
        thread.daemon = True
        thread.start()

    def enable_controls(self):
        """Re-enable form controls"""
        self.process_button.config(state="normal")
        self.date_entry.config(state="normal")