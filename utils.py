import os
import sys
import subprocess

'''
Place "helper" functions that don't belong specifically to a UI but are used by both (like update_application, _is_port_free, and find_free_port).
'''

DEFAULT_PORT = 7000

# ---------------------------------------------------------------------------
# Update helper
# ---------------------------------------------------------------------------

def update_application():
    """Pull latest code from GitHub and restart the process."""
    print("\n[UPDATE] Pulling latest changes from GitHub...")
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("[ERROR] Git pull failed. Check your internet connection and repository status.")
            print(f"        Details: {result.stderr}")
            return False
        
        print(result.stdout)
        print("[UPDATE] Update successful! Restarting application...")
        # os.execv replaces the current process image with the same Python interpreter
        # and arguments, effectively restarting the app.
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except FileNotFoundError:
        print("[ERROR] Git is not installed or not on PATH. Cannot update automatically.")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during update: {e}")
        return False
