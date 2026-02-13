# 番茄钟 (FanqieClock)

A modern, minimalist Pomodoro timer application built with Python and PyQt6. Designed to help you stay focused and manage your time effectively using the Pomodoro Technique.

**Author:** 饿梦

## Features

- **Timer**: Customizable work, break, and long break durations.
- **Task Management**: Kanban-style task board with quadrants (Eisenhower Matrix).
- **Statistics**: Track your focus time and interruptions.
- **Customization**: Dark mode, sound notifications, and UI preferences.
- **Minimalist Mode**: Floating window for unobtrusive monitoring.
- **Daily Quotes**: Inspirational quotes to keep you motivated.

## Requirements

- Python 3.10+
- PyQt6

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fanqie-clock.git
   cd fanqie-clock
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application using the startup script:

**Windows:**
```cmd
run_app.bat
```

**Manual:**
```bash
python src/main.py
```

## Structure

- `src/`: Source code.
  - `logic/`: Business logic (Timer, DataManager).
  - `ui/`: User Interface (PyQt6 widgets).
  - `resources/`: Icons and assets.
  - `styles/`: QSS stylesheets.
- `tests/`: Unit and integration tests.
- `docs/`: Documentation.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
