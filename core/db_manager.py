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