# 番茄钟 (FanqieClock)

一个基于 Python 和 PyQt6 构建的现代、极简主义番茄工作法计时器应用。旨在帮助你保持专注，利用番茄工作法高效管理时间。

**作者:** 饿梦

## 功能特点

- **计时器**: 可自定义工作、休息和长休息时长。
- **任务管理**: 带有四象限（艾森豪威尔矩阵）的看板式任务板。
- **统计数据**: 追踪你的专注时间和中断次数。
- **个性化**: 支持暗黑模式、声音通知和界面偏好设置。
- **极简模式**: 悬浮窗设计，便于监控且不干扰工作。
- **每日一句**: 励志名言，助你保持动力。

## 环境要求

- Python 3.10+
- PyQt6

## 安装指南

1. 克隆仓库:
   ```bash
   git clone https://github.com/Hungerdream/FanqieClock.git
   cd FanqieClock
   ```

2. 创建虚拟环境 (可选但推荐):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

## 使用说明

使用启动脚本运行应用程序:

**Windows:**
```cmd
run_app.bat
```

**手动运行:**
```bash
python src/main.py
```

## 打包/构建

将应用程序打包为可执行文件:

**Windows:**
```cmd
build_exe.bat
```

打包流程说明:
1. 自动安装项目依赖 (`requirements.txt`)
2. 检查依赖是否完整
3. 清理旧的构建文件 (`build/` 和 `dist/` 目录)
4. 使用 PyInstaller 打包应用程序
5. 生成的可执行文件位于 `dist/FanqieClock/FanqieClock.exe`

**注意事项:**
- 首次打包需要下载 PyInstaller，可能需要一些时间
- 打包过程中会生成 `build/` 和 `dist/` 目录
- 如果打包失败，请查看 `build.log` 文件获取详细错误信息
- 确保已安装 Python 3.10+ 和所有依赖项

## 项目结构

- `src/`: 源代码。
  - `logic/`: 业务逻辑 (计时器, 数据管理)。
  - `ui/`: 用户界面 (PyQt6 组件)。
  - `resources/`: 图标和资源文件。
  - `styles/`: QSS 样式表。
- `tests/`: 单元测试和集成测试。
- `docs/`: 文档。

## 贡献指南

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解我们的行为准则以及提交拉取请求（Pull Request）的流程。

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
