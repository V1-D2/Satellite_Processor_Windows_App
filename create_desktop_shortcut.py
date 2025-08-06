#!/usr/bin/env python3
"""
Creates a desktop shortcut for SatelliteProcessor with SILENT launch (no console window)
Run this script to create/update the desktop shortcut
"""

import os
import sys
import pathlib
import subprocess


def install_dependencies():
    """Install required packages for shortcut creation"""
    try:
        import winshell
        from win32com.client import Dispatch
        return True
    except ImportError:
        print("📦 Installing required packages...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "winshell", "pywin32"])
            print("✅ Packages installed!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            return False


def create_desktop_shortcut():
    """Create the desktop shortcut pointing to VBS script for silent launch"""
    try:
        import winshell
        from win32com.client import Dispatch

        # Get paths
        project_root = pathlib.Path(__file__).parent.absolute()
        vbs_file = project_root / "launch_satellite_silent.vbs"
        batch_file = project_root / "launch_satellite.bat"  # Backup option
        icon_file = project_root / "assets" / "satellite_icon.ico"

        print(f"🔍 Checking launcher files:")
        print(f"VBS launcher: {vbs_file} {'✅' if vbs_file.exists() else '❌ NOT FOUND'}")
        print(f"Batch launcher: {batch_file} {'✅' if batch_file.exists() else '❌ NOT FOUND'}")
        print(f"Icon file: {icon_file} {'✅' if icon_file.exists() else '⚠️  DEFAULT ICON'}")

        # Choose launcher (prefer VBS for silent launch)
        if vbs_file.exists():
            target_file = vbs_file
            launcher_type = "Silent VBS launcher"
            print("🔇 Using VBS script for COMPLETELY SILENT launch")
        elif batch_file.exists():
            target_file = batch_file
            launcher_type = "Batch file launcher"
            print("🖥️  Using batch file (console window will appear)")
        else:
            print("❌ ERROR: No launcher files found!")
            print("Please ensure you have either:")
            print("- launch_satellite_silent.vbs (recommended)")
            print("- launch_satellite.bat (fallback)")
            return False

        # Get desktop path and create shortcut
        desktop = pathlib.Path(winshell.desktop())
        shortcut_path = desktop / "SatelliteProcessor.lnk"

        print(f"\n🔗 Creating desktop shortcut...")
        print(f"Target: {target_file}")
        print(f"Type: {launcher_type}")

        # Create the shortcut
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))

        # Set shortcut properties
        shortcut.Targetpath = str(target_file)
        shortcut.Arguments = ""
        shortcut.WorkingDirectory = str(project_root)
        shortcut.Description = "AMSR-2 Satellite Data Processing Tool"

        # Set custom icon if available
        if icon_file.exists():
            shortcut.IconLocation = str(icon_file)
            print(f"🎨 Using custom icon: {icon_file.name}")

        # Save shortcut
        shortcut.save()

        print("✅ Desktop shortcut created successfully!")
        print(f"📍 Location: {shortcut_path}")

        # Provide user feedback based on launcher type
        if vbs_file.exists():
            print("\n🎉 SILENT LAUNCH ENABLED!")
            print("- No console window will appear")
            print("- App will start directly with GUI only")
            print("- Professional appearance for end users")
        else:
            print("\n⚠️  Console window will appear briefly")
            print("To enable silent launch:")
            print("1. Create the VBS file (launch_satellite_silent.vbs)")
            print("2. Re-run this script to update the shortcut")

        return True

    except Exception as e:
        print(f"❌ Error creating shortcut: {e}")
        return False


def check_setup():
    """Check current setup and provide recommendations"""
    project_root = pathlib.Path(__file__).parent

    files_status = {
        'main.py': project_root / 'main.py',
        'launch_satellite.bat': project_root / 'launch_satellite.bat',
        'launch_satellite_silent.vbs': project_root / 'launch_satellite_silent.vbs',
        'assets/satellite_icon.ico': project_root / 'assets' / 'satellite_icon.ico',
        '.venv/Scripts/activate.bat': project_root.parent / '.venv' / 'Scripts' / 'activate.bat'
    }

    print("📋 Current Setup Status:")
    print("-" * 30)

    all_good = True
    for name, path in files_status.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"{status} {name}")

        if not exists and name in ['main.py', '.venv/Scripts/activate.bat']:
            all_good = False

    print("\n💡 Recommendations:")

    if not files_status['launch_satellite_silent.vbs'].exists():
        print("⚠️  For SILENT launch: Create launch_satellite_silent.vbs")
        print("   (No console window - professional appearance)")

    if not files_status['launch_satellite.bat'].exists():
        print("⚠️  For BASIC launch: Create launch_satellite.bat")
        print("   (Console window appears - easier troubleshooting)")

    if not files_status['assets/satellite_icon.ico'].exists():
        print("🎨 For CUSTOM ICON: Add satellite_icon.ico to assets/ folder")

    return all_good


def main():
    """Main function"""
    print("🛠️  SatelliteProcessor Desktop Shortcut Creator")
    print("   (Silent Launch Version)")
    print("=" * 50)

    # Check setup
    if not check_setup():
        print("\n❌ Critical files missing. Please fix setup first.")
        input("Press Enter to exit...")
        return

    # Install dependencies
    if not install_dependencies():
        input("Press Enter to exit...")
        return

    print()  # Add spacing

    # Create shortcut
    success = create_desktop_shortcut()

    if success:
        print("\n🎊 Setup complete!")
        print("🖱️  Double-click the desktop shortcut to test it")
        print("🔄 Code changes will automatically work - no need to recreate shortcut")
    else:
        print("\n⚠️  Setup had issues. Check messages above.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()