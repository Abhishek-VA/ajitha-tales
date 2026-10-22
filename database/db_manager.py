"""
database/db_manager.py
Complete SQLite database manager for Ajitha Tailors ERP.
Handles schema creation, migrations, connection pooling, and all CRUD queries.
"""

import sqlite3
import os
import sys
import json
import threading
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple


# Resolve database path relative to the executable or script
def get_db_path() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: place data next to the .exe
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "tailor_shop.db")


DB_PATH = get_db_path()

# Thread-local storage for connections
_thread_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection with row_factory set."""
    if not hasattr(_thread_local, "conn") or _thread_local.conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        _thread_local.conn = conn
    return _thread_local.conn


def close_connection():
    """Close the thread-local connection if open."""
    if hasattr(_thread_local, "conn") and _thread_local.conn:
        _thread_local.conn.close()
        _thread_local.conn = None


# ---------------------------------------------------------------------------
# Schema creation & migration
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS customers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    mobile           TEXT NOT NULL UNIQUE,
    alternate_mobile TEXT,
    address          TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      INTEGER NOT NULL,
    booking_date     DATE NOT NULL,
    collection_date  DATE NOT NULL,
    total_amount     REAL NOT NULL DEFAULT 0.0,
    advance_amount   REAL NOT NULL DEFAULT 0.0,
    balance_amount   REAL NOT NULL DEFAULT 0.0,
    payment_status   TEXT DEFAULT 'Unpaid',
    order_status     TEXT DEFAULT 'Pending',
    payment_mode     TEXT DEFAULT 'Cash',
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id             INTEGER NOT NULL,
    garment_type         TEXT NOT NULL,
    quantity             INTEGER DEFAULT 1,
    item_rate            REAL NOT NULL,
    measurements_json    TEXT NOT NULL DEFAULT '{}',
    design_instructions  TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_customers_mobile   ON customers(mobile);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status      ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_collection  ON orders(collection_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items(order_id);
"""

TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS update_orders_timestamp
    AFTER UPDATE ON orders
    FOR EACH ROW
BEGIN
    UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE order_id = OLD.order_id;
END;
"""


def initialize_database():
    """Create tables, indexes, and triggers if they do not exist."""
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(TRIGGER_SQL)
        # Set schema version
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (1)"
        )


# ---------------------------------------------------------------------------
# Customer queries
# ---------------------------------------------------------------------------

def upsert_customer(
    name: str,
    mobile: str,
    alternate_mobile: str = "",
    address: str = "",
) -> int:
    """Insert new customer or update existing record. Returns customer id."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            "SELECT id FROM customers WHERE mobile = ?", (mobile,)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                """UPDATE customers
                   SET name = ?, alternate_mobile = ?, address = ?
                   WHERE mobile = ?""",
                (name, alternate_mobile, address, mobile),
            )
            return row["id"]
        else:
            cur = conn.execute(
                """INSERT INTO customers (name, mobile, alternate_mobile, address)
                   VALUES (?, ?, ?, ?)""",
                (name, mobile, alternate_mobile, address),
            )
            return cur.lastrowid


def get_customer_by_mobile(mobile: str) -> Optional[Dict]:
    """Fetch a customer by mobile number."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM customers WHERE mobile = ?", (mobile,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_customer_by_id(customer_id: int) -> Optional[Dict]:
    """Fetch a customer by primary key."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def search_customers(query: str) -> List[Dict]:
    """Search customers by name or mobile."""
    conn = get_connection()
    q = f"%{query}%"
    cur = conn.execute(
        "SELECT * FROM customers WHERE name LIKE ? OR mobile LIKE ? LIMIT 20",
        (q, q),
    )
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Order queries
# ---------------------------------------------------------------------------

def create_order(
    customer_id: int,
    booking_date: str,
    collection_date: str,
    total_amount: float,
    advance_amount: float,
    balance_amount: float,
    payment_status: str,
    order_status: str,
    payment_mode: str,
    notes: str,
    items: List[Dict],
) -> int:
    """Create a new order with its items. Returns the new order_id."""
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """INSERT INTO orders
               (customer_id, booking_date, collection_date,
                total_amount, advance_amount, balance_amount,
                payment_status, order_status, payment_mode, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                customer_id, booking_date, collection_date,
                total_amount, advance_amount, balance_amount,
                payment_status, order_status, payment_mode, notes,
            ),
        )
        order_id = cur.lastrowid
        _insert_items(conn, order_id, items)
    return order_id


def update_order(
    order_id: int,
    customer_id: int,
    booking_date: str,
    collection_date: str,
    total_amount: float,
    advance_amount: float,
    balance_amount: float,
    payment_status: str,
    order_status: str,
    payment_mode: str,
    notes: str,
    items: List[Dict],
) -> bool:
    """Update existing order and replace all its items. Returns True on success."""
    conn = get_connection()
    with conn:
        conn.execute(
            """UPDATE orders
               SET customer_id=?, booking_date=?, collection_date=?,
                   total_amount=?, advance_amount=?, balance_amount=?,
                   payment_status=?, order_status=?, payment_mode=?, notes=?
               WHERE order_id=?""",
            (
                customer_id, booking_date, collection_date,
                total_amount, advance_amount, balance_amount,
                payment_status, order_status, payment_mode, notes,
                order_id,
            ),
        )
        # Delete old items (CASCADE handles this only on DELETE ORDER, so manual here)
        conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        _insert_items(conn, order_id, items)
    return True


def _insert_items(conn: sqlite3.Connection, order_id: int, items: List[Dict]):
    """Helper to bulk-insert order items."""
    for item in items:
        measurements = item.get("measurements", {})
        if isinstance(measurements, dict):
            measurements = json.dumps(measurements)
        conn.execute(
            """INSERT INTO order_items
               (order_id, garment_type, quantity, item_rate,
                measurements_json, design_instructions)
               VALUES (?,?,?,?,?,?)""",
            (
                order_id,
                item.get("garment_type", "Custom"),
                item.get("quantity", 1),
                item.get("item_rate", 0.0),
                measurements,
                item.get("design_instructions", ""),
            ),
        )


def update_order_status(order_id: int, order_status: str) -> bool:
    """Quick-update only the order_status field."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE orders SET order_status=? WHERE order_id=?",
            (order_status, order_id),
        )
    return True


def update_payment_status(order_id: int, payment_status: str) -> bool:
    """Quick-update only the payment_status field."""
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE orders SET payment_status=? WHERE order_id=?",
            (payment_status, order_id),
        )
    return True


def settle_order_payment(
    order_id: int,
    payment_amount: float,
    payment_mode: str = "Cash",
    mark_delivered: bool = False,
    notes_append: str = "",
) -> Dict:
    """
    Record final payment / balance settlement for an order.
    Adds payment_amount to advance_amount (total collected),
    recalculates balance_amount, sets payment_status ('Paid' or 'Partial'),
    optionally marks order_status as 'Delivered', and updates notes with a receipt log.
    Returns the updated order dict.
    """
    conn = get_connection()
    with conn:
        cur = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order = cur.fetchone()
        if not order:
            raise ValueError(f"Order #{order_id} not found.")

        total = float(order["total_amount"])
        current_advance = float(order["advance_amount"])
        new_advance = min(total, current_advance + float(payment_amount))
        new_balance = max(0.0, total - new_advance)

        if new_balance <= 0.01:
            new_pay_status = "Paid"
            new_balance = 0.0
        else:
            new_pay_status = "Partial"

        new_order_status = "Delivered" if mark_delivered else order["order_status"]

        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        pay_note = f"[Settlement: Paid ₹{payment_amount:,.2f} via {payment_mode} on {now_str}]"
        existing_notes = order["notes"] or ""
        combined_notes = (existing_notes + "\n" + pay_note).strip()
        if notes_append:
            combined_notes += f" ({notes_append})"

        conn.execute(
            """UPDATE orders
               SET advance_amount = ?, balance_amount = ?,
                   payment_status = ?, order_status = ?,
                   payment_mode = ?, notes = ?
               WHERE order_id = ?""",
            (
                new_advance, new_balance,
                new_pay_status, new_order_status,
                payment_mode, combined_notes,
                order_id,
            ),
        )

    return get_order_by_id(order_id)


def delete_order(order_id: int) -> bool:
    """Delete an order and all its items (CASCADE)."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
    return True


def get_order_by_id(order_id: int) -> Optional[Dict]:
    """Fetch a single order joined with customer details."""
    conn = get_connection()
    cur = conn.execute(
        """SELECT o.*, c.name AS customer_name, c.mobile, c.alternate_mobile, c.address
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           WHERE o.order_id = ?""",
        (order_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_order_items(order_id: int) -> List[Dict]:
    """Fetch all items for a given order."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ? ORDER BY item_id",
        (order_id,),
    )
    rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["measurements"] = json.loads(d.get("measurements_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            d["measurements"] = {}
        result.append(d)
    return result


def get_all_orders(
    search: str = "",
    order_status: str = "All",
    date_filter: str = "All",
) -> List[Dict]:
    """
    Fetch orders with optional filters:
      - search: matches customer name, mobile, or order_id
      - order_status: one of All/Pending/In Progress/Ready/Delivered/Cancelled
      - date_filter: All/Today/Tomorrow/This Week/Overdue
    """
    conn = get_connection()
    today = date.today().isoformat()

    base_sql = """
        SELECT o.order_id, c.name AS customer_name, c.mobile,
               o.booking_date, o.collection_date,
               o.total_amount, o.advance_amount, o.balance_amount,
               o.payment_status, o.order_status, o.payment_mode,
               o.notes, o.created_at, o.updated_at,
               GROUP_CONCAT(oi.garment_type, ', ') AS items_summary
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
    """

    conditions = []
    params: List[Any] = []

    # Search filter
    if search.strip():
        s = f"%{search.strip()}%"
        conditions.append(
            "(c.name LIKE ? OR c.mobile LIKE ? OR CAST(o.order_id AS TEXT) LIKE ?)"
        )
        params.extend([s, s, s])

    # Status filter
    if order_status != "All":
        conditions.append("o.order_status = ?")
        params.append(order_status)

    # Date filter
    if date_filter == "Due Today":
        conditions.append("o.collection_date = ?")
        params.append(today)
    elif date_filter == "Due Tomorrow":
        conditions.append("o.collection_date = DATE(?, '+1 day')")
        params.append(today)
    elif date_filter == "Due This Week":
        conditions.append(
            "o.collection_date BETWEEN ? AND DATE(?, '+7 day')"
        )
        params.extend([today, today])
    elif date_filter == "Overdue":
        conditions.append(
            "o.collection_date < ? AND o.order_status NOT IN ('Delivered','Cancelled')"
        )
        params.append(today)

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " GROUP BY o.order_id ORDER BY o.order_id DESC"

    cur = conn.execute(base_sql, params)
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Summary / Analytics queries
# ---------------------------------------------------------------------------

def get_daily_summary(target_date: Optional[str] = None) -> Dict:
    """Return totals for a given date (defaults to today)."""
    conn = get_connection()
    d = target_date or date.today().isoformat()
    cur = conn.execute(
        """SELECT
               COUNT(*) AS total_orders,
               SUM(total_amount)   AS revenue,
               SUM(advance_amount) AS collected,
               SUM(balance_amount) AS pending_amount
           FROM orders
           WHERE booking_date = ?""",
        (d,),
    )
    row = cur.fetchone()
    return dict(row) if row else {}


def get_dashboard_stats() -> Dict:
    """Return aggregate stats shown in the header/stats row."""
    conn = get_connection()
    today = date.today().isoformat()
    stats = {}

    cur = conn.execute(
        "SELECT COUNT(*) AS cnt FROM orders WHERE order_status NOT IN ('Delivered','Cancelled')"
    )
    stats["active_orders"] = cur.fetchone()["cnt"]

    cur = conn.execute(
        "SELECT COUNT(*) AS cnt FROM orders WHERE collection_date = ? AND order_status != 'Delivered'",
        (today,),
    )
    stats["due_today"] = cur.fetchone()["cnt"]

    cur = conn.execute(
        "SELECT COUNT(*) AS cnt FROM orders WHERE collection_date < ? AND order_status NOT IN ('Delivered','Cancelled')",
        (today,),
    )
    stats["overdue"] = cur.fetchone()["cnt"]

    cur = conn.execute(
        "SELECT SUM(balance_amount) AS bal FROM orders WHERE order_status NOT IN ('Delivered','Cancelled')"
    )
    row = cur.fetchone()
    stats["total_pending_balance"] = row["bal"] or 0.0

    return stats


def get_orders_for_export(start_date: str, end_date: str) -> List[Dict]:
    """Fetch all orders in a date range for CSV/Excel export."""
    conn = get_connection()
    cur = conn.execute(
        """SELECT o.order_id, c.name, c.mobile,
                  o.booking_date, o.collection_date,
                  o.total_amount, o.advance_amount, o.balance_amount,
                  o.payment_status, o.order_status, o.payment_mode, o.notes
           FROM orders o
           JOIN customers c ON o.customer_id = c.id
           WHERE o.booking_date BETWEEN ? AND ?
           ORDER BY o.booking_date""",
        (start_date, end_date),
    )
    return [dict(r) for r in cur.fetchall()]
