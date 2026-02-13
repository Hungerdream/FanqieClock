@echo off
echo Building 番茄钟 (FanqieClock)...

:: Ensure PyInstaller is installed
pip install pyinstaller

:: Clean previous build
rmdir /s /q build
rmdir /s /q dist
del /q *.spec

:: Build Command
:: --noconfirm: overwrite output directory
:: --windowed: no console window
:: --onedir: folder output (faster startup than onefile)
:: --icon: set exe icon
:: --add-data: include resources and styles
:: --name: exe name

pyinstaller --noconfirm --windowed --onedir ^
    --name "FanqieClock" ^
    --icon "src/resources/icon.ico" ^
    --add-data "src/resources;resources" ^
    --add-data "src/styles;styles" ^
    --hidden-import "PyQt6" ^
    --hidden-import "logic" ^
    --hidden-import "ui" ^
    src/main.py

echo.
echo Build complete!
echo You can find the executable in: dist\FanqieClock\FanqieClock.exe
pause
