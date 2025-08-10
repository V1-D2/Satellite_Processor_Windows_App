"""
Individual function windows for each processing task
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import threading
from utils.validators import DateValidator
from core.gportal_client import GPortalClient
from core.image_processor import ImageProcessor
from core.data_handler import DataHandler
from utils.device_utils import get_best_device
import numpy as np
import sys


try:
    import torch
    device, device_name = get_best_device()
    print(f"Using device: {device_name}")
    print(f"PyTorch version: {torch.__version__}")
except ImportError:
    print("PyTorch not available")
    torch = None
    device = None
    device_name = "None"

class BaseFunctionWindow:
    """Base class for function windows"""

    def __init__(self, parent, auth_manager, path_manager, file_manager, title):
        self.parent = parent
        self.auth_manager = auth_manager
        self.path_manager = path_manager
        self.file_manager = file_manager

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"SatProcessor - {title}")
        self.window.resizable(False, False)

        # Prevent parent interaction
        self.window.transient(parent)
        self.window.grab_set()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initialize components
        self.gportal_client = GPortalClient(auth_manager)
        self.image_processor = ImageProcessor()
        self.data_handler = DataHandler()

    def center_window(self, width=600, height=400):
        """Center the window on screen"""
        self.window.geometry(f"{width}x{height}")
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def on_close(self):
        """Handle window close"""
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


class PolarCircleWindow(BaseFunctionWindow):
    """Window for creating circular polar images"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "Polar Circle")
        self.center_window(500, 350)
        self.create_widgets()

    def create_widgets(self):
        """Create polar circle widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Create Circular Polar Image",
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

        # Pole selection (for future use)
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
            text="Process",
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

        # Process in thread
        thread = threading.Thread(
            target=self.process_polar_circle,
            args=(date_obj, orbit_type, pole)
        )
        thread.daemon = True
        thread.start()

    def process_polar_circle(self, date_obj, orbit_type, pole):
        """Process polar circle creation (runs in thread)"""
        try:
            # Update status
            self.window.after(0, self.show_progress, "Connecting to GPORTAL...")

            # Convert date to format needed by gportal
            date_str = date_obj.strftime("%Y-%m-%d")

            # Check data availability
            self.window.after(0, self.show_progress, f"Checking data for {date_str}...")
            available_files = self.gportal_client.check_availability(date_str, orbit_type)

            if not available_files or len(available_files) == 0:
                self.window.after(0, self.show_error, "No data available for this date")
                return

            self.window.after(0, self.show_progress, f"Found {len(available_files)} files. Downloading...")

            # Download files to temp directory
            temp_dir = self.file_manager.get_temp_dir()
            downloaded_files = self.gportal_client.download_files(
                date_str,
                orbit_type,
                temp_dir,
                progress_callback=lambda msg: self.window.after(0, self.show_progress, msg)
            )

            if not downloaded_files:
                self.window.after(0, self.show_error, "Failed to download files")
                return

            # Process files to create polar image
            self.window.after(0, self.show_progress, "Creating polar image...")

            # Create output directory
            output_base = self.path_manager.get_output_path()
            orbit_char = "A" if orbit_type == "A" else "D"
            output_dir = output_base / f"{date_str}-{orbit_char}-{pole}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Process with image processor
            result_data = self.image_processor.create_polar_image(
                downloaded_files,
                orbit_type,
                pole
            )

            if result_data is None:
                self.window.after(0, self.show_error, "Failed to create polar image")
                return

            # Save outputs
            self.window.after(0, self.show_progress, "Saving results...")

            # Save color image (turbo colormap)
            color_path = output_dir / "polar_color.png"
            self.image_processor.save_color_image(result_data, color_path)

            # Save color image (percentile filtered)
            color_percentile_path = output_dir / "polar_color_percentile.png"
            self.image_processor.save_color_image_percentile(result_data, color_percentile_path)

            # Save viridis image
            viridis_path = output_dir / "polar_viridis.png"  # or appropriate name
            self.image_processor.save_viridis_image(result_data, viridis_path)

            # Save grayscale image
            gray_path = output_dir / "polar_grayscale.png"
            self.image_processor.save_grayscale_image(result_data, gray_path)

            # Save grayscale image (percentile filtered)
            gray_percentile_path = output_dir / "polar_grayscale_percentile.png"
            self.image_processor.save_grayscale_image_percentile(result_data, gray_percentile_path)

            # Save temperature array
            temp_path = output_dir / "temperature_data.npz"
            self.data_handler.save_temperature_array(result_data, temp_path)

            # Clean up temp files
            self.window.after(0, self.show_progress, "Cleaning up...")
            self.file_manager.cleanup_temp()

            # Success
            self.window.after(
                0,
                self.show_success,
                f"Processing complete!\nResults saved to:\n{output_dir}"
            )

            # Close window after short delay
            self.window.after(1500, self.on_close)

        except Exception as e:
            self.window.after(0, self.show_error, f"Processing failed: {str(e)}")

        finally:
            # Re-enable controls
            self.window.after(0, self.enable_controls)

    def enable_controls(self):
        """Re-enable form controls"""
        self.process_button.config(state="normal")
        self.date_entry.config(state="normal")


class SingleStripWindow(BaseFunctionWindow):
    """Window for processing single data strips"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "Single Strip")
        self.center_window(600, 500)
        self.available_files = []
        self.create_widgets()

    def create_widgets(self):
        """Create single strip widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="Process Single Data Strip",
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
            text="Process",
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

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and check for available files",
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

            # Get all files for date
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

        # Disable controls
        self.process_button.config(state="disabled")
        self.files_listbox.config(state="disabled")

        # Process in thread
        thread = threading.Thread(
            target=self.process_single_strip,
            args=(file_info,)
        )
        thread.daemon = True
        thread.start()

    def process_single_strip(self, file_info):
        """Process single strip (runs in thread)"""
        try:
            # Update status
            self.window.after(0, self.show_progress, f"Downloading {file_info['name']}...")

            # Download file
            temp_dir = self.file_manager.get_temp_dir()
            downloaded_file = self.gportal_client.download_single_file(
                file_info,
                temp_dir
            )

            if not downloaded_file:
                self.window.after(0, self.show_error, "Failed to download file")
                return

            # Process file
            self.window.after(0, self.show_progress, "Processing data...")

            # Extract temperature data with scale factor
            temp_data, scale_factor = self.data_handler.extract_temperature_data(downloaded_file)

            if temp_data is None:
                self.window.after(0, self.show_error, "Failed to extract temperature data")
                return

            # Create output directory
            date_str = self.date_entry.get().strip().replace("/", "-")
            output_base = self.path_manager.get_output_path()
            output_dir = output_base / f"SingleStrip-{date_str}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save outputs
            self.window.after(0, self.show_progress, "Saving results...")

            # Save color image
            color_path = output_dir / f"{file_info['name']}_color.png"
            self.image_processor.save_color_image(temp_data, color_path)

            # Save color image (percentile filtered)
            color_percentile_path = output_dir / f"{file_info['name']}_color_percentile.png"
            self.image_processor.save_color_image_percentile(temp_data, color_percentile_path)

            viridis_path = output_dir / "polar_viridis.png"  # or appropriate name
            self.image_processor.save_viridis_image(temp_data, viridis_path)

            # Save grayscale image
            gray_path = output_dir / f"{file_info['name']}_grayscale.png"
            self.image_processor.save_grayscale_image(temp_data, gray_path)

            # Save grayscale image (percentile filtered)
            gray_percentile_path = output_dir / f"{file_info['name']}_grayscale_percentile.png"
            self.image_processor.save_grayscale_image_percentile(temp_data, gray_percentile_path)

            # Save corrected temperature array
            temp_path = output_dir / f"{file_info['name']}_temperature.npz"
            self.data_handler.save_temperature_array(temp_data, temp_path)

            # Clean up
            self.window.after(0, self.show_progress, "Cleaning up...")
            self.file_manager.cleanup_temp()

            # Success
            self.window.after(
                0,
                self.show_success,
                f"Processing complete!\nResults saved to:\n{output_dir}"
            )

            # Close window after delay
            self.window.after(1500, self.on_close)

        except Exception as e:
            self.window.after(0, self.show_error, f"Processing failed: {str(e)}")

        finally:
            # Re-enable controls
            self.window.after(0, self.enable_controls)

    def enable_controls(self):
        """Re-enable controls"""
        self.process_button.config(state="normal")
        self.files_listbox.config(state="normal")


# Add these imports at the top of function_windows.py
from core.enhanced_processor import EnhancedProcessor
from ml_models import TemperatureSRProcessor
import numpy as np
import pathlib


# Replace the Enhance8xWindow class implementation:

class Enhance8xWindow(BaseFunctionWindow):
    """Window for 8x quality enhancement of single strip"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "8x Enhancement")
        self.center_window(600, 500)
        self.available_files = []

        # Initialize ML processor
        if getattr(sys, 'frozen', False):
            model_path = pathlib.Path(sys._MEIPASS) / "ml_models" / "checkpoints" / "net_g_45738.pth"
        else:
            model_path = pathlib.Path(__file__).parent.parent / "ml_models" / "checkpoints" / "net_g_45738.pth"
        if model_path.exists():
            if torch is not None:
                device_obj, device_name = get_best_device()
                self.enhanced_processor = EnhancedProcessor(model_path, device=str(device_obj))
                print(f"Enhancement model loaded on: {device_name}")
            else:
                self.enhanced_processor = EnhancedProcessor(model_path, device='cpu')
            self.model_loaded = True
        else:
            self.enhanced_processor = None
            self.model_loaded = False

        self.create_widgets()

    def create_widgets(self):
        """Create 8x enhancement widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="8x Quality Enhancement",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        if not self.model_loaded:
            # Show error if model not found
            error_label = tk.Label(
                self.window,
                text="Error: ML model not found!\nPlease ensure net_g_66099.pth is in ml_models/checkpoints/",
                font=("Arial", 12),
                fg="red"
            )
            error_label.pack(pady=20)

            # Back button only
            back_button = ttk.Button(
                self.window,
                text="Back",
                command=self.on_close,
                width=15
            )
            back_button.pack(pady=20)
            return

        # Date frame (same as SingleStripWindow)
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

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=20)

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="Enhance 8x",
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

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Enter date and check for available files",
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

            # Get all files for date
            all_files = self.gportal_client.list_files_for_date(date_str)

            if not all_files:
                self.window.after(0, self.show_error, "No files available for this date")
                return

            # Update listbox (you need to add this method)
            self.window.after(0, self.update_files_list, all_files)

        except Exception as e:
            self.window.after(0, self.show_error, f"Failed to check files: {str(e)}")

        finally:
            # Re-enable controls
            self.window.after(0, lambda: self.check_button.config(state="normal"))
            self.window.after(0, lambda: self.date_entry.config(state="normal"))

    def check_files_thread(self, date_obj):
        """Check files in thread"""
        try:
            self.window.after(0, self.show_progress, "Checking available files...")

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

        # Disable controls
        self.process_button.config(state="disabled")
        self.files_listbox.config(state="disabled")

        # Process in thread
        thread = threading.Thread(
            target=self.process_8x_enhancement,
            args=(file_info,)
        )
        thread.daemon = True
        thread.start()

    def process_8x_enhancement(self, file_info):
        """Process 8x enhancement (runs in thread)"""
        try:
            # Download file
            self.window.after(0, self.show_progress, f"Downloading {file_info['name']}...")

            temp_dir = self.file_manager.get_temp_dir()
            downloaded_file = self.gportal_client.download_single_file(
                file_info,
                temp_dir
            )

            if not downloaded_file:
                self.window.after(0, self.show_error, "Failed to download file")
                return

            # Extract temperature data
            self.window.after(0, self.show_progress, "Extracting temperature data...")

            temp_data, scale_factor = self.data_handler.extract_temperature_data(downloaded_file)

            if temp_data is None:
                self.window.after(0, self.show_error, "Failed to extract temperature data")
                return

            # Extract coordinates
            self.window.after(0, self.show_progress, "Extracting coordinates...")

            lat, lon = self.enhanced_processor.extract_coordinates_from_h5(downloaded_file)

            # Process with 8x enhancement
            self.window.after(0, self.show_progress, "Applying 8x enhancement (this may take a few minutes)...")

            metadata = {
                'filename': file_info['name'],
                'orbit_type': file_info.get('orbit_type', 'unknown'),
                'scale_factor': scale_factor
            }

            # Run 8x enhancement
            enhanced_results = self.enhanced_processor.sr_processor.process_single_strip_8x(
                temp_data, lat, lon, metadata
            )

            # Create output directory
            date_str = self.date_entry.get().strip().replace("/", "-")
            output_base = self.path_manager.get_output_path()
            output_dir = output_base / f"Enhanced8x-{date_str}"

            # Save results
            self.window.after(0, self.show_progress, "Saving enhanced results...")

            self.enhanced_processor.save_enhanced_results(
                enhanced_results,
                output_dir,
                file_info['name'].replace('.h5', ''),
                percentile_filter=True  # Apply 1-99 percentile filter
            )

            # Clean up
            self.window.after(0, self.show_progress, "Cleaning up...")
            self.file_manager.cleanup_temp()

            # Success
            self.window.after(
                0,
                self.show_success,
                f"8x Enhancement complete!\nResults saved to:\n{output_dir}"
            )

            # Close window after delay
            self.window.after(1500, self.on_close)

        except Exception as e:
            self.window.after(0, self.show_error, f"Enhancement failed: {str(e)}")

        finally:
            self.window.after(0, self.enable_controls)

    def enable_controls(self):
        """Re-enable controls"""
        self.process_button.config(state="normal")
        self.files_listbox.config(state="normal")


# Replace the PolarEnhanced8xWindow class implementation:


class PolarEnhanced8xWindow(BaseFunctionWindow):
    """Window for 8x enhanced polar circle"""

    def __init__(self, parent, auth_manager, path_manager, file_manager):
        super().__init__(parent, auth_manager, path_manager, file_manager, "8x Enhanced Polar")
        self.center_window(500, 350)

        # Initialize ML processor
        if getattr(sys, 'frozen', False):
            model_path = pathlib.Path(sys._MEIPASS) / "ml_models" / "checkpoints" / "net_g_45738.pth"
        else:
            model_path = pathlib.Path(__file__).parent.parent / "ml_models" / "checkpoints" / "net_g_45738.pth"
        if model_path.exists():
            if torch is not None:
                device_obj, device_name = get_best_device()
                self.enhanced_processor = EnhancedProcessor(model_path, device=str(device_obj))
                print(f"Enhancement model loaded on: {device_name}")
            else:
                self.enhanced_processor = EnhancedProcessor(model_path, device='cpu')
            self.model_loaded = True
        else:
            self.enhanced_processor = None
            self.model_loaded = False

        self.create_widgets()

    def create_widgets(self):
        """Create 8x polar widgets"""
        # Title
        title_label = tk.Label(
            self.window,
            text="8x Enhanced Polar Circle",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        if not self.model_loaded:
            # Show error if model not found
            error_label = tk.Label(
                self.window,
                text="Error: ML model not found!\nPlease ensure net_g_45738.pth is in ml_models/checkpoints/",
                font=("Arial", 12),
                fg="red"
            )
            error_label.pack(pady=20)

            # Back button only
            back_button = ttk.Button(
                self.window,
                text="Back",
                command=self.on_close,
                width=15
            )
            back_button.pack(pady=20)
            return

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

        # Pole selection (North only for now)
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

        # Process button (now enabled!)
        self.process_button = ttk.Button(
            button_frame,
            text="Process",
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

        # Disable controls
        self.process_button.config(state="disabled")
        self.date_entry.config(state="disabled")

        # Process in thread
        thread = threading.Thread(
            target=self.process_polar_enhanced,
            args=(date_obj, orbit_type, pole)
        )
        thread.daemon = True
        thread.start()

    def process_polar_enhanced(self, date_obj, orbit_type, pole):
        """Process enhanced polar circle"""
        try:
            # Convert date
            date_str = date_obj.strftime("%Y-%m-%d")

            # Update status
            self.window.after(0, self.show_progress, "Connecting to GPORTAL...")

            # Check data availability
            self.window.after(0, self.show_progress, f"Checking data for {date_str}...")
            available_files = self.gportal_client.check_availability(date_str, orbit_type)

            if not available_files:
                self.window.after(0, self.show_error, "No data available for this date")
                return

            self.window.after(0, self.show_progress, f"Found {len(available_files)} files. Downloading...")

            # Download files
            temp_dir = self.file_manager.get_temp_dir()
            downloaded_files = self.gportal_client.download_files(
                date_str,
                orbit_type,
                temp_dir,
                progress_callback=lambda msg: self.window.after(0, self.show_progress, msg)
            )

            if not downloaded_files:
                self.window.after(0, self.show_error, "Failed to download files")
                return

            # Process with 8x enhancement
            self.window.after(0, self.show_progress,
                              "Applying 8x enhancement to polar projection (this may take several minutes)...")

            # Use the ML processor to create enhanced polar image
            enhanced_result = self.enhanced_processor.sr_processor.process_polar_8x_enhanced(
                downloaded_files,
                orbit_type,
                pole
            )

            # Create output directory
            output_base = self.path_manager.get_output_path()
            orbit_char = "A" if orbit_type == "A" else "D"
            output_dir = output_base / f"{date_str}-{orbit_char}-{pole}-Enhanced8x"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save results
            self.window.after(0, self.show_progress, "Saving enhanced polar image...")

            # Get enhanced temperature data
            polar_temp_8x = enhanced_result['temperature_8x']
            percentile_range = enhanced_result['percentile_range']

            # Save color image with percentile filtering
            color_path = output_dir / "polar_enhanced_8x_color.png"
            self.image_processor.save_color_image_percentile(polar_temp_8x, color_path)

            # Save grayscale image with percentile filtering
            gray_path = output_dir / "polar_enhanced_8x_grayscale.png"
            self.image_processor.save_grayscale_image_percentile(polar_temp_8x, gray_path)

            # Save temperature array
            temp_path = output_dir / "temperature_data_enhanced_8x.npz"
            np.savez_compressed(
                temp_path,
                temperature=polar_temp_8x,
                statistics=enhanced_result['statistics'],
                metadata=enhanced_result['metadata']
            )

            # Clean up
            self.window.after(0, self.show_progress, "Cleaning up...")
            self.file_manager.cleanup_temp()

            # Success
            self.window.after(
                0,
                self.show_success,
                f"8x Enhanced processing complete!\nResults saved to:\n{output_dir}"
            )

            # Close window after delay
            self.window.after(1500, self.on_close)

        except Exception as e:
            self.window.after(0, self.show_error, f"Processing failed: {str(e)}")
        finally:
            self.window.after(0, self.enable_controls)

    def enable_controls(self):
        """Re-enable controls"""
        self.process_button.config(state="normal")
        self.date_entry.config(state="normal")