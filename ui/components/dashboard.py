"""
ui/components/dashboard.py
Right-pane: Stats cards, search/filter toolbar, interactive orders table,
right-click context menu, export controls, and one-click status transitions.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import date, datetime
from typing import Optional, Callable, Dict, List
import threading

from ui.styles import COLORS, FONTS, ORDER_STATUSES, STATUS_COLORS, PAY_COLORS
from ui.styles import configure_ttk_treeview_style
from database import db_manager


class DashboardPanel(ctk.CTkFrame):
    """
    Full-featured order dashboard with real-time search, filtering,
    stats cards, treeview table, and context menu actions.
    """

    def __init__(
        self,
        parent,
        on_edit_order: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color=COLORS["bg_darkest"], **kwargs)
        self.on_edit_order = on_edit_order

        self._all_orders: List[Dict] = []
        self._search_after_id = None   # For debounced search

        # Build TTK style once
        self._style = ttk.Style()
        configure_ttk_treeview_style(self._style)

        self._build_ui()
        self.refresh()   # Initial load

    # ─────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C, F = COLORS, FONTS

        # ── Stats cards row ──────────────────────────────────────────────────
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=14, pady=(12, 6))

        self._stat_labels = {}
        stats_def = [
            ("active_orders",        "Active Orders",   "📋", C["primary"]),
            ("due_today",            "Due Today",        "⏰", C["gold"]),
            ("overdue",              "Overdue",          "🚨", C["status_cancelled"]),
            ("total_pending_balance","Pending Balance",  "💰", C["status_ready"]),
        ]
        for i, (key, label, icon, color) in enumerate(stats_def):
            card = ctk.CTkFrame(stats_frame, fg_color=C["bg_card"], corner_radius=12)
            card.grid(row=0, column=i, padx=5, pady=4, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=icon, font=("Segoe UI", 20),
                         text_color=color).pack(pady=(10, 0))
            val_lbl = ctk.CTkLabel(card, text="—", font=F["heading_lg"],
                                   text_color=color)
            val_lbl.pack()
            ctk.CTkLabel(card, text=label, font=F["label"],
                         text_color=C["text_muted"]).pack(pady=(0, 10))
            self._stat_labels[key] = val_lbl

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        toolbar.pack(fill="x", padx=14, pady=(4, 6))

        # Search bar
        search_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        search_row.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(search_row, text="🔍", font=("Segoe UI", 14),
                     text_color=C["text_muted"]).pack(side="left", padx=(0, 6))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self._search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self._search_var,
            height=36,
            fg_color=C["bg_input"],
            border_color=C["border"],
            text_color=C["text_primary"],
            font=F["body_md"],
            placeholder_text="Search by name, mobile, or order ID…",
        )
        self._search_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            search_row, text="✕ Clear", width=80, height=36,
            fg_color=C["btn_neutral"], hover_color=C["border_light"],
            text_color=C["text_muted"], font=F["body_xs"],
            command=lambda: self._search_var.set(""),
            corner_radius=6,
        ).pack(side="left", padx=(6, 0))

        # Filter rows
        filters_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        filters_row.pack(fill="x", padx=12, pady=(0, 10))

        # Date filter
        ctk.CTkLabel(filters_row, text="Date:", font=F["label_bold"],
                     text_color=C["text_muted"]).pack(side="left")
        self._date_filter_var = tk.StringVar(value="All")
        date_opts = ["All", "Due Today", "Due Tomorrow", "Due This Week", "Overdue"]
        self._date_filter_menu = ctk.CTkOptionMenu(
            filters_row,
            variable=self._date_filter_var,
            values=date_opts,
            fg_color=C["bg_input"],
            button_color=C["border_light"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_xs"],
            height=30,
            width=140,
            command=lambda _: self._apply_filters(),
        )
        self._date_filter_menu.pack(side="left", padx=(4, 14))

        # Status filter
        ctk.CTkLabel(filters_row, text="Status:", font=F["label_bold"],
                     text_color=C["text_muted"]).pack(side="left")
        self._status_filter_var = tk.StringVar(value="All")
        status_opts = ["All"] + ORDER_STATUSES
        self._status_filter_menu = ctk.CTkOptionMenu(
            filters_row,
            variable=self._status_filter_var,
            values=status_opts,
            fg_color=C["bg_input"],
            button_color=C["border_light"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_xs"],
            height=30,
            width=130,
            command=lambda _: self._apply_filters(),
        )
        self._status_filter_menu.pack(side="left", padx=(4, 14))

        # Quick status buttons
        for status, color_pair in STATUS_COLORS.items():
            fg_c = color_pair[0]
            btn = ctk.CTkButton(
                filters_row,
                text=status,
                fg_color="transparent",
                hover_color=color_pair[1],
                text_color=fg_c,
                border_color=fg_c,
                border_width=1,
                font=F["body_xs"],
                height=28,
                width=90,
                command=lambda s=status: self._quick_status_filter(s),
                corner_radius=14,
            )
            btn.pack(side="left", padx=3)

        ctk.CTkButton(
            filters_row,
            text="↺ Refresh",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_xs"],
            height=28,
            width=80,
            command=self.refresh,
            corner_radius=6,
        ).pack(side="right", padx=3)

        # Export buttons
        ctk.CTkButton(
            filters_row,
            text="📊 Export Excel",
            fg_color=C["btn_success"],
            hover_color="#1D8348",
            text_color="#FFFFFF",
            font=F["body_xs"],
            height=28,
            width=110,
            command=self._export_excel,
            corner_radius=6,
        ).pack(side="right", padx=3)

        ctk.CTkButton(
            filters_row,
            text="📄 Export CSV",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_xs"],
            height=28,
            width=95,
            command=self._export_csv,
            corner_radius=6,
        ).pack(side="right", padx=3)

        # ── Orders table ─────────────────────────────────────────────────────
        table_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Column header
        col_header = ctk.CTkFrame(table_frame, fg_color=C["bg_medium"], corner_radius=0, height=36)
        col_header.pack(fill="x")
        self._result_count_label = ctk.CTkLabel(
            col_header,
            text="Loading…",
            font=F["body_sm"],
            text_color=C["text_muted"],
        )
        self._result_count_label.pack(side="left", padx=14, pady=8)

        # Quick actions on selected order
        ctk.CTkButton(
            col_header,
            text="💰 Settle Balance",
            fg_color=C["btn_success"],
            hover_color="#1E8449",
            text_color="#FFFFFF",
            font=F["body_xs"],
            height=26,
            command=self._ctx_settle,
            corner_radius=4,
        ).pack(side="right", padx=6, pady=4)

        ctk.CTkButton(
            col_header,
            text="✏️ Edit",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_xs"],
            height=26,
            width=50,
            command=self._ctx_edit,
            corner_radius=4,
        ).pack(side="right", padx=2, pady=4)

        ctk.CTkButton(
            col_header,
            text="🖨️ Bill",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_xs"],
            height=26,
            width=50,
            command=self._ctx_print,
            corner_radius=4,
        ).pack(side="right", padx=2, pady=4)

        # Treeview
        tree_container = tk.Frame(table_frame, bg=C["bg_card"])
        tree_container.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        columns = (
            "order_id", "customer", "mobile",
            "items", "delivery", "total", "advance", "balance",
            "pay_status", "order_status",
        )
        self._tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        col_config = [
            ("order_id",    "#",          55,  "center"),
            ("customer",    "Customer",   160, "w"),
            ("mobile",      "Mobile",     110, "center"),
            ("items",       "Items",      140, "w"),
            ("delivery",    "Delivery",   95,  "center"),
            ("total",       "Total (₹)",  90,  "e"),
            ("advance",     "Advance (₹)",90,  "e"),
            ("balance",     "Balance (₹)",90,  "e"),
            ("pay_status",  "Payment",    80,  "center"),
            ("order_status","Status",     90,  "center"),
        ]
        for col_id, heading, width, anchor in col_config:
            self._tree.heading(col_id, text=heading, anchor=anchor)
            self._tree.column(col_id, width=width, minwidth=50, anchor=anchor)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical",
                             command=self._tree.yview, style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal",
                             command=self._tree.xview, style="Dark.Horizontal.TScrollbar")
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        # Bind events
        self._tree.bind("<Double-1>",  self._on_double_click)
        self._tree.bind("<Button-3>",  self._on_right_click)
        self._tree.bind("<Return>",    self._on_double_click)

        # ── Context menu ─────────────────────────────────────────────────────
        self._ctx_menu = tk.Menu(self._tree, tearoff=0,
                                 bg=C["bg_medium"], fg=C["text_primary"],
                                 activebackground=C["primary"],
                                 activeforeground="#FFFFFF",
                                 font=("Segoe UI", 10))
        self._ctx_menu.add_command(label="💰  Settle Payment / Collect Balance", command=self._ctx_settle)
        self._ctx_menu.add_command(label="✏️  Edit Order",         command=self._ctx_edit)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="📋  Mark: Pending",      command=lambda: self._ctx_status("Pending"))
        self._ctx_menu.add_command(label="🔵  Mark: In Progress",  command=lambda: self._ctx_status("In Progress"))
        self._ctx_menu.add_command(label="✅  Mark: Ready",        command=lambda: self._ctx_status("Ready"))
        self._ctx_menu.add_command(label="🎁  Mark: Delivered",    command=lambda: self._ctx_status("Delivered"))
        self._ctx_menu.add_command(label="❌  Mark: Cancelled",    command=lambda: self._ctx_status("Cancelled"))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🖨️  Print / View Bill",  command=self._ctx_print)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🗑️  Delete Order",       command=self._ctx_delete)

    # ─────────────────────────────────────────────────────────────────────────
    # Data loading & display
    # ─────────────────────────────────────────────────────────────────────────

    def refresh(self):
        """Reload stats and table data from DB."""
        self._refresh_stats()
        self._apply_filters()

    def _refresh_stats(self):
        try:
            stats = db_manager.get_dashboard_stats()
            self._stat_labels["active_orders"].configure(
                text=str(stats.get("active_orders", 0))
            )
            self._stat_labels["due_today"].configure(
                text=str(stats.get("due_today", 0))
            )
            self._stat_labels["overdue"].configure(
                text=str(stats.get("overdue", 0))
            )
            bal = stats.get("total_pending_balance", 0) or 0
            self._stat_labels["total_pending_balance"].configure(
                text=f"₹{bal:,.0f}"
            )
        except Exception:
            pass

    def _apply_filters(self, *_):
        search     = self._search_var.get().strip()
        date_f     = self._date_filter_var.get()
        status_f   = self._status_filter_var.get()

        try:
            orders = db_manager.get_all_orders(
                search=search,
                order_status=status_f,
                date_filter=date_f,
            )
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            orders = []

        self._all_orders = orders
        self._populate_table(orders)

    def _populate_table(self, orders: List[Dict]):
        """Clear and re-populate the treeview."""
        # Detach all
        self._tree.delete(*self._tree.get_children())

        today = date.today().isoformat()

        for order in orders:
            oid        = order.get("order_id", "")
            customer   = order.get("customer_name", "")
            mobile     = order.get("mobile", "")
            items_sum  = order.get("items_summary", "") or "—"
            delivery   = order.get("collection_date", "")
            total      = f"{float(order.get('total_amount', 0)):,.0f}"
            advance    = f"{float(order.get('advance_amount', 0)):,.0f}"
            balance    = f"{float(order.get('balance_amount', 0)):,.0f}"
            pay_status = order.get("payment_status", "")
            ord_status = order.get("order_status", "")

            # Tag for row colour
            tag = ord_status.lower().replace(" ", "_")
            if delivery and delivery < today and ord_status not in ("Delivered", "Cancelled"):
                tag = "overdue"

            self._tree.insert(
                "", "end",
                iid=str(oid),
                values=(oid, customer, mobile, items_sum, delivery,
                        total, advance, balance, pay_status, ord_status),
                tags=(tag,),
            )

        # Configure row tag colours
        C = COLORS
        self._tree.tag_configure("pending",     foreground=C["status_pending"])
        self._tree.tag_configure("in_progress", foreground=C["status_inprogress"])
        self._tree.tag_configure("ready",       foreground=C["status_ready"])
        self._tree.tag_configure("delivered",   foreground=C["status_delivered"])
        self._tree.tag_configure("cancelled",   foreground=C["status_cancelled"])
        self._tree.tag_configure("overdue",     foreground=C["status_cancelled"], background="#1A0505")

        n = len(orders)
        self._result_count_label.configure(
            text=f"Showing {n} order{'s' if n != 1 else ''}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Search / filter helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_search_changed(self, *_):
        """Debounce search to avoid hammering DB on every keystroke."""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self._apply_filters)

    def _quick_status_filter(self, status: str):
        self._status_filter_var.set(status)
        self._apply_filters()

    # ─────────────────────────────────────────────────────────────────────────
    # Event handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _selected_order_id(self) -> Optional[int]:
        sel = self._tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _on_double_click(self, event=None):
        oid = self._selected_order_id()
        if oid and self.on_edit_order:
            self.on_edit_order(oid)

    def _on_right_click(self, event):
        # Select the row under cursor
        iid = self._tree.identify_row(event.y)
        if iid:
            self._tree.selection_set(iid)
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_edit(self):
        oid = self._selected_order_id()
        if oid and self.on_edit_order:
            self.on_edit_order(oid)

    def _ctx_settle(self):
        oid = self._selected_order_id()
        if not oid:
            messagebox.showinfo("Select Order", "Please select an order from the table to settle payment.", parent=self.winfo_toplevel())
            return
        order = db_manager.get_order_by_id(oid)
        if not order:
            return

        from ui.components.payment_modal import PaymentModal

        def on_settled(updated_order):
            self.refresh()

        PaymentModal(self.winfo_toplevel(), order=order, on_settled=on_settled)

    def _ctx_status(self, status: str):
        oid = self._selected_order_id()
        if not oid:
            return
        if messagebox.askyesno(
            "Confirm Status Change",
            f"Mark Order #{oid} as '{status}'?",
            parent=self.winfo_toplevel(),
        ):
            db_manager.update_order_status(oid, status)
            self.refresh()

    def _ctx_print(self):
        oid = self._selected_order_id()
        if not oid:
            return
        try:
            from services.pdf_service import generate_invoice, open_pdf
            order = db_manager.get_order_by_id(oid)
            items = db_manager.get_order_items(oid)
            customer = db_manager.get_customer_by_id(order["customer_id"])
            pdf_path = generate_invoice(order, items, customer)
            open_pdf(pdf_path)
        except Exception as e:
            messagebox.showerror("PDF Error", str(e), parent=self.winfo_toplevel())

    def _ctx_delete(self):
        oid = self._selected_order_id()
        if not oid:
            return
        if messagebox.askyesno(
            "Confirm Delete",
            f"⚠️  Permanently delete Order #{oid} and all its items?\n\nThis cannot be undone.",
            icon="warning",
            parent=self.winfo_toplevel(),
        ):
            db_manager.delete_order(oid)
            self.refresh()

    # ─────────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────────

    def _export_csv(self):
        from services.export_service import export_csv, open_file
        today = date.today().isoformat()
        try:
            orders = db_manager.get_orders_for_export("2000-01-01", today)
            path   = export_csv(orders, "2000-01-01", today)
            if messagebox.askyesno("Export Complete",
                                   f"CSV saved:\n{path}\n\nOpen file?",
                                   parent=self.winfo_toplevel()):
                open_file(path)
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self.winfo_toplevel())

    def _export_excel(self):
        from services.export_service import export_excel, open_file
        today = date.today().isoformat()
        try:
            orders = db_manager.get_orders_for_export("2000-01-01", today)
            path   = export_excel(orders, "2000-01-01", today)
            if messagebox.askyesno("Export Complete",
                                   f"Excel saved:\n{path}\n\nOpen file?",
                                   parent=self.winfo_toplevel()):
                open_file(path)
        except Exception as e:
            messagebox.showerror("Export Error", str(e), parent=self.winfo_toplevel())
