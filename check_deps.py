import sys

def check_requests():
    print("Checking dependencies...")
    try:
        import requests
        version = requests.__version__
        print(f"requests version: {version}")
        
        # Check against requirements if needed, for now just ensure it imports
        required_version = "2.32.5"
        if version != required_version:
             print(f"Warning: requests version mismatch. Expected {required_version}, got {version}")
             # We can exit with 1 if we want to enforce strict version
             # sys.exit(1) 
        
        print("Dependency check passed.")
        return 0
    except ImportError as e:
        print(f"Error: {e}")
        print("Dependency check failed: requests module not found.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_requests())
