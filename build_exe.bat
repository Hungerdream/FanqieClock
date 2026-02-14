@echo off
chcp 65001 >nul
echo Building FanqieClock...

:: Ensure PyInstaller is installed
echo Checking and installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies!
    pause
    exit /b %errorlevel%
)

:: Check dependencies
python check_deps.py
if %errorlevel% neq 0 (
    echo Dependency check failed!
    pause
    exit /b %errorlevel%
)

:: Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: Build Command
echo Running PyInstaller with spec file...
if not exist FanqieClock.spec (
    echo Generating spec file...
    python -m PyInstaller --noconfirm --windowed --onedir --log-level WARN ^
        --name "FanqieClock" ^
        --icon "src\resources\icon.ico" ^
        --paths "src" ^
        --add-data "src/resources;resources" ^
        --add-data "src/styles;styles" ^
        --hidden-import "PyQt6" ^
        --hidden-import "PyQt6.QtSvg" ^
        --hidden-import "requests" ^
        src/main.py
) else (
    python -m PyInstaller --noconfirm --log-level WARN FanqieClock.spec > build.log 2>&1
)

if %errorlevel% neq 0 (
    echo Build failed! See build.log for details.
    type build.log
    pause
    exit /b %errorlevel%
)

echo.
echo Build complete!
if exist dist\FanqieClock\FanqieClock.exe (
    echo You can find the executable in: %CD%\dist\FanqieClock\FanqieClock.exe
) else (
    echo WARNING: Executable not found in expected location!
)
pause