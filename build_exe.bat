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
        --exclude-module "PyQt6.QtWebEngine" ^
        --exclude-module "PyQt6.QtWebEngineCore" ^
        --exclude-module "PyQt6.QtWebEngineWidgets" ^
        --exclude-module "PyQt6.QtNetwork" ^
        --exclude-module "PyQt6.QtSql" ^
        --exclude-module "PyQt6.QtMultimedia" ^
        --exclude-module "PyQt6.QtMultimediaWidgets" ^
        --exclude-module "PyQt6.QtBluetooth" ^
        --exclude-module "PyQt6.QtNfc" ^
        --exclude-module "PyQt6.QtPositioning" ^
        --exclude-module "PyQt6.QtSensors" ^
        --exclude-module "PyQt6.QtSerialPort" ^
        --exclude-module "PyQt6.QtTest" ^
        --exclude-module "PyQt6.QtDesigner" ^
        --exclude-module "PyQt6.QtHelp" ^
        --exclude-module "PyQt6.QtOpenGL" ^
        --exclude-module "PyQt6.QtOpenGLWidgets" ^
        --exclude-module "PyQt6.QtPdf" ^
        --exclude-module "PyQt6.QtPdfWidgets" ^
        --exclude-module "PyQt6.QtQuick" ^
        --exclude-module "PyQt6.QtQuick3D" ^
        --exclude-module "PyQt6.QtQuickWidgets" ^
        --exclude-module "PyQt6.QtQml" ^
        --exclude-module "PyQt6.QtSvgWidgets" ^
        --exclude-module "PyQt6.QtDBus" ^
        --exclude-module "tkinter" ^
        --exclude-module "unittest" ^
        --exclude-module "pytest" ^
        --exclude-module "numpy" ^
        --exclude-module "scipy" ^
        --exclude-module "pandas" ^
        --exclude-module "matplotlib" ^
        --exclude-module "PIL" ^
        --exclude-module "cv2" ^
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