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
    """Mock QuoteWorker to avoid real network requests in CI / test environment."""
    # Patch QuoteWorker.run so it emits a default quote instantly without HTTP call.
    # This prevents threads from hanging on network timeouts and blocking test teardown.
    try:
        from logic.quote_worker import QuoteWorker

        def _noop_run(self):
            self.quote_fetched.emit("生活原本沉闷，但跑起来就有风。", "—— 佚名")

        QuoteWorker.run = _noop_run
    except Exception:
        pass  # If import fails for any reason, let tests handle it themselves


