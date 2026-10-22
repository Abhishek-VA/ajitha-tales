"""
ui/components/payment_modal.py
Dedicated payment settlement popup dialog for collecting final balances,
recording payment modes (Cash/UPI/Card), transitioning order status,
and generating updated paid invoices.
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Dict, Callable, Optional

from ui.styles import COLORS, FONTS, PAYMENT_MODES
from database import db_manager


class PaymentModal(ctk.CTkToplevel):
    """
    Modal dialog to settle remaining balance payments on an order.
    """

    def __init__(
        self,
        parent,
        order: Dict,
        on_settled: Optional[Callable[[Dict], None]] = None,
    ):
        super().__init__(parent)
        self.order = order
        self.on_settled = on_settled
        self.order_id = int(order["order_id"])

        C = COLORS
        self.title(f"Settle Payment — Order #{self.order_id}")
        self.configure(fg_color=C["bg_card"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_window(parent)

        self.bind("<Escape>", lambda _: self.destroy())

    def _build_ui(self):
        C, F = COLORS, FONTS
        pad = {"padx": 18, "pady": 6}

        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text=f"  💰  Final Payment Settlement — Order #{self.order_id:05d}",
            font=F["heading_sm"],
            text_color=C["gold"],
        ).pack(side="left", padx=14, pady=10)

        ctk.CTkButton(
            hdr, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=C["primary"],
            text_color=C["text_secondary"], font=("Segoe UI", 11, "bold"),
            command=self.destroy,
        ).pack(side="right", padx=10)

        # Body Container
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Customer badge
        cust_name = self.order.get("customer_name") or self.order.get("name", "Customer")
        cust_mob = self.order.get("mobile", "")
        cust_box = ctk.CTkFrame(body, fg_color=C["bg_dark"], corner_radius=8)
        cust_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            cust_box,
            text=f"👤  {cust_name}    📱  {cust_mob}",
            font=F["body_md"],
            text_color=C["text_primary"],
        ).pack(padx=14, pady=8, anchor="w")

        # Balance summary cards
        total_amt = float(self.order.get("total_amount", 0.0))
        adv_amt   = float(self.order.get("advance_amount", 0.0))
        bal_amt   = float(self.order.get("balance_amount", 0.0))

        summary_box = ctk.CTkFrame(body, fg_color=C["bg_input"], corner_radius=8)
        summary_box.pack(fill="x", pady=(0, 12))
        summary_box.grid_columnconfigure((0, 1, 2), weight=1)

        # Total
        c0 = ctk.CTkFrame(summary_box, fg_color="transparent")
        c0.grid(row=0, column=0, padx=8, pady=8)
        ctk.CTkLabel(c0, text="Total Bill", font=F["label"], text_color=C["text_muted"]).pack()
        ctk.CTkLabel(c0, text=f"₹{total_amt:,.2f}", font=F["heading_sm"], text_color=C["text_primary"]).pack()

        # Advance Paid
        c1 = ctk.CTkFrame(summary_box, fg_color="transparent")
        c1.grid(row=0, column=1, padx=8, pady=8)
        ctk.CTkLabel(c1, text="Paid So Far", font=F["label"], text_color=C["text_muted"]).pack()
        ctk.CTkLabel(c1, text=f"₹{adv_amt:,.2f}", font=F["heading_sm"], text_color=C["status_delivered"]).pack()

        # Balance Due
        c2 = ctk.CTkFrame(summary_box, fg_color="transparent")
        c2.grid(row=0, column=2, padx=8, pady=8)
        ctk.CTkLabel(c2, text="Balance Due", font=F["label_bold"], text_color=C["gold"]).pack()
        ctk.CTkLabel(c2, text=f"₹{bal_amt:,.2f}", font=F["heading_md"], text_color=C["primary"]).pack()

        # ── Form Inputs ──────────────────────────────────────────────────────
        form = ctk.CTkFrame(body, fg_color="transparent")
        form.pack(fill="x", pady=(0, 8))

        # Amount to pay
        ctk.CTkLabel(form, text="Amount Receiving Now (₹) *", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", pady=(0, 2))

        self._amount_var = tk.StringVar(value=f"{bal_amt:.2f}" if bal_amt > 0 else "0.00")
        self._amount_entry = ctk.CTkEntry(
            form, textvariable=self._amount_var,
            height=38, fg_color=C["bg_input"], border_color=C["primary"],
            text_color=C["text_primary"], font=("Segoe UI", 13, "bold"),
        )
        self._amount_entry.pack(fill="x", pady=(0, 10))

        # Payment Mode
        ctk.CTkLabel(form, text="Payment Mode *", font=F["label_bold"],
                     text_color=C["text_secondary"]).pack(anchor="w", pady=(0, 2))

        self._mode_var = tk.StringVar(value="UPI")
        ctk.CTkOptionMenu(
            form, variable=self._mode_var,
            values=PAYMENT_MODES,
            height=36,
            fg_color=C["bg_input"],
            button_color=C["primary"],
            button_hover_color=C["primary_dark"],
            text_color=C["text_primary"],
            dropdown_fg_color=C["bg_medium"],
            dropdown_text_color=C["text_primary"],
            font=F["body_md"],
        ).pack(fill="x", pady=(0, 10))

        # Reference / Remarks
        ctk.CTkLabel(form, text="Payment Remarks (e.g. UPI Ref / Cheque No)", font=F["label"],
                     text_color=C["text_muted"]).pack(anchor="w", pady=(0, 2))
        self._remarks_entry = ctk.CTkEntry(
            form, height=34, fg_color=C["bg_input"], border_color=C["border"],
            text_color=C["text_primary"], font=F["body_sm"],
            placeholder_text="Optional reference note",
        )
        self._remarks_entry.pack(fill="x", pady=(0, 10))

        # Checkboxes
        self._mark_delivered_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            body,
            text="Mark Order Status as 'Delivered' upon payment",
            variable=self._mark_delivered_var,
            font=F["body_sm"],
            text_color=C["text_primary"],
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
        ).pack(anchor="w", pady=(0, 6))

        self._gen_invoice_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            body,
            text="Generate and open updated Paid Invoice PDF",
            variable=self._gen_invoice_var,
            font=F["body_sm"],
            text_color=C["text_primary"],
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
        ).pack(anchor="w", pady=(0, 12))

        # Footer Buttons
        foot = ctk.CTkFrame(self, fg_color=C["bg_medium"], height=52, corner_radius=0)
        foot.pack(fill="x", side="bottom")

        ctk.CTkButton(
            foot,
            text="✓ Confirm & Settle Payment",
            font=F["heading_sm"],
            fg_color=C["btn_success"],
            hover_color="#1E8449",
            text_color="#FFFFFF",
            height=36,
            command=self._confirm,
            corner_radius=6,
        ).pack(side="right", padx=16, pady=8)

        ctk.CTkButton(
            foot,
            text="Cancel",
            font=F["body_md"],
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_muted"],
            height=36,
            width=80,
            command=self.destroy,
            corner_radius=6,
        ).pack(side="right", padx=4, pady=8)

    def _confirm(self):
        try:
            amt = float(self._amount_var.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid payment amount.", parent=self)
            return

        if amt <= 0:
            messagebox.showwarning("Zero Amount", "Payment amount must be greater than zero.", parent=self)
            return

        mode = self._mode_var.get()
        remarks = self._remarks_entry.get().strip()
        mark_deliv = self._mark_delivered_var.get()

        try:
            updated_order = db_manager.settle_order_payment(
                order_id=self.order_id,
                payment_amount=amt,
                payment_mode=mode,
                mark_delivered=mark_deliv,
                notes_append=remarks,
            )

            # Generate updated invoice if selected
            if self._gen_invoice_var.get():
                try:
                    from services.pdf_service import generate_invoice, open_pdf
                    items = db_manager.get_order_items(self.order_id)
                    customer = db_manager.get_customer_by_id(updated_order["customer_id"])
                    pdf_path = generate_invoice(updated_order, items, customer)
                    open_pdf(pdf_path)
                except Exception as ex:
                    print(f"Could not generate invoice: {ex}")

            if self.on_settled:
                self.on_settled(updated_order)

            messagebox.showinfo(
                "Payment Recorded",
                f"Successfully recorded payment of ₹{amt:,.2f} for Order #{self.order_id:05d}!\n\n"
                f"Remaining Balance: ₹{float(updated_order['balance_amount']):,.2f}\n"
                f"Status: {updated_order['order_status']} ({updated_order['payment_status']})",
                parent=self.master,
            )
            self.destroy()

        except Exception as e:
            messagebox.showerror("Settlement Error", str(e), parent=self)

    def _center_window(self, parent):
        self.update_idletasks()
        w = 460
        h = 520
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        except Exception:
            px = 250
            py = 150
        self.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")
