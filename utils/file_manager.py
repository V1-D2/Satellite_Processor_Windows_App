"""
File management utilities
"""

import os
import shutil
import pathlib
from typing import List
import sys


class FileManager:
    """Manages temporary files and cleanup"""

    def __init__(self):
        # Get temp directory relative to project root
        if getattr(sys, 'frozen', False):
            # When frozen, use system temp directory
            import tempfile
            self.temp_dir = pathlib.Path(tempfile.gettempdir()) / "satelliteprocessor_temp"
        else:
            self.project_root = pathlib.Path(__file__).parent.parent
            self.temp_dir = self.project_root / "temp"

    def get_temp_dir(self) -> pathlib.Path:
        """Get temporary directory path, creating if needed"""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir

    def cleanup_temp(self) -> bool:
        """Clean up all files in temp directory"""
        try:
            if self.temp_dir.exists():
                # Remove all files
                for file in self.temp_dir.glob("*"):
                    try:
                        if file.is_file():
                            file.unlink()
                        elif file.is_dir():
                            shutil.rmtree(file)
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

                print(f"Cleaned up temp directory: {self.temp_dir}")
                return True
            return True

        except Exception as e:
            print(f"Error cleaning temp directory: {e}")
            return False

    def cleanup_specific_files(self, pattern: str = "*.h5") -> int:
        """
        Clean up specific files matching pattern

        Args:
            pattern: File pattern to match (e.g., "*.h5")

        Returns:
            Number of files deleted
        """
        count = 0
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob(pattern):
                    try:
                        file.unlink()
                        count += 1
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

            return count

        except Exception as e:
            print(f"Error in cleanup_specific_files: {e}")
            return count

    def get_temp_files(self, pattern: str = "*") -> List[pathlib.Path]:
        """
        Get list of files in temp directory

        Args:
            pattern: File pattern to match

        Returns:
            List of file paths
        """
        if self.temp_dir.exists():
            return list(self.temp_dir.glob(pattern))
        return []

    def get_temp_size(self) -> float:
        """
        Get total size of temp directory in MB

        Returns:
            Size in megabytes
        """
        total_size = 0

        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size

            return total_size / (1024 * 1024)  # Convert to MB

        except Exception as e:
            print(f"Error calculating temp size: {e}")
            return 0.0

    def ensure_directory(self, path: pathlib.Path) -> bool:
        """
        Ensure directory exists

        Args:
            path: Directory path

        Returns:
            True if successful
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False

    def safe_delete_file(self, file_path: pathlib.Path) -> bool:
        """
        Safely delete a file

        Args:
            file_path: Path to file

        Returns:
            True if successful
        """
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return True

        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False

    def move_file(self, source: pathlib.Path, destination: pathlib.Path) -> bool:
        """
        Move file from source to destination

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(source), str(destination))
            return True

        except Exception as e:
            print(f"Error moving file from {source} to {destination}: {e}")
            return False

    def copy_file(self, source: pathlib.Path, destination: pathlib.Path) -> bool:
        """
        Copy file from source to destination

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(str(source), str(destination))
            return True

        except Exception as e:
            print(f"Error copying file from {source} to {destination}: {e}")
            return False

    def get_directory_size(self, directory: pathlib.Path) -> float:
        """
        Get total size of directory in MB

        Args:
            directory: Directory path

        Returns:
            Size in megabytes
        """
        total_size = 0

        try:
            if directory.exists() and directory.is_dir():
                for file in directory.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size

            return total_size / (1024 * 1024)  # Convert to MB

        except Exception as e:
            print(f"Error calculating directory size: {e}")
            return 0.0