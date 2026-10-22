"""
ui/components/order_entry.py
Left-pane: Customer info + multi-item cart + billing summary.
Supports Create and Edit modes, visual calendar pickers, inline measurement editing,
cart item editing, and one-click balance settlements.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import date, datetime
from typing import Optional, Callable, Dict, List, Any
import json

from ui.styles import COLORS, FONTS, GARMENT_TYPES, PAYMENT_STATUSES, PAYMENT_MODES, ORDER_STATUSES
from ui.components.measurement_modal import MeasurementModal
from ui.components.calendar_picker import CalendarPickerModal
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
            scrollbar_button_color=COLORS["border_light"],
            scrollbar_button_hover_color=COLORS["primary"],
            **kwargs,
        )
        self.on_order_saved = on_order_saved

        # State
        self._edit_order_id: Optional[int] = None      # None = create mode
        self._cart_items: List[Dict] = []               # In-memory cart
        self._customer_id: Optional[int] = None
        self._editing_cart_index: Optional[int] = None  # None = adding new, int = editing cart item

        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        C, F = COLORS, FONTS
        pad = {"padx": 10, "pady": 5}

        # ── Panel title ──────────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=8)
        title_frame.pack(fill="x", **pad)

        self._mode_label = ctk.CTkLabel(
            title_frame,
            text="  ✂️  New Order",
            font=F["heading_lg"],
            text_color=C["primary"],
        )
        self._mode_label.pack(side="left", padx=12, pady=10)

        self._order_badge = ctk.CTkLabel(
            title_frame,
            text="",
            font=F["heading_sm"],
            text_color=C["gold"],
        )
        self._order_badge.pack(side="right", padx=12)

        # ── Customer section ─────────────────────────────────────────────────
        self._section("👤  Customer Information")

        cust_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        cust_frame.pack(fill="x", **pad)

        # Mobile + auto-lookup
        mob_row = ctk.CTkFrame(cust_frame, fg_color="transparent")
        mob_row.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(mob_row, text="Mobile *", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(side="left")
        ctk.CTkLabel(mob_row, text="(auto-fills on 10 digits)",
                     font=F["label"], text_color=C["text_muted"]).pack(side="left", padx=6)

        self._mobile_var = tk.StringVar()
        self._mobile_var.trace_add("write", self._on_mobile_changed)
        self._mobile_entry = ctk.CTkEntry(
            cust_frame, textvariable=self._mobile_var,
            height=36, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="10-digit mobile number",
        )
        self._mobile_entry.pack(fill="x", padx=10, pady=(0, 6))

        # Name
        self._labeled_entry(cust_frame, "Customer Name *", "_name_entry", "Full name")
        # Alt mobile
        self._labeled_entry(cust_frame, "Alternate Mobile", "_alt_mobile_entry", "Optional")
        # Address
        ctk.CTkLabel(cust_frame, text="Address", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=10, pady=(4, 2))
        self._address_text = ctk.CTkTextbox(
            cust_frame, height=48, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_sm"], corner_radius=6,
        )
        self._address_text.pack(fill="x", padx=10, pady=(0, 10))

        # ── Dates (with Calendar picker buttons) ──────────────────────────────
        self._section("📅  Dates")

        dates_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        dates_frame.pack(fill="x", **pad)
        dates_frame.grid_columnconfigure((0, 1), weight=1)

        today_str = date.today().strftime("%Y-%m-%d")

        self._booking_entry = self._date_field(dates_frame, "Booking Date *", 0, today_str, is_delivery=False)
        self._collection_entry = self._date_field(dates_frame, "Delivery Date *", 1, "", is_delivery=True)

        # ── Items form ───────────────────────────────────────────────────────
        self._section("🧵  Order Items")

        item_form = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        item_form.pack(fill="x", **pad)

        # Garment type
        ctk.CTkLabel(item_form, text="Garment Type", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=10, pady=(8, 2))
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
            height=34,
        )
        self._garment_menu.pack(fill="x", padx=10, pady=(0, 6))

        # Qty + Rate
        qty_rate_row = ctk.CTkFrame(item_form, fg_color="transparent")
        qty_rate_row.pack(fill="x", padx=10, pady=(0, 6))
        qty_rate_row.grid_columnconfigure(0, weight=0)
        qty_rate_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(qty_rate_row, text="Qty", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(qty_rate_row, text="Rate (₹) *", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self._qty_var = tk.StringVar(value="1")
        self._qty_entry = ctk.CTkEntry(
            qty_rate_row, textvariable=self._qty_var,
            height=34, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"], width=70,
        )
        self._qty_entry.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self._rate_var = tk.StringVar()
        self._rate_var.trace_add("write", self._recalculate)
        self._rate_entry = ctk.CTkEntry(
            qty_rate_row, textvariable=self._rate_var,
            height=34, fg_color=C["bg_input"], border_color=C["border"],
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
            height=32,
            command=self._open_measurement_modal,
            corner_radius=6,
        )
        self._meas_btn.pack(fill="x", padx=10, pady=(0, 4))

        self._meas_indicator = ctk.CTkLabel(
            item_form, text="", font=F["label"],
            text_color=C["status_delivered"],
        )
        self._meas_indicator.pack(anchor="w", padx=10, pady=(0, 4))

        # Add / Update item button row
        item_btn_row = ctk.CTkFrame(item_form, fg_color="transparent")
        item_btn_row.pack(fill="x", padx=10, pady=(4, 10))

        self._add_item_btn = ctk.CTkButton(
            item_btn_row,
            text="  ➕  Add Item to Order",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["heading_sm"],
            height=38,
            command=self._add_or_update_item,
            corner_radius=6,
        )
        self._add_item_btn.pack(side="left", fill="x", expand=True)

        self._cancel_item_edit_btn = ctk.CTkButton(
            item_btn_row,
            text="✕ Cancel Edit",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_muted"],
            font=F["body_xs"],
            height=38,
            width=90,
            command=self._cancel_item_edit,
            corner_radius=6,
        )
        # Not packed initially, only when editing a cart item

        # ── Cart display ─────────────────────────────────────────────────────
        self._section("🛒  Cart Summary")
        self._cart_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        self._cart_frame.pack(fill="x", **pad)
        self._refresh_cart_display()

        # ── Payment section ──────────────────────────────────────────────────
        self._section("💳  Payment & Status")

        pay_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        pay_frame.pack(fill="x", **pad)

        # Advance
        ctk.CTkLabel(pay_frame, text="Advance Received (₹)", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=10, pady=(8, 2))
        self._advance_var = tk.StringVar(value="0")
        self._advance_var.trace_add("write", self._recalculate)
        self._advance_entry = ctk.CTkEntry(
            pay_frame, textvariable=self._advance_var,
            height=36, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="0.00",
        )
        self._advance_entry.pack(fill="x", padx=10, pady=(0, 6))

        # Quick Settle Full Balance Button (visible when editing an order with remaining balance)
        self._quick_settle_btn = ctk.CTkButton(
            pay_frame,
            text="  💰  Settle Full Balance Now",
            fg_color=C["btn_success"],
            hover_color="#1E8449",
            text_color="#FFFFFF",
            font=F["body_sm"],
            height=32,
            command=self._on_quick_settle_clicked,
            corner_radius=6,
        )
        # Not packed by default

        # Payment mode + status
        row2 = ctk.CTkFrame(pay_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 6))
        row2.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(row2, text="Payment Mode", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row2, text="Order Status", font=F["label_bold"],
                     text_color=C["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._pay_mode_var = tk.StringVar(value="Cash")
        ctk.CTkOptionMenu(
            row2, variable=self._pay_mode_var,
            values=PAYMENT_MODES,
            fg_color=C["bg_input"], button_color=C["border_light"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_sm"], height=32,
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
            font=F["body_sm"], height=32,
        ).grid(row=1, column=1, sticky="ew", pady=(2, 0), padx=(8, 0))

        # Notes
        ctk.CTkLabel(pay_frame, text="Order Notes", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=10, pady=(6, 2))
        self._notes_text = ctk.CTkTextbox(
            pay_frame, height=48,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_sm"], corner_radius=6,
        )
        self._notes_text.pack(fill="x", padx=10, pady=(0, 10))

        # ── Billing summary ──────────────────────────────────────────────────
        self._section("💰  Billing Summary")
        summary_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        summary_frame.pack(fill="x", **pad)

        self._total_label = self._billing_row(summary_frame, "Total Amount", "₹ 0.00", C["text_primary"])
        self._advance_disp = self._billing_row(summary_frame, "Advance Paid", "₹ 0.00", C["status_ready"])
        self._balance_label = self._billing_row(summary_frame, "Balance Due", "₹ 0.00", C["primary"], big=True)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(8, 14))

        self._save_btn = ctk.CTkButton(
            btn_frame,
            text="  💾  Save & Print Invoice",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["heading_md"],
            height=44,
            command=self._on_save,
            corner_radius=8,
        )
        self._save_btn.pack(fill="x", pady=(0, 6))

        self._cancel_btn = ctk.CTkButton(
            btn_frame,
            text="  ✕  Cancel / Reset Form",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_md"],
            height=34,
            command=self.reset_form,
            corner_radius=6,
        )
        self._cancel_btn.pack(fill="x")

    # ─────────────────────────────────────────────────────────────────────────
    # Helper UI builders
    # ─────────────────────────────────────────────────────────────────────────

    def _section(self, title: str):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(frame, text=title, font=FONTS["heading_sm"],
                     text_color=COLORS["gold"]).pack(side="left")
        ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6
        )

    def _labeled_entry(self, parent, label: str, attr: str, placeholder: str) -> ctk.CTkEntry:
        C, F = COLORS, FONTS
        ctk.CTkLabel(parent, text=label, font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", padx=10, pady=(4, 2))
        entry = ctk.CTkEntry(
            parent, height=34,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text=placeholder,
        )
        entry.pack(fill="x", padx=10, pady=(0, 6))
        setattr(self, attr, entry)
        return entry

    def _date_field(self, parent, label: str, col: int, default: str, is_delivery: bool = False) -> ctk.CTkEntry:
        C, F = COLORS, FONTS
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")

        ctk.CTkLabel(cell, text=label, font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", pady=(0, 2))

        row = ctk.CTkFrame(cell, fg_color="transparent")
        row.pack(fill="x")

        entry = ctk.CTkEntry(
            row, height=34,
            fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_md"],
            placeholder_text="YYYY-MM-DD",
        )
        entry.pack(side="left", fill="x", expand=True)

        cal_btn = ctk.CTkButton(
            row, text="📅", width=34, height=34,
            fg_color=C["bg_input"], hover_color=C["primary_dark"],
            text_color=C["gold"], font=("Segoe UI", 12),
            corner_radius=6,
            command=lambda: self._open_calendar(entry, label, is_delivery),
        )
        cal_btn.pack(side="left", padx=(4, 0))

        if default:
            entry.insert(0, default)

        entry.bind("<Double-1>", lambda _: self._open_calendar(entry, label, is_delivery))
        return entry

    def _open_calendar(self, entry: ctk.CTkEntry, label: str, is_delivery: bool):
        clean_title = label.replace("*", "").strip()
        CalendarPickerModal(
            self.winfo_toplevel(),
            title=f"Pick {clean_title}",
            initial_date=entry.get(),
            is_delivery=is_delivery,
            callback=lambda val: (entry.delete(0, "end"), entry.insert(0, val)),
        )

    def _billing_row(self, parent, label: str, value: str, color: str,
                     big: bool = False) -> ctk.CTkLabel:
        C, F = COLORS, FONTS
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(row, text=label,
                     font=F["heading_sm"] if big else F["body_md"],
                     text_color=C["text_secondary"]).pack(side="left")
        lbl = ctk.CTkLabel(row, text=value,
                            font=F["heading_md"] if big else F["body_md"],
                            text_color=color)
        lbl.pack(side="right")
        return lbl

    # ─────────────────────────────────────────────────────────────────────────
    # Event handlers & Cart Logic
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
                self._meas_btn.configure(
                    text="  📐  Add Measurements & Design Notes",
                    fg_color=COLORS["btn_neutral"],
                )

        MeasurementModal(
            self.winfo_toplevel(),
            garment_type=garment,
            existing_measurements=self._current_measurements,
            existing_design=self._current_design,
            callback=on_result,
        )

    def _add_or_update_item(self):
        garment = self._garment_var.get()
        try:
            qty = int(self._qty_var.get() or 1)
            rate = float(self._rate_var.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Quantity and Rate must be valid numbers.", parent=self.winfo_toplevel())
            return

        if rate <= 0:
            messagebox.showwarning("Missing Rate", "Please enter a valid rate for this item.", parent=self.winfo_toplevel())
            return

        item = {
            "garment_type": garment,
            "quantity": qty,
            "item_rate": rate,
            "measurements": self._current_measurements.copy(),
            "measurements_json": json.dumps(self._current_measurements),
            "design_instructions": self._current_design,
        }

        if self._editing_cart_index is not None and 0 <= self._editing_cart_index < len(self._cart_items):
            # Update existing cart item
            self._cart_items[self._editing_cart_index] = item
            self._editing_cart_index = None
            self._add_item_btn.configure(
                text="  ➕  Add Item to Order",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_dark"],
                text_color="#FFFFFF",
            )
            self._cancel_item_edit_btn.pack_forget()
        else:
            # Add new item
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

    def _cancel_item_edit(self):
        self._editing_cart_index = None
        self._qty_var.set("1")
        self._rate_var.set("")
        self._current_measurements = {}
        self._current_design = ""
        self._meas_indicator.configure(text="")
        self._meas_btn.configure(
            text="  📐  Add Measurements & Design Notes",
            fg_color=COLORS["btn_neutral"],
        )
        self._add_item_btn.configure(
            text="  ➕  Add Item to Order",
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_dark"],
            text_color="#FFFFFF",
        )
        self._cancel_item_edit_btn.pack_forget()

    def _start_edit_cart_item(self, idx: int):
        if not (0 <= idx < len(self._cart_items)):
            return
        self._editing_cart_index = idx
        item = self._cart_items[idx]

        self._garment_var.set(item.get("garment_type", GARMENT_TYPES[0]))
        self._qty_var.set(str(item.get("quantity", 1)))
        self._rate_var.set(str(item.get("item_rate", "")))
        self._current_measurements = item.get("measurements", {}).copy()
        self._current_design = item.get("design_instructions", "")

        filled = len(self._current_measurements)
        if filled:
            self._meas_indicator.configure(text=f"✓  {filled} measurement(s) saved")
            self._meas_btn.configure(text="  📐  Edit Measurements & Notes", fg_color=COLORS["bg_medium"])
        else:
            self._meas_indicator.configure(text="")
            self._meas_btn.configure(text="  📐  Add Measurements & Notes", fg_color=COLORS["btn_neutral"])

        self._add_item_btn.configure(
            text=f"  ✓  Update Item #{idx + 1}",
            fg_color=COLORS["gold"],
            hover_color=COLORS["gold_light"],
            text_color="#1A1A2E",
        )
        self._cancel_item_edit_btn.pack(side="left", padx=(6, 0), fill="x", expand=True)

    def _edit_cart_item_measurements(self, idx: int):
        """Open measurement modal directly for a specific item in the cart."""
        if not (0 <= idx < len(self._cart_items)):
            return
        item = self._cart_items[idx]
        garment = item.get("garment_type", "Custom")

        def on_result(result: Dict):
            item["measurements"] = result.get("measurements", {})
            item["measurements_json"] = json.dumps(item["measurements"])
            item["design_instructions"] = result.get("design_instructions", "")
            self._refresh_cart_display()

        MeasurementModal(
            self.winfo_toplevel(),
            garment_type=garment,
            existing_measurements=item.get("measurements", {}),
            existing_design=item.get("design_instructions", ""),
            callback=on_result,
        )

    def _remove_cart_item(self, idx: int):
        if 0 <= idx < len(self._cart_items):
            self._cart_items.pop(idx)
            if self._editing_cart_index == idx:
                self._cancel_item_edit()
        self._refresh_cart_display()
        self._recalculate()

    def _refresh_cart_display(self):
        C, F = COLORS, FONTS
        # Clear previous rows
        for widget in self._cart_frame.winfo_children():
            widget.destroy()

        if not self._cart_items:
            ctk.CTkLabel(
                self._cart_frame,
                text="  No items added yet. Use the form above to add garments.",
                font=F["body_sm"],
                text_color=C["text_muted"],
            ).pack(pady=12)
            return

        # Header Row
        hdr = ctk.CTkFrame(self._cart_frame, fg_color=C["table_header"], corner_radius=6)
        hdr.pack(fill="x", padx=6, pady=(6, 2))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="#", font=F["label_bold"], text_color=C["text_primary"], width=24).grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ctk.CTkLabel(hdr, text="Garment Details", font=F["label_bold"], text_color=C["text_primary"]).grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ctk.CTkLabel(hdr, text="Qty", font=F["label_bold"], text_color=C["text_primary"], width=32).grid(row=0, column=2, padx=4, pady=4)
        ctk.CTkLabel(hdr, text="Rate", font=F["label_bold"], text_color=C["text_primary"], width=55).grid(row=0, column=3, padx=4, pady=4, sticky="e")
        ctk.CTkLabel(hdr, text="Total", font=F["label_bold"], text_color=C["text_primary"], width=55).grid(row=0, column=4, padx=4, pady=4, sticky="e")
        ctk.CTkLabel(hdr, text="Actions", font=F["label_bold"], text_color=C["text_primary"], width=85).grid(row=0, column=5, padx=4, pady=4)

        # Cart Rows
        for idx, item in enumerate(self._cart_items):
            qty   = item.get("quantity", 1)
            rate  = item.get("item_rate", 0.0)
            total = qty * rate
            bg    = C["bg_card"] if idx % 2 == 0 else C["table_row_alt"]

            row = ctk.CTkFrame(self._cart_frame, fg_color=bg, corner_radius=4)
            row.pack(fill="x", padx=6, pady=2)
            row.grid_columnconfigure(1, weight=1)

            # Index
            ctk.CTkLabel(row, text=str(idx + 1), font=F["body_xs"],
                         text_color=C["text_muted"], width=24).grid(row=0, column=0, padx=4, pady=4, sticky="w")

            # Garment + Measurement summary
            details_cell = ctk.CTkFrame(row, fg_color="transparent")
            details_cell.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

            garment_name = item.get("garment_type", "Custom")
            meas_count = len(item.get("measurements", {}))
            design_hint = item.get("design_instructions", "").strip()

            g_lbl = ctk.CTkLabel(details_cell, text=garment_name, font=F["heading_sm"],
                                 text_color=C["text_primary"], anchor="w")
            g_lbl.pack(anchor="w")

            sub_parts = []
            if meas_count > 0:
                sub_parts.append(f"✓ {meas_count} meas")
            else:
                sub_parts.append("no meas")
            if design_hint:
                sub_parts.append(f"✦ {design_hint[:24]}")

            sub_text = "  |  ".join(sub_parts)
            ctk.CTkLabel(details_cell, text=sub_text, font=F["body_xs"],
                         text_color=C["status_delivered"] if meas_count else C["text_muted"],
                         anchor="w").pack(anchor="w")

            # Qty, Rate, Total
            ctk.CTkLabel(row, text=str(qty), font=F["body_sm"],
                         text_color=C["text_secondary"], width=32).grid(row=0, column=2, padx=4, pady=4)
            ctk.CTkLabel(row, text=f"₹{rate:,.0f}", font=F["body_xs"],
                         text_color=C["text_secondary"], width=55).grid(row=0, column=3, padx=4, pady=4, sticky="e")
            ctk.CTkLabel(row, text=f"₹{total:,.0f}", font=F["body_sm"],
                         text_color=C["gold"], width=55).grid(row=0, column=4, padx=4, pady=4, sticky="e")

            # Actions cell: 📐 Edit Measurements, ✏️ Edit Item, ✕ Delete
            act_cell = ctk.CTkFrame(row, fg_color="transparent")
            act_cell.grid(row=0, column=5, padx=4, pady=4)

            i = idx  # closure variable
            # 📐 Meas button
            ctk.CTkButton(
                act_cell, text="📐", width=26, height=24,
                fg_color=C["primary"] if meas_count else C["btn_neutral"],
                hover_color=C["primary_dark"],
                text_color="#FFFFFF", font=("Segoe UI", 9),
                command=lambda i=i: self._edit_cart_item_measurements(i),
                corner_radius=4,
            ).pack(side="left", padx=1)

            # ✏️ Edit item button
            ctk.CTkButton(
                act_cell, text="✏️", width=26, height=24,
                fg_color=C["btn_neutral"], hover_color=C["border_light"],
                text_color=C["text_secondary"], font=("Segoe UI", 9),
                command=lambda i=i: self._start_edit_cart_item(i),
                corner_radius=4,
            ).pack(side="left", padx=1)

            # ✕ Remove item button
            ctk.CTkButton(
                act_cell, text="✕", width=24, height=24,
                fg_color=C["btn_danger"], hover_color="#A00000",
                text_color="#FFFFFF", font=("Segoe UI", 9, "bold"),
                command=lambda i=i: self._remove_cart_item(i),
                corner_radius=4,
            ).pack(side="left", padx=1)

        # Bottom space
        ctk.CTkFrame(self._cart_frame, fg_color="transparent", height=4).pack()

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

        # Toggle Quick Settle button
        if self._edit_order_id is not None and balance > 0:
            self._quick_settle_btn.configure(text=f"  💰  Settle Remaining Balance (₹{balance:,.2f})")
            self._quick_settle_btn.pack(fill="x", padx=10, pady=(0, 8))
        else:
            self._quick_settle_btn.pack_forget()

    def _on_quick_settle_clicked(self):
        """Open the payment settlement modal for the currently loaded order."""
        if not self._edit_order_id:
            return
        order = db_manager.get_order_by_id(self._edit_order_id)
        if not order:
            return

        from ui.components.payment_modal import PaymentModal

        def on_settled(updated_order: Dict):
            self.load_order_for_edit(self._edit_order_id)
            if self.on_order_saved:
                self.on_order_saved(self._edit_order_id)

        PaymentModal(self.winfo_toplevel(), order=order, on_settled=on_settled)

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
            raise ValueError("Dates must be in YYYY-MM-DD format (use the 📅 calendar button).")
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
            msg = f"Order #{order_id:05d} created successfully!"
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
            msg = f"Order #{order_id:05d} updated successfully!"

        # Generate & open PDF invoice
        try:
            from services.pdf_service import generate_invoice, open_pdf
            order_record    = db_manager.get_order_by_id(order_id)
            items_records   = db_manager.get_order_items(order_id)
            customer_record = db_manager.get_customer_by_id(customer_id)
            pdf_path = generate_invoice(order_record, items_records, customer_record)
            open_pdf(pdf_path)
        except Exception as exc:
            messagebox.showwarning(
                "PDF Warning",
                f"Order was saved, but invoice could not be generated:\n{exc}",
                parent=self.winfo_toplevel(),
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
        self._order_badge.configure(text=f"Order #{order_id:05d}")
        self._save_btn.configure(text=f"  💾  Update Order #{order_id:05d}")

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
                "garment_type":        item.get("garment_type", "Custom"),
                "quantity":            item.get("quantity", 1),
                "item_rate":           item.get("item_rate", 0.0),
                "measurements":        meas,
                "measurements_json":   item.get("measurements_json", "{}"),
                "design_instructions": item.get("design_instructions", ""),
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
        self._editing_cart_index = None

        # Reset labels
        self._mode_label.configure(text="  ✂️  New Order")
        self._order_badge.configure(text="")
        self._save_btn.configure(text="  💾  Save & Print Invoice")
        self._quick_settle_btn.pack_forget()
        self._cancel_item_edit_btn.pack_forget()

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
