import os
import sqlite3

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

'''
This file should contain only SQL logic, Table creation (the init_db method), and raw data retrieval methods. It should not import Flask or CustomTkinter.
Web app and Desktop app will call the exact same functions to get data, ensuring consistency across both interfaces.
'''

class ReceiptVault:
    def init_db(self):
        os.makedirs("data", exist_ok=True)
        # check_same_thread=False: Flask's dev server (and any future GUI event
        # callbacks) may call into this connection from a different thread than
        # the one that created it. SQLite's own internal locking makes this safe
        # for a single local process like this one; we're not sharing the
        # connection across separate processes, just separate threads of the
        # same app.
        self.conn = sqlite3.connect("data/bills_data.db", check_same_thread=False)
        # Row objects support both index- and name-based access (row[0] or
        # row["name"]) and convert cleanly to dicts via dict(row) - this is
        # what all the operation methods below rely on.
        self.conn.row_factory = sqlite3.Row
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

    # -----------------------------------------------------------------------
    # Vendors
    # -----------------------------------------------------------------------

    def get_all_vendors(self):
        """Return every vendor as a list of dicts: {id, name}, sorted by name."""
        rows = self.conn.execute(
            "SELECT id, name FROM vendors ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_vendor_by_id(self, vendor_id: int):
        """Return a single vendor dict, or None if vendor_id doesn't exist."""
        row = self.conn.execute(
            "SELECT id, name FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_or_create_vendor(self, name: str) -> int:
        """
        Look up a vendor by name (case-insensitive, whitespace-trimmed),
        creating it if it doesn't exist yet. Returns the vendor's id.

        This is the method both the OCR import flow and any manual "type a
        vendor name" form should call - it's the only way a bill's vendor_id
        gets resolved from free-text input, so the same vendor name never
        accidentally creates two separate rows due to a stray space or
        differing capitalization.
        """
        name = name.strip()
        if not name:
            raise ValueError("Vendor name cannot be empty.")

        row = self.conn.execute(
            "SELECT id FROM vendors WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            return row["id"]

        cur = self.conn.execute(
            "INSERT INTO vendors (name) VALUES (?)", (name,)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_vendor(self, vendor_id: int, new_name: str) -> bool:
        """Rename a vendor. Returns True if a row was actually updated."""
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Vendor name cannot be empty.")

        cur = self.conn.execute(
            "UPDATE vendors SET name = ? WHERE id = ?", (new_name, vendor_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_vendor(self, vendor_id: int) -> bool:
        """
        Delete a vendor. Bills referencing it have vendor_id set to NULL
        rather than being deleted themselves (see the bills table's
        ON DELETE SET NULL foreign key) - removing a vendor should never
        silently destroy someone's receipt history.
        Returns True if a row was actually deleted.
        """
        cur = self.conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Categories
    # -----------------------------------------------------------------------

    def get_all_categories(self):
        """Return every category as a list of dicts: {id, category_name}."""
        rows = self.conn.execute(
            "SELECT id, category_name FROM categories ORDER BY category_name"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_category_by_id(self, category_id: int):
        """Return a single category dict, or None if category_id doesn't exist."""
        row = self.conn.execute(
            "SELECT id, category_name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_or_create_category(self, category_name: str) -> int:
        """
        Look up a category by name (case-insensitive, whitespace-trimmed),
        creating it if it doesn't exist yet. Returns the category's id.
        Mirrors get_or_create_vendor for the same reason: free-text category
        input (e.g. typed into a tag field) should never create accidental
        duplicates that differ only in case or stray whitespace.
        """
        category_name = category_name.strip()
        if not category_name:
            raise ValueError("Category name cannot be empty.")

        row = self.conn.execute(
            "SELECT id FROM categories WHERE category_name = ? COLLATE NOCASE",
            (category_name,),
        ).fetchone()
        if row:
            return row["id"]

        cur = self.conn.execute(
            "INSERT INTO categories (category_name) VALUES (?)", (category_name,)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_category(self, category_id: int, new_name: str) -> bool:
        """Rename a category. Returns True if a row was actually updated."""
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Category name cannot be empty.")

        cur = self.conn.execute(
            "UPDATE categories SET category_name = ? WHERE id = ?",
            (new_name, category_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_category(self, category_id: int) -> bool:
        """
        Delete a category. Any bill_categories rows linking bills to this
        category are removed automatically (ON DELETE CASCADE on the
        junction table) - the bills themselves are never touched, they just
        lose this one category tag.
        Returns True if a row was actually deleted.
        """
        cur = self.conn.execute(
            "DELETE FROM categories WHERE id = ?", (category_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Bills
    # -----------------------------------------------------------------------
    # Bills are returned as dicts shaped like:
    #   {id, date, vendor_id, vendor, price, created_at, updated_at,
    #    categories: [{id, category_name}, ...]}
    # "vendor" is the resolved vendor name (or None if vendor_id is NULL);
    # "categories" is always a list, even if empty.

    def _get_category_ids_for_bill(self, bill_id: int) -> list[int]:
        """Internal helper: category ids currently linked to a bill."""
        rows = self.conn.execute(
            "SELECT category_id FROM bill_categories WHERE bill_id = ?",
            (bill_id,),
        ).fetchall()
        return [r["category_id"] for r in rows]

    def _attach_categories(self, bills: list[dict]) -> list[dict]:
        """
        Internal helper: given a list of bill dicts (each with an 'id'),
        attach a 'categories' list of {id, category_name} dicts to each one.
        Uses a single query for all bills rather than one query per bill, so
        a dashboard listing many bills doesn't trigger an N+1 query pattern.
        """
        if not bills:
            return bills

        bill_ids = [b["id"] for b in bills]
        placeholders = ",".join("?" * len(bill_ids))
        rows = self.conn.execute(
            f"""
            SELECT bc.bill_id, c.id, c.category_name
            FROM   bill_categories bc
            JOIN   categories c ON c.id = bc.category_id
            WHERE  bc.bill_id IN ({placeholders})
            ORDER BY c.category_name
            """,
            bill_ids,
        ).fetchall()

        by_bill: dict[int, list[dict]] = {bid: [] for bid in bill_ids}
        for r in rows:
            by_bill[r["bill_id"]].append({"id": r["id"], "category_name": r["category_name"]})

        for b in bills:
            b["categories"] = by_bill.get(b["id"], [])
        return bills

    def create_bill(self, date: str, vendor_id: int | None, price: float,
                     category_ids: list[int] | None = None) -> int:
        """
        Insert a new bill. `date` should be 'YYYY-MM-DD'. `vendor_id` may be
        None (a receipt with no vendor recorded yet). `category_ids`, if
        given, immediately tags the new bill with those categories via the
        junction table. Returns the new bill's id.
        """
        cur = self.conn.execute(
            "INSERT INTO bills (date, vendor_id, price) VALUES (?, ?, ?)",
            (date, vendor_id, price),
        )
        bill_id = cur.lastrowid
        self.conn.commit()

        if category_ids:
            self.set_bill_categories(bill_id, category_ids)

        return bill_id

    def get_all_bills(self) -> list[dict]:
        """
        Return every bill, newest date first, each with its resolved vendor
        name and full category list attached. This replaces the inline SQL
        that used to live directly in the /api/bills Flask route.
        """
        rows = self.conn.execute("""
            SELECT b.id, b.date, b.vendor_id, v.name AS vendor, b.price,
                   b.created_at, b.updated_at
            FROM   bills b
            LEFT JOIN vendors v ON b.vendor_id = v.id
            ORDER BY b.date DESC, b.id DESC
        """).fetchall()
        bills = [dict(r) for r in rows]
        return self._attach_categories(bills)

    def get_bill_by_id(self, bill_id: int) -> dict | None:
        """Return a single bill dict (with vendor + categories), or None."""
        row = self.conn.execute("""
            SELECT b.id, b.date, b.vendor_id, v.name AS vendor, b.price,
                   b.created_at, b.updated_at
            FROM   bills b
            LEFT JOIN vendors v ON b.vendor_id = v.id
            WHERE  b.id = ?
        """, (bill_id,)).fetchone()
        if not row:
            return None
        bill = dict(row)
        self._attach_categories([bill])
        return bill

    def get_bills_filtered(self, date_from: str | None = None, date_to: str | None = None,
                            vendor_id: int | None = None, category_id: int | None = None) -> list[dict]:
        """
        Return bills matching the given filters (all optional - any
        combination may be supplied, or none for "all bills"). Powers the
        "All Receipts" browse/filter/search view.

        date_from / date_to: inclusive 'YYYY-MM-DD' bounds.
        vendor_id: only bills from this vendor.
        category_id: only bills tagged with this category.
        """
        clauses = []
        params: list = []

        if date_from:
            clauses.append("b.date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("b.date <= ?")
            params.append(date_to)
        if vendor_id is not None:
            clauses.append("b.vendor_id = ?")
            params.append(vendor_id)

        # category_id requires a join against the junction table; handled
        # separately from the simpler equality clauses above.
        category_join = ""
        if category_id is not None:
            category_join = "JOIN bill_categories fc ON fc.bill_id = b.id AND fc.category_id = ?"
            params.insert(0, category_id)  # joins are bound before WHERE params

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(f"""
            SELECT b.id, b.date, b.vendor_id, v.name AS vendor, b.price,
                   b.created_at, b.updated_at
            FROM   bills b
            LEFT JOIN vendors v ON b.vendor_id = v.id
            {category_join}
            {where_sql}
            ORDER BY b.date DESC, b.id DESC
        """, params).fetchall()
        bills = [dict(r) for r in rows]
        return self._attach_categories(bills)

    def update_bill(self, bill_id: int, date: str | None = None,
                     vendor_id: int | None = -1, price: float | None = None,
                     category_ids: list[int] | None = None) -> bool:
        """
        Partially update a bill - only fields you pass are changed.

        Because None is a meaningful value for vendor_id (clear the vendor),
        it can't also mean "don't touch this field" the way it does for the
        other parameters. So vendor_id uses -1 as its "leave unchanged"
        sentinel instead: pass vendor_id=None explicitly to clear it, omit
        it entirely to leave it as-is, or pass an actual id to change it.

        category_ids, if given, REPLACES the bill's full category list
        (use set_bill_categories directly if you only have it, or
        get_bill_by_id().categories first if you need to add/remove rather
        than replace).

        Returns True if the bill existed and was updated.
        """
        existing = self.get_bill_by_id(bill_id)
        if existing is None:
            return False

        fields = []
        params: list = []

        if date is not None:
            fields.append("date = ?")
            params.append(date)
        if vendor_id != -1:
            fields.append("vendor_id = ?")
            params.append(vendor_id)
        if price is not None:
            fields.append("price = ?")
            params.append(price)

        if fields:
            params.append(bill_id)
            self.conn.execute(
                f"UPDATE bills SET {', '.join(fields)} WHERE id = ?", params
            )
            self.conn.commit()

        if category_ids is not None:
            self.set_bill_categories(bill_id, category_ids)

        return True

    def delete_bill(self, bill_id: int) -> bool:
        """
        Delete a bill. Its bill_categories rows are removed automatically
        (ON DELETE CASCADE). Returns True if a row was actually deleted.
        """
        cur = self.conn.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # -----------------------------------------------------------------------
    # Bill <-> Category junction
    # -----------------------------------------------------------------------

    def set_bill_categories(self, bill_id: int, category_ids: list[int]) -> None:
        """
        Replace a bill's full set of categories with exactly the given list
        (removes any not in the list, adds any new ones, leaves unchanged
        ones alone). This is the natural shape for a save/edit form, which
        submits the complete desired tag set rather than incremental
        add/remove instructions.
        """
        self.conn.execute(
            "DELETE FROM bill_categories WHERE bill_id = ?", (bill_id,)
        )
        if category_ids:
            # de-duplicate while preserving order, in case the caller passed
            # the same category twice (e.g. a multi-select widget glitch)
            seen = []
            for cid in category_ids:
                if cid not in seen:
                    seen.append(cid)
            self.conn.executemany(
                "INSERT INTO bill_categories (bill_id, category_id) VALUES (?, ?)",
                [(bill_id, cid) for cid in seen],
            )
        self.conn.commit()

    # -----------------------------------------------------------------------
    # Dashboard / summary
    # -----------------------------------------------------------------------
    # Supports the Dashboard sidebar section ("Summary of spending").

    def get_total_spend(self, date_from: str | None = None, date_to: str | None = None) -> float:
        """
        Total of all bill prices, optionally restricted to an inclusive
        'YYYY-MM-DD' date range. Returns 0.0 if there are no matching bills.
        """
        clauses = []
        params: list = []
        if date_from:
            clauses.append("date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("date <= ?")
            params.append(date_to)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        row = self.conn.execute(
            f"SELECT COALESCE(SUM(price), 0) AS total FROM bills {where_sql}",
            params,
        ).fetchone()
        return row["total"]

    def get_spend_by_category(self, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
        """
        Total spend per category, highest first, as a list of dicts:
        {category_id, category_name, total}. A bill tagged with multiple
        categories contributes its full price to each of them (this is a
        tagging breakdown, not a strict partition of total spend - use
        get_total_spend for the actual grand total).
        Bills with no categories at all are not included here.
        """
        clauses = []
        params: list = []
        if date_from:
            clauses.append("b.date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("b.date <= ?")
            params.append(date_to)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = self.conn.execute(f"""
            SELECT c.id AS category_id, c.category_name, SUM(b.price) AS total
            FROM   bill_categories bc
            JOIN   bills b      ON b.id = bc.bill_id
            JOIN   categories c ON c.id = bc.category_id
            {where_sql}
            GROUP BY c.id, c.category_name
            ORDER BY total DESC
        """, params).fetchall()
        return [dict(r) for r in rows]

    def get_spend_by_vendor(self, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
        """
        Total spend per vendor, highest first, as a list of dicts:
        {vendor_id, vendor, total}. Bills with no vendor set are excluded.
        """
        clauses = ["b.vendor_id IS NOT NULL"]
        params: list = []
        if date_from:
            clauses.append("b.date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("b.date <= ?")
            params.append(date_to)
        where_sql = f"WHERE {' AND '.join(clauses)}"

        rows = self.conn.execute(f"""
            SELECT v.id AS vendor_id, v.name AS vendor, SUM(b.price) AS total
            FROM   bills b
            JOIN   vendors v ON v.id = b.vendor_id
            {where_sql}
            GROUP BY v.id, v.name
            ORDER BY total DESC
        """, params).fetchall()
        return [dict(r) for r in rows]

    def get_recent_bills(self, limit: int = 10) -> list[dict]:
        """Convenience wrapper for a dashboard's 'recent activity' list."""
        rows = self.conn.execute("""
            SELECT b.id, b.date, b.vendor_id, v.name AS vendor, b.price,
                   b.created_at, b.updated_at
            FROM   bills b
            LEFT JOIN vendors v ON b.vendor_id = v.id
            ORDER BY b.created_at DESC, b.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        bills = [dict(r) for r in rows]
        return self._attach_categories(bills)