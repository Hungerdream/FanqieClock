@echo off
echo Building 番茄钟 (FanqieClock)...

:: Ensure PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

:: Build Command
:: --noconfirm: overwrite output directory
:: --windowed: no console window
:: --onedir: folder output (faster startup than onefile)
:: --icon: set exe icon
:: --add-data: include resources and styles
:: --name: exe name

echo Running PyInstaller...
pyinstaller --noconfirm --windowed --onedir ^
    --name "FanqieClock" ^
    --icon "src/resources/icon.ico" ^
    --add-data "src/resources;resources" ^
    --add-data "src/styles;styles" ^
    --hidden-import "PyQt6" ^
    --hidden-import "logic" ^
    --hidden-import "ui" ^
    src/main.py

if %errorlevel% neq 0 (
    echo Build failed!
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
:: pause
