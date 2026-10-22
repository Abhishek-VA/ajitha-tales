"""
ui/components/measurement_modal.py
Dynamic measurement popup that renders garment-specific measurement fields.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Dict, Callable, Optional
from ui.styles import COLORS, FONTS


# ── Garment measurement field definitions ──────────────────────────────────────
MEASUREMENT_FIELDS: Dict[str, list] = {
    "Blouse": [
        ("Length",        "cm"),
        ("Bust/Chest",    "cm"),
        ("Waist",         "cm"),
        ("Shoulder",      "cm"),
        ("Sleeve Length", "cm"),
        ("Sleeve Round",  "cm"),
        ("Front Neck",    "cm"),
        ("Back Neck",     "cm"),
        ("Armhole",       "cm"),
        ("Hip",           "cm"),
    ],
    "Kurti": [
        ("Length",        "cm"),
        ("Bust",          "cm"),
        ("Waist",         "cm"),
        ("Hip",           "cm"),
        ("Shoulder",      "cm"),
        ("Sleeve Length", "cm"),
        ("Sleeve Round",  "cm"),
        ("Front Neck",    "cm"),
        ("Back Neck",     "cm"),
        ("Slit",          "cm"),
    ],
    "Salwar/Pants": [
        ("Length",        "cm"),
        ("Waist",         "cm"),
        ("Hip",           "cm"),
        ("Thigh",         "cm"),
        ("Inseam",        "cm"),
        ("Bottom/Ankle",  "cm"),
        ("Seat",          "cm"),
    ],
    "Churidar": [
        ("Length",        "cm"),
        ("Waist",         "cm"),
        ("Hip",           "cm"),
        ("Thigh",         "cm"),
        ("Inseam",        "cm"),
        ("Ankle",         "cm"),
    ],
    "Gown": [
        ("Total Length",  "cm"),
        ("Bust",          "cm"),
        ("Waist",         "cm"),
        ("Hip",           "cm"),
        ("Shoulder",      "cm"),
        ("Sleeve Length", "cm"),
        ("Sleeve Round",  "cm"),
        ("Front Neck",    "cm"),
        ("Back Neck",     "cm"),
        ("Train",         "cm"),
    ],
    "Shirt": [
        ("Length",        "cm"),
        ("Chest",         "cm"),
        ("Waist",         "cm"),
        ("Shoulder",      "cm"),
        ("Sleeve Length", "cm"),
        ("Sleeve Round",  "cm"),
        ("Collar",        "cm"),
        ("Cuff",          "cm"),
    ],
    "Frock": [
        ("Total Length",  "cm"),
        ("Chest",         "cm"),
        ("Waist",         "cm"),
        ("Hip",           "cm"),
        ("Shoulder",      "cm"),
        ("Sleeve Length", "cm"),
        ("Armhole",       "cm"),
    ],
    "Custom": [
        ("Measurement 1", ""),
        ("Measurement 2", ""),
        ("Measurement 3", ""),
        ("Measurement 4", ""),
        ("Measurement 5", ""),
        ("Measurement 6", ""),
        ("Measurement 7", ""),
        ("Measurement 8", ""),
    ],
}


class MeasurementModal(ctk.CTkToplevel):
    """
    A modal dialog that shows measurement input fields based on garment type.
    On confirmation, calls the provided callback with the measurements dict.
    """

    def __init__(
        self,
        parent,
        garment_type: str,
        existing_measurements: Optional[Dict] = None,
        existing_design: str = "",
        callback: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self.garment_type = garment_type
        self.callback = callback
        self.result: Optional[Dict] = None

        # Window configuration
        self.title(f"📐 Measurements — {garment_type}")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        self.grab_set()            # Modal behaviour
        self.focus_force()

        # Centre on parent
        self.update_idletasks()
        pw = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw_w = parent.winfo_width()
        pw_h = parent.winfo_height()
        w, h = 540, 620
        x = pw + (pw_w - w) // 2
        y = py + (pw_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui(existing_measurements or {}, existing_design)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, existing: Dict, existing_design: str):
        C = COLORS
        F = FONTS

        # ── Title bar ─────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=56)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        icon_map = {
            "Blouse": "👗", "Kurti": "👘", "Salwar/Pants": "👖",
            "Churidar": "👗", "Gown": "🌟", "Shirt": "👔",
            "Frock": "🌸", "Custom": "✂️",
        }
        icon = icon_map.get(self.garment_type, "✂️")
        ctk.CTkLabel(
            title_frame,
            text=f"  {icon}  {self.garment_type} Measurements",
            font=F["heading_md"],
            text_color=C["text_primary"],
        ).pack(side="left", padx=16, pady=12)

        ctk.CTkLabel(
            title_frame,
            text="All values in cm unless noted",
            font=F["body_xs"],
            text_color=C["text_muted"],
        ).pack(side="right", padx=16)

        # ── Scrollable content ────────────────────────────────────────
        scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=C["bg_dark"],
            scrollbar_button_color=C["primary"],
            scrollbar_button_hover_color=C["primary_dark"],
        )
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Measurement fields
        fields = MEASUREMENT_FIELDS.get(self.garment_type, MEASUREMENT_FIELDS["Custom"])
        self._entries: Dict[str, ctk.CTkEntry] = {}

        # Two-column grid layout for fields
        meas_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        meas_frame.pack(fill="x", padx=16, pady=12)

        for idx, (field_name, unit) in enumerate(fields):
            col = idx % 2
            row = idx // 2

            cell = ctk.CTkFrame(meas_frame, fg_color=C["bg_card"], corner_radius=8)
            cell.grid(row=row, column=col, padx=6, pady=5, sticky="ew")
            meas_frame.grid_columnconfigure(col, weight=1)

            label_text = f"{field_name}" + (f" ({unit})" if unit else "")
            ctk.CTkLabel(
                cell,
                text=label_text,
                font=F["label_bold"],
                text_color=C["text_secondary"],
            ).pack(anchor="w", padx=10, pady=(8, 2))

            entry = ctk.CTkEntry(
                cell,
                height=34,
                fg_color=C["bg_input"],
                border_color=C["border"],
                text_color=C["text_primary"],
                font=F["body_md"],
                placeholder_text="—",
            )
            entry.pack(fill="x", padx=10, pady=(0, 8))

            # Pre-fill if editing
            prev_val = existing.get(field_name, "")
            if prev_val:
                entry.insert(0, str(prev_val))

            self._entries[field_name] = entry

        # ── Design Instructions ────────────────────────────────────────
        design_frame = ctk.CTkFrame(scroll_frame, fg_color=C["bg_card"], corner_radius=8)
        design_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            design_frame,
            text="✦  Design & Style Instructions",
            font=F["heading_sm"],
            text_color=C["gold"],
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            design_frame,
            text="Neck pattern, lining, piping, sleeve style, embroidery, etc.",
            font=F["label"],
            text_color=C["text_muted"],
        ).pack(anchor="w", padx=12, pady=(0, 4))

        self._design_text = ctk.CTkTextbox(
            design_frame,
            height=80,
            fg_color=C["bg_input"],
            border_color=C["border"],
            text_color=C["text_primary"],
            font=F["body_sm"],
            corner_radius=6,
        )
        self._design_text.pack(fill="x", padx=12, pady=(0, 12))
        if existing_design:
            self._design_text.insert("0.0", existing_design)

        # ── Button row ────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color=C["bg_medium"], corner_radius=0, height=60)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        ctk.CTkButton(
            btn_frame,
            text="  ✕  Cancel",
            fg_color=C["btn_neutral"],
            hover_color=C["border_light"],
            text_color=C["text_secondary"],
            font=F["body_md"],
            width=120,
            height=38,
            command=self._on_cancel,
            corner_radius=8,
        ).pack(side="left", padx=16, pady=11)

        ctk.CTkButton(
            btn_frame,
            text="  ✓  Save Measurements",
            fg_color=C["primary"],
            hover_color=C["primary_dark"],
            text_color="#FFFFFF",
            font=F["heading_sm"],
            width=200,
            height=38,
            command=self._on_save,
            corner_radius=8,
        ).pack(side="right", padx=16, pady=11)

        # Quick-clear button
        ctk.CTkButton(
            btn_frame,
            text="Clear All",
            fg_color="transparent",
            hover_color=C["bg_card"],
            text_color=C["text_muted"],
            font=F["body_xs"],
            width=80,
            height=38,
            command=self._clear_all,
            corner_radius=8,
        ).pack(side="right", padx=4, pady=11)

    def _clear_all(self):
        for entry in self._entries.values():
            entry.delete(0, "end")
        self._design_text.delete("0.0", "end")

    def _on_save(self):
        measurements = {}
        for field_name, entry in self._entries.items():
            val = entry.get().strip()
            if val:
                measurements[field_name] = val

        design = self._design_text.get("0.0", "end").strip()
        self.result = {"measurements": measurements, "design_instructions": design}

        if self.callback:
            self.callback(self.result)
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
