"""
ui/components/ledger_panel.py
Comprehensive Daily Cashflow Ledger, Day-Book, and Expense Management for Ajitha Tailors.
Enables the shop owner to track Cash in Drawer, UPI receipts, expenses, and net daily cashflow.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import date, datetime, timedelta
from typing import Optional, Callable, Dict, List

from ui.styles import COLORS, FONTS
from database import db_manager
from services import export_service
from ui.components.calendar_picker import CalendarPickerModal


EXPENSE_CATEGORIES = [
    "Tailor Wages / Karigar",
    "Threads & Needles",
    "Lining & Canvas Cloth",
    "Embroidery / Aari Charges",
    "Ironing & Pressing",
    "Machine Maintenance & Oil",
    "Shop Rent / Electricity",
    "Tea & Refreshments",
    "Packaging Bags & Hangers",
    "Miscellaneous",
]


class ExpenseModal(ctk.CTkToplevel):
    """
    Modal dialog for recording a shop expense or cash outflow.
    """

    def __init__(self, parent, initial_date: str, on_saved: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.initial_date = initial_date
        self.on_saved = on_saved

        self.title("Record Shop Expense / Payout")
        self.configure(fg_color=COLORS["bg_card"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_window(parent)

        self.bind("<Escape>", lambda _: self.destroy())

    def _build_ui(self):
        C, F = COLORS, FONTS

        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="  💸  Record Shop Expense / Payout",
            font=F["heading_sm"],
            text_color=C["primary"],
        ).pack(side="left", padx=14, pady=8)

        ctk.CTkButton(
            hdr, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=C["primary_dark"],
            text_color=C["text_secondary"], font=F["body_md"],
            command=self.destroy,
        ).pack(side="right", padx=8, pady=8)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Date
        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(row1, text="Expense Date (YYYY-MM-DD)", font=F["label_bold"], text_color=C["text_secondary"]).pack(anchor="w")
        date_box = ctk.CTkFrame(row1, fg_color="transparent")
        date_box.pack(fill="x", pady=(4, 0))

        self.date_var = tk.StringVar(value=self.initial_date)
        self.date_entry = ctk.CTkEntry(
            date_box, textvariable=self.date_var,
            font=F["body_md"], fg_color=C["bg_input"], border_color=C["border"], height=32,
        )
        self.date_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            date_box, text="📅", width=36, height=32,
            fg_color=C["bg_input"], hover_color=C["primary"],
            text_color=C["text_primary"], font=F["body_md"],
            command=self._open_date_picker,
        ).pack(side="right")

        # 2. Category
        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(row2, text="Expense Category", font=F["label_bold"], text_color=C["text_secondary"]).pack(anchor="w")
        self.cat_var = tk.StringVar(value=EXPENSE_CATEGORIES[0])
        self.cat_menu = ctk.CTkOptionMenu(
            row2, variable=self.cat_var, values=EXPENSE_CATEGORIES,
            font=F["body_md"], fg_color=C["bg_input"], button_color=C["primary"],
            button_hover_color=C["primary_dark"], height=32,
        )
        self.cat_menu.pack(fill="x", pady=(4, 0))

        # 3. Amount & Payment Mode
        row3 = ctk.CTkFrame(body, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 10))
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=1)

        amt_box = ctk.CTkFrame(row3, fg_color="transparent")
        amt_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(amt_box, text="Amount (₹) *", font=F["label_bold"], text_color=C["text_secondary"]).pack(anchor="w")
        self.amt_var = tk.StringVar(value="")
        self.amt_entry = ctk.CTkEntry(
            amt_box, textvariable=self.amt_var, placeholder_text="e.g. 250",
            font=F["heading_md"], fg_color=C["bg_input"], border_color=C["border"], height=34,
            text_color=C["primary_light"],
        )
        self.amt_entry.pack(fill="x", pady=(4, 0))
        self.amt_entry.focus_set()

        mode_box = ctk.CTkFrame(row3, fg_color="transparent")
        mode_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(mode_box, text="Paid Via *", font=F["label_bold"], text_color=C["text_secondary"]).pack(anchor="w")
        self.mode_var = tk.StringVar(value="Cash")
        self.mode_menu = ctk.CTkOptionMenu(
            mode_box, variable=self.mode_var,
            values=["Cash", "UPI", "Card", "Bank Transfer"],
            font=F["body_md"], fg_color=C["bg_input"], button_color=C["bg_medium"],
            height=34,
        )
        self.mode_menu.pack(fill="x", pady=(4, 0))

        # Drawer impact hint
        self.hint_label = ctk.CTkLabel(
            body,
            text="💡 Cash expenses directly deduct from today's Physical Drawer Cash.",
            font=F["body_xs"],
            text_color=C["status_pending"],
            anchor="w",
        )
        self.hint_label.pack(fill="x", pady=(0, 10))

        # 4. Notes / Narration
        row4 = ctk.CTkFrame(body, fg_color="transparent")
        row4.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(row4, text="Narration / Item Description", font=F["label_bold"], text_color=C["text_secondary"]).pack(anchor="w")
        self.notes_var = tk.StringVar(value="")
        self.notes_entry = ctk.CTkEntry(
            row4, textvariable=self.notes_var,
            placeholder_text="e.g. Overlock machine oil, 2 boxes needle #14, Raju tailor advance",
            font=F["body_md"], fg_color=C["bg_input"], border_color=C["border"], height=32,
        )
        self.notes_entry.pack(fill="x", pady=(4, 0))

        # Actions
        btn_bar = ctk.CTkFrame(body, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(6, 0))

        ctk.CTkButton(
            btn_bar, text="Cancel", width=90, height=34,
            fg_color=C["bg_input"], hover_color=C["border_light"],
            text_color=C["text_secondary"], font=F["body_md"],
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_bar, text="✓ Save Expense", height=34,
            fg_color=C["primary"], hover_color=C["primary_dark"],
            text_color="#FFFFFF", font=F["heading_sm"],
            command=self._save_expense,
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _open_date_picker(self):
        CalendarPickerModal(
            self,
            title="Select Expense Date",
            initial_date=self.date_var.get().strip(),
            callback=lambda d: self.date_var.set(d),
            is_delivery=False,
        )

    def _save_expense(self):
        d_val = self.date_var.get().strip()
        cat_val = self.cat_var.get().strip()
        amt_str = self.amt_var.get().strip().replace(",", "")
        mode_val = self.mode_var.get().strip()
        notes_val = self.notes_var.get().strip()

        if not d_val:
            messagebox.showwarning("Missing Date", "Please enter a valid expense date.", parent=self)
            return

        try:
            amt = float(amt_str)
            if amt <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Invalid Amount", "Please enter a valid expense amount greater than 0.", parent=self)
            self.amt_entry.focus_set()
            return

        try:
            db_manager.add_shop_expense(
                expense_date=d_val,
                category=cat_val,
                amount=amt,
                payment_mode=mode_val,
                notes=notes_val,
            )
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not record expense: {e}", parent=self)

    def _center_window(self, parent):
        self.update_idletasks()
        w, h = 440, 390
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


class LedgerPanel(ctk.CTkFrame):
    """
    Daily Cashflow, Day-Book & Expense Ledger Component for Ajitha Tailors.
    """

    def __init__(self, parent, on_view_order: Optional[Callable[[int], None]] = None):
        super().__init__(parent, fg_color=COLORS["bg_darkest"], corner_radius=0)
        self.on_view_order = on_view_order
        self._current_date = date.today().isoformat()
        self._ledger_data: Dict = {}

        self._build_header_toolbar()
        self._build_kpi_cards()
        self._build_tabs_and_tables()

        self.refresh()

    # ─────────────────────────────────────────────────────────────────────────
    # Header Toolbar
    # ─────────────────────────────────────────────────────────────────────────

    def _build_header_toolbar(self):
        C, F = COLORS, FONTS

        bar = ctk.CTkFrame(self, fg_color=C["bg_sidebar"], corner_radius=0, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Title
        title_box = ctk.CTkFrame(bar, fg_color="transparent")
        title_box.pack(side="left", padx=(14, 10), pady=6)

        ctk.CTkLabel(
            title_box,
            text="📖  Daily Cashflow & Day-Book Ledger",
            font=F["heading_md"],
            text_color=C["text_primary"],
        ).pack(side="left")

        # Date controls
        date_bar = ctk.CTkFrame(bar, fg_color="transparent")
        date_bar.pack(side="left", padx=10, pady=6)

        ctk.CTkButton(
            date_bar, text="◀ Prev", width=54, height=30,
            fg_color=C["bg_input"], hover_color=C["border_light"],
            text_color=C["text_secondary"], font=F["body_xs"],
            command=self._prev_day,
        ).pack(side="left", padx=2)

        self.date_var = tk.StringVar(value=self._current_date)
        self.date_entry = ctk.CTkEntry(
            date_bar, textvariable=self.date_var, width=105, height=30,
            font=F["body_md"], fg_color=C["bg_input"], border_color=C["border"],
            justify="center",
        )
        self.date_entry.pack(side="left", padx=2)
        self.date_entry.bind("<Return>", lambda _: self._on_date_entered())

        ctk.CTkButton(
            date_bar, text="📅", width=34, height=30,
            fg_color=C["bg_input"], hover_color=C["primary"],
            text_color=C["text_primary"], font=F["body_sm"],
            command=self._open_calendar,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            date_bar, text="Next ▶", width=54, height=30,
            fg_color=C["bg_input"], hover_color=C["border_light"],
            text_color=C["text_secondary"], font=F["body_xs"],
            command=self._next_day,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            date_bar, text="Today", width=54, height=30,
            fg_color=C["bg_card"], hover_color=C["primary"],
            text_color=C["gold"], font=F["body_xs"],
            command=self._today,
        ).pack(side="left", padx=(6, 2))

        ctk.CTkButton(
            date_bar, text="↺", width=32, height=30,
            fg_color=C["bg_input"], hover_color=C["border_light"],
            text_color=C["text_secondary"], font=F["body_md"],
            command=self.refresh,
        ).pack(side="left", padx=2)

        # Right Action Buttons
        right_box = ctk.CTkFrame(bar, fg_color="transparent")
        right_box.pack(side="right", padx=(10, 14), pady=6)

        ctk.CTkButton(
            right_box,
            text="📊 Export Day-Book (.xlsx)",
            font=F["body_xs"],
            fg_color=C["bg_input"],
            hover_color=C["border_light"],
            text_color=C["text_primary"],
            height=30,
            command=self._export_excel,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            right_box,
            text="➕ Add Shop Expense",
            font=F["heading_sm"],
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            height=30,
            command=self._open_expense_modal,
        ).pack(side="right", padx=4)

    # ─────────────────────────────────────────────────────────────────────────
    # Top KPI Cards (Cash in Drawer, UPI, Expenses, Net Cashflow)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_kpi_cards(self):
        C, F = COLORS, FONTS

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=14, pady=10)
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1, uniform="kpi")

        # 1. Cash in Drawer (Physical Cash)
        c1 = ctk.CTkFrame(cards_frame, fg_color=C["bg_card"], border_color=C["status_delivered"], border_width=1, corner_radius=8)
        c1.grid(row=0, column=0, sticky="nsew", padx=4)
        ctk.CTkLabel(c1, text="💵 CASH IN DRAWER (IN-HAND)", font=F["label_bold"], text_color=C["status_delivered"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.lbl_drawer = ctk.CTkLabel(c1, text="₹ 0.00", font=F["heading_lg"], text_color="#FFFFFF")
        self.lbl_drawer.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_drawer_sub = ctk.CTkLabel(c1, text="In: ₹0  |  Out: ₹0", font=F["body_xs"], text_color=C["text_muted"])
        self.lbl_drawer_sub.pack(anchor="w", padx=12, pady=(0, 10))

        # 2. UPI / Online Receipts
        c2 = ctk.CTkFrame(cards_frame, fg_color=C["bg_card"], border_color=C["status_inprogress"], border_width=1, corner_radius=8)
        c2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c2, text="📱 UPI & ONLINE RECEIPTS", font=F["label_bold"], text_color=C["status_inprogress"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.lbl_upi = ctk.CTkLabel(c2, text="₹ 0.00", font=F["heading_lg"], text_color="#FFFFFF")
        self.lbl_upi.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_upi_sub = ctk.CTkLabel(c2, text="GPay, PhonePe, Card", font=F["body_xs"], text_color=C["text_muted"])
        self.lbl_upi_sub.pack(anchor="w", padx=12, pady=(0, 10))

        # 3. Shop Expenses
        c3 = ctk.CTkFrame(cards_frame, fg_color=C["bg_card"], border_color=C["primary"], border_width=1, corner_radius=8)
        c3.grid(row=0, column=2, sticky="nsew", padx=4)
        ctk.CTkLabel(c3, text="💸 TOTAL SHOP EXPENSES", font=F["label_bold"], text_color=C["primary_light"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.lbl_exp = ctk.CTkLabel(c3, text="₹ 0.00", font=F["heading_lg"], text_color="#FFFFFF")
        self.lbl_exp.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_exp_sub = ctk.CTkLabel(c3, text="0 expense items recorded", font=F["body_xs"], text_color=C["text_muted"])
        self.lbl_exp_sub.pack(anchor="w", padx=12, pady=(0, 10))

        # 4. Net Daily Cashflow
        c4 = ctk.CTkFrame(cards_frame, fg_color=C["bg_card"], border_color=C["gold"], border_width=1, corner_radius=8)
        c4.grid(row=0, column=3, sticky="nsew", padx=4)
        ctk.CTkLabel(c4, text="📈 NET DAILY CASHFLOW", font=F["label_bold"], text_color=C["gold"]).pack(anchor="w", padx=12, pady=(10, 2))
        self.lbl_net = ctk.CTkLabel(c4, text="₹ 0.00", font=F["heading_lg"], text_color="#FFFFFF")
        self.lbl_net.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_net_sub = ctk.CTkLabel(c4, text="Total Inflow − Total Outflow", font=F["body_xs"], text_color=C["text_muted"])
        self.lbl_net_sub.pack(anchor="w", padx=12, pady=(0, 10))

    # ─────────────────────────────────────────────────────────────────────────
    # Tabs & Tables
    # ─────────────────────────────────────────────────────────────────────────

    def _build_tabs_and_tables(self):
        C, F = COLORS, FONTS

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # View Selector Toolbar
        tab_bar = ctk.CTkFrame(container, fg_color="transparent", height=36)
        tab_bar.pack(fill="x", pady=(0, 6))

        self.tab_seg = ctk.CTkSegmentedButton(
            tab_bar,
            values=["📋 All Day-Book Activity", "📥 Customer Receipts", "💸 Shop Expenses & Payouts"],
            command=self._on_tab_changed,
            fg_color=C["bg_input"],
            selected_color=C["primary"],
            selected_hover_color=C["primary_dark"],
            unselected_color=C["bg_input"],
            unselected_hover_color=C["border_light"],
            text_color="#FFFFFF",
            font=F["body_xs"],
            height=30,
        )
        self.tab_seg.set("📋 All Day-Book Activity")
        self.tab_seg.pack(side="left")

        # Context action for shop expenses (Delete)
        self.del_exp_btn = ctk.CTkButton(
            tab_bar,
            text="🗑️ Delete Selected Expense",
            font=F["body_xs"],
            fg_color=C["bg_card"],
            hover_color=C["btn_danger"],
            text_color=C["text_secondary"],
            height=30,
            command=self._delete_selected_expense,
        )

        # Content frame for tables
        self.table_deck = ctk.CTkFrame(container, fg_color=C["bg_card"], corner_radius=8)
        self.table_deck.pack(fill="both", expand=True)

        # 1. Day-Book Treeview (All Inflows + Outflows unified)
        self._build_daybook_tree()

        # 2. Inflows Treeview
        self._build_inflows_tree()

        # 3. Expenses Treeview
        self._build_expenses_tree()

        # Show Day-Book table by default
        self._show_active_table("📋 All Day-Book Activity")

    def _build_daybook_tree(self):
        C, F = COLORS, FONTS

        self.frame_daybook = ctk.CTkFrame(self.table_deck, fg_color="transparent")

        cols = ("time", "nature", "ref", "party", "mode", "inflow", "outflow", "notes")
        self.tree_daybook = ttk.Treeview(
            self.frame_daybook,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        self.tree_daybook.heading("time",    text="Time",            anchor="center")
        self.tree_daybook.heading("nature",  text="Transaction Type", anchor="w")
        self.tree_daybook.heading("ref",     text="Reference #",     anchor="center")
        self.tree_daybook.heading("party",   text="Customer / Narration", anchor="w")
        self.tree_daybook.heading("mode",    text="Mode",            anchor="center")
        self.tree_daybook.heading("inflow",  text="Money IN (+)",    anchor="e")
        self.tree_daybook.heading("outflow", text="Money OUT (-)",   anchor="e")
        self.tree_daybook.heading("notes",   text="Notes / Details", anchor="w")

        self.tree_daybook.column("time",    width=75,  minwidth=65,  anchor="center")
        self.tree_daybook.column("nature",  width=140, minwidth=120, anchor="w")
        self.tree_daybook.column("ref",     width=80,  minwidth=70,  anchor="center")
        self.tree_daybook.column("party",   width=210, minwidth=160, anchor="w")
        self.tree_daybook.column("mode",    width=80,  minwidth=70,  anchor="center")
        self.tree_daybook.column("inflow",  width=120, minwidth=100, anchor="e")
        self.tree_daybook.column("outflow", width=120, minwidth=100, anchor="e")
        self.tree_daybook.column("notes",   width=220, minwidth=140, anchor="w")

        # Color tags
        self.tree_daybook.tag_configure("inflow_tag", foreground="#2ECC71", font=("Segoe UI", 10, "bold"))
        self.tree_daybook.tag_configure("outflow_tag", foreground="#FF6B8A", font=("Segoe UI", 10, "bold"))
        self.tree_daybook.tag_configure("row_even", background=C["bg_card"])
        self.tree_daybook.tag_configure("row_odd",  background=C["table_row_alt"])

        sb_y = ttk.Scrollbar(self.frame_daybook, orient="vertical", command=self.tree_daybook.yview, style="Dark.Vertical.TScrollbar")
        self.tree_daybook.configure(yscrollcommand=sb_y.set)

        self.tree_daybook.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        sb_y.pack(side="right", fill="y", pady=1)

        self.tree_daybook.bind("<Double-1>", self._on_daybook_double_click)

    def _build_inflows_tree(self):
        C = COLORS
        self.frame_inflows = ctk.CTkFrame(self.table_deck, fg_color="transparent")

        cols = ("time", "order_id", "customer", "mobile", "type", "mode", "amount", "notes")
        self.tree_inflows = ttk.Treeview(
            self.frame_inflows,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        self.tree_inflows.heading("time",     text="Time",          anchor="center")
        self.tree_inflows.heading("order_id", text="Order #",       anchor="center")
        self.tree_inflows.heading("customer", text="Customer Name", anchor="w")
        self.tree_inflows.heading("mobile",   text="Mobile",        anchor="center")
        self.tree_inflows.heading("type",     text="Payment Type",  anchor="w")
        self.tree_inflows.heading("mode",     text="Mode",          anchor="center")
        self.tree_inflows.heading("amount",   text="Amount (₹)",    anchor="e")
        self.tree_inflows.heading("notes",    text="Notes",         anchor="w")

        self.tree_inflows.column("time",     width=75,  anchor="center")
        self.tree_inflows.column("order_id", width=80,  anchor="center")
        self.tree_inflows.column("customer", width=180, anchor="w")
        self.tree_inflows.column("mobile",   width=110, anchor="center")
        self.tree_inflows.column("type",     width=140, anchor="w")
        self.tree_inflows.column("mode",     width=80,  anchor="center")
        self.tree_inflows.column("amount",   width=120, anchor="e")
        self.tree_inflows.column("notes",    width=240, anchor="w")

        self.tree_inflows.tag_configure("inflow_green", foreground="#2ECC71", font=("Segoe UI", 10, "bold"))
        self.tree_inflows.tag_configure("row_even", background=C["bg_card"])
        self.tree_inflows.tag_configure("row_odd",  background=C["table_row_alt"])

        sb_y = ttk.Scrollbar(self.frame_inflows, orient="vertical", command=self.tree_inflows.yview, style="Dark.Vertical.TScrollbar")
        self.tree_inflows.configure(yscrollcommand=sb_y.set)

        self.tree_inflows.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        sb_y.pack(side="right", fill="y", pady=1)

        self.tree_inflows.bind("<Double-1>", self._on_inflow_double_click)

    def _build_expenses_tree(self):
        C = COLORS
        self.frame_expenses = ctk.CTkFrame(self.table_deck, fg_color="transparent")

        cols = ("id", "time", "category", "mode", "amount", "notes")
        self.tree_expenses = ttk.Treeview(
            self.frame_expenses,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        self.tree_expenses.heading("id",       text="ID",          anchor="center")
        self.tree_expenses.heading("time",     text="Time",        anchor="center")
        self.tree_expenses.heading("category", text="Category",    anchor="w")
        self.tree_expenses.heading("mode",     text="Paid Via",    anchor="center")
        self.tree_expenses.heading("amount",   text="Amount (₹)",  anchor="e")
        self.tree_expenses.heading("notes",    text="Narration / Description", anchor="w")

        self.tree_expenses.column("id",       width=65,  anchor="center")
        self.tree_expenses.column("time",     width=75,  anchor="center")
        self.tree_expenses.column("category", width=200, anchor="w")
        self.tree_expenses.column("mode",     width=90,  anchor="center")
        self.tree_expenses.column("amount",   width=120, anchor="e")
        self.tree_expenses.column("notes",    width=320, anchor="w")

        self.tree_expenses.tag_configure("exp_red", foreground="#FF6B8A", font=("Segoe UI", 10, "bold"))
        self.tree_expenses.tag_configure("row_even", background=C["bg_card"])
        self.tree_expenses.tag_configure("row_odd",  background=C["table_row_alt"])

        sb_y = ttk.Scrollbar(self.frame_expenses, orient="vertical", command=self.tree_expenses.yview, style="Dark.Vertical.TScrollbar")
        self.tree_expenses.configure(yscrollcommand=sb_y.set)

        self.tree_expenses.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        sb_y.pack(side="right", fill="y", pady=1)

    def _show_active_table(self, tab_name: str):
        self.frame_daybook.pack_forget()
        self.frame_inflows.pack_forget()
        self.frame_expenses.pack_forget()
        self.del_exp_btn.pack_forget()

        if tab_name == "📋 All Day-Book Activity":
            self.frame_daybook.pack(fill="both", expand=True)
        elif tab_name == "📥 Customer Receipts":
            self.frame_inflows.pack(fill="both", expand=True)
        else:  # "💸 Shop Expenses & Payouts"
            self.frame_expenses.pack(fill="both", expand=True)
            self.del_exp_btn.pack(side="right")

    def _on_tab_changed(self, tab_name: str):
        self._show_active_table(tab_name)

    # ─────────────────────────────────────────────────────────────────────────
    # Data Loading & Rendering
    # ─────────────────────────────────────────────────────────────────────────

    def refresh(self):
        """Fetch daily ledger data for current date and refresh UI."""
        self._current_date = self.date_var.get().strip() or date.today().isoformat()
        try:
            self._ledger_data = db_manager.get_daily_ledger(self._current_date)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch daily ledger: {e}")
            return

        self._render_kpis()
        self._render_daybook()
        self._render_inflows()
        self._render_expenses()

    def _render_kpis(self):
        d = self._ledger_data

        # 1. Drawer Cash
        cash_hand = float(d.get("cash_in_hand", 0.0))
        cash_in = float(d.get("cash_in", 0.0))
        cash_exp = float(d.get("cash_expenses", 0.0))
        self.lbl_drawer.configure(text=f"₹ {cash_hand:,.2f}")
        self.lbl_drawer_sub.configure(text=f"In: +₹{cash_in:,.2f}  |  Out: -₹{cash_exp:,.2f}")

        # 2. UPI
        upi_in = float(d.get("upi_in", 0.0))
        card_in = float(d.get("card_in", 0.0))
        self.lbl_upi.configure(text=f"₹ {upi_in + card_in:,.2f}")
        self.lbl_upi_sub.configure(text=f"UPI: ₹{upi_in:,.2f}  |  Card: ₹{card_in:,.2f}")

        # 3. Total Expenses
        tot_exp = float(d.get("total_expenses", 0.0))
        exp_count = len(d.get("expenses", []))
        self.lbl_exp.configure(text=f"₹ {tot_exp:,.2f}")
        self.lbl_exp_sub.configure(text=f"{exp_count} expense item(s) logged")

        # 4. Net Cashflow
        net = float(d.get("net_cashflow", 0.0))
        tot_in = float(d.get("total_inflow", 0.0))
        self.lbl_net.configure(text=f"₹ {net:,.2f}")
        self.lbl_net_sub.configure(text=f"Revenue: ₹{tot_in:,.2f}  |  Costs: ₹{tot_exp:,.2f}")

    def _render_daybook(self):
        self.tree_daybook.delete(*self.tree_daybook.get_children())

        # Interleave inflows and expenses sorted chronologically
        timeline = []
        for tx in self._ledger_data.get("inflows", []):
            timeline.append({
                "time": tx.get("created_at", "")[11:16] if tx.get("created_at") else "--:--",
                "nature": "📥 " + tx.get("transaction_type", "").replace("_", " ").title(),
                "ref": f"#{tx.get('order_id', '')}",
                "party": tx.get("customer_name") or "Direct Order",
                "mode": tx.get("payment_mode", "Cash"),
                "inflow": f"+ ₹{float(tx.get('amount', 0)):,.2f}",
                "outflow": "-",
                "notes": tx.get("notes") or "",
                "is_inflow": True,
                "order_id": tx.get("order_id"),
                "sort_key": tx.get("created_at", ""),
            })

        for exp in self._ledger_data.get("expenses", []):
            timeline.append({
                "time": exp.get("created_at", "")[11:16] if exp.get("created_at") else "--:--",
                "nature": "💸 " + exp.get("category", "Expense"),
                "ref": f"EXP-{exp.get('id', '')}",
                "party": exp.get("category", ""),
                "mode": exp.get("payment_mode", "Cash"),
                "inflow": "-",
                "outflow": f"- ₹{float(exp.get('amount', 0)):,.2f}",
                "notes": exp.get("notes") or "",
                "is_inflow": False,
                "order_id": None,
                "sort_key": exp.get("created_at", ""),
            })

        timeline.sort(key=lambda x: x["sort_key"], reverse=True)

        for idx, item in enumerate(timeline):
            base_tag = "row_even" if idx % 2 == 0 else "row_odd"
            color_tag = "inflow_tag" if item["is_inflow"] else "outflow_tag"
            self.tree_daybook.insert(
                "",
                "end",
                values=(
                    item["time"],
                    item["nature"],
                    item["ref"],
                    item["party"],
                    item["mode"],
                    item["inflow"],
                    item["outflow"],
                    item["notes"],
                ),
                tags=(base_tag, color_tag),
            )

    def _render_inflows(self):
        self.tree_inflows.delete(*self.tree_inflows.get_children())
        for idx, tx in enumerate(self._ledger_data.get("inflows", [])):
            base_tag = "row_even" if idx % 2 == 0 else "row_odd"
            t_str = tx.get("created_at", "")[11:16] if tx.get("created_at") else "--:--"
            self.tree_inflows.insert(
                "",
                "end",
                iid=str(tx.get("id")),
                values=(
                    t_str,
                    f"#{tx.get('order_id', '')}",
                    tx.get("customer_name") or "Direct Order",
                    tx.get("mobile") or "-",
                    tx.get("transaction_type", "").replace("_", " ").title(),
                    tx.get("payment_mode", ""),
                    f"₹ {float(tx.get('amount', 0)):,.2f}",
                    tx.get("notes") or "",
                ),
                tags=(base_tag, "inflow_green"),
            )

    def _render_expenses(self):
        self.tree_expenses.delete(*self.tree_expenses.get_children())
        for idx, exp in enumerate(self._ledger_data.get("expenses", [])):
            base_tag = "row_even" if idx % 2 == 0 else "row_odd"
            t_str = exp.get("created_at", "")[11:16] if exp.get("created_at") else "--:--"
            self.tree_expenses.insert(
                "",
                "end",
                iid=str(exp.get("id")),
                values=(
                    f"EXP-{exp.get('id', '')}",
                    t_str,
                    exp.get("category", ""),
                    exp.get("payment_mode", ""),
                    f"₹ {float(exp.get('amount', 0)):,.2f}",
                    exp.get("notes") or "",
                ),
                tags=(base_tag, "exp_red"),
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Actions & Navigation
    # ─────────────────────────────────────────────────────────────────────────

    def _prev_day(self):
        try:
            cur = datetime.strptime(self._current_date, "%Y-%m-%d").date()
            prev_d = cur - timedelta(days=1)
            self.date_var.set(prev_d.isoformat())
            self.refresh()
        except Exception:
            pass

    def _next_day(self):
        try:
            cur = datetime.strptime(self._current_date, "%Y-%m-%d").date()
            next_d = cur + timedelta(days=1)
            self.date_var.set(next_d.isoformat())
            self.refresh()
        except Exception:
            pass

    def _today(self):
        self.date_var.set(date.today().isoformat())
        self.refresh()

    def _on_date_entered(self):
        self.refresh()

    def _open_calendar(self):
        CalendarPickerModal(
            self.winfo_toplevel(),
            title="Select Ledger Date",
            initial_date=self.date_var.get().strip(),
            callback=lambda d: (self.date_var.set(d), self.refresh()),
            is_delivery=False,
        )

    def _open_expense_modal(self):
        ExpenseModal(
            self.winfo_toplevel(),
            initial_date=self._current_date,
            on_saved=self.refresh,
        )

    def _delete_selected_expense(self):
        sel = self.tree_expenses.selection()
        if not sel:
            messagebox.showinfo("Select Expense", "Please click on an expense row to select it.", parent=self)
            return

        exp_id_str = sel[0]
        try:
            exp_id = int(exp_id_str)
        except ValueError:
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete Expense #{exp_id}?",
            parent=self,
        )
        if confirm:
            db_manager.delete_shop_expense(exp_id)
            self.refresh()

    def _export_excel(self):
        try:
            path = export_service.export_daily_ledger_excel(self._ledger_data)
            open_now = messagebox.askyesno(
                "Export Successful",
                f"Daily Cashflow Ledger exported to:\n\n{path}\n\nWould you like to open it now?",
                parent=self,
            )
            if open_now:
                export_service.open_file(path)
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export ledger: {e}", parent=self)

    def _on_daybook_double_click(self, event):
        sel = self.tree_daybook.selection()
        if not sel:
            return
        vals = self.tree_daybook.item(sel[0], "values")
        if not vals:
            return
        ref = vals[2]
        if ref.startswith("#") and self.on_view_order:
            try:
                order_id = int(ref.replace("#", ""))
                self.on_view_order(order_id)
            except ValueError:
                pass

    def _on_inflow_double_click(self, event):
        sel = self.tree_inflows.selection()
        if not sel:
            return
        vals = self.tree_inflows.item(sel[0], "values")
        if not vals:
            return
        ref = vals[1]
        if ref.startswith("#") and self.on_view_order:
            try:
                order_id = int(ref.replace("#", ""))
                self.on_view_order(order_id)
            except ValueError:
                pass
