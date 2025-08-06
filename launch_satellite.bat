@echo off
REM SatelliteProcessor Launcher with Virtual Environment
REM Place this file in your project root directory (same folder as main.py)

echo Starting SatelliteProcessor...
echo.

REM Get the directory where this batch file is located
set PROJECT_DIR=%~dp0

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Check if virtual environment exists
if not exist "C:\Users\tomg\PycharmProjects\Satellite_Processor\.venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Expected: C:\Users\tomg\PycharmProjects\Satellite_Processor\.venv\Scripts\activate.bat
    echo.
    echo Please ensure your virtual environment is set up correctly.
    echo Current directory: %PROJECT_DIR%
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found!
    echo Expected: %PROJECT_DIR%main.py
    echo Current directory: %PROJECT_DIR%
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call C:\Users\tomg\PycharmProjects\Satellite_Processor\.venv\Scripts\activate.bat

REM Verify Python is available in venv
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not available in virtual environment
    echo Please check your virtual environment setup
    pause
    exit /b 1
)

REM Launch the application
echo Launching SatelliteProcessor application...
echo.
python main.py

REM Check exit status
if errorlevel 1 (
    echo.
    echo Application exited with an error (Exit code: %errorlevel%)
    echo Check the error messages above
    pause
) else (
    echo.
    echo Application closed normally
)

REM Deactivate virtual environment (cleanup)
call deactivate 2>nul

REM Optional: Remove this line if you don't want the window to stay open
echo Press any key to close...
pause >nul