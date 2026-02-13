import json
import os
import base64
import datetime
from itertools import cycle
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool

class SaveWorker(QRunnable):
    def __init__(self, filename, data, key, error_signal):
        super().__init__()
        self.filename = filename
        self.data = data
        self.key = key
        self.error_signal = error_signal
    
    def run(self):
        try:
            dir_path = os.path.dirname(os.path.abspath(self.filename))
            os.makedirs(dir_path, exist_ok=True)
            
            # Serialize
            json_str = json.dumps(self.data, ensure_ascii=False, indent=None)
            json_bytes = json_str.encode('utf-8')
            
            # Optimized XOR Encryption
            key_bytes = self.key.encode('utf-8')
            encrypted_bytes = bytes(a ^ b for a, b in zip(json_bytes, cycle(key_bytes)))
            
            final_content = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            # Atomic Write
            temp_filename = f"{self.filename}.tmp"
            with open(temp_filename, "w", encoding="utf-8") as f:
                f.write(final_content)
            
            os.replace(temp_filename, self.filename)
        except Exception as e:
            if self.error_signal:
                self.error_signal.emit(str(e))
            print(f"Error saving data in worker: {e}")

class DataManager(QObject):
    save_error = pyqtSignal(str)
    
    def __init__(self, filename="data.json"):
        super().__init__()
        self.filename = filename
        self.key = "Fanqie_Secure_Key_2026" 
        self.thread_pool = QThreadPool.globalInstance()
        self.data = self.load_data()

    def _xor_cipher(self, text):
        # Legacy method for loading old string-based encrypted data if any
        # New method uses bytes which is much faster.
        # This is kept for backward compatibility if needed, but we will upgrade to bytes.
        return "".join([chr(ord(c) ^ ord(self.key[i % len(self.key)])) for i, c in enumerate(text)])

    def _xor_cipher_bytes(self, data_bytes):
        key_bytes = self.key.encode('utf-8')
        return bytes(a ^ b for a, b in zip(data_bytes, cycle(key_bytes)))

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    content = f.read()
                
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # Try decrypting
                    try:
                        decoded_bytes = base64.b64decode(content)
                        # Try new bytes method first
                        try:
                            decrypted_bytes = self._xor_cipher_bytes(decoded_bytes)
                            data = json.loads(decrypted_bytes.decode('utf-8'))
                        except:
                            # Fallback to old string method (if user has old data)
                            decoded_str = decoded_bytes.decode('utf-8')
                            decrypted_str = self._xor_cipher(decoded_str)
                            data = json.loads(decrypted_str)
                    except:
                        return self.get_default_data()

                # Data Migration for Tasks
                if "tasks" in data:
                    tasks = data["tasks"]
                    if isinstance(tasks, list):
                        new_tasks = self.get_default_data()["tasks"]
                        # Assume old list was 'todo' or generic tasks, move to q2 (Important Not Urgent) as default inbox
                        for t in tasks:
                            new_tasks["q2"].append(self._ensure_task_obj(t))
                        data["tasks"] = new_tasks
                    elif "todo" in tasks:
                        new_tasks = self.get_default_data()["tasks"]
                        for t in tasks.get("todo", []):
                            new_tasks["q2"].append(self._ensure_task_obj(t))
                        for t in tasks.get("in_progress", []):
                            new_tasks["q1"].append(self._ensure_task_obj(t))
                        for t in tasks.get("completed", []):
                            new_tasks["completed"].append(self._ensure_task_obj(t))
                        data["tasks"] = new_tasks
                
                default_data = self.get_default_data()
                if "interruptions" not in data:
                    data["interruptions"] = []
                if "settings" not in data:
                    data["settings"] = default_data["settings"]
                
                return data
            except Exception as e:
                print(f"Load Error: {e}")
                return self.get_default_data()
        return self.get_default_data()

    def _ensure_task_obj(self, task):
        if isinstance(task, str):
            import uuid
            return {
                "id": str(uuid.uuid4()),
                "content": task,
                "pomodoros": 0,
                "created_at": datetime.date.today().isoformat()
            }
        return task

    def get_default_data(self):
        return {
            "tasks": {
                "q1": [], 
                "q2": [], 
                "q3": [], 
                "q4": [], 
                "completed": []
            },
            "interruptions": [],
            "notes": [],
            "stats": {
                "total_pomodoros": 0,
                "total_days": 0,
                "total_minutes": 0,
                "history": {} 
            },
            "settings": {
                "work_mins": 25,
                "break_mins": 5,
                "long_break_mins": 15,
                "sound_enabled": True,
                "white_noise_enabled": False,
                "auto_hide_sidebar": True,
                "sidebar_manual_state": None # None=Auto, 'collapsed', 'expanded'
            }
        }

    def save_data(self):
        # Fire and forget
        worker = SaveWorker(self.filename, self.data, self.key, self.save_error)
        self.thread_pool.start(worker)

    def update_tasks(self, tasks_dict):
        self.data["tasks"] = tasks_dict
        self.save_data()

    def update_settings(self, settings_dict):
        current = self.data.get("settings", {})
        current.update(settings_dict)
        self.data["settings"] = current
        self.save_data()

    def update_notes(self, notes_list):
        self.data["notes"] = notes_list
        self.save_data()

    def record_interruption(self, type_name):
        entry = {
            "type": type_name,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.data["interruptions"].append(entry)
        self.save_data()

    def record_session(self, minutes, is_work=True):
        if not is_work: return
        
        today = datetime.date.today().isoformat()
        stats = self.data.get("stats", self.get_default_data()["stats"])
        
        if "history" not in stats: stats["history"] = {}
        
        day_stats = stats["history"].get(today, {"minutes": 0, "count": 0})
        day_stats["minutes"] += minutes
        day_stats["count"] += 1
        
        stats["history"][today] = day_stats
        stats["total_pomodoros"] += 1
        stats["total_minutes"] += minutes
        stats["total_days"] = len(stats["history"])
        
        self.data["stats"] = stats
        self.save_data()
