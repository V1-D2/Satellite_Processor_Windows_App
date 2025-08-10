"""
Authentication manager for gportal credentials
"""

import pathlib
import os
import sys


class AuthManager:
    """Manages gportal authentication credentials"""

    def __init__(self):
        if getattr(sys, 'frozen', False):
            # When frozen, use user's home directory for config
            self.config_dir = pathlib.Path.home() / ".satelliteprocessor" / "config"
        else:
            self.config_dir = pathlib.Path(__file__).parent.parent / "config"
        self.credentials_file = self.config_dir / "credentials.txt"
        self.config_dir.mkdir(exist_ok=True)

    def has_credentials(self):
        """Check if credentials file exists and is not empty"""
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    content = f.read().strip()
                    return len(content) > 0
            except:
                return False
        return False

    def get_credentials(self):
        """Get stored credentials"""
        if not self.has_credentials():
            return None, None

        try:
            with open(self.credentials_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    username = lines[0].strip()
                    password = lines[1].strip()
                    return username, password
        except:
            pass

        return None, None

    def save_credentials(self, username, password):
        """Save credentials to file"""
        try:
            with open(self.credentials_file, 'w') as f:
                f.write(f"{username}\n{password}")
            return True
        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    def test_credentials(self, username, password):
        """Test credentials with gportal API by attempting to download a file"""
        try:
            # Import gportal module
            import gportal
            import datetime as dt
            import pathlib
            import tempfile

            print(f"Testing credentials for user: {username}")

            # Set credentials
            gportal.username = username
            gportal.password = password

            # Get datasets
            datasets = gportal.datasets()
            _DS = datasets["GCOM-W/AMSR2"]["LEVEL1"]
            DS_L1B_TB = _DS["L1B-Brightness temperature（TB）"][0]

            # Search for recent data (try last few days)
            test_file = None
            for days_back in range(1, 8):  # Try up to 7 days back
                test_date = dt.date.today() - dt.timedelta(days=days_back)

                res = gportal.search(
                    dataset_ids=[DS_L1B_TB],
                    start_time=f"{test_date}T00:00:00",
                    end_time=f"{test_date}T23:59:59"
                )

                if res.matched() > 0:
                    test_file = list(res.products())[0]  # Get first file
                    print(f"Found test file from {test_date}: {test_file['identifier']}")
                    break

            if not test_file:
                print("No recent files found for credential testing")
                return False

            # Try to download the file - this is the real authentication test
            with tempfile.TemporaryDirectory() as temp_dir:
                print("Attempting download to test credentials...")

                try:
                    local_path = gportal.download(
                        test_file,
                        local_dir=temp_dir
                    )
                    print("Download successful - credentials are valid!")

                    # Clean up is automatic with tempfile.TemporaryDirectory
                    return True

                except Exception as download_error:
                    print(f"Download failed - invalid credentials: {download_error}")
                    return False

        except ImportError:
            print("Error: gportal module not found. Please install it.")
            return False
        except Exception as e:
            print(f"Credential test failed: {e}")
            return False

    def clear_credentials(self):
        """Clear stored credentials"""
        try:
            if self.credentials_file.exists():
                self.credentials_file.unlink()
            return True
        except:
            return False