@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set VERSION=1.0.0
set APP_NAME=FanqieClock
set DIST_DIR=dist
set OUTPUT_DIR=%DIST_DIR%\release

echo ========================================
echo FanqieClock Release Builder
echo ========================================
echo.

:: Check PyInstaller
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Clean
echo [1/3] Cleaning...
if exist build rmdir /s /q build
if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
mkdir %OUTPUT_DIR% 2>nul

:: Build single exe (onefile)
echo [2/3] Building single exe...
python -m PyInstaller --noconfirm --log-level WARN FanqieClock.spec
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b %errorlevel%
)

:: Package portable zip
echo [3/3] Creating portable zip...
cd %DIST_DIR%
tar -a -cf "%OUTPUT_DIR%\%APP_NAME%_v%VERSION%.zip" "%APP_NAME%.exe"
cd ..

echo.
echo ========================================
echo Done!
echo ========================================
echo.
echo Output: %OUTPUT_DIR%\%APP_NAME%_v%VERSION%.zip
dir "%OUTPUT_DIR%\%APP_NAME%_v%VERSION%.zip"
echo.
pause
