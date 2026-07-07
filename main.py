import argparse

from web.server import run_web
from utils import DEFAULT_PORT
'''
Keep the argparse configuration here. Instead of containing logic, it will now act as a "router." 
If no flags are passed, it defaults to web mode.
'''


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ReceiptVault",
        description="Local receipt tracking app - run in Web",
    )
    parser.add_argument("--web", action="store_true", help="Launch the web interface (Flask)")

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open a browser tab",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument(
        "--port", type=int, default=None,
        help=f"Port number. If omitted, the next free port "
             f"starting at {DEFAULT_PORT} is chosen automatically.",
    )

    args = parser.parse_args()

    
    run_web(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()