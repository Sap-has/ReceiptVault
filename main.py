import argparse

from gui.app_gui import run_gui
from web.server import run_web
from utils import DEFAULT_PORT
'''
Keep the argparse configuration here. Instead of containing logic, it will now act as a "router." 
If --gui is passed, it imports and calls gui.app_gui.run_gui(). 
If --web is passed, it imports and calls web.server.run_web().
'''


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ReceiptVault",
        description="Local receipt tracking app - run in Web or GUI mode.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--web", action="store_true", help="Launch the web interface (Flask)")
    group.add_argument("--gui", action="store_true", help="Launch the desktop GUI (CustomTkinter)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="(Web mode only) Don't auto-open a browser tab",
    )
    parser.add_argument("--host", default="127.0.0.1", help="(Web mode only) Bind address")
    parser.add_argument(
        "--port", type=int, default=None,
        help=f"(Web mode only) Port number. If omitted, the next free port "
             f"starting at {DEFAULT_PORT} is chosen automatically.",
    )

    args = parser.parse_args()

    if args.gui:
        run_gui()
    else:
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()