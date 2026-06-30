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
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        print("Successfully updated from GitHub!")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except subprocess.CalledProcessError:
        print("Update failed. Make sure Git is installed and you are inside the repo.")
    except FileNotFoundError:
        print("Git is not installed or not on PATH.")
