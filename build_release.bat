@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set VERSION=1.0.0
set APP_NAME=FanqieClock
set DIST_DIR=dist
set PORTABLE_DIR=%DIST_DIR%\%APP_NAME%
set OUTPUT_DIR=%DIST_DIR%\release

echo ========================================
echo 番茄钟 发行版构建工具
echo ========================================
echo.

:: 检查 PyInstaller 是否安装
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 未安装，正在安装...
    pip install pyinstaller
)

:: 清理旧的构建
echo [1/4] 清理旧文件...
if exist build rmdir /s /q build
if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
mkdir %OUTPUT_DIR% 2>nul

:: 构建 exe
echo [2/4] 使用 PyInstaller 构建...
python -m PyInstaller --noconfirm --log-level WARN FanqieClock.spec
if %errorlevel% neq 0 (
    echo [错误] 构建失败！
    pause
    exit /b %errorlevel%
)

:: 检查构建结果
if not exist "%PORTABLE_DIR%\%APP_NAME%.exe" (
    echo [错误] 未找到生成的 exe 文件！
    pause
    exit /b 1
)

:: 打包便携版 zip
echo [3/4] 打包便携版...
cd %DIST_DIR%
tar -a -cf "..\%OUTPUT_DIR%\%APP_NAME%_Portable_v%VERSION%.zip" "%APP_NAME%"
cd ..

:: 检查 Inno Setup 并构建安装包
echo [4/4] 构建安装包...
set INNO_COMPILER=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_COMPILER="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined INNO_COMPILER (
    %INNO_COMPILER% setup.iss
    if %errorlevel% equ 0 (
        echo [完成] 安装包已生成: %OUTPUT_DIR%\FanqieClock_Setup_v%VERSION%.exe
    ) else (
        echo [警告] 安装包构建失败
    )
) else (
    echo [提示] 未找到 Inno Setup，跳过安装包构建
    echo        下载地址: https://jrsoftware.org/isinfo.php
)

:: 显示结果
echo.
echo ========================================
echo 构建完成！
echo ========================================
echo.
echo 输出目录: %OUTPUT_DIR%
echo.
echo 生成的文件:
dir /b %OUTPUT_DIR% 2>nul
echo.
echo 便携版: 解压后直接运行 FanqieClock.exe
echo 安装版: 运行 FanqieClock_Setup_v%VERSION%.exe
echo.
pause
