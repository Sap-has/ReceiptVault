import sys

from core.db_manager import ReceiptVault
from utils import update_application
'''
Contains the run_gui() function, all CustomTkinter widget definitions (buttons, frames, colors), and the logic for handling clicks within the GUI. 
It will import ReceiptVault from core.db_manager.
It will import update_application from root.utils.py
'''

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