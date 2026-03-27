# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src\\main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src/resources', 'resources'), ('src/styles', 'styles')],
    hiddenimports=[
        'PyQt6', 'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets',
        'requests', 'pygame', 'pygame.mixer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtNetwork', 'PyQt6.QtSql', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtBluetooth', 'PyQt6.QtNfc', 'PyQt6.QtPositioning', 'PyQt6.QtSensors',
        'PyQt6.QtSerialPort', 'PyQt6.QtTest', 'PyQt6.QtDesigner', 'PyQt6.QtHelp',
        'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets',
        'PyQt6.QtQuick', 'PyQt6.QtQuick3D', 'PyQt6.QtQuickWidgets', 'PyQt6.QtQml',
        'PyQt6.QtDBus',
        'tkinter', 'unittest', 'pytest', 'numpy', 'scipy', 'pandas', 'matplotlib', 'PIL', 'cv2',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FanqieClock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src\\resources\\icon.ico',
)
