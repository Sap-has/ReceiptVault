"""
gui/app_gui.py - Full CustomTkinter desktop GUI for ReceiptVault.

Pages:
  Dashboard   - "Coming soon" placeholder
  All Receipts - Sortable/filterable/searchable table; select a row to delete
  Add Receipt  - Manual entry (vendor autocomplete, DateEntry, categories)
               - Scan Receipt (OCR multi-image queue with side-by-side review)
  Categories   - Add / delete categories
  Vendors      - Add / delete vendors

Navigation is a left-hand sidebar; clicking a button swaps the main content
frame without rebuilding the sidebar.

All DB access goes through ReceiptVault (core/db_manager.py).
OCR scanning goes through core/ocr_processor (lazy-loaded; failure shows a
graceful error message in the Scan tab, not an app crash).
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from datetime import date
from typing import Optional

from core.db_manager import ReceiptVault
from utils import update_application


# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_NAV_PAGES   = ("Dashboard", "All Receipts", "Add Receipt", "Categories", "Vendors")

# Dimensions & Layout
_WINDOW_MIN_W = 900
_WINDOW_MIN_H = 600
_SIDEBAR_W = 200
_CONTENT_PAD = 16
_NAV_BTN_H = 38
_TOAST_DURATION_MS = 2800

# Input & Image Constraints
_INPUT_W_LARGE = 300
_INPUT_W_MED = 200
_INPUT_W_SMALL = 120
_THUMBNAIL_MAX_W = 400
_THUMBNAIL_MAX_H = 550

# Fonts
_FONT_SIDEBAR = 21
_FONT_HEADER = 26
_FONT_TITLE = 36
_FONT_SYS = 18
_FONT_SMALL = 16

# Colors
_COLOR_PRIMARY = "#2a9d2a"
_COLOR_DANGER = "#c0392b"
_COLOR_DANGER_HOVER = "#922b21"
_COLOR_TRANSPARENT = "transparent"
_COLOR_ROW_EVEN = ("gray93", "gray22")
_COLOR_ROW_ODD = ("gray88", "gray26")
_COLOR_SELECTED = ("#b3d4ff", "#1a3a5c")
_COLOR_TEXT_PRIMARY = ("gray10", "gray90")
_COLOR_TEXT_MUTED = "gray"

# Table Columns: (Heading, MinWidth, GridWeight)
_TABLE_COLS = [
    ("Date", 90, 0),
    ("Vendor", 180, 1),
    ("Price", 80, 0),
    ("Categories", 250, 2),
    ("ID", 50, 0)
]

def _center_window(win: tk.Tk | tk.Toplevel, w: int, h: int) -> None:
    """Position *win* at the centre of its screen."""
    win.update_idletasks()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

def _build_date_input(ctk, parent: tk.Widget, date_var: tk.StringVar) -> None:
    try:
        from tkcalendar import DateEntry as TkDateEntry
    except ImportError:
        ctk.CTkLabel(
            parent, text="(install tkcalendar for the calendar picker)", text_color=_COLOR_TEXT_MUTED,
        ).pack(side="left")
        return

    class _PopupSafeDateEntry(TkDateEntry):
        
        def _on_focus_out_cal(self, event):
            pass

        def drop_down(self) -> None:
            if getattr(self, "_calendar", None) and self._calendar.winfo_ismapped():
                if getattr(self, "_top_cal", None):
                    try:
                        self._top_cal.withdraw()
                    except Exception:
                        pass
                return

            self.update_idletasks()
            self._validate_date()
            selected = self.parse_date(self.get())

            if getattr(self, "_top_cal", None):
                try:
                    self._top_cal.deiconify()
                    self._top_cal.lift()
                except Exception:
                    pass

            try:
                self._calendar.focus_set()
                self._calendar.selection_set(selected)
                
                self._calendar.unbind('<FocusOut>')
            except Exception:
                pass

            def _on_root_click(event):
                try:
                    root = self.winfo_toplevel()
                    try:
                        widget_top = event.widget.winfo_toplevel()
                    except Exception:
                        widget_top = None

                    if widget_top is not None and widget_top is not root:
                        return

                    if getattr(self, "_top_cal", None):
                        try:
                            if self._top_cal.winfo_containing(event.x_root, event.y_root) is not None:
                                return
                        except Exception:
                            pass

                    try:
                        root.unbind('<Button-1>')
                    except Exception:
                        pass
                    try:
                        if getattr(self, "_top_cal", None):
                            self._top_cal.withdraw()
                    except Exception:
                        pass
                except Exception:
                    pass

            try:
                root = self.winfo_toplevel()
                root.bind('<Button-1>', _on_root_click, add='+')
            except Exception:
                pass

    today = date.today()
    _PopupSafeDateEntry(
        parent, textvariable=date_var, date_pattern="mm/dd/yyyy", selectmode="day",
        year=today.year, month=today.month, day=today.day, width=12,
    ).pack(side="left")

# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------

class ReceiptVaultApp:
    def __init__(self) -> None:
        try:
            import customtkinter as ctk
        except ImportError:
            print(
                "\n[ERROR] customtkinter is not installed.\n"
                "        Run:  pip install customtkinter\n"
                "        or re-run the launch script so it can install dependencies.\n"
            )
            sys.exit(1)

        self.ctk = ctk
        self.vault = ReceiptVault()
        self.vault.init_db()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.app = ctk.CTk()
        self.app.title("ReceiptVault")
        _center_window(self.app, int(self.app.winfo_screenwidth() * 0.7), int(self.app.winfo_screenheight() * 0.7))
        self.app.minsize(_WINDOW_MIN_W, _WINDOW_MIN_H)

        self._nav_buttons: dict[str, object] = {}
        self._current_page: str = ""

        self._build_layout()
        self.show_page("Dashboard")

    # ------------------------------------------------------------------
    # Top-level layout: sidebar + content area
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        ctk = self.ctk

        # ── Sidebar ───────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self.app, width=_SIDEBAR_W, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="ReceiptVault",
            font=ctk.CTkFont(size=_FONT_SIDEBAR, weight="bold"),
        ).pack(pady=(28, 18), padx=_CONTENT_PAD)

        for label in _NAV_PAGES:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=_NAV_BTN_H,
                corner_radius=6, fg_color=_COLOR_TRANSPARENT,
                text_color=_COLOR_TEXT_PRIMARY,
                hover_color=("gray85", "gray30"),
                command=lambda p=label: self.show_page(p),
            )
            btn.pack(fill="x", padx=10, pady=3)
            self._nav_buttons[label] = btn

        ctk.CTkButton(
            self.sidebar, text="⬆  Update App", command=self._do_update,
            fg_color=_COLOR_TRANSPARENT, border_width=1, height=32, anchor="w",
        ).pack(side="bottom", fill="x", padx=10, pady=14)

        # ── Content area ──────────────────────────────────────────────
        self.content = ctk.CTkFrame(self.app, corner_radius=0, fg_color=_COLOR_TRANSPARENT)
        self.content.pack(side="right", fill="both", expand=True)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_page(self, page: str) -> None:
        """Destroy the current page frame and build the new one."""
        if self._current_page == page:
            return
        self._current_page = page

        for child in self.content.winfo_children():
            child.destroy()

        for label, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=("gray75", "gray35") if label == page else _COLOR_TRANSPARENT,
                text_color=_COLOR_TEXT_PRIMARY,
            )

        builders = {
            "Dashboard":    self._build_dashboard_page,
            "All Receipts": self._build_receipts_page,
            "Add Receipt":  self._build_add_receipt_page,
            "Categories":   self._build_categories_page,
            "Vendors":      self._build_vendors_page,
        }
        builders.get(page, self._build_dashboard_page)()

    # ------------------------------------------------------------------
    # Helpers shared across pages
    # ------------------------------------------------------------------

    def _page_header(self, title: str) -> None:
        self.ctk.CTkLabel(
            self.content, text=title, font=self.ctk.CTkFont(size=_FONT_HEADER, weight="bold"), anchor="w",
        ).pack(fill="x", padx=_CONTENT_PAD, pady=(_CONTENT_PAD, 6))

    def _show_toast(self, message: str, color: str = _COLOR_PRIMARY, duration_ms: int = _TOAST_DURATION_MS) -> None:
        lbl = self.ctk.CTkLabel(
            self.content, text=message, text_color="white",
            fg_color=color, corner_radius=6, height=30,
        )
        lbl.pack(fill="x", padx=_CONTENT_PAD, pady=(4, _CONTENT_PAD))
        self.app.after(duration_ms, lambda: lbl.destroy() if lbl.winfo_exists() else None)

    def _do_update(self) -> None:
        """Pull latest code and restart, run in a thread so the UI doesn't freeze."""
        threading.Thread(target=update_application, daemon=True).start()

    # ==================================================================
    # PAGE: Dashboard
    # ==================================================================

    def _build_dashboard_page(self) -> None:
        self._page_header("Dashboard")
        frame = self.ctk.CTkFrame(self.content, fg_color=_COLOR_TRANSPARENT)
        frame.pack(expand=True)

        self.ctk.CTkLabel(frame, text="Coming Soon", font=self.ctk.CTkFont(size=_FONT_TITLE, weight="bold"), text_color=_COLOR_TEXT_MUTED).pack(pady=(60, 12))
        self.ctk.CTkLabel(frame, text="Spending summaries, charts, and trends will appear here.", font=self.ctk.CTkFont(size=_FONT_SYS), text_color=_COLOR_TEXT_MUTED).pack()

    # ==================================================================
    # PAGE: All Receipts
    # ==================================================================

    def _build_receipts_page(self) -> None:
        ctk = self.ctk
        self._page_header("All Receipts")

        # ── Filter / search bar ───────────────────────────────────────
        bar = ctk.CTkFrame(self.content, fg_color=_COLOR_TRANSPARENT)
        bar.pack(fill="x", padx=_CONTENT_PAD, pady=(0, 8))

        # Search box
        self._receipt_search_var = tk.StringVar()
        ctk.CTkLabel(bar, text="Search:").pack(side="left", padx=(0, 4))
        search_entry = ctk.CTkEntry(bar, width=_INPUT_W_MED, textvariable=self._receipt_search_var, placeholder_text="vendor / date / cat…")
        search_entry.pack(side="left", padx=(0, 16), fill="x", expand=True)

        # Vendor filter
        vendors = ["All Vendors"] + [v["name"] for v in self.vault.get_all_vendors()]
        self._receipt_vendor_var = tk.StringVar(value="All Vendors")
        ctk.CTkOptionMenu(bar, values=vendors, variable=self._receipt_vendor_var, width=_INPUT_W_MED).pack(side="left", padx=(0, 8))

        # Category filter
        cats = ["All Categories"] + [c["category_name"] for c in self.vault.get_all_categories()]
        self._receipt_cat_var = tk.StringVar(value="All Categories")
        ctk.CTkOptionMenu(bar, values=cats, variable=self._receipt_cat_var, width=_INPUT_W_MED).pack(side="left", padx=(0, 16))

        ctk.CTkButton(bar, text="Filter", width=90, command=self._refresh_receipts_table).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="Clear", width=70, fg_color=_COLOR_TRANSPARENT, border_width=1, command=self._clear_receipt_filters).pack(side="left", padx=(0, 16))

        # Sort controls
        ctk.CTkLabel(bar, text="Sort by:").pack(side="left", padx=(0, 4))
        self._receipt_sort_var = tk.StringVar(value="Date ↓")
        ctk.CTkOptionMenu(
            bar, values=["Date ↓", "Date ↑", "Price ↓", "Price ↑", "Vendor A-Z"],
            variable=self._receipt_sort_var, width=_INPUT_W_SMALL,
            command=lambda _: self._refresh_receipts_table(),
        ).pack(side="left", padx=(0, 8))

        # ── Table area ────────────────────────────────────────────────
        self._receipt_table_frame = ctk.CTkScrollableFrame(self.content)
        self._receipt_table_frame.pack(fill="both", expand=True, padx=_CONTENT_PAD, pady=(0, 4))

        # ── Action bar ────────────────────────────────────────────────
        action = ctk.CTkFrame(self.content, fg_color=_COLOR_TRANSPARENT)
        action.pack(fill="x", padx=_CONTENT_PAD, pady=(4, _CONTENT_PAD))
        
        self._receipt_selected_id: Optional[int] = None
        self._receipt_selected_label = ctk.CTkLabel(action, text="No receipt selected", text_color=_COLOR_TEXT_MUTED)
        self._receipt_selected_label.pack(side="left")
        ctk.CTkButton(
            action, text="Delete Selected", fg_color=_COLOR_DANGER, hover_color=_COLOR_DANGER_HOVER, width=160,
            command=self._delete_selected_receipt,
        ).pack(side="right")

        # Bind search-on-enter and auto-search on type
        self._receipt_search_var.trace_add("write", lambda *_: self.app.after(300, self._refresh_receipts_table))
        self._refresh_receipts_table()


    def _clear_receipt_filters(self) -> None:
        self._receipt_search_var.set("")
        self._receipt_vendor_var.set("All Vendors")
        self._receipt_cat_var.set("All Categories")
        self._receipt_sort_var.set("Date ↓")
        self._refresh_receipts_table()

    def _setup_table_grid_weights(self, target_frame) -> None:
        """Applies consistent grid sizing to a row, allowing it to respond to window resizes."""
        for col_i, (_, min_w, weight) in enumerate(_TABLE_COLS):
            target_frame.grid_columnconfigure(col_i, weight=weight, minsize=min_w)

    def _refresh_receipts_table(self) -> None:
        frame = self._receipt_table_frame
        try:
            if not frame.winfo_exists(): return
        except Exception: return

        for w in frame.winfo_children():
            w.destroy()

        # Database retrieval and filtering logic
        vendor_name = self._receipt_vendor_var.get()
        cat_name = self._receipt_cat_var.get()
        search_q = self._receipt_search_var.get().strip().lower()

        vendor_id_filter = next((v["id"] for v in self.vault.get_all_vendors() if v["name"] == vendor_name), None) if vendor_name != "All Vendors" else None
        cat_id_filter = next((c["id"] for c in self.vault.get_all_categories() if c["category_name"] == cat_name), None) if cat_name != "All Categories" else None

        bills = self.vault.get_bills_filtered(vendor_id=vendor_id_filter, category_id=cat_id_filter)

        if search_q:
            bills = [b for b in bills if search_q in " ".join([b.get("vendor") or "", b.get("date") or "", " ".join(c["category_name"] for c in b.get("categories", []))]).lower()]

        sort = self._receipt_sort_var.get()
        if sort == "Date ↓": bills.sort(key=lambda b: b["date"], reverse=True)
        elif sort == "Date ↑": bills.sort(key=lambda b: b["date"])
        elif sort == "Price ↓": bills.sort(key=lambda b: b["price"] or 0, reverse=True)
        elif sort == "Price ↑": bills.sort(key=lambda b: b["price"] or 0)
        elif sort == "Vendor A-Z": bills.sort(key=lambda b: (b.get("vendor") or "").lower())

        # Render responsive headers
        hdr_frame = self.ctk.CTkFrame(frame, fg_color=_COLOR_TRANSPARENT)
        hdr_frame.pack(fill="x", padx=4, pady=(2, 4))
        self._setup_table_grid_weights(hdr_frame)

        for col_i, (hdr, _, _) in enumerate(_TABLE_COLS):
            self.ctk.CTkLabel(hdr_frame, text=hdr, font=self.ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=col_i, padx=8, sticky="ew")
        self.ctk.CTkFrame(frame, height=1, fg_color="gray50").pack(fill="x", padx=4, pady=(0, 6))

        if not bills:
            self.ctk.CTkLabel(frame, text="No receipts found.", text_color=_COLOR_TEXT_MUTED).pack(pady=20)
            return

        self._receipt_row_frames = []
        self._receipt_selected_id = None

        # Render responsive rows
        for row_i, bill in enumerate(bills):
            from core.ocr_processor import from_db_date
            row_data = [
                from_db_date(bill["date"]),
                bill.get("vendor") or "(no vendor)",
                f"${bill['price']:.2f}" if bill.get("price") else "—",
                ", ".join(c["category_name"] for c in bill.get("categories", [])),
                str(bill["id"])
            ]
            
            row_bg = _COLOR_ROW_EVEN if row_i % 2 == 0 else _COLOR_ROW_ODD
            row_frame = self.ctk.CTkFrame(frame, fg_color=row_bg, corner_radius=4)
            row_frame.pack(fill="x", padx=2, pady=1)
            self._setup_table_grid_weights(row_frame)

            def on_click(event=None, bid=bill["id"], rf=row_frame, vname=row_data[1]):
                self._select_receipt_row(bid, rf, vname)

            for col_i, text in enumerate(row_data):
                lbl = self.ctk.CTkLabel(row_frame, text=text, anchor="w", font=self.ctk.CTkFont(size=_FONT_SYS))
                lbl.grid(row=0, column=col_i, padx=8, pady=6, sticky="ew")
                lbl.bind("<Button-1>", on_click)
                
            row_frame.bind("<Button-1>", on_click)
            self._receipt_row_frames.append((bill["id"], row_frame))

    def _select_receipt_row(self, bill_id: int, clicked_frame, vendor_name: str) -> None:
        for idx, (bid, rf) in enumerate(self._receipt_row_frames):
            if rf.winfo_exists():
                rf.configure(fg_color=_COLOR_ROW_EVEN if idx % 2 == 0 else _COLOR_ROW_ODD)
                
        if clicked_frame.winfo_exists():
            clicked_frame.configure(fg_color=_COLOR_SELECTED)

        self._receipt_selected_id = bill_id
        self._receipt_selected_label.configure(text=f"Selected: #{bill_id}  {vendor_name}", text_color=_COLOR_TEXT_PRIMARY)

    def _delete_selected_receipt(self) -> None:
        if self._receipt_selected_id is None:
            self._show_toast("Select a receipt first.", color=_COLOR_DANGER)
            return
            
        bid = self._receipt_selected_id
        if self.vault.delete_bill(bid):
            self._show_toast(f"Receipt #{bid} deleted.")
            self._receipt_selected_id = None
            self._refresh_receipts_table()
        else:
            self._show_toast(f"Could not delete receipt #{bid}.", color=_COLOR_DANGER)

    # ==================================================================
    # PAGE: Add Receipt  (tabs: Manual Entry | Scan Receipt)
    # ==================================================================

    def _build_add_receipt_page(self) -> None:
        self._page_header("Add Receipt")
        tabs = self.ctk.CTkTabview(self.content, anchor="nw")
        tabs.pack(fill="both", expand=True, padx=_CONTENT_PAD, pady=(0, _CONTENT_PAD))
        tabs.add("Manual Entry")
        tabs.add("Scan Receipt (OCR)")

        self._build_manual_entry_tab(tabs.tab("Manual Entry"))
        self._build_ocr_tab(tabs.tab("Scan Receipt (OCR)"))

    # ── Manual Entry tab ──────────────────────────────────────────────

    def _build_manual_entry_tab(self, parent) -> None:
        ctk = self.ctk
        form = ctk.CTkScrollableFrame(parent, fg_color=_COLOR_TRANSPARENT)
        form.pack(fill="both", expand=True, padx=8, pady=8)
        form.columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(form, text="Vendor *", anchor="e", width=90).grid(row=row, column=0, padx=(0, 8), pady=8, sticky="e")
        vendor_frame = ctk.CTkFrame(form, fg_color=_COLOR_TRANSPARENT)
        vendor_frame.grid(row=row, column=1, padx=0, pady=8, sticky="ew")
        vendor_frame.columnconfigure(0, weight=1)

        self._manual_vendor_var = tk.StringVar()
        self._manual_vendor_entry = ctk.CTkEntry(vendor_frame, textvariable=self._manual_vendor_var, placeholder_text="Start typing to see suggestions…", width=_INPUT_W_LARGE)
        self._manual_vendor_entry.grid(row=0, column=0, sticky="ew")
        self._vendor_suggest_frame = ctk.CTkScrollableFrame(vendor_frame, height=120, fg_color=("white", "gray20"), border_width=1, border_color="gray60")
        self._manual_vendor_var.trace_add("write", lambda *_: self._update_vendor_suggestions())
        row += 1

        ctk.CTkLabel(form, text="Price ($) *", anchor="e", width=90).grid(row=row, column=0, padx=(0, 8), pady=8, sticky="e")
        self._manual_price_var = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self._manual_price_var, placeholder_text="e.g. 12.99", width=_INPUT_W_MED).grid(row=row, column=1, padx=0, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(form, text="Date *", anchor="e", width=90).grid(row=row, column=0, padx=(0, 8), pady=8, sticky="e")
        date_frame = ctk.CTkFrame(form, fg_color=_COLOR_TRANSPARENT)
        date_frame.grid(row=row, column=1, padx=0, pady=8, sticky="w")

        self._manual_date_var = tk.StringVar(value=date.today().strftime("%m/%d/%Y"))
        _build_date_input(ctk, date_frame, self._manual_date_var)
        row += 1

        ctk.CTkLabel(form, text="Categories", anchor="ne", width=90).grid(row=row, column=0, padx=(0, 8), pady=8, sticky="ne")
        cats_frame = ctk.CTkScrollableFrame(form, height=140, fg_color=_COLOR_TRANSPARENT)
        cats_frame.grid(row=row, column=1, padx=0, pady=8, sticky="ew")
        self._manual_cat_vars: dict[int, tk.IntVar] = {}
        self._rebuild_category_checkboxes(cats_frame, self._manual_cat_vars)
        row += 1

        btn_row = ctk.CTkFrame(form, fg_color=_COLOR_TRANSPARENT)
        btn_row.grid(row=row, column=0, columnspan=2, pady=16)
        ctk.CTkButton(btn_row, text="💾  Save Receipt", width=180, command=self._save_manual_receipt).pack()
        row += 1

        self._manual_status = ctk.CTkLabel(form, text="", text_color=_COLOR_TEXT_MUTED)
        self._manual_status.grid(row=row, column=0, columnspan=2, pady=(0, 8))

    def _rebuild_category_checkboxes(self, frame, var_dict: dict) -> None:
        for w in frame.winfo_children(): w.destroy()
        var_dict.clear()
        cats = self.vault.get_all_categories()
        if not cats:
            self.ctk.CTkLabel(frame, text="No categories yet - add them in the Categories page.", text_color=_COLOR_TEXT_MUTED, font=self.ctk.CTkFont(size=_FONT_SYS)).pack(anchor="w", pady=4)
            return
        for cat in cats:
            var = tk.IntVar(value=0)
            var_dict[cat["id"]] = var
            self.ctk.CTkCheckBox(frame, text=cat["category_name"], variable=var).pack(anchor="w", padx=4, pady=2)

    def _update_vendor_suggestions(self) -> None:
        query, frame = self._manual_vendor_var.get(), self._vendor_suggest_frame
        for w in frame.winfo_children(): w.destroy()
        
        results = self.vault.search_vendors(query)
        if results:
            frame.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            for v in results:
                self.ctk.CTkButton(
                    frame, text=v["name"], anchor="w", height=28, fg_color=_COLOR_TRANSPARENT,
                    text_color=_COLOR_TEXT_PRIMARY, hover_color=("gray80", "gray30"),
                    command=lambda n=v["name"]: self._pick_vendor_suggestion(n),
                ).pack(fill="x", padx=2, pady=1)
        else:
            frame.grid_remove()

    def _pick_vendor_suggestion(self, name: str) -> None:
        self._manual_vendor_var.set(name)
        self._vendor_suggest_frame.grid_remove()
        self._manual_vendor_entry.focus_set()
        self._manual_vendor_entry.icursor("end")

    def _save_manual_receipt(self) -> None:
        vendor_name = self._manual_vendor_var.get().strip()
        price_raw   = self._manual_price_var.get().strip()
        date_str    = self._manual_date_var.get().strip()
        errors = []

        if not vendor_name: errors.append("Vendor is required.")
        if not price_raw: errors.append("Price is required.")
        else:
            try:
                if float(price_raw.replace(",", ".")) <= 0: raise ValueError
            except ValueError: errors.append("Price must be a positive number.")

        try:
            from core.ocr_processor import to_db_date
            db_date = to_db_date(date_str)
        except ValueError:
            errors.append("Date must be in mm/dd/yyyy format.")

        if errors:
            self._manual_status.configure(text="\n".join(errors), text_color=_COLOR_DANGER)
            return

        price = float(price_raw.replace(",", "."))
        vendor_id = self.vault.get_or_create_vendor(vendor_name)
        cat_ids = [cid for cid, var in self._manual_cat_vars.items() if var.get() == 1]
        bill_id = self.vault.create_bill(db_date, vendor_id, price, cat_ids)

        self._manual_vendor_var.set("")
        self._manual_price_var.set("")
        self._manual_date_var.set(date.today().strftime("%m/%d/%Y"))
        for var in self._manual_cat_vars.values(): var.set(0)
        self._vendor_suggest_frame.grid_remove()
        
        self._manual_status.configure(text=f"✔  Receipt #{bill_id} saved!", text_color=_COLOR_PRIMARY)

    # ── OCR / Scan Receipt tab ────────────────────────────────────────

    def _build_ocr_tab(self, parent) -> None:
        ctk = self.ctk
        self._ocr_queue, self._ocr_index = [], 0

        ctrl = ctk.CTkFrame(parent, fg_color=_COLOR_TRANSPARENT)
        ctrl.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkButton(ctrl, text="Select Images…", width=160, command=self._ocr_select_images).pack(side="left", padx=(0, 12))
        self._ocr_progress_label = ctk.CTkLabel(ctrl, text="No images selected.", text_color=_COLOR_TEXT_MUTED)
        self._ocr_progress_label.pack(side="left")

        # Responsive Split Pane
        pane = ctk.CTkFrame(parent, fg_color=_COLOR_TRANSPARENT)
        pane.pack(fill="both", expand=True, padx=8, pady=4)
        pane.columnconfigure(0, weight=1)
        pane.columnconfigure(1, weight=1)
        pane.rowconfigure(0, weight=1)

        # Left Column - Receipt Thumbnail
        img_outer = ctk.CTkFrame(pane, corner_radius=8)
        img_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        self._ocr_img_label = ctk.CTkLabel(img_outer, text="Receipt image will appear here.", text_color=_COLOR_TEXT_MUTED)
        self._ocr_img_label.pack(expand=True, fill="both", padx=12, pady=12)

        # Right Column - Data Verification
        fields_outer = ctk.CTkScrollableFrame(pane, fg_color=_COLOR_TRANSPARENT)
        fields_outer.grid(row=0, column=1, sticky="nsew", pady=0)
        fields_outer.columnconfigure(1, weight=1)

        def make_row(lbl_text, row_n):
            ctk.CTkLabel(fields_outer, text=lbl_text, anchor="e", width=80).grid(row=row_n, column=0, padx=(0, 8), pady=8, sticky="e")

        make_row("Vendor *", 0)
        self._ocr_vendor_var = tk.StringVar()
        ctk.CTkEntry(fields_outer, textvariable=self._ocr_vendor_var, placeholder_text="Vendor name", width=_INPUT_W_MED).grid(row=0, column=1, padx=0, pady=8, sticky="ew")
        
        self._ocr_vendor_suggest_frame = ctk.CTkScrollableFrame(fields_outer, height=100, fg_color=("white", "gray20"), border_width=1, border_color="gray60")
        self._ocr_vendor_var.trace_add("write", lambda *_: self._update_ocr_vendor_suggestions())

        make_row("Price ($) *", 2)
        self._ocr_price_var = tk.StringVar()
        ctk.CTkEntry(fields_outer, textvariable=self._ocr_price_var, placeholder_text="e.g. 12.99", width=_INPUT_W_SMALL).grid(row=2, column=1, padx=0, pady=8, sticky="w")

        make_row("Date *", 3)
        date_frame2 = ctk.CTkFrame(fields_outer, fg_color=_COLOR_TRANSPARENT)
        date_frame2.grid(row=3, column=1, padx=0, pady=8, sticky="w")
        self._ocr_date_var = tk.StringVar(value=date.today().strftime("%m/%d/%Y"))
        _build_date_input(ctk, date_frame2, self._ocr_date_var)

        make_row("Categories", 4)
        ocr_cats = ctk.CTkScrollableFrame(fields_outer, height=110, fg_color=_COLOR_TRANSPARENT)
        ocr_cats.grid(row=4, column=1, padx=0, pady=8, sticky="ew")
        self._ocr_cat_vars: dict[int, tk.IntVar] = {}
        self._rebuild_category_checkboxes(ocr_cats, self._ocr_cat_vars)

        nav_row = ctk.CTkFrame(fields_outer, fg_color=_COLOR_TRANSPARENT)
        nav_row.grid(row=5, column=0, columnspan=2, pady=(12, 4))
        ctk.CTkButton(nav_row, text="⬅  Previous", width=110, command=lambda: self._ocr_navigate(-1)).pack(side="left", padx=4)
        ctk.CTkButton(nav_row, text="Save & Next ➡", width=150, command=self._ocr_save_and_next).pack(side="left", padx=4)
        ctk.CTkButton(nav_row, text="Skip ➡", width=80, fg_color=_COLOR_TRANSPARENT, border_width=1, command=lambda: self._ocr_navigate(1)).pack(side="left", padx=4)

        self._ocr_status = ctk.CTkLabel(fields_outer, text="", text_color=_COLOR_TEXT_MUTED, wraplength=280)
        self._ocr_status.grid(row=6, column=0, columnspan=2, pady=(4, 0))

    def _update_ocr_vendor_suggestions(self) -> None:
        query, frame = self._ocr_vendor_var.get(), self._ocr_vendor_suggest_frame
        for w in frame.winfo_children(): w.destroy()
        
        results = self.vault.search_vendors(query)
        if results:
            frame.grid(row=1, column=1, sticky="ew", pady=(0, 4))
            for v in results:
                self.ctk.CTkButton(
                    frame, text=v["name"], anchor="w", height=26, fg_color=_COLOR_TRANSPARENT,
                    text_color=_COLOR_TEXT_PRIMARY, hover_color=("gray80", "gray30"),
                    command=lambda n=v["name"]: (self._ocr_vendor_var.set(n), self._ocr_vendor_suggest_frame.grid_remove()),
                ).pack(fill="x", padx=2, pady=1)
        else:
            frame.grid_remove()

    def _ocr_select_images(self) -> None:
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(title="Select Receipt Images", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"), ("All files", "*.*")])
        if not paths: return
        
        self._ocr_queue, self._ocr_index = list(paths), 0
        self._ocr_progress_label.configure(text=f"0 / {len(self._ocr_queue)} — scanning…", text_color=_COLOR_TEXT_MUTED)
        self._ocr_load_current()

    def _ocr_load_current(self) -> None:
        if not self._ocr_queue or self._ocr_index >= len(self._ocr_queue):
            self._ocr_progress_label.configure(text="All images processed.", text_color=_COLOR_PRIMARY)
            return

        path = self._ocr_queue[self._ocr_index]
        self._ocr_progress_label.configure(text=f"Image {self._ocr_index + 1} / {len(self._ocr_queue)}  —  {path.split('/')[-1]}", text_color=_COLOR_TEXT_MUTED)
        self._ocr_status.configure(text="⏳ Scanning…", text_color=_COLOR_TEXT_MUTED)
        self.app.update_idletasks()

        self._ocr_show_image(path)

        def _scan():
            try:
                from core.ocr_processor import scan_receipt
                result = scan_receipt(path)
                self.app.after(0, lambda: self._ocr_fill_fields(result))
            except RuntimeError as exc:
                self.app.after(0, lambda e=exc: self._ocr_status.configure(text=f"OCR unavailable: {e}", text_color=_COLOR_DANGER))
            except Exception as exc:
                self.app.after(0, lambda e=exc: self._ocr_status.configure(text=f"Scan error: {e}", text_color=_COLOR_DANGER))

        threading.Thread(target=_scan, daemon=True).start()

    def _ocr_show_image(self, path: str) -> None:
        try:
            from PIL import Image
            img = Image.open(path)
            img.thumbnail((_THUMBNAIL_MAX_W, _THUMBNAIL_MAX_H), Image.LANCZOS)
            ctk_img = self.ctk.CTkImage(light_image=img, size=img.size)
            self._ocr_img_label.configure(image=ctk_img, text="")
            self._ocr_img_label._ctk_image_ref = ctk_img 
        except Exception as exc:
            self._ocr_img_label.configure(image=None, text=f"Cannot display image:\n{exc}")

    def _ocr_fill_fields(self, result) -> None:
        self._ocr_vendor_var.set(result.vendor)
        self._ocr_price_var.set(result.price)
        if result.date_str: self._ocr_date_var.set(result.date_str)
        self._ocr_status.configure(text="✔ Scan complete. Review the fields and save.", text_color=_COLOR_PRIMARY)

    def _ocr_navigate(self, direction: int) -> None:
        new_idx = self._ocr_index + direction
        if 0 <= new_idx < len(self._ocr_queue):
            self._ocr_index = new_idx
            self._ocr_load_current()

    def _ocr_save_and_next(self) -> None:
        vendor_name = self._ocr_vendor_var.get().strip()
        price_raw   = self._ocr_price_var.get().strip()
        date_str    = self._ocr_date_var.get().strip()
        errors = []

        if not vendor_name: errors.append("Vendor is required.")
        if not price_raw: errors.append("Price is required.")
        else:
            try:
                if float(price_raw.replace(",", ".")) <= 0: raise ValueError
            except ValueError: errors.append("Price must be a positive number.")

        try:
            from core.ocr_processor import to_db_date
            db_date = to_db_date(date_str)
        except ValueError:
            errors.append("Date must be in mm/dd/yyyy format.")

        if errors:
            self._ocr_status.configure(text="\n".join(errors), text_color=_COLOR_DANGER)
            return

        price = float(price_raw.replace(",", "."))
        vendor_id = self.vault.get_or_create_vendor(vendor_name)
        cat_ids = [cid for cid, var in self._ocr_cat_vars.items() if var.get() == 1]
        bill_id = self.vault.create_bill(db_date, vendor_id, price, cat_ids)

        self._ocr_status.configure(text=f"✔ Receipt #{bill_id} saved!", text_color=_COLOR_PRIMARY)
        for var in self._ocr_cat_vars.values(): var.set(0)

        self._ocr_index += 1
        if self._ocr_index < len(self._ocr_queue):
            self.app.after(600, self._ocr_load_current)
        else:
            self._ocr_progress_label.configure(text=f"All {len(self._ocr_queue)} image(s) processed.", text_color=_COLOR_PRIMARY)
            self._ocr_img_label.configure(image=None, text="All done! Select more images to continue.")

    # ==================================================================
    # PAGE: Categories
    # ==================================================================

    def _build_categories_page(self) -> None:
        ctk = self.ctk
        self._page_header("Categories")

        add_frame = ctk.CTkFrame(self.content, fg_color=_COLOR_TRANSPARENT)
        add_frame.pack(fill="x", padx=_CONTENT_PAD, pady=(0, 12))

        self._new_cat_var = tk.StringVar()
        ctk.CTkEntry(add_frame, textvariable=self._new_cat_var, placeholder_text="New category name…", width=_INPUT_W_LARGE).pack(side="left", padx=(0, 8))
        ctk.CTkButton(add_frame, text="+ Add", width=80, command=self._add_category).pack(side="left")

        self._cat_list_frame = ctk.CTkScrollableFrame(self.content, label_text="Existing Categories")
        self._cat_list_frame.pack(fill="both", expand=True, padx=_CONTENT_PAD, pady=(0, _CONTENT_PAD))
        self._refresh_cat_list()

    def _refresh_cat_list(self) -> None:
        ctk = self.ctk
        for w in self._cat_list_frame.winfo_children(): w.destroy()
        
        cats = self.vault.get_all_categories()
        if not cats:
            ctk.CTkLabel(self._cat_list_frame, text="No categories yet.", text_color=_COLOR_TEXT_MUTED).pack(pady=12)
            return
            
        for cat in cats:
            row = ctk.CTkFrame(self._cat_list_frame, fg_color=_COLOR_TRANSPARENT)
            row.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(row, text=cat["category_name"], anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="Delete", width=70, fg_color=_COLOR_DANGER, hover_color=_COLOR_DANGER_HOVER,
                command=lambda cid=cat["id"]: self._delete_category(cid),
            ).pack(side="right")

    def _add_category(self) -> None:
        name = self._new_cat_var.get().strip()
        if not name: return self._show_toast("Enter a category name first.", color=_COLOR_DANGER)
        try:
            self.vault.get_or_create_category(name)
            self._new_cat_var.set("")
            self._refresh_cat_list()
            self._show_toast(f"Category '{name}' added.")
        except Exception as exc:
            self._show_toast(str(exc), color=_COLOR_DANGER)

    def _delete_category(self, cat_id: int) -> None:
        cat = self.vault.get_category_by_id(cat_id)
        name = cat["category_name"] if cat else f"#{cat_id}"
        if self.vault.delete_category(cat_id):
            self._refresh_cat_list()
            self._show_toast(f"Category '{name}' deleted.")
        else:
            self._show_toast(f"Could not delete category '{name}'.", color=_COLOR_DANGER)

    # ==================================================================
    # PAGE: Vendors
    # ==================================================================

    def _build_vendors_page(self) -> None:
        ctk = self.ctk
        self._page_header("Vendors")

        add_frame = ctk.CTkFrame(self.content, fg_color=_COLOR_TRANSPARENT)
        add_frame.pack(fill="x", padx=_CONTENT_PAD, pady=(0, 12))

        self._new_vendor_var = tk.StringVar()
        ctk.CTkEntry(add_frame, textvariable=self._new_vendor_var, placeholder_text="New vendor name…", width=_INPUT_W_LARGE).pack(side="left", padx=(0, 8))
        ctk.CTkButton(add_frame, text="+ Add", width=80, command=self._add_vendor).pack(side="left")

        self._vendor_list_frame = ctk.CTkScrollableFrame(self.content, label_text="Existing Vendors")
        self._vendor_list_frame.pack(fill="both", expand=True, padx=_CONTENT_PAD, pady=(0, _CONTENT_PAD))
        self._refresh_vendor_list()

    def _refresh_vendor_list(self) -> None:
        ctk = self.ctk
        for w in self._vendor_list_frame.winfo_children(): w.destroy()
        
        vendors = self.vault.get_all_vendors()
        if not vendors:
            ctk.CTkLabel(self._vendor_list_frame, text="No vendors yet.", text_color=_COLOR_TEXT_MUTED).pack(pady=12)
            return
            
        for v in vendors:
            row = ctk.CTkFrame(self._vendor_list_frame, fg_color=_COLOR_TRANSPARENT)
            row.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(row, text=v["name"], anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="Delete", width=70, fg_color=_COLOR_DANGER, hover_color=_COLOR_DANGER_HOVER,
                command=lambda vid=v["id"]: self._delete_vendor(vid),
            ).pack(side="right")

    def _add_vendor(self) -> None:
        name = self._new_vendor_var.get().strip()
        if not name: return self._show_toast("Enter a vendor name first.", color=_COLOR_DANGER)
        try:
            self.vault.get_or_create_vendor(name)
            self._new_vendor_var.set("")
            self._refresh_vendor_list()
            self._show_toast(f"Vendor '{name}' added.")
        except Exception as exc:
            self._show_toast(str(exc), color=_COLOR_DANGER)

    def _delete_vendor(self, vendor_id: int) -> None:
        vendor = self.vault.get_vendor_by_id(vendor_id)
        name = vendor["name"] if vendor else f"#{vendor_id}"
        if self.vault.delete_vendor(vendor_id):
            self._refresh_vendor_list()
            self._show_toast(f"Vendor '{name}' deleted. Bills using it will show no vendor.")
        else:
            self._show_toast(f"Could not delete vendor '{name}'.", color=_COLOR_DANGER)

    # ==================================================================
    # Run
    # ==================================================================

    def run(self) -> None:
        self.app.mainloop()


# ---------------------------------------------------------------------------
# Entry point called by main.py
# ---------------------------------------------------------------------------

def run_gui() -> None:
    ReceiptVaultApp().run()