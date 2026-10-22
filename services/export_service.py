"""
services/export_service.py
CSV and Excel export for Ajitha Tailors daily accounts.
"""

import os
import csv
import json
from datetime import datetime, date
from typing import List, Dict, Optional

try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def _get_exports_dir() -> str:
    import sys
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _unique_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return candidate


EXPORT_HEADERS = [
    "Order ID", "Customer Name", "Mobile",
    "Booking Date", "Delivery Date",
    "Total Amount", "Advance", "Balance",
    "Payment Status", "Order Status",
    "Payment Mode", "Notes",
]


def _row_from_order(order: Dict) -> List:
    return [
        order.get("order_id", ""),
        order.get("name", order.get("customer_name", "")),
        order.get("mobile", ""),
        order.get("booking_date", ""),
        order.get("collection_date", ""),
        order.get("total_amount", 0.0),
        order.get("advance_amount", 0.0),
        order.get("balance_amount", 0.0),
        order.get("payment_status", ""),
        order.get("order_status", ""),
        order.get("payment_mode", ""),
        order.get("notes", ""),
    ]


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(orders: List[Dict], start_date: str, end_date: str) -> str:
    """Export orders to CSV. Returns the file path."""
    exp_dir = _get_exports_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"AjithaTailors_Orders_{start_date}_to_{end_date}_{ts}.csv"
    path = _unique_path(exp_dir, filename)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(EXPORT_HEADERS)
        for order in orders:
            writer.writerow(_row_from_order(order))

    return path


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def export_excel(orders: List[Dict], start_date: str, end_date: str) -> Optional[str]:
    """Export orders to Excel with formatting. Returns file path or None."""
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl is not installed. Run: pip install openpyxl")

    exp_dir = _get_exports_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"AjithaTailors_Orders_{start_date}_to_{end_date}_{ts}.xlsx"
    path = _unique_path(exp_dir, filename)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"

    # ── Colour scheme ──────────────────────────────────────────────────
    HDR_FILL   = PatternFill("solid", fgColor="1A1A2E")
    TOTAL_FILL = PatternFill("solid", fgColor="FFF0F3")
    ALT_FILL   = PatternFill("solid", fgColor="F9F0F3")

    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── Title row ──────────────────────────────────────────────────────
    ws.merge_cells("A1:L1")
    title_cell = ws["A1"]
    title_cell.value = f"AJITHA TAILORS – Order Report ({start_date} to {end_date})"
    title_cell.font = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1A1A2E")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:L2")
    gen_cell = ws["A2"]
    gen_cell.value = f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    gen_cell.font = Font(name="Calibri", italic=True, size=9, color="666666")
    gen_cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 18

    # ── Header row ─────────────────────────────────────────────────────
    for col_idx, header in enumerate(EXPORT_HEADERS, start=1):
        cell = ws.cell(row=3, column=col_idx, value=header)
        cell.font = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
        cell.fill = HDR_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    ws.row_dimensions[3].height = 22

    # ── Data rows ──────────────────────────────────────────────────────
    for row_idx, order in enumerate(orders, start=4):
        row_data = _row_from_order(order)
        fill = ALT_FILL if row_idx % 2 == 0 else PatternFill()
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=9)
            cell.border = border
            cell.fill = fill
            if col_idx in (6, 7, 8):  # currency columns
                cell.number_format = '#,##0.00'
            if col_idx in (10, 11):   # status columns — colour coding
                status = str(val)
                if status == "Delivered":
                    cell.font = Font(name="Calibri", size=9, color="1A7A3C", bold=True)
                elif status in ("Pending", "In Progress"):
                    cell.font = Font(name="Calibri", size=9, color="B8860B", bold=True)
                elif status == "Ready":
                    cell.font = Font(name="Calibri", size=9, color="0056B3", bold=True)
                elif status == "Cancelled":
                    cell.font = Font(name="Calibri", size=9, color="CC0000", bold=True)

    # ── Totals row ─────────────────────────────────────────────────────
    if orders:
        total_row = len(orders) + 4
        ws.cell(row=total_row, column=5, value="TOTALS").font = Font(bold=True, name="Calibri", size=10)
        for col, field in zip([6, 7, 8], ["total_amount", "advance_amount", "balance_amount"]):
            total = sum(float(o.get(field, 0) or 0) for o in orders)
            cell = ws.cell(row=total_row, column=col, value=total)
            cell.font = Font(bold=True, name="Calibri", size=10, color="E94560")
            cell.fill = TOTAL_FILL
            cell.number_format = '#,##0.00'
            cell.border = border

    # ── Column widths ──────────────────────────────────────────────────
    col_widths = [10, 22, 15, 14, 14, 14, 12, 12, 16, 14, 14, 30]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── Freeze panes ──────────────────────────────────────────────────
    ws.freeze_panes = "A4"

    wb.save(path)
    return path


def open_file(path: str):
    """Open the exported file with the default application."""
    import subprocess, sys
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"[export_service] Could not open file: {e}")
