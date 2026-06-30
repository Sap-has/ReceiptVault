import sys
import socket
import webbrowser
import threading

from core.db_manager import ReceiptVault
from utils import update_application, DEFAULT_PORT

'''
Contains the Flask application logic, the @flask_app.route decorators, and the run_web() function. 
It will import ReceiptVault from core.db_manager.
It will import update_application from root.utils.py
'''

# ---------------------------------------------------------------------------
# Web mode  (Flask)
# ---------------------------------------------------------------------------
def _is_port_free(host: str, port: int) -> bool:
    """Return True if `port` can be bound on `host` right now."""
    # 0.0.0.0 means "all interfaces" – probe the wildcard address itself,
    # since that's what Flask will actually try to bind to.
    probe_host = host if host not in ("0.0.0.0", "") else "0.0.0.0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((probe_host, port))
        except OSError:
            return False
        return True


def find_free_port(host: str = "127.0.0.1", start_port: int = DEFAULT_PORT,
                    max_attempts: int = 100) -> int:
    """
    Return `start_port` if it's free, otherwise scan upward and return the
    first free port found. Raises RuntimeError if nothing is free in range.
    """
    for port in range(start_port, start_port + max_attempts):
        if _is_port_free(host, port):
            return port
    raise RuntimeError(
        f"Could not find a free port in range {start_port}-{start_port + max_attempts - 1} "
        f"on {host}. Try freeing up a port or specifying one manually with --port."
    )


def run_web(host: str = "127.0.0.1", port: int | None = None, open_browser: bool = True):
    """Start the Flask web server.

    If `port` is None, the next available port starting at DEFAULT_PORT
    (7000) is chosen automatically and announced to the user. If `port` is
    given explicitly (e.g. via --port), that exact port is used and Flask
    will raise its normal error if it's already taken.
    """
    try:
        from flask import Flask, jsonify, render_template, request as flask_request
    except ImportError:
        print(
            "\n[ERROR] Flask is not installed. Run:  pip install flask\n"
            "        or re-run the launch script so it can install dependencies.\n"
        )
        sys.exit(1)

    auto_selected = port is None
    if auto_selected:
        try:
            port = find_free_port(host=host, start_port=DEFAULT_PORT)
        except RuntimeError as exc:
            print(f"\n[ERROR] {exc}\n")
            sys.exit(1)
        if port != DEFAULT_PORT:
            print(
                f"\n[INFO] Port {DEFAULT_PORT} is already in use – "
                f"using port {port} instead.\n"
            )

    vault = ReceiptVault()
    vault.init_db()

    # static_folder / template_folder are resolved relative to this package's
    # own directory (web/, since that's where server.py lives) — so "static"
    # and "templates" here correctly point at web/static and web/templates.
    flask_app = Flask(__name__, static_folder="static", template_folder="templates")

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @flask_app.route("/")
    def index():
        return render_template("index.html")

    @flask_app.route("/api/bills")
    def api_bills():
        return jsonify(vault.get_all_bills())

    @flask_app.route("/api/vendors")
    def api_vendors():
        return jsonify(vault.get_all_vendors())

    @flask_app.route("/api/categories")
    def api_categories():
        return jsonify(vault.get_all_categories())

    @flask_app.route("/api/update", methods=["POST"])
    def api_update():
        """Start an update in a background thread. Returns immediately so the browser
        gets a response before the server restarts."""
        def perform_update():
            success = update_application()
            if not success:
                print("[WARNING] Update failed - server still running with current version")
        
        threading.Thread(target=perform_update, daemon=True).start()
        return jsonify({
            "status": "Update started",
            "message": "Checking for updates from GitHub. The app will restart shortly with any new changes."
        })

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    if not auto_selected and not _is_port_free(host, port):
        print(
            f"\n[ERROR] Port {port} is already in use on {host}.\n"
            f"        Choose a different port with --port, "
            f"or omit --port to auto-select a free one.\n"
        )
        sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"\n  ReceiptVault is running → {url}\n  Press Ctrl+C to stop.\n")

    if open_browser:
        # Open after a short delay so Flask is ready
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    flask_app.run(host=host, port=port, debug=False)