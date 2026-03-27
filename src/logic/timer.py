from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QDateTime, QRunnable, QThreadPool
import os
import threading

# ── Audio Backend ──────────────────────────────────────────────────────────────
try:
    import pygame
    _PYGAME_AVAILABLE = True
except Exception as _e:
    _PYGAME_AVAILABLE = False
    print(f"[Audio] pygame import FAILED: {_e}")

_pygame_initialized = False

def _ensure_pygame_init():
    """Lazy initialize pygame mixer on first use."""
    global _pygame_initialized, _PYGAME_AVAILABLE
    if _pygame_initialized or not _PYGAME_AVAILABLE:
        return
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        _pygame_initialized = True
        print(f"[Audio] pygame mixer initialized: {pygame.mixer.get_init()}")
    except Exception as e:
        _PYGAME_AVAILABLE = False
        print(f"[Audio] pygame mixer init failed: {e}")

try:
    import winsound
    _WINSOUND_AVAILABLE = True
except ImportError:
    _WINSOUND_AVAILABLE = False

# ── 内置滴答声 ────────────────────────────────────────────────────────────────
_BUILTIN_TICK_SOUND = None   # 懒初始化

def _builtin_tick_wav_path():
    """返回内置 tick.wav 的绝对路径（与本文件同在 src/ 目录下）"""
    # timer.py 在 src/logic/ 下，tick.wav 在 src/resources/
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "resources", "tick.wav")

def _get_builtin_tick():
    """优先加载内置 tick.wav；不存在则合成简单点击音"""
    global _BUILTIN_TICK_SOUND
    if _BUILTIN_TICK_SOUND is not None:
        return _BUILTIN_TICK_SOUND
    if not _PYGAME_AVAILABLE:
        return None
    _ensure_pygame_init()  # Lazy init on first use
    if not _pygame_initialized:
        return None
    # 1. 尝试加载 tick.wav
    wav_path = _builtin_tick_wav_path()
    if os.path.exists(wav_path):
        try:
            sound = pygame.mixer.Sound(wav_path)
            _BUILTIN_TICK_SOUND = sound
            return sound
        except Exception as e:
            print(f"tick.wav load error: {e}")
    # 2. 回退：pygame 合成
    try:
        import array, math
        sample_rate = 44100
        duration_ms = 80
        n_samples = int(sample_rate * duration_ms / 1000)
        buf = array.array('h')
        for i in range(n_samples):
            t = i / sample_rate
            f1, decay1 = 3200.0, math.exp(-t * 180)
            f2, decay2 = 800.0,  math.exp(-t * 60)
            f3, decay3 = 6400.0, math.exp(-t * 300)
            onset = min(1.0, i / 10.0)
            val = onset * (
                math.sin(2 * math.pi * f1 * t) * decay1 +
                math.sin(2 * math.pi * f2 * t) * decay2 * 0.35 +
                math.sin(2 * math.pi * f3 * t) * decay3 * 0.12
            )
            s = int(max(-32768, min(32767, val * 28000)))
            buf.append(s)
            buf.append(s)  # stereo
        sound = pygame.mixer.Sound(buffer=buf)
        _BUILTIN_TICK_SOUND = sound
        return sound
    except Exception as e:
        print(f"Builtin tick synthesis error: {e}")
        return None


def _play_file(path):
    """在独立线程播放音频文件（非阻塞）"""
    if not _PYGAME_AVAILABLE or not path or not os.path.exists(path):
        return
    _ensure_pygame_init()  # Lazy init on first use
    if not _pygame_initialized:
        return
    def _do_play():
        try:
            sound = pygame.mixer.Sound(path)
            sound.play()
        except Exception as e:
            print(f"Sound playback error: {e}")
    threading.Thread(target=_do_play, daemon=True).start()

def _play_default_beep():
    """无自定义音效时的后备提示音"""
    if _WINSOUND_AVAILABLE:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

# ── SoundWorker ────────────────────────────────────────────────────────────────
class SoundWorker(QRunnable):
    """播放阶段结束提示音（放入线程池）"""
    def __init__(self, sound_path=None):
        super().__init__()
        self.sound_path = sound_path

    def run(self):
        if self.sound_path and os.path.exists(self.sound_path):
            _play_file(self.sound_path)
        else:
            _play_default_beep()

# ── TickWorker ─────────────────────────────────────────────────────────────────
class TickWorker(QRunnable):
    """播放单次滴答声（放入线程池）"""
    def __init__(self, sound_path=None):
        super().__init__()
        self.sound_path = sound_path

    def run(self):
        if self.sound_path and os.path.exists(self.sound_path):
            _play_file(self.sound_path)
        else:
            # 使用内置合成滴答声
            tick = _get_builtin_tick()
            if tick:
                try:
                    tick.play()
                except Exception as e:
                    print(f"Builtin tick play error: {e}")


# ── PomodoroTimer ──────────────────────────────────────────────────────────────
class PomodoroTimer(QObject):
    tick = pyqtSignal(int)          # 剩余秒数
    finished = pyqtSignal()
    mode_changed = pyqtSignal(str)  # 'work' | 'break' | 'long_break'
    started = pyqtSignal()
    paused = pyqtSignal()
    abandoned = pyqtSignal()

    def __init__(self, work_minutes=25, break_minutes=5, long_break_minutes=15):
        super().__init__()
        self.work_seconds = int(work_minutes * 60)
        self.break_seconds = int(break_minutes * 60)
        self.long_break_seconds = int(long_break_minutes * 60)

        self.current_mode = 'work'
        self.remaining_seconds = self.work_seconds

        self.is_running = False
        self.sound_enabled = True

        # 三种阶段的自定义提示音路径
        self.sound_work = None        # 工作结束音
        self.sound_break = None       # 短休息结束音
        self.sound_long_break = None  # 长休息结束音

        # 滴答声
        self.tick_sound_work = None         # 工作阶段滴答声路径
        self.tick_sound_break = None        # 休息阶段滴答声路径
        self.tick_enabled_work = False      # 工作阶段滴答声开关
        self.tick_enabled_break = False     # 休息阶段滴答声开关

        self.pomodoros_completed = 0
        self.pomodoros_until_long_break = 4
        self.auto_start = True  # 阶段结束后自动开始下一阶段

        self.timer = QTimer()
        self.timer.timeout.connect(self._handle_tick)
        self.timer.setInterval(200)
        self.end_time = None

        # 滴答声计时器（每秒触发一次）
        self._tick_sound_timer = QTimer()
        self._tick_sound_timer.setInterval(1000)
        self._tick_sound_timer.timeout.connect(self._on_tick_sound)

        self.thread_pool = QThreadPool.globalInstance()

    # ── 时长与设置 ──────────────────────────────────────────────────────────────
    def set_durations(self, work_mins, break_mins, long_break_mins=15):
        self.work_seconds = int(work_mins * 60)
        self.break_seconds = int(break_mins * 60)
        self.long_break_seconds = int(long_break_mins * 60)
        if not self.is_running:
            self.reset()

    def set_long_break_interval(self, interval: int):
        """设置每隔几轮专注触发一次长休息（默认 4 轮）"""
        self.pomodoros_until_long_break = max(1, interval)

    def set_sound_enabled(self, enabled):
        self.sound_enabled = enabled

    def set_sound_paths(self, work=None, short_break=None, long_break=None):
        """设置三种阶段的自定义提示音文件路径"""
        self.sound_work = work
        self.sound_break = short_break
        self.sound_long_break = long_break

    def set_tick_enabled(self, work_tick: bool, break_tick: bool):
        """设置滴答声开关（运行时也立即生效）"""
        self.tick_enabled_work = work_tick
        self.tick_enabled_break = break_tick
        # 若计时器正在运行，立即刷新滴答声定时器
        if self.is_running:
            self._start_tick_sound()

    def set_tick_sound_paths(self, work_tick=None, break_tick=None):
        """设置滴答声文件路径（可选，None 则静音）"""
        self.tick_sound_work = work_tick
        self.tick_sound_break = break_tick

    # ── 计时器控制 ──────────────────────────────────────────────────────────────
    def start(self):
        if not self.is_running:
            self.is_running = True
            self.end_time = QDateTime.currentDateTime().addSecs(self.remaining_seconds)
            self.timer.start()
            self._play_sound()          # 阶段开始音
            self._start_tick_sound()    # 开始滴答声
            self.started.emit()

    def pause(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self._tick_sound_timer.stop()
            self.paused.emit()

    def reset(self):
        self.pause()
        if self.current_mode == 'work':
            self.remaining_seconds = self.work_seconds
        elif self.current_mode == 'break':
            self.remaining_seconds = self.break_seconds
        else:
            self.remaining_seconds = self.long_break_seconds
        self.tick.emit(self.remaining_seconds)

    def abandon(self):
        self.reset()
        self.abandoned.emit()

    def skip(self):
        self.remaining_seconds = 0
        self._finish_session()

    def _finish_session(self):
        self._tick_sound_timer.stop()
        self.pause()
        self._play_sound()       # 阶段结束音
        self.finished.emit()
        self.switch_mode()
        if self.auto_start:
            self.start()        # 自动开始下一阶段

    def switch_mode(self):
        if self.current_mode == 'work':
            self.pomodoros_completed += 1
            if self.pomodoros_completed % self.pomodoros_until_long_break == 0:
                self.current_mode = 'long_break'
                self.remaining_seconds = self.long_break_seconds
            else:
                self.current_mode = 'break'
                self.remaining_seconds = self.break_seconds
        else:
            self.current_mode = 'work'
            self.remaining_seconds = self.work_seconds
        self.mode_changed.emit(self.current_mode)
        self.tick.emit(self.remaining_seconds)

    def _handle_tick(self):
        if not self.is_running:
            return
        now = QDateTime.currentDateTime()
        seconds_left = now.secsTo(self.end_time)
        if seconds_left >= 0:
            if seconds_left != self.remaining_seconds:
                self.remaining_seconds = seconds_left
                self.tick.emit(self.remaining_seconds)
        else:
            self.remaining_seconds = 0
            self.tick.emit(0)
            self._finish_session()

    # ── 音效播放 ────────────────────────────────────────────────────────────────
    def _get_current_sound_path(self):
        """根据当前模式返回对应提示音路径"""
        if self.current_mode == 'work':
            return self.sound_work
        elif self.current_mode == 'break':
            return self.sound_break
        else:
            return self.sound_long_break

    def _play_sound(self):
        if not self.sound_enabled:
            return
        path = self._get_current_sound_path()
        worker = SoundWorker(path)
        self.thread_pool.start(worker)

    def _start_tick_sound(self):
        """根据当前模式决定是否启动滴答声"""
        is_work = (self.current_mode == 'work')
        should_tick = self.tick_enabled_work if is_work else self.tick_enabled_break
        if should_tick:
            self._tick_sound_timer.start()
        else:
            self._tick_sound_timer.stop()

    def _on_tick_sound(self):
        """每秒触发一次，播放滴答声"""
        if not self.is_running:
            return
        is_work = (self.current_mode == 'work')
        should_tick = self.tick_enabled_work if is_work else self.tick_enabled_break
        if not should_tick:
            self._tick_sound_timer.stop()
            return
        path = self.tick_sound_work if is_work else self.tick_sound_break
        worker = TickWorker(path)
        self.thread_pool.start(worker)

    @property
    def is_working(self):
        return self.current_mode == 'work'
