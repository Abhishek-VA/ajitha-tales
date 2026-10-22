"""
ui/app.py
Main application window: navigation, layout, theme, and component wiring.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

from ui.styles import COLORS, FONTS, apply_theme
from ui.components.order_entry import OrderEntryPanel
from ui.components.dashboard import DashboardPanel
from database import db_manager


class AjithaTailorsApp(ctk.CTk):
    """
    Root application window.
    Implements a split-pane layout:
      Left  (40%): Order Entry / Edit
      Right (60%): Dashboard / Table
    """

    APP_TITLE   = "Ajitha Tailors — Billing & Order ERP"
    MIN_WIDTH   = 1200
    MIN_HEIGHT  = 750

    def __init__(self):
        apply_theme()
        super().__init__()

        self._configure_window()
        self._build_header()
        self._build_main_layout()
        self._wire_components()
        self._start_clock()

    # ─────────────────────────────────────────────────────────────────────────
    # Window configuration
    # ─────────────────────────────────────────────────────────────────────────

    def _configure_window(self):
        self.title(self.APP_TITLE)
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.configure(fg_color=COLORS["bg_darkest"])

        # Centre window on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(1440, sw - 80)
        h  = min(900, sh - 80)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.state("zoomed")   # Maximise on Windows

        # Window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico")
        if getattr(sys, "frozen", False):
            icon_path = os.path.join(os.path.dirname(sys.executable), "assets", "icon.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # Header / top navigation bar
    # ─────────────────────────────────────────────────────────────────────────

    def _build_header(self):
        C, F = COLORS, FONTS

        header = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Left: branding
        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", padx=18, pady=10)

        ctk.CTkLabel(
            brand_frame,
            text="✂️  AJITHA TAILORS",
            font=("Segoe UI", 18, "bold"),
            text_color=C["primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            brand_frame,
            text=" — Billing & Order ERP",
            font=F["body_md"],
            text_color=C["text_muted"],
        ).pack(side="left", pady=4)

        # Right: clock + date
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=18)

        self._clock_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=F["heading_sm"],
            text_color=C["gold"],
        )
        self._clock_label.pack(anchor="e")

        self._date_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=F["label"],
            text_color=C["text_muted"],
        )
        self._date_label.pack(anchor="e")

        # Centre: quick-action buttons
        centre_frame = ctk.CTkFrame(header, fg_color="transparent")
        centre_frame.pack(side="left", padx=20, expand=True)

        ctk.CTkButton(
            centre_frame,
            text="  ➕  New Order",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["body_md"],
            height=36,
            width=130,
            command=self._new_order,
            corner_radius=8,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            centre_frame,
            text="  ↺  Refresh",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_md"],
            height=36,
            width=110,
            command=self._refresh_all,
            corner_radius=8,
        ).pack(side="left", padx=5)

        # Divider
        ctk.CTkFrame(self, fg_color=C["primary"], height=2).pack(fill="x")

    # ─────────────────────────────────────────────────────────────────────────
    # Main split-pane layout
    # ─────────────────────────────────────────────────────────────────────────

    def _build_main_layout(self):
        C = COLORS

        # Outer container
        self._main_pane = ctk.CTkFrame(self, fg_color="transparent")
        self._main_pane.pack(fill="both", expand=True)
        self._main_pane.grid_columnconfigure(0, weight=40)
        self._main_pane.grid_columnconfigure(1, weight=60)
        self._main_pane.grid_rowconfigure(0, weight=1)

        # ── Left pane — Order Entry ──────────────────────────────────────────
        left_outer = ctk.CTkFrame(
            self._main_pane,
            fg_color=C["bg_dark"],
            corner_radius=0,
        )
        left_outer.grid(row=0, column=0, sticky="nsew")

        # Left pane title bar
        left_title = ctk.CTkFrame(left_outer, fg_color=C["bg_sidebar"], corner_radius=0, height=40)
        left_title.pack(fill="x")
        left_title.pack_propagate(False)
        ctk.CTkLabel(
            left_title,
            text="  📝  Order Entry",
            font=FONTS["heading_sm"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=14, pady=10)

        self._order_entry = OrderEntryPanel(
            left_outer,
            on_order_saved=self._on_order_saved,
        )
        self._order_entry.pack(fill="both", expand=True)

        # Thin vertical separator
        ctk.CTkFrame(self._main_pane, fg_color=C["border"], width=2).grid(
            row=0, column=0, sticky="nse"
        )

        # ── Right pane — Dashboard ───────────────────────────────────────────
        right_outer = ctk.CTkFrame(
            self._main_pane,
            fg_color=C["bg_darkest"],
            corner_radius=0,
        )
        right_outer.grid(row=0, column=1, sticky="nsew")

        # Right pane title bar
        right_title = ctk.CTkFrame(right_outer, fg_color=C["bg_sidebar"], corner_radius=0, height=40)
        right_title.pack(fill="x")
        right_title.pack_propagate(False)
        ctk.CTkLabel(
            right_title,
            text="  📊  Order Dashboard",
            font=FONTS["heading_sm"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=14, pady=10)

        self._dashboard = DashboardPanel(
            right_outer,
            on_edit_order=self._on_edit_order,
        )
        self._dashboard.pack(fill="both", expand=True)

        # ── Status bar ───────────────────────────────────────────────────────
        status_bar = ctk.CTkFrame(self, fg_color=C["bg_sidebar"], corner_radius=0, height=26)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        self._status_label = ctk.CTkLabel(
            status_bar,
            text="  ✓  Ready",
            font=FONTS["label"],
            text_color=COLORS["status_delivered"],
        )
        self._status_label.pack(side="left", padx=12)

        ctk.CTkLabel(
            status_bar,
            text="Ajitha Tailors ERP v1.0  |  SQLite  |  Offline-First",
            font=FONTS["label"],
            text_color=COLORS["text_muted"],
        ).pack(side="right", padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    # Component wiring & event handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _wire_components(self):
        """No additional wiring needed — callbacks already passed in constructors."""
        pass

    def _on_order_saved(self, order_id: int):
        """Called when the order entry panel saves/updates an order."""
        self._dashboard.refresh()
        self._set_status(f"  ✓  Order #{order_id} saved successfully")

    def _on_edit_order(self, order_id: int):
        """Called when dashboard requests an order to be loaded for editing."""
        self._order_entry.load_order_for_edit(order_id)
        self._set_status(f"  ✏️  Editing Order #{order_id}")

    def _new_order(self):
        self._order_entry.reset_form()
        self._set_status("  ✂️  New order form ready")

    def _refresh_all(self):
        self._dashboard.refresh()
        self._set_status("  ↺  Dashboard refreshed")

    def _set_status(self, text: str):
        self._status_label.configure(text=text)
        # Reset after 5 seconds
        self.after(5000, lambda: self._status_label.configure(text="  ✓  Ready"))

    # ─────────────────────────────────────────────────────────────────────────
    # Clock
    # ─────────────────────────────────────────────────────────────────────────

    def _start_clock(self):
        self._update_clock()

    def _update_clock(self):
        now = datetime.now()
        self._clock_label.configure(text=now.strftime("%I:%M:%S %p"))
        self._date_label.configure(text=now.strftime("%A, %d %B %Y"))
        self.after(1000, self._update_clock)

    # ─────────────────────────────────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────────────────────────────────

    def _on_close(self):
        if messagebox.askyesno(
            "Exit",
            "Exit Ajitha Tailors ERP?",
            parent=self,
        ):
            db_manager.close_connection()
            self.destroy()
