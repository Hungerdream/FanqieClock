import sys


def check_requests():
    print("Checking requests...")
    try:
        import requests
        version = requests.__version__
        print(f"  requests version: {version}")

        required_version = "2.32.5"
        if version != required_version:
            print(f"  WARNING: requests version mismatch. Expected {required_version}, got {version}")
            sys.exit(1)

        print("  requests OK.")
        return 0
    except ImportError as e:
        print(f"  Error: {e}")
        print("  FAILED: requests module not found.")
        return 1
    except Exception as e:
        print(f"  Unexpected error: {e}")
        return 1


def check_pyqt6():
    print("Checking PyQt6...")
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR
        version = PYQT_VERSION_STR
        print(f"  PyQt6 version: {version}")

        required_version = "6.10.2"
        if version != required_version:
            print(f"  WARNING: PyQt6 version mismatch. Expected {required_version}, got {version}")
            sys.exit(1)

        print("  PyQt6 OK.")
        return 0
    except ImportError as e:
        print(f"  Error: {e}")
        print("  FAILED: PyQt6 module not found.")
        return 1
    except Exception as e:
        print(f"  Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    print("Checking dependencies...")
    rc1 = check_requests()
    rc2 = check_pyqt6()
    if rc1 != 0 or rc2 != 0:
        print("Dependency check FAILED.")
        sys.exit(1)
    print("All dependency checks passed.")
    sys.exit(0)
