"""
ui/components/calendar_picker.py
Interactive calendar modal dialog with dark theme styling and tailor quick-presets.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from datetime import date, datetime, timedelta
from typing import Optional, Callable
from tkcalendar import Calendar

from ui.styles import COLORS, FONTS


class CalendarPickerModal(ctk.CTkToplevel):
    """
    Modern popup calendar for quick and error-free date selection.
    Includes quick-preset buttons tailored for shop booking/delivery workflows.
    """

    def __init__(
        self,
        parent,
        title: str = "Select Date",
        initial_date: Optional[str] = None,
        callback: Optional[Callable[[str], None]] = None,
        is_delivery: bool = False,
    ):
        super().__init__(parent)
        self.callback = callback
        self.is_delivery = is_delivery
        self._selected_date: Optional[str] = None

        self.title(title)
        self.configure(fg_color=COLORS["bg_card"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Parse initial date or default to today
        init_dt = date.today()
        if initial_date:
            try:
                init_dt = datetime.strptime(initial_date.strip(), "%Y-%m-%d").date()
            except Exception:
                init_dt = date.today()

        self._build_ui(init_dt, title)
        self._center_window(parent)

        self.bind("<Escape>", lambda _: self.destroy())

    def _build_ui(self, init_dt: date, title_text: str):
        C, F = COLORS, FONTS

        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text=f"  📅  {title_text}",
            font=F["heading_sm"],
            text_color=C["gold"],
        ).pack(side="left", padx=14, pady=8)

        close_btn = ctk.CTkButton(
            hdr, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=C["primary"],
            text_color=C["text_secondary"], font=("Segoe UI", 11, "bold"),
            command=self.destroy,
        )
        close_btn.pack(side="right", padx=10)

        # Main Calendar Container
        cal_frame = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
        cal_frame.pack(padx=16, pady=12)

        self._cal = Calendar(
            cal_frame,
            selectmode="day",
            year=init_dt.year,
            month=init_dt.month,
            day=init_dt.day,
            date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 10),
            background=C["bg_card"],
            foreground=C["text_primary"],
            headersbackground=C["bg_medium"],
            headersforeground=C["gold"],
            selectbackground=C["primary"],
            selectforeground="#FFFFFF",
            normalbackground=C["bg_input"],
            normalforeground=C["text_primary"],
            weekendbackground=C["bg_dark"],
            weekendforeground=C["primary_light"],
            othermonthforeground=C["text_muted"],
            othermonthbackground=C["bg_darkest"],
            bordercolor=C["border"],
            showweeknumbers=False,
        )
        self._cal.pack(padx=6, pady=6)
        self._cal.bind("<<CalendarSelected>>", self._on_date_click)
        self._cal.bind("<Double-1>", lambda _: self._confirm())

        # Quick preset buttons
        presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        presets_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            presets_frame,
            text="Quick Presets:",
            font=F["label_bold"],
            text_color=C["text_muted"],
        ).pack(anchor="w", pady=(0, 4))

        p_row = ctk.CTkFrame(presets_frame, fg_color="transparent")
        p_row.pack(fill="x")

        today = date.today()
        presets = [("Today", 0)]
        if self.is_delivery:
            presets.extend([
                ("+3 Days", 3),
                ("+5 Days", 5),
                ("+7 Days (1 Wk)", 7),
                ("+10 Days", 10),
                ("+15 Days", 15),
            ])
        else:
            presets.extend([
                ("Yesterday", -1),
                ("Tomorrow", 1),
            ])

        for label, offset in presets:
            target_date = today + timedelta(days=offset)
            btn = ctk.CTkButton(
                p_row,
                text=label,
                font=F["body_xs"],
                height=26,
                fg_color=C["bg_input"],
                hover_color=C["primary_dark"],
                text_color=C["text_secondary"],
                corner_radius=5,
                command=lambda d=target_date: self._select_preset(d),
            )
            btn.pack(side="left", padx=3, pady=2)

        # Selected Date Label + Action Buttons
        bot_frame = ctk.CTkFrame(self, fg_color=C["bg_medium"], height=48, corner_radius=0)
        bot_frame.pack(fill="x", side="bottom")

        self._preview_lbl = ctk.CTkLabel(
            bot_frame,
            text=f"Selected: {self._cal.get_date()}",
            font=F["body_sm"],
            text_color=C["gold"],
        )
        self._preview_lbl.pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            bot_frame,
            text="✓ Confirm Date",
            font=F["body_sm"],
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            width=110,
            height=30,
            command=self._confirm,
            corner_radius=6,
        ).pack(side="right", padx=14, pady=10)

        ctk.CTkButton(
            bot_frame,
            text="Cancel",
            font=F["body_sm"],
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_muted"],
            width=70,
            height=30,
            command=self.destroy,
            corner_radius=6,
        ).pack(side="right", padx=4, pady=10)

    def _select_preset(self, d: date):
        self._cal.selection_set(d)
        self._on_date_click()

    def _on_date_click(self, *_):
        val = self._cal.get_date()
        self._preview_lbl.configure(text=f"Selected: {val}")

    def _confirm(self):
        val = self._cal.get_date()
        self._selected_date = val
        if self.callback:
            self.callback(val)
        self.destroy()

    def _center_window(self, parent):
        self.update_idletasks()
        w = 340
        h = 420
        # Position near parent centre or cursor
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        except Exception:
            px = 200
            py = 200
        self.geometry(f"{w}x{h}+{max(0, px)}+{max(0, py)}")
