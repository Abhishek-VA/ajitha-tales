"""
ui/styles.py
Centralised design-system: colours, fonts, and CustomTkinter theme configuration.
"""

import customtkinter as ctk

# ─── Colour tokens ────────────────────────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_darkest":   "#0D0D1A",
    "bg_dark":      "#12122A",
    "bg_medium":    "#1A1A3E",
    "bg_card":      "#1E1E40",
    "bg_input":     "#252550",
    "bg_sidebar":   "#16163A",

    # Accent / Brand
    "primary":      "#E94560",   # Rose-red
    "primary_dark": "#C73652",
    "primary_light":"#FF6B8A",
    "gold":         "#F5A623",
    "gold_light":   "#F7B944",

    # Status colours
    "status_pending":    "#F5A623",   # Gold/amber
    "status_inprogress": "#5B7FFF",   # Soft blue
    "status_ready":      "#00D4FF",   # Cyan
    "status_delivered":  "#2ECC71",   # Green
    "status_cancelled":  "#E74C3C",   # Red

    # Payment status
    "pay_unpaid":   "#E74C3C",
    "pay_partial":  "#F5A623",
    "pay_paid":     "#2ECC71",

    # Text
    "text_primary":   "#FFFFFF",
    "text_secondary": "#B0B0C8",
    "text_muted":     "#6E6E8E",
    "text_accent":    "#E94560",

    # Borders / dividers
    "border":     "#2A2A5A",
    "border_light":"#3A3A6E",

    # Table
    "table_header": "#1A1A2E",
    "table_row_alt":"#1C1C3A",
    "table_row_sel":"#2D1A2E",
    "table_fg":     "#D0D0E8",

    # Buttons
    "btn_primary":  "#E94560",
    "btn_success":  "#27AE60",
    "btn_warning":  "#F39C12",
    "btn_danger":   "#E74C3C",
    "btn_neutral":  "#2C2C5E",
}

# ─── Typography ───────────────────────────────────────────────────────────────
FONTS = {
    "heading_xl":  ("Segoe UI", 22, "bold"),
    "heading_lg":  ("Segoe UI", 16, "bold"),
    "heading_md":  ("Segoe UI", 13, "bold"),
    "heading_sm":  ("Segoe UI", 11, "bold"),
    "body_lg":     ("Segoe UI", 12),
    "body_md":     ("Segoe UI", 11),
    "body_sm":     ("Segoe UI", 10),
    "body_xs":     ("Segoe UI",  9),
    "mono":        ("Consolas", 10),
    "label":       ("Segoe UI",  9),
    "label_bold":  ("Segoe UI",  9, "bold"),
}

# ─── Status maps ──────────────────────────────────────────────────────────────
ORDER_STATUSES    = ["Pending", "In Progress", "Ready", "Delivered", "Cancelled"]
PAYMENT_STATUSES  = ["Unpaid", "Partial", "Paid"]
PAYMENT_MODES     = ["Cash", "UPI", "Card", "Cheque", "Bank Transfer"]
GARMENT_TYPES     = ["Blouse", "Kurti", "Salwar/Pants", "Churidar", "Gown", "Shirt", "Frock", "Custom"]

STATUS_COLORS = {
    "Pending":     (COLORS["status_pending"],    "#1A1000"),
    "In Progress": (COLORS["status_inprogress"], "#001030"),
    "Ready":       (COLORS["status_ready"],      "#001520"),
    "Delivered":   (COLORS["status_delivered"],  "#001A0A"),
    "Cancelled":   (COLORS["status_cancelled"],  "#1A0000"),
}

PAY_COLORS = {
    "Unpaid":  COLORS["pay_unpaid"],
    "Partial": COLORS["pay_partial"],
    "Paid":    COLORS["pay_paid"],
}


def apply_theme():
    """Configure CustomTkinter appearance."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def configure_ttk_treeview_style(style_obj):
    """
    Apply dark theme styling to the ttk.Treeview used in the dashboard.
    style_obj is a ttk.Style instance.
    """
    bg      = COLORS["bg_dark"]
    card    = COLORS["bg_card"]
    fg      = COLORS["text_primary"]
    fg2     = COLORS["table_fg"]
    border  = COLORS["border"]
    hdr_bg  = COLORS["table_header"]
    sel_bg  = COLORS["primary"]
    alt_bg  = COLORS["table_row_alt"]

    style_obj.theme_use("clam")

    style_obj.configure("Dark.Treeview",
        background=card,
        foreground=fg2,
        fieldbackground=card,
        bordercolor=border,
        lightcolor=border,
        darkcolor=border,
        rowheight=34,
        font=("Segoe UI", 10),
    )
    style_obj.configure("Dark.Treeview.Heading",
        background=hdr_bg,
        foreground=fg,
        bordercolor=border,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
    )
    style_obj.map("Dark.Treeview",
        background=[("selected", sel_bg)],
        foreground=[("selected", "#FFFFFF")],
    )
    style_obj.map("Dark.Treeview.Heading",
        background=[("active", COLORS["primary_dark"])],
    )

    # Scrollbar styling
    style_obj.configure("Dark.Vertical.TScrollbar",
        background=COLORS["bg_medium"],
        troughcolor=COLORS["bg_dark"],
        bordercolor=border,
        arrowcolor=COLORS["text_secondary"],
        width=10,
    )
    style_obj.configure("Dark.Horizontal.TScrollbar",
        background=COLORS["bg_medium"],
        troughcolor=COLORS["bg_dark"],
        bordercolor=border,
        arrowcolor=COLORS["text_secondary"],
        width=10,
    )
