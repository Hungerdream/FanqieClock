from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QDateTime, QRunnable, QThreadPool
import winsound

class SoundWorker(QRunnable):
    def run(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception as e:
            print(f"Sound playback error: {e}")

class PomodoroTimer(QObject):
    tick = pyqtSignal(int)  # Sends remaining seconds
    finished = pyqtSignal()
    mode_changed = pyqtSignal(str) # 'work', 'break', 'long_break'

    def __init__(self, work_minutes=25, break_minutes=5, long_break_minutes=15):
        super().__init__()
        self.work_seconds = int(work_minutes * 60)
        self.break_seconds = int(break_minutes * 60)
        self.long_break_seconds = int(long_break_minutes * 60)
        
        self.current_mode = 'work' # 'work', 'break', 'long_break'
        self.remaining_seconds = self.work_seconds
        
        self.is_running = False
        self.sound_enabled = True
        
        self.pomodoros_completed = 0
        self.pomodoros_until_long_break = 4
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._handle_tick)
        self.timer.setInterval(200) # Check more frequently for smoothness
        self.end_time = None
        
        self.thread_pool = QThreadPool.globalInstance()

    def set_durations(self, work_mins, break_mins, long_break_mins=15):
        self.work_seconds = int(work_mins * 60)
        self.break_seconds = int(break_mins * 60)
        self.long_break_seconds = int(long_break_mins * 60)
        
        # If currently stopped, reset to apply new duration to current mode if applicable
        if not self.is_running:
            self.reset()

    def start(self):
        if not self.is_running:
            self.is_running = True
            # Calculate expected end time
            self.end_time = QDateTime.currentDateTime().addSecs(self.remaining_seconds)
            self.timer.start()
            self._play_sound()

    def pause(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            # remaining_seconds is already up to date from _handle_tick logic

    def reset(self):
        self.pause()
        if self.current_mode == 'work':
            self.remaining_seconds = self.work_seconds
        elif self.current_mode == 'break':
            self.remaining_seconds = self.break_seconds
        else: # long_break
            self.remaining_seconds = self.long_break_seconds
        self.tick.emit(self.remaining_seconds)

    def skip(self):
        """Skip current session and move to next mode"""
        self.remaining_seconds = 0
        self._finish_session()

    def _finish_session(self):
        self.pause()
        self._play_sound()
        self.finished.emit()
        self.switch_mode()

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
            # After any break, go back to work
            self.current_mode = 'work'
            self.remaining_seconds = self.work_seconds
            
        self.mode_changed.emit(self.current_mode)
        self.tick.emit(self.remaining_seconds)

    def set_sound_enabled(self, enabled):
        self.sound_enabled = enabled

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

    def _play_sound(self):
        if self.sound_enabled:
            worker = SoundWorker()
            self.thread_pool.start(worker)
    
    @property
    def is_working(self):
        return self.current_mode == 'work'
