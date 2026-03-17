"""
pytest 全局配置：
  1. 确保测试产生的临时文件写到项目内的 tmp/ 目录，而不是随 cwd 散落到桌面。
  2. 设置 QT_QPA_PLATFORM=offscreen，让所有 Qt 窗口在离屏模式下运行，
     不会真实弹出到桌面，测试期间桌面保持干净。
"""
import os
import sys

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


