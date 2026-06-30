import os
import sqlite3
import subprocess
import sys
import argparse
import webbrowser
import threading


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class ReceiptVault:
    def init_db(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect("data/bills_data.db")
        self.cur = self.conn.cursor()

        # Enable Foreign Key support (important for SQLite)
        self.cur.execute("PRAGMA foreign_keys = ON;")

        # 1. Vendors Table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )""")

        # 2. Categories Table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL
            )""")

        # 3. Bills Table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       TEXT    NOT NULL,          -- Format: YYYY-MM-DD
                vendor_id  INTEGER,
                price      REAL    CHECK(price > 0),
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE SET NULL
            )""")

        # 4. Trigger – auto-update 'updated_at' on edit
        self.cur.execute("""
            CREATE TRIGGER IF NOT EXISTS update_bills_timestamp
            AFTER UPDATE OF date, vendor_id, price ON bills
            BEGIN
                UPDATE bills SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;""")

        # 5. Indexes
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_date      ON bills(date);")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_bills_vendor_id ON bills(vendor_id);")

        # 6. Junction Table – one bill can belong to multiple categories
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_categories (
                bill_id     INTEGER,
                category_id INTEGER,
                PRIMARY KEY (bill_id, category_id),
                FOREIGN KEY (bill_id)     REFERENCES bills      (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            )""")

        self.cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bill_categories_category_id
            ON bill_categories(category_id);""")

        self.conn.commit()


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


# ---------------------------------------------------------------------------
# Web mode  (Flask)
# ---------------------------------------------------------------------------

def run_web(host: str = "127.0.0.1", port: int = 7000, open_browser: bool = True):
    """Start the Flask web server."""
    try:
        from flask import Flask, jsonify, request as flask_request
    except ImportError:
        print(
            "\n[ERROR] Flask is not installed. Run:  pip install flask\n"
            "        or re-run the launch script so it can install dependencies.\n"
        )
        sys.exit(1)

    vault = ReceiptVault()
    vault.init_db()

    flask_app = Flask(__name__, static_folder="web/static", template_folder="web/templates")

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @flask_app.route("/")
    def index():
        # Serve a minimal landing page until you add real templates
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ReceiptVault</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 80px auto; padding: 0 1rem; }
    h1   { color: #2563eb; }
    a    { color: #2563eb; }
  </style>
</head>
<body>
  <h1>📄 ReceiptVault</h1>
  <p>The web interface is running. Your data is stored locally in <code>data/bills_data.db</code>.</p>
  <ul>
    <li><a href="/api/bills">GET /api/bills</a> – list all bills (JSON)</li>
    <li><a href="/api/vendors">GET /api/vendors</a> – list all vendors (JSON)</li>
    <li><a href="/api/categories">GET /api/categories</a> – list all categories (JSON)</li>
    <li>POST /api/update – pull latest code from GitHub and restart</li>
  </ul>
</body>
</html>"""

    @flask_app.route("/api/bills")
    def api_bills():
        rows = vault.conn.execute("""
            SELECT b.id, b.date, v.name AS vendor, b.price, b.created_at, b.updated_at
            FROM   bills b
            LEFT JOIN vendors v ON b.vendor_id = v.id
            ORDER BY b.date DESC
        """).fetchall()
        cols = ["id", "date", "vendor", "price", "created_at", "updated_at"]
        return jsonify([dict(zip(cols, r)) for r in rows])

    @flask_app.route("/api/vendors")
    def api_vendors():
        rows = vault.conn.execute("SELECT id, name FROM vendors ORDER BY name").fetchall()
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])

    @flask_app.route("/api/categories")
    def api_categories():
        rows = vault.conn.execute(
            "SELECT id, category_name FROM categories ORDER BY category_name"
        ).fetchall()
        return jsonify([{"id": r[0], "category_name": r[1]} for r in rows])

    @flask_app.route("/api/update", methods=["POST"])
    def api_update():
        threading.Thread(target=update_application, daemon=True).start()
        return jsonify({"status": "Update initiated. The server will restart shortly."})

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    url = f"http://{host}:{port}"
    print(f"\n  ReceiptVault is running → {url}\n  Press Ctrl+C to stop.\n")

    if open_browser:
        # Open after a short delay so Flask is ready
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    flask_app.run(host=host, port=port, debug=False)


# ---------------------------------------------------------------------------
# GUI mode  (CustomTkinter)
# ---------------------------------------------------------------------------

def run_gui():
    """Start the CustomTkinter desktop application."""
    try:
        import customtkinter as ctk
    except ImportError:
        print(
            "\n[ERROR] customtkinter is not installed. Run:  pip install customtkinter\n"
            "        or re-run the launch script so it can install dependencies.\n"
        )
        sys.exit(1)

    vault = ReceiptVault()
    vault.init_db()

    app = ctk.CTk()
    app.title("ReceiptVault")
    app.geometry("900x600")

    # ── Sidebar ──────────────────────────────────────────────────────────
    sidebar = ctk.CTkFrame(app, width=200, corner_radius=0)
    sidebar.pack(side="left", fill="y")

    ctk.CTkLabel(sidebar, text="📄 ReceiptVault", font=ctk.CTkFont(size=18, weight="bold")).pack(
        pady=(30, 10), padx=20
    )

    def nav(label):
        return ctk.CTkButton(sidebar, text=label, anchor="w", height=36)

    nav("Dashboard").pack(fill="x", padx=12, pady=4)
    nav("All Receipts").pack(fill="x", padx=12, pady=4)
    nav("Add Receipt").pack(fill="x", padx=12, pady=4)
    nav("Categories").pack(fill="x", padx=12, pady=4)
    nav("Vendors").pack(fill="x", padx=12, pady=4)

    ctk.CTkButton(
        sidebar,
        text="⬆ Update App",
        command=update_application,
        fg_color="transparent",
        border_width=1,
    ).pack(side="bottom", fill="x", padx=12, pady=16)

    # ── Main area ─────────────────────────────────────────────────────────
    main_area = ctk.CTkFrame(app)
    main_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(
        main_area,
        text="Welcome to ReceiptVault",
        font=ctk.CTkFont(size=22, weight="bold"),
    ).pack(pady=(30, 8))

    ctk.CTkLabel(
        main_area,
        text="Your receipts are stored locally in  data/bills_data.db",
        text_color="gray",
    ).pack()

    app.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ReceiptVault",
        description="Local receipt tracking app – run in Web or GUI mode.",
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
    parser.add_argument("--port", type=int, default=7000, help="(Web mode only) Port number")

    args = parser.parse_args()

    if args.gui:
        run_gui()
    else:
        run_web(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()