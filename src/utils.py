"""Utility functions shared across the application."""
import sys
import os


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, 'frozen'):
        # PyInstaller
        if hasattr(sys, '_MEIPASS'):
            # OneFile mode
            base_path = sys._MEIPASS
        else:
            # OneDir mode
            base_path = os.path.dirname(sys.executable)
    else:
        # Dev mode: src/utils.py -> src
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)
