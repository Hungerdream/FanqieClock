"""
pytest 全局配置：
  1. 确保测试产生的临时文件写到项目内的 tmp/ 目录，而不是随 cwd 散落到桌面。
  2. 设置 QT_QPA_PLATFORM=offscreen，让所有 Qt 窗口在离屏模式下运行，
     不会真实弹出到桌面，测试期间桌面保持干净。
  3. Mock QuoteWorker.run() 避免 CI 中发起网络请求，防止线程卡死。
"""
import os
import sys
from unittest.mock import patch

# ── 必须在任何 Qt 模块被导入之前设置，否则不生效 ──────────────────────────────
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_TMP_DIR = os.path.join(_PROJECT_ROOT, "tmp")

# 把 src/ 加到 sys.path，让测试能直接 import logic.*
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def pytest_configure(config):
    """在测试开始前把 cwd 固定到项目根目录。"""
    os.makedirs(_TMP_DIR, exist_ok=True)
    os.chdir(_PROJECT_ROOT)


def pytest_sessionstart(session):
    """Mock network-dependent modules to avoid hangs in CI environment."""
    # 1. Patch QuoteWorker.run so it emits a default quote instantly without HTTP call.
    # This prevents threads from hanging on network timeouts and blocking test teardown.
    try:
        from logic.quote_worker import QuoteWorker

        def _noop_run(self):
            self.quote_fetched.emit("生活原本沉闷，但跑起来就有风。", "—— 佚名")

        QuoteWorker.run = _noop_run
    except Exception:
        pass  # If import fails for any reason, let tests handle it themselves

    # 2. Mock keyboard module to prevent background threads from blocking test teardown.
    # The keyboard library creates listener threads that never exit, causing pytest to hang.
    try:
        import unittest.mock as mock
        import sys

        _keyboard_mock = mock.MagicMock()
        _keyboard_mock.add_hotkey = mock.MagicMock()
        _keyboard_mock.unhook_all = mock.MagicMock()
        sys.modules['keyboard'] = _keyboard_mock
    except Exception:
        pass

    # 3. Mock QMessageBox to prevent blocking dialogs in test environment.
    # In offscreen mode, modal dialogs can cause hangs.
    try:
        from unittest.mock import patch, MagicMock
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning = MagicMock()
        QMessageBox.critical = MagicMock()
        QMessageBox.information = MagicMock()
        QMessageBox.question = MagicMock(return_value=QMessageBox.StandardButton.Yes)
    except Exception:
        pass

    # 4. Mock DataManager save methods to prevent file lock conflicts between tests.
    # Multiple tests share data.json, causing WinError 32 on concurrent writes.
    try:
        from logic.data_manager import DataManager

        def _noop_save(self):
            pass

        def _noop_save_sync(self):
            pass

        DataManager.save_data = _noop_save
        DataManager.save_data_sync = _noop_save_sync
    except Exception:
        pass


