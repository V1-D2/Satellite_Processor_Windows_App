"""
Output path manager
"""

import pathlib
import os
import sys


class PathManager:
    """Manages output directory paths"""

    def __init__(self):
        if getattr(sys, 'frozen', False):
            # When frozen, use user's home directory for config
            self.config_dir = pathlib.Path.home() / ".satelliteprocessor" / "config"
        else:
            self.config_dir = pathlib.Path(__file__).parent.parent / "config"

        self.path_file = self.config_dir / "output_path.txt"
        self.config_dir.mkdir(exist_ok=True)

    def has_output_path(self):
        """Check if output path is configured"""
        if self.path_file.exists():
            try:
                with open(self.path_file, 'r') as f:
                    content = f.read().strip()
                    return len(content) > 0
            except:
                return False
        return False

    def get_output_path(self):
        """Get stored output path"""
        if not self.has_output_path():
            return None

        try:
            with open(self.path_file, 'r') as f:
                path_str = f.read().strip()
                path = pathlib.Path(path_str)

                # Verify path still exists
                if path.exists() and path.is_dir():
                    return path
                else:
                    # Path no longer exists, clear it
                    self.clear_output_path()
                    return None
        except:
            return None

    def save_output_path(self, path):
        """Save output path"""
        try:
            # Convert to Path object if string
            if isinstance(path, str):
                path = pathlib.Path(path)

            # Create directory if it doesn't exist
            path.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(self.path_file, 'w') as f:
                f.write(str(path))

            return True

        except Exception as e:
            print(f"Error saving output path: {e}")
            return False

    def clear_output_path(self):
        """Clear stored output path"""
        try:
            if self.path_file.exists():
                self.path_file.unlink()
            return True
        except:
            return False

    def create_subdirectory(self, name):
        """Create a subdirectory in the output path"""
        output_path = self.get_output_path()
        if output_path:
            subdir = output_path / name
            subdir.mkdir(parents=True, exist_ok=True)
            return subdir
        return None