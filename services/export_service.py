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


def export_daily_ledger_excel(ledger_data: Dict) -> str:
    """
    Export comprehensive Daily Cashflow & Ledger (Inflows, Expenses, Drawer Cash) to Excel.
    """
    d_str = ledger_data.get("date", date.today().isoformat())
    exports_dir = _get_exports_dir()

    if not HAS_OPENPYXL:
        # Fallback to CSV
        csv_path = _unique_path(exports_dir, f"AjithaTailors_Ledger_{d_str}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["AJITHA TAILORS - DAILY CASHFLOW LEDGER", d_str])
            writer.writerow([])
            writer.writerow(["Cash In (Collections)", ledger_data.get("cash_in", 0)])
            writer.writerow(["Cash Out (Expenses)", ledger_data.get("cash_expenses", 0)])
            writer.writerow(["NET CASH IN DRAWER", ledger_data.get("cash_in_hand", 0)])
            writer.writerow(["UPI / Online In", ledger_data.get("upi_in", 0)])
            writer.writerow(["Total Inflows", ledger_data.get("total_inflow", 0)])
            writer.writerow(["Total Expenses", ledger_data.get("total_expenses", 0)])
            writer.writerow(["NET CASHFLOW", ledger_data.get("net_cashflow", 0)])
            writer.writerow([])
            writer.writerow(["--- INFLOWS ---"])
            writer.writerow(["Order ID", "Time", "Customer", "Mobile", "Type", "Mode", "Amount", "Notes"])
            for tx in ledger_data.get("inflows", []):
                writer.writerow([
                    tx.get("order_id", ""),
                    tx.get("created_at", "")[11:16] if tx.get("created_at") else "",
                    tx.get("customer_name", ""),
                    tx.get("mobile", ""),
                    tx.get("transaction_type", "").title(),
                    tx.get("payment_mode", ""),
                    tx.get("amount", 0),
                    tx.get("notes", ""),
                ])
            writer.writerow([])
            writer.writerow(["--- SHOP EXPENSES ---"])
            writer.writerow(["ID", "Time", "Category", "Mode", "Amount", "Notes"])
            for exp in ledger_data.get("expenses", []):
                writer.writerow([
                    exp.get("id", ""),
                    exp.get("created_at", "")[11:16] if exp.get("created_at") else "",
                    exp.get("category", ""),
                    exp.get("payment_mode", ""),
                    exp.get("amount", 0),
                    exp.get("notes", ""),
                ])
        return csv_path

    filename = f"AjithaTailors_Ledger_{d_str}.xlsx"
    path = _unique_path(exports_dir, filename)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Ledger_{d_str}"
    ws.views.sheetView[0].showGridLines = True

    thin = Side(border_style="thin", color="CCCCCC")
    border = Border(top=thin, left=thin, right=thin, bottom=thin)

    title_fill = PatternFill(start_color="1A1A2E", end_color="1A1A2E", fill_type="solid")
    kpi_hdr_fill = PatternFill(start_color="2A2A5A", end_color="2A2A5A", fill_type="solid")
    inflow_hdr_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
    expense_hdr_fill = PatternFill(start_color="B71C1C", end_color="B71C1C", fill_type="solid")
    summary_fill = PatternFill(start_color="FFF8E7", end_color="FFF8E7", fill_type="solid")

    # Banner
    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value = f"AJITHA TAILORS  |  DAILY CASHFLOW & DAY-BOOK LEDGER  |  {d_str}"
    title_cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    title_cell.fill = title_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # KPI summary block
    kpis = [
        ("💵 Cash in Drawer (In-Hand):", ledger_data.get("cash_in_hand", 0.0), "007A3D"),
        ("📱 UPI / Online Collections:", ledger_data.get("upi_in", 0.0), "0D47A1"),
        ("💸 Total Daily Expenses:", ledger_data.get("total_expenses", 0.0), "C62828"),
        ("📈 Net Daily Cashflow:", ledger_data.get("net_cashflow", 0.0), "E94560"),
    ]
    for idx, (label, val, col_hex) in enumerate(kpis, start=3):
        ws.cell(row=idx, column=1, value=label).font = Font(name="Calibri", size=10, bold=True)
        c_val = ws.cell(row=idx, column=2, value=float(val))
        c_val.font = Font(name="Calibri", size=11, bold=True, color=col_hex)
        c_val.number_format = '#,##0.00'
        c_val.fill = summary_fill
        ws.cell(row=idx, column=1).border = border
        c_val.border = border

    row_cur = 8

    # ── Section 1: Customer Inflows ──────────────────────────────────────────
    ws.cell(row=row_cur, column=1, value="📥 CUSTOMER INFLOWS (ADVANCES & BALANCE SETTLEMENTS)").font = Font(name="Calibri", size=11, bold=True, color="1B5E20")
    row_cur += 1

    inflow_headers = ["Time", "Order #", "Customer Name", "Mobile", "Payment Type", "Mode", "Amount (Rs.)", "Notes"]
    for col_i, h in enumerate(inflow_headers, start=1):
        c = ws.cell(row=row_cur, column=col_i, value=h)
        c.font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
        c.fill = inflow_hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border
    row_cur += 1

    inflows = ledger_data.get("inflows", [])
    if inflows:
        for tx in inflows:
            t_str = tx.get("created_at", "")[11:16] if tx.get("created_at") else ""
            vals = [
                t_str,
                f"#{tx.get('order_id', '')}",
                tx.get("customer_name", ""),
                tx.get("mobile", ""),
                tx.get("transaction_type", "").replace("_", " ").title(),
                tx.get("payment_mode", ""),
                float(tx.get("amount", 0.0)),
                tx.get("notes", ""),
            ]
            for col_i, val in enumerate(vals, start=1):
                c = ws.cell(row=row_cur, column=col_i, value=val)
                c.font = Font(name="Calibri", size=9)
                c.border = border
                if col_i == 7:
                    c.number_format = '#,##0.00'
                    c.font = Font(name="Calibri", size=9, bold=True, color="1B5E20")
            row_cur += 1
    else:
        c = ws.cell(row=row_cur, column=1, value="No customer inflows recorded for this date.")
        c.font = Font(name="Calibri", size=9, italic=True, color="777777")
        row_cur += 1

    # Inflow Total
    ws.cell(row=row_cur, column=6, value="Total Inflows:").font = Font(name="Calibri", size=10, bold=True)
    c_tot_in = ws.cell(row=row_cur, column=7, value=float(ledger_data.get("total_inflow", 0.0)))
    c_tot_in.font = Font(name="Calibri", size=10, bold=True, color="1B5E20")
    c_tot_in.number_format = '#,##0.00'
    c_tot_in.border = border
    row_cur += 2

    # ── Section 2: Shop Expenses ─────────────────────────────────────────────
    ws.cell(row=row_cur, column=1, value="💸 SHOP EXPENSES & PAYOUTS").font = Font(name="Calibri", size=11, bold=True, color="B71C1C")
    row_cur += 1

    exp_headers = ["Time", "ID", "Expense Category", "Payment Mode", "Amount (Rs.)", "Narration / Notes"]
    for col_i, h in enumerate(exp_headers, start=1):
        c = ws.cell(row=row_cur, column=col_i, value=h)
        c.font = Font(name="Calibri", size=9, bold=True, color="FFFFFF")
        c.fill = expense_hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border
    row_cur += 1

    expenses = ledger_data.get("expenses", [])
    if expenses:
        for exp in expenses:
            t_str = exp.get("created_at", "")[11:16] if exp.get("created_at") else ""
            vals = [
                t_str,
                f"EXP-{exp.get('id', '')}",
                exp.get("category", ""),
                exp.get("payment_mode", ""),
                float(exp.get("amount", 0.0)),
                exp.get("notes", ""),
            ]
            for col_i, val in enumerate(vals, start=1):
                c = ws.cell(row=row_cur, column=col_i, value=val)
                c.font = Font(name="Calibri", size=9)
                c.border = border
                if col_i == 5:
                    c.number_format = '#,##0.00'
                    c.font = Font(name="Calibri", size=9, bold=True, color="B71C1C")
            row_cur += 1
    else:
        c = ws.cell(row=row_cur, column=1, value="No shop expenses recorded for this date.")
        c.font = Font(name="Calibri", size=9, italic=True, color="777777")
        row_cur += 1

    # Expense Total
    ws.cell(row=row_cur, column=4, value="Total Expenses:").font = Font(name="Calibri", size=10, bold=True)
    c_tot_exp = ws.cell(row=row_cur, column=5, value=float(ledger_data.get("total_expenses", 0.0)))
    c_tot_exp.font = Font(name="Calibri", size=10, bold=True, color="B71C1C")
    c_tot_exp.number_format = '#,##0.00'
    c_tot_exp.border = border

    # Set column widths
    col_widths = [12, 12, 22, 16, 18, 14, 16, 26]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

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
