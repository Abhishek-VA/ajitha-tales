"""
ui/components/order_entry.py
Left-pane: Customer info + multi-item cart + billing summary.
Supports both Create and Edit modes with full form pre-fill.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import date, datetime
from typing import Optional, Callable, Dict, List, Any
import json

from ui.styles import COLORS, FONTS, GARMENT_TYPES, PAYMENT_STATUSES, PAYMENT_MODES, ORDER_STATUSES
from ui.components.measurement_modal import MeasurementModal
from database import db_manager


class OrderEntryPanel(ctk.CTkScrollableFrame):
    """
    Complete order entry / editing panel.
    Emits: on_order_saved(order_id: int) callback when an order is created/updated.
    """

    def __init__(self, parent, on_order_saved: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_dark"],
            scrollbar_button_color=COLORS["primary"],
            scrollbar_button_hover_color=COLORS["primary_dark"],
            **kwargs,
        )
        self.on_order_saved = on_order_saved

        # State
        self._edit_order_id: Optional[int] = None   # None = create mode
        self._cart_items: List[Dict] = []            # In-memory cart
        self._customer_id: Optional[int] = None

        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C, F = COLORS, FONTS
        pad = {"padx": 14, "pady": 6}

        # ── Panel title ──────────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=10)
        title_frame.pack(fill="x", **pad)

        self._mode_label = ctk.CTkLabel(
            title_frame,
            text="  ✂️  New Order",
            font=F["heading_lg"],
            text_color=C["primary"],
        )
        self._mode_label.pack(side="left", padx=14, pady=12)

        self._order_badge = ctk.CTkLabel(
            title_frame,
            text="",
            font=F["body_sm"],
            text_color=C["gold"],
        )
        self._order_badge.pack(side="right", padx=14)

        # ── Customer section ─────────────────────────────────────────────────
        self._section("👤  Customer Information")

        cust_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        cust_frame.pack(fill="x", **pad)

        # Mobile + auto-lookup
        mob_row = ctk.CTkFrame(cust_frame, fg_color="transparent")
        mob_row.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(mob_row, text="Mobile *", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(side="left")
        ctk.CTkLabel(mob_row, text="(auto-fills on 10 digits)",
                     font=F["label"], text_color=C["text_muted"]).pack(side="left", padx=6)

        self._mobile_var = tk.StringVar()
        self._mobile_var.trace_add("write", self._on_mobile_changed)
        self._mobile_entry = ctk.CTkEntry(
            cust_frame, textvariable=self._mobile_var,
            height=38, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="10-digit mobile number",
        )
        self._mobile_entry.pack(fill="x", padx=12, pady=(0, 8))

        # Name
        self._labeled_entry(cust_frame, "Customer Name *", "_name_entry", "Full name")
        # Alt mobile
        self._labeled_entry(cust_frame, "Alternate Mobile", "_alt_mobile_entry", "Optional")
        # Address
        ctk.CTkLabel(cust_frame, text="Address", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=12, pady=(4, 2))
        self._address_text = ctk.CTkTextbox(
            cust_frame, height=52, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_sm"], corner_radius=6,
        )
        self._address_text.pack(fill="x", padx=12, pady=(0, 12))

        # ── Dates ────────────────────────────────────────────────────────────
        self._section("📅  Dates")

        dates_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        dates_frame.pack(fill="x", **pad)
        dates_frame.grid_columnconfigure((0, 1), weight=1)

        today_str = date.today().strftime("%Y-%m-%d")

        self._booking_entry = self._date_field(dates_frame, "Booking Date *", 0, today_str)
        self._collection_entry = self._date_field(dates_frame, "Delivery Date *", 1, "")

        # ── Items cart ───────────────────────────────────────────────────────
        self._section("🧵  Order Items")

        item_form = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        item_form.pack(fill="x", **pad)

        # Garment type
        ctk.CTkLabel(item_form, text="Garment Type", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=12, pady=(10, 2))
        self._garment_var = tk.StringVar(value=GARMENT_TYPES[0])
        self._garment_menu = ctk.CTkOptionMenu(
            item_form,
            variable=self._garment_var,
            values=GARMENT_TYPES,
            fg_color=C["bg_input"],
            button_color=C["primary"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_md"],
            height=36,
        )
        self._garment_menu.pack(fill="x", padx=12, pady=(0, 8))

        # Qty + Rate
        qty_rate_row = ctk.CTkFrame(item_form, fg_color="transparent")
        qty_rate_row.pack(fill="x", padx=12, pady=(0, 8))
        qty_rate_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(qty_rate_row, text="Qty", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(qty_rate_row, text="Rate (₹) *", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self._qty_var = tk.StringVar(value="1")
        self._qty_entry = ctk.CTkEntry(
            qty_rate_row, textvariable=self._qty_var,
            height=36, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"], width=80,
        )
        self._qty_entry.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._rate_var = tk.StringVar()
        self._rate_var.trace_add("write", self._recalculate)
        self._rate_entry = ctk.CTkEntry(
            qty_rate_row, textvariable=self._rate_var,
            height=36, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="0.00",
        )
        self._rate_entry.grid(row=1, column=1, sticky="ew", pady=(2, 0), padx=(10, 0))

        # Measurement button
        self._current_measurements: Dict = {}
        self._current_design: str = ""
        self._meas_btn = ctk.CTkButton(
            item_form,
            text="  📐  Add Measurements & Design Notes",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_sm"],
            height=34,
            command=self._open_measurement_modal,
            corner_radius=6,
        )
        self._meas_btn.pack(fill="x", padx=12, pady=(0, 4))

        self._meas_indicator = ctk.CTkLabel(
            item_form, text="", font=F["label"],
            text_color=C["status_delivered"],
        )
        self._meas_indicator.pack(anchor="w", padx=12, pady=(0, 4))

        # Add item button
        ctk.CTkButton(
            item_form,
            text="  ➕  Add Item to Order",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["heading_sm"],
            height=40,
            command=self._add_item_to_cart,
            corner_radius=8,
        ).pack(fill="x", padx=12, pady=(4, 12))

        # ── Cart display ─────────────────────────────────────────────────────
        self._section("🛒  Cart Summary")
        self._cart_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        self._cart_frame.pack(fill="x", **pad)
        self._refresh_cart_display()

        # ── Payment section ──────────────────────────────────────────────────
        self._section("💳  Payment & Status")

        pay_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        pay_frame.pack(fill="x", **pad)

        # Advance
        ctk.CTkLabel(pay_frame, text="Advance Received (₹)", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=12, pady=(10, 2))
        self._advance_var = tk.StringVar(value="0")
        self._advance_var.trace_add("write", self._recalculate)
        self._advance_entry = ctk.CTkEntry(
            pay_frame, textvariable=self._advance_var,
            height=38, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="0.00",
        )
        self._advance_entry.pack(fill="x", padx=12, pady=(0, 8))

        # Payment mode + status
        row2 = ctk.CTkFrame(pay_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 8))
        row2.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(row2, text="Payment Mode", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row2, text="Order Status", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self._pay_mode_var = tk.StringVar(value="Cash")
        ctk.CTkOptionMenu(
            row2, variable=self._pay_mode_var,
            values=PAYMENT_MODES,
            fg_color=C["bg_input"], button_color=C["border_light"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_sm"], height=34,
        ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._order_status_var = tk.StringVar(value="Pending")
        ctk.CTkOptionMenu(
            row2, variable=self._order_status_var,
            values=ORDER_STATUSES,
            fg_color=C["bg_input"], button_color=C["border_light"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_sm"], height=34,
        ).grid(row=1, column=1, sticky="ew", pady=(2, 0), padx=(10, 0))

        # Notes
        ctk.CTkLabel(pay_frame, text="Order Notes", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=12, pady=(8, 2))
        self._notes_text = ctk.CTkTextbox(
            pay_frame, height=52,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_sm"], corner_radius=6,
        )
        self._notes_text.pack(fill="x", padx=12, pady=(0, 12))

        # ── Billing summary ──────────────────────────────────────────────────
        self._section("💰  Billing Summary")
        summary_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=10)
        summary_frame.pack(fill="x", **pad)

        self._total_label = self._billing_row(summary_frame, "Total Amount", "₹ 0.00", C["text_primary"])
        self._advance_disp = self._billing_row(summary_frame, "Advance Paid", "₹ 0.00", C["status_ready"])
        self._balance_label = self._billing_row(summary_frame, "Balance Due", "₹ 0.00", C["primary"], big=True)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(10, 16))

        self._save_btn = ctk.CTkButton(
            btn_frame,
            text="  💾  Save & Print Invoice",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["heading_md"],
            height=48,
            command=self._on_save,
            corner_radius=10,
        )
        self._save_btn.pack(fill="x", pady=(0, 6))

        self._cancel_btn = ctk.CTkButton(
            btn_frame,
            text="  ✕  Cancel / Reset",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_md"],
            height=38,
            command=self.reset_form,
            corner_radius=8,
        )
        self._cancel_btn.pack(fill="x")

    # ─────────────────────────────────────────────────────────────────────────
    # Helper UI builders
    # ─────────────────────────────────────────────────────────────────────────

    def _section(self, title: str):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(frame, text=title, font=FONTS["heading_sm"],
                     text_color=COLORS["gold"]).pack(side="left")
        ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6
        )

    def _labeled_entry(self, parent, label: str, attr: str, placeholder: str) -> ctk.CTkEntry:
        C, F = COLORS, FONTS
        ctk.CTkLabel(parent, text=label, font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=12, pady=(6, 2))
        entry = ctk.CTkEntry(
            parent, height=36,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text=placeholder,
        )
        entry.pack(fill="x", padx=12, pady=(0, 6))
        setattr(self, attr, entry)
        return entry

    def _date_field(self, parent, label: str, col: int, default: str) -> ctk.CTkEntry:
        C, F = COLORS, FONTS
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, padx=12 if col == 0 else 6, pady=10, sticky="ew")
        ctk.CTkLabel(cell, text=label, font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", pady=(0, 2))
        entry = ctk.CTkEntry(
            cell, height=36,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="YYYY-MM-DD",
        )
        entry.pack(fill="x")
        if default:
            entry.insert(0, default)
        return entry

    def _billing_row(self, parent, label: str, value: str, color: str,
                     big: bool = False) -> ctk.CTkLabel:
        C, F = COLORS, FONTS
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row, text=label,
                     font=F["heading_sm"] if big else F["body_md"],
                     text_color=C["text_secondary"]).pack(side="left")
        lbl = ctk.CTkLabel(row, text=value,
                           font=F["heading_md"] if big else F["body_md"],
                           text_color=color)
        lbl.pack(side="right")
        return lbl

    # ─────────────────────────────────────────────────────────────────────────
    # Event handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _on_mobile_changed(self, *_):
        mobile = self._mobile_var.get().strip()
        if len(mobile) == 10 and mobile.isdigit():
            customer = db_manager.get_customer_by_mobile(mobile)
            if customer:
                self._fill_customer_fields(customer)
                self._customer_id = customer["id"]

    def _fill_customer_fields(self, customer: Dict):
        """Pre-fill customer fields from a DB record."""
        self._name_entry.delete(0, "end")
        self._name_entry.insert(0, customer.get("name", ""))

        self._alt_mobile_entry.delete(0, "end")
        self._alt_mobile_entry.insert(0, customer.get("alternate_mobile", "") or "")

        self._address_text.delete("0.0", "end")
        self._address_text.insert("0.0", customer.get("address", "") or "")

    def _open_measurement_modal(self):
        garment = self._garment_var.get()

        def on_result(result: Dict):
            self._current_measurements = result.get("measurements", {})
            self._current_design = result.get("design_instructions", "")
            filled = len(self._current_measurements)
            if filled:
                self._meas_indicator.configure(
                    text=f"✓  {filled} measurement(s) saved"
                )
                self._meas_btn.configure(
                    text="  📐  Edit Measurements & Design Notes",
                    fg_color=COLORS["bg_medium"],
                )
            else:
                self._meas_indicator.configure(text="")

        MeasurementModal(
            self.winfo_toplevel(),
            garment_type=garment,
            existing_measurements=self._current_measurements,
            existing_design=self._current_design,
            callback=on_result,
        )

    def _add_item_to_cart(self):
        garment = self._garment_var.get()
        try:
            qty = int(self._qty_var.get() or 1)
            rate = float(self._rate_var.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Quantity and Rate must be numbers.", parent=self.winfo_toplevel())
            return

        if rate <= 0:
            messagebox.showwarning("Missing Rate", "Please enter a rate for this item.", parent=self.winfo_toplevel())
            return

        item = {
            "garment_type": garment,
            "quantity": qty,
            "item_rate": rate,
            "measurements": self._current_measurements.copy(),
            "measurements_json": json.dumps(self._current_measurements),
            "design_instructions": self._current_design,
        }
        self._cart_items.append(item)

        # Reset item fields
        self._qty_var.set("1")
        self._rate_var.set("")
        self._current_measurements = {}
        self._current_design = ""
        self._meas_indicator.configure(text="")
        self._meas_btn.configure(
            text="  📐  Add Measurements & Design Notes",
            fg_color=COLORS["btn_neutral"],
        )

        self._refresh_cart_display()
        self._recalculate()

    def _remove_cart_item(self, idx: int):
        if 0 <= idx < len(self._cart_items):
            self._cart_items.pop(idx)
        self._refresh_cart_display()
        self._recalculate()

    def _refresh_cart_display(self):
        C, F = COLORS, FONTS
        # Clear
        for widget in self._cart_frame.winfo_children():
            widget.destroy()

        if not self._cart_items:
            ctk.CTkLabel(
                self._cart_frame,
                text="  No items added yet.  Use the form above to add garments.",
                font=F["body_sm"],
                text_color=C["text_muted"],
            ).pack(pady=14)
            return

        # Header
        hdr = ctk.CTkFrame(self._cart_frame, fg_color=C["table_header"], corner_radius=6)
        hdr.pack(fill="x", padx=10, pady=(10, 4))
        for col, (text, w) in enumerate([
            ("#", 30), ("Garment", 0), ("Qty", 40), ("Rate", 70), ("Total", 70), ("", 34)
        ]):
            ctk.CTkLabel(hdr, text=text, font=F["label_bold"],
                         text_color=C["text_primary"],
                         width=w if w else 0).grid(
                row=0, column=col,
                padx=6, pady=6,
                sticky="w" if col == 1 else "e" if col in (3, 4) else "w"
            )
        hdr.grid_columnconfigure(1, weight=1)

        # Rows
        for idx, item in enumerate(self._cart_items):
            qty   = item.get("quantity", 1)
            rate  = item.get("item_rate", 0.0)
            total = qty * rate
            bg    = C["bg_card"] if idx % 2 == 0 else C["table_row_alt"]

            row = ctk.CTkFrame(self._cart_frame, fg_color=bg, corner_radius=0)
            row.pack(fill="x", padx=10)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text=str(idx + 1), font=F["body_xs"],
                         text_color=C["text_muted"], width=30).grid(row=0, column=0, padx=6, pady=5, sticky="w")
            garment_name = item.get("garment_type", "")
            design_hint = item.get("design_instructions", "")
            garment_display = garment_name
            if design_hint:
                garment_display += f"  ✦"
            ctk.CTkLabel(row, text=garment_display, font=F["body_sm"],
                         text_color=C["text_primary"], anchor="w").grid(row=0, column=1, padx=4, pady=5, sticky="ew")
            ctk.CTkLabel(row, text=str(qty), font=F["body_xs"],
                         text_color=C["text_secondary"], width=40).grid(row=0, column=2, padx=4, pady=5)
            ctk.CTkLabel(row, text=f"₹{rate:,.0f}", font=F["body_xs"],
                         text_color=C["text_secondary"], width=70).grid(row=0, column=3, padx=4, pady=5)
            ctk.CTkLabel(row, text=f"₹{total:,.0f}", font=F["body_sm"],
                         text_color=C["gold"], width=70).grid(row=0, column=4, padx=4, pady=5)

            i = idx  # capture for lambda
            ctk.CTkButton(
                row, text="✕", width=28, height=24,
                fg_color=C["btn_danger"], hover_color="#A00000",
                text_color="#FFFFFF", font=("Segoe UI", 9, "bold"),
                command=lambda i=i: self._remove_cart_item(i),
                corner_radius=4,
            ).grid(row=0, column=5, padx=6, pady=5)

        # Spacer
        ctk.CTkFrame(self._cart_frame, fg_color="transparent", height=6).pack()

    def _recalculate(self, *_):
        total = sum(
            float(i.get("item_rate", 0)) * int(i.get("quantity", 1))
            for i in self._cart_items
        )
        try:
            advance = float(self._advance_var.get() or 0)
        except ValueError:
            advance = 0.0
        balance = max(total - advance, 0.0)

        self._total_label.configure(text=f"₹ {total:,.2f}")
        self._advance_disp.configure(text=f"₹ {advance:,.2f}")
        self._balance_label.configure(text=f"₹ {balance:,.2f}")

        # Auto-set payment status
        if advance == 0:
            ps = "Unpaid"
        elif advance >= total:
            ps = "Paid"
        else:
            ps = "Partial"
        # (no need to call UI change; status is read at save time)

    # ─────────────────────────────────────────────────────────────────────────
    # Save / Update order
    # ─────────────────────────────────────────────────────────────────────────

    def _collect_form_data(self):
        """Validate and collect all form data. Raises ValueError on missing fields."""
        mobile = self._mobile_var.get().strip()
        name   = self._name_entry.get().strip()
        alt_mob = self._alt_mobile_entry.get().strip()
        address = self._address_text.get("0.0", "end").strip()
        booking = self._booking_entry.get().strip()
        collection = self._collection_entry.get().strip()
        notes = self._notes_text.get("0.0", "end").strip()

        if not mobile or not name:
            raise ValueError("Customer name and mobile are required.")
        if not len(mobile) == 10 or not mobile.isdigit():
            raise ValueError("Mobile must be exactly 10 digits.")
        if not booking or not collection:
            raise ValueError("Both Booking Date and Delivery Date are required.")
        try:
            datetime.strptime(booking, "%Y-%m-%d")
            datetime.strptime(collection, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Dates must be in YYYY-MM-DD format.")
        if not self._cart_items:
            raise ValueError("Please add at least one garment item to the order.")

        total   = sum(float(i["item_rate"]) * int(i["quantity"]) for i in self._cart_items)
        try:
            advance = float(self._advance_var.get() or 0)
        except ValueError:
            advance = 0.0
        balance = max(total - advance, 0.0)

        # Determine payment status
        if advance <= 0:
            pay_status = "Unpaid"
        elif advance >= total:
            pay_status = "Paid"
        else:
            pay_status = "Partial"

        return {
            "mobile": mobile, "name": name,
            "alt_mobile": alt_mob, "address": address,
            "booking": booking, "collection": collection,
            "total": total, "advance": advance, "balance": balance,
            "pay_status": pay_status,
            "order_status": self._order_status_var.get(),
            "pay_mode": self._pay_mode_var.get(),
            "notes": notes,
            "items": self._cart_items,
        }

    def _on_save(self):
        try:
            data = self._collect_form_data()
        except ValueError as err:
            messagebox.showerror("Validation Error", str(err), parent=self.winfo_toplevel())
            return

        # Upsert customer
        customer_id = db_manager.upsert_customer(
            name=data["name"],
            mobile=data["mobile"],
            alternate_mobile=data["alt_mobile"],
            address=data["address"],
        )

        if self._edit_order_id is None:
            # CREATE
            order_id = db_manager.create_order(
                customer_id=customer_id,
                booking_date=data["booking"],
                collection_date=data["collection"],
                total_amount=data["total"],
                advance_amount=data["advance"],
                balance_amount=data["balance"],
                payment_status=data["pay_status"],
                order_status=data["order_status"],
                payment_mode=data["pay_mode"],
                notes=data["notes"],
                items=data["items"],
            )
            msg = f"Order #{order_id} created successfully!"
        else:
            # UPDATE
            order_id = self._edit_order_id
            db_manager.update_order(
                order_id=order_id,
                customer_id=customer_id,
                booking_date=data["booking"],
                collection_date=data["collection"],
                total_amount=data["total"],
                advance_amount=data["advance"],
                balance_amount=data["balance"],
                payment_status=data["pay_status"],
                order_status=data["order_status"],
                payment_mode=data["pay_mode"],
                notes=data["notes"],
                items=data["items"],
            )
            msg = f"Order #{order_id} updated successfully!"

        # Generate and open PDF
        try:
            from services.pdf_service import generate_invoice, open_pdf
            order_record = db_manager.get_order_by_id(order_id)
            items_record = db_manager.get_order_items(order_id)
            customer_record = db_manager.get_customer_by_id(customer_id)
            pdf_path = generate_invoice(order_record, items_record, customer_record)
            open_pdf(pdf_path)
        except Exception as e:
            messagebox.showwarning(
                "PDF Warning",
                f"Order saved, but PDF generation failed:\n{e}",
                parent=self.winfo_toplevel()
            )

        messagebox.showinfo("Success", msg, parent=self.winfo_toplevel())

        if self.on_order_saved:
            self.on_order_saved(order_id)

        self.reset_form()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API – called from dashboard
    # ─────────────────────────────────────────────────────────────────────────

    def load_order_for_edit(self, order_id: int):
        """Pre-fill the form with an existing order's data for editing."""
        order = db_manager.get_order_by_id(order_id)
        items = db_manager.get_order_items(order_id)
        if not order:
            messagebox.showerror("Error", f"Order #{order_id} not found.")
            return

        self.reset_form(silent=True)
        self._edit_order_id = order_id

        # Mode label
        self._mode_label.configure(text="  ✏️  Edit Order")
        self._order_badge.configure(text=f"Order #{order_id}")
        self._save_btn.configure(text=f"  💾  Update Order #{order_id}")

        # Customer info
        self._mobile_var.set(order.get("mobile", ""))
        self._name_entry.delete(0, "end")
        self._name_entry.insert(0, order.get("customer_name", ""))
        self._alt_mobile_entry.delete(0, "end")
        self._alt_mobile_entry.insert(0, order.get("alternate_mobile", "") or "")
        self._address_text.delete("0.0", "end")
        self._address_text.insert("0.0", order.get("address", "") or "")
        self._customer_id = order.get("customer_id")

        # Dates
        self._booking_entry.delete(0, "end")
        self._booking_entry.insert(0, order.get("booking_date", ""))
        self._collection_entry.delete(0, "end")
        self._collection_entry.insert(0, order.get("collection_date", ""))

        # Items
        self._cart_items = []
        for item in items:
            meas = item.get("measurements", {})
            if isinstance(meas, str):
                try:
                    meas = json.loads(meas)
                except Exception:
                    meas = {}
            self._cart_items.append({
                "garment_type":       item.get("garment_type", "Custom"),
                "quantity":           item.get("quantity", 1),
                "item_rate":          item.get("item_rate", 0.0),
                "measurements":       meas,
                "measurements_json":  item.get("measurements_json", "{}"),
                "design_instructions":item.get("design_instructions", ""),
            })
        self._refresh_cart_display()

        # Payment
        self._advance_var.set(str(order.get("advance_amount", 0)))
        self._pay_mode_var.set(order.get("payment_mode", "Cash"))
        self._order_status_var.set(order.get("order_status", "Pending"))
        self._notes_text.delete("0.0", "end")
        self._notes_text.insert("0.0", order.get("notes", "") or "")

        self._recalculate()

        # Scroll to top
        try:
            self._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def reset_form(self, silent: bool = False):
        """Reset the form to new-order mode."""
        self._edit_order_id = None
        self._cart_items = []
        self._customer_id = None
        self._current_measurements = {}
        self._current_design = ""

        # Reset labels
        self._mode_label.configure(text="  ✂️  New Order")
        self._order_badge.configure(text="")
        self._save_btn.configure(text="  💾  Save & Print Invoice")

        # Clear fields
        self._mobile_var.set("")
        self._name_entry.delete(0, "end")
        self._alt_mobile_entry.delete(0, "end")
        self._address_text.delete("0.0", "end")

        today = date.today().strftime("%Y-%m-%d")
        self._booking_entry.delete(0, "end")
        self._booking_entry.insert(0, today)
        self._collection_entry.delete(0, "end")

        self._qty_var.set("1")
        self._rate_var.set("")
        self._advance_var.set("0")
        self._pay_mode_var.set("Cash")
        self._order_status_var.set("Pending")
        self._notes_text.delete("0.0", "end")

        self._meas_indicator.configure(text="")
        self._meas_btn.configure(
            text="  📐  Add Measurements & Design Notes",
            fg_color=COLORS["btn_neutral"],
        )

        self._refresh_cart_display()
        self._recalculate()
