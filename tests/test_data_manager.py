
import unittest
import os
import json
import time
import shutil
from logic.data_manager import DataManager

class TestDataManager(unittest.TestCase):
    def setUp(self):
        self.test_filename = f"test_data_{self.id().split('.')[-1]}.json"
        if os.path.exists(self.test_filename):
            try: os.remove(self.test_filename)
            except: pass
        if os.path.exists(self.test_filename + ".tmp"):
            try: os.remove(self.test_filename + ".tmp")
            except: pass
        self.dm = DataManager(self.test_filename)

    def tearDown(self):
        # Give a small buffer for any lingering threads to release files
        # (Though unique filenames solve the conflict, we still want to clean up)
        time.sleep(0.05)
        if os.path.exists(self.test_filename):
            try: os.remove(self.test_filename)
            except: pass
        if os.path.exists(self.test_filename + ".tmp"):
            try: os.remove(self.test_filename + ".tmp")
            except: pass

    def test_default_data(self):
        data = self.dm.get_default_data()
        self.assertIn("tasks", data)
        self.assertIn("settings", data)
        self.assertIn("stats", data)
        self.assertEqual(data["stats"]["total_pomodoros"], 0)

    def test_encryption_roundtrip(self):
        # Test the low-level encryption logic
        original_data = {"test": "data", "num": 123}
        json_str = json.dumps(original_data)
        json_bytes = json_str.encode('utf-8')
        
        encrypted = self.dm._xor_cipher_bytes(json_bytes)
        decrypted = self.dm._xor_cipher_bytes(encrypted)
        
        self.assertEqual(json_bytes, decrypted)
        self.assertEqual(json.loads(decrypted.decode('utf-8')), original_data)

    def test_save_and_load(self):
        # DataManager.save_data is async, so we need to wait for it.
        # However, for unit testing, we might want to bypass the thread pool or wait.
        # Since we can't easily force the QRunnable to finish without a loop,
        # let's try a small sleep or rely on the fact that for a small file it's fast.
        # A better way is to instantiate the worker directly and run it.
        
        from logic.data_manager import SaveWorker
        
        self.dm.data["stats"]["total_pomodoros"] = 5
        
        # Manually run the worker to ensure synchronous execution for test
        worker = SaveWorker(self.dm.filename, self.dm.data, self.dm.key, None)
        worker.run()
        
        # Now check if file exists
        self.assertTrue(os.path.exists(self.test_filename))
        
        # Now create a new DataManager and load it
        new_dm = DataManager(self.test_filename)
        self.assertEqual(new_dm.data["stats"]["total_pomodoros"], 5)

    def test_corrupt_file(self):
        # Write garbage to file
        with open(self.test_filename, "w") as f:
            f.write("Not valid JSON or Base64")
            
        # Should return default data without crashing
        new_dm = DataManager(self.test_filename)
        self.assertEqual(new_dm.data["stats"]["total_pomodoros"], 0)

    def test_record_session(self):
        # Initial state
        self.assertEqual(self.dm.data["stats"]["total_minutes"], 0)
        
        self.dm.record_session(25)
        
        self.assertEqual(self.dm.data["stats"]["total_minutes"], 25)
        self.assertEqual(self.dm.data["stats"]["total_pomodoros"], 1)
        
        # Verify history structure
        import datetime
        today = datetime.date.today().isoformat()
        self.assertIn(today, self.dm.data["stats"]["history"])
        self.assertEqual(self.dm.data["stats"]["history"][today]["count"], 1)

    def test_task_migration(self):
        # Create a file with old format (list of strings in "tasks")
        old_data = {
            "tasks": ["Task 1", "Task 2"],
            "settings": {"work_mins": 25}
        }
        # Save it unencrypted (to simulate plain json if supported, or encrypted old way)
        # But wait, load_data tries json first. So if I write plain JSON, it should load.
        
        with open(self.test_filename, "w", encoding="utf-8") as f:
            json.dump(old_data, f)
            
        new_dm = DataManager(self.test_filename)
        
        # Check migration: should be moved to 'q2' (Important Not Urgent) as per code?
        # Code says: if isinstance(tasks, list): data["tasks"]["q2"] = tasks
        # And tasks should be converted to objects
        
        self.assertIsInstance(new_dm.data["tasks"], dict)
        self.assertIn("q2", new_dm.data["tasks"])
        self.assertEqual(len(new_dm.data["tasks"]["q2"]), 2)
        self.assertEqual(new_dm.data["tasks"]["q2"][0]["content"], "Task 1")
        self.assertIn("id", new_dm.data["tasks"]["q2"][0])

if __name__ == '__main__':
    unittest.main()
