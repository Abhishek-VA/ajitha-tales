"""
services/pdf_service.py
Professional PDF invoice generator for Ajitha Tailors using ReportLab.
Produces fully-itemized, non-overwriting invoices with auto-open capability.
"""

import os
import re
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.pdfgen import canvas


# ---------------------------------------------------------------------------
# Colour palette (Ajitha Tailors brand)
# ---------------------------------------------------------------------------
BRAND_DARK    = colors.HexColor("#1A1A2E")   # Deep navy
BRAND_PRIMARY = colors.HexColor("#E94560")   # Rose-red accent
BRAND_LIGHT   = colors.HexColor("#16213E")   # Slightly lighter navy
BRAND_GOLD    = colors.HexColor("#F5A623")   # Gold accent
GRAY_DARK     = colors.HexColor("#333333")
GRAY_MID      = colors.HexColor("#666666")
GRAY_LIGHT    = colors.HexColor("#CCCCCC")
TABLE_HEADER  = colors.HexColor("#1A1A2E")
TABLE_ALT     = colors.HexColor("#F9F0F3")   # Very light rose for alternate rows
WHITE         = colors.white
BLACK         = colors.black


def _get_invoices_dir() -> str:
    """Return the invoices/ directory, creating it if necessary."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "invoices")
    os.makedirs(path, exist_ok=True)
    return path


def _sanitize(text: str) -> str:
    """Remove non-alphanumeric characters and collapse spaces to underscores."""
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:40]


def _unique_path(directory: str, filename: str) -> str:
    """
    Return a collision-free file path.
    If the file already exists, append _v2, _v3, … until unique.
    """
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}_v{counter}{ext}")
        counter += 1
    return candidate


def _fmt_currency(value: float) -> str:
    return f"\u20B9 {value:,.2f}"


def _measurements_summary(measurements_json: str) -> str:
    """Convert measurements JSON to a compact human-readable string."""
    try:
        data = json.loads(measurements_json) if isinstance(measurements_json, str) else measurements_json
        parts = []
        for key, val in data.items():
            if val and str(val).strip():
                parts.append(f"{key}: {val}")
        return " | ".join(parts) if parts else "—"
    except Exception:
        return str(measurements_json)


# ---------------------------------------------------------------------------
# Number-to-words converter (Indian style, rupees)
# ---------------------------------------------------------------------------
def _num_to_words(n: float) -> str:
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    def _below_1000(num: int) -> str:
        if num == 0:
            return ""
        elif num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
        else:
            return ones[num // 100] + " Hundred" + (" " + _below_1000(num % 100) if num % 100 else "")

    rupees = int(n)
    paise = round((n - rupees) * 100)
    if rupees == 0:
        words = "Zero"
    elif rupees < 1000:
        words = _below_1000(rupees)
    elif rupees < 100000:
        words = _below_1000(rupees // 1000) + " Thousand" + (" " + _below_1000(rupees % 1000) if rupees % 1000 else "")
    elif rupees < 10000000:
        words = _below_1000(rupees // 100000) + " Lakh" + (" " + _num_to_words(rupees % 100000).replace(" Rupees Only", "") if rupees % 100000 else "")
    else:
        words = _below_1000(rupees // 10000000) + " Crore" + (" " + _num_to_words(rupees % 10000000).replace(" Rupees Only", "") if rupees % 10000000 else "")

    result = words.strip() + " Rupees"
    if paise:
        result += " and " + _below_1000(paise) + " Paise"
    return result + " Only"


# ---------------------------------------------------------------------------
# Canvas-level header / footer (drawn on every page)
# ---------------------------------------------------------------------------
class _InvoiceCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self._order_meta = kwargs.pop("order_meta", {})
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_header_footer(self, page_count):
        width, height = A4
        page_num = self._pageNumber

        # ── Header band ─────────────────────────────────────────────────────
        self.setFillColor(BRAND_DARK)
        self.rect(0, height - 70 * mm, width, 70 * mm, fill=True, stroke=False)

        # Shop name
        self.setFillColor(WHITE)
        self.setFont("Helvetica-Bold", 26)
        self.drawCentredString(width / 2, height - 22 * mm, "AJITHA TAILORS")

        self.setFont("Helvetica", 10)
        self.setFillColor(GRAY_LIGHT)
        self.drawCentredString(width / 2, height - 32 * mm,
                               "No. 12, Main Street, Coimbatore – 641001  |  Ph: +91 98765 43210")
        self.drawCentredString(width / 2, height - 39 * mm,
                               "GST No: 33AABCA1234F1Z5  |  ajithatailors@gmail.com")

        # Accent bar
        self.setFillColor(BRAND_PRIMARY)
        self.rect(0, height - 45 * mm, width, 4 * mm, fill=True, stroke=False)

        # "TAX INVOICE" tag (right-aligned inside header)
        self.setFillColor(BRAND_GOLD)
        self.setFont("Helvetica-Bold", 12)
        self.drawRightString(width - 15 * mm, height - 58 * mm, "TAX INVOICE")

        # ── Footer ──────────────────────────────────────────────────────────
        self.setFillColor(BRAND_DARK)
        self.rect(0, 0, width, 18 * mm, fill=True, stroke=False)
        self.setFillColor(GRAY_LIGHT)
        self.setFont("Helvetica", 8)
        self.drawCentredString(
            width / 2, 11 * mm,
            "Please present this slip at collection.  "
            "Alterations supported within 7 days of delivery."
        )
        self.drawCentredString(
            width / 2, 6 * mm,
            f"Page {page_num} of {page_count}   |   Thank you for your patronage!"
        )


# ---------------------------------------------------------------------------
# Main PDF generation function
# ---------------------------------------------------------------------------

def generate_invoice(
    order: Dict,
    items: List[Dict],
    customer: Dict,
) -> str:
    """
    Generate a professional PDF invoice.

    Parameters
    ----------
    order    : dict with all order fields
    items    : list of order_item dicts
    customer : dict with customer details

    Returns
    -------
    Absolute path of the generated PDF file.
    """
    # ── Build unique file path ───────────────────────────────────────────
    inv_dir = _get_invoices_dir()
    c_name  = _sanitize(customer.get("name", "Customer"))
    c_mob   = re.sub(r"\D", "", customer.get("mobile", "0000000000"))[-10:]
    order_id = order.get("order_id", 0)
    filename = f"AjithaTailors_{c_name}_{c_mob}_Order{order_id}.pdf"
    pdf_path = _unique_path(inv_dir, filename)

    # ── Styles ───────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def style(name="Normal", **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, parent=styles[name], **kwargs)

    s_normal   = style(fontSize=9,  textColor=GRAY_DARK, leading=13)
    s_bold     = style(fontSize=9,  textColor=GRAY_DARK, fontName="Helvetica-Bold", leading=13)
    s_label    = style(fontSize=8,  textColor=GRAY_MID,  leading=11)
    s_value    = style(fontSize=9,  textColor=GRAY_DARK, fontName="Helvetica-Bold", leading=13)
    s_small    = style(fontSize=7.5, textColor=GRAY_MID, leading=11)
    s_center   = style(fontSize=9,  textColor=GRAY_DARK, alignment=TA_CENTER, leading=13)
    s_meas     = style(fontSize=7.5, textColor=GRAY_MID, leading=10)
    s_total_lbl= style(fontSize=10, textColor=GRAY_DARK, fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=14)
    s_total_val= style(fontSize=10, textColor=BRAND_PRIMARY, fontName="Helvetica-Bold", leading=14)
    s_words    = style(fontSize=8,  textColor=GRAY_MID, fontName="Helvetica-Oblique", leading=11)

    # ── Document setup ───────────────────────────────────────────────────
    margin_h = 15 * mm
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=margin_h,
        rightMargin=margin_h,
        topMargin=75 * mm,   # leave space for header drawn on canvas
        bottomMargin=25 * mm,
    )

    story = []
    W = A4[0] - 2 * margin_h   # usable width

    # ── Invoice meta + customer info (two-column grid) ───────────────────
    invoice_date = datetime.now().strftime("%d-%b-%Y")
    booking_date = order.get("booking_date", "")
    collection_date = order.get("collection_date", "")
    try:
        booking_date = datetime.strptime(booking_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        pass
    try:
        collection_date = datetime.strptime(collection_date, "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        pass

    meta_data = [
        [
            Paragraph("INVOICE NO.", s_label),
            Paragraph(f"#{order_id:05d}", s_value),
            Paragraph("INVOICE DATE", s_label),
            Paragraph(invoice_date, s_value),
        ],
        [
            Paragraph("BOOKING DATE", s_label),
            Paragraph(booking_date, s_value),
            Paragraph("DELIVERY DATE", s_label),
            Paragraph(collection_date, s_value),
        ],
        [
            Paragraph("CUSTOMER NAME", s_label),
            Paragraph(customer.get("name", ""), s_value),
            Paragraph("MOBILE", s_label),
            Paragraph(customer.get("mobile", ""), s_value),
        ],
        [
            Paragraph("PAYMENT MODE", s_label),
            Paragraph(order.get("payment_mode", "Cash"), s_value),
            Paragraph("ORDER STATUS", s_label),
            Paragraph(order.get("order_status", ""), s_value),
        ],
    ]

    if customer.get("address"):
        meta_data.append([
            Paragraph("ADDRESS", s_label),
            Paragraph(customer.get("address", ""), s_value),
            Paragraph("", s_label),
            Paragraph("", s_value),
        ])

    col_w = [30 * mm, 55 * mm, 30 * mm, 55 * mm]
    meta_table = Table(meta_data, colWidths=col_w, hAlign="LEFT")
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
        ("BOX",         (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ("INNERGRID",   (0, 0), (-1, -1), 0.3, GRAY_LIGHT),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ── Items Table ───────────────────────────────────────────────────────
    story.append(Paragraph("ORDER ITEMS", style(
        fontSize=10, fontName="Helvetica-Bold",
        textColor=BRAND_DARK, spaceAfter=4,
    )))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_PRIMARY, spaceAfter=3))

    item_header = ["#", "Garment", "Measurements & Notes", "Qty", "Rate (₹)", "Total (₹)"]
    item_rows   = [item_header]

    subtotal = 0.0
    for idx, item in enumerate(items, start=1):
        garment    = item.get("garment_type", "Custom")
        qty        = int(item.get("quantity", 1))
        rate       = float(item.get("item_rate", 0.0))
        line_total = qty * rate
        subtotal  += line_total

        meas_str = _measurements_summary(item.get("measurements_json", "{}"))
        design   = item.get("design_instructions", "")
        detail   = meas_str
        if design and design.strip():
            detail += f"\n✦ {design}"

        item_rows.append([
            Paragraph(str(idx), s_center),
            Paragraph(f"<b>{garment}</b>", s_normal),
            Paragraph(detail.replace("\n", "<br/>"), s_meas),
            Paragraph(str(qty), s_center),
            Paragraph(f"{rate:,.2f}", style(alignment=TA_RIGHT, fontSize=9, textColor=GRAY_DARK)),
            Paragraph(f"{line_total:,.2f}", style(alignment=TA_RIGHT, fontSize=9, textColor=GRAY_DARK, fontName="Helvetica-Bold")),
        ])

    col_widths = [10 * mm, 28 * mm, W - 10 - 28 - 16 - 22 - 22, 16 * mm, 22 * mm, 22 * mm]
    items_table = Table(item_rows, colWidths=col_widths, repeatRows=1)

    row_count = len(item_rows)
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0),  (-1, 0),   TABLE_HEADER),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),   WHITE),
        ("FONTNAME",      (0, 0),  (-1, 0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0),  (-1, 0),   9),
        ("ALIGN",         (0, 0),  (-1, 0),   "CENTER"),
        ("TOPPADDING",    (0, 0),  (-1, 0),   5),
        ("BOTTOMPADDING", (0, 0),  (-1, 0),   5),
        # Data rows
        ("FONTSIZE",      (0, 1),  (-1, -1),  8),
        ("TOPPADDING",    (0, 1),  (-1, -1),  4),
        ("BOTTOMPADDING", (0, 1),  (-1, -1),  4),
        ("LEFTPADDING",   (0, 0),  (-1, -1),  4),
        ("RIGHTPADDING",  (0, 0),  (-1, -1),  4),
        ("VALIGN",        (0, 1),  (-1, -1),  "TOP"),
        # Alternating row colours
        *[
            ("BACKGROUND", (0, r), (-1, r), TABLE_ALT)
            for r in range(2, row_count, 2)
        ],
        ("BOX",       (0, 0), (-1, -1), 0.5, GRAY_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GRAY_LIGHT),
    ]))

    story.append(items_table)
    story.append(Spacer(1, 5 * mm))

    # ── Payment Summary ───────────────────────────────────────────────────
    total_amt   = float(order.get("total_amount", subtotal))
    advance_amt = float(order.get("advance_amount", 0.0))
    balance_amt = float(order.get("balance_amount", total_amt))

    summary_data = [
        [Paragraph("Sub-Total",        s_total_lbl), Paragraph(_fmt_currency(subtotal),   s_total_val)],
        [Paragraph("Advance Received", s_total_lbl), Paragraph(_fmt_currency(advance_amt), s_total_val)],
        [Paragraph("BALANCE DUE",      style(
            fontSize=12, fontName="Helvetica-Bold",
            textColor=BRAND_DARK, alignment=TA_RIGHT,
        )), Paragraph(_fmt_currency(balance_amt), style(
            fontSize=12, fontName="Helvetica-Bold",
            textColor=BRAND_PRIMARY,
        ))],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[W - 60 * mm, 60 * mm],
        hAlign="RIGHT",
    )
    summary_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 1), (-1, 1),  0.5, GRAY_LIGHT),
        ("LINEABOVE",     (0, 2), (-1, 2),  1,   BRAND_PRIMARY),
        ("LINEBELOW",     (0, 2), (-1, 2),  1,   BRAND_PRIMARY),
        ("BACKGROUND",    (0, 2), (-1, 2),  colors.HexColor("#FFF0F3")),
    ]))
    story.append(summary_table)

    # Amount in words
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Amount in words: <i>{_num_to_words(balance_amt)}</i>",
        style(fontSize=8, textColor=GRAY_MID, fontName="Helvetica-Oblique"),
    ))

    story.append(Spacer(1, 8 * mm))

    # ── Notes ─────────────────────────────────────────────────────────────
    order_notes = order.get("notes", "")
    if order_notes and order_notes.strip():
        story.append(Paragraph("Notes / Special Instructions:", s_bold))
        story.append(Paragraph(order_notes, s_normal))
        story.append(Spacer(1, 5 * mm))

    # ── Signature area ────────────────────────────────────────────────────
    sig_data = [
        [
            Paragraph("Customer Signature", style(fontSize=8, textColor=GRAY_MID, alignment=TA_CENTER)),
            Paragraph("", s_normal),
            Paragraph("For AJITHA TAILORS", style(fontSize=8, textColor=GRAY_MID, alignment=TA_CENTER)),
        ],
        [
            Paragraph("_________________________", s_center),
            Paragraph("", s_normal),
            Paragraph("_________________________", s_center),
        ],
        [
            Paragraph("Date: _______________", style(fontSize=8, textColor=GRAY_MID, alignment=TA_CENTER)),
            Paragraph("", s_normal),
            Paragraph("Authorized Signatory", style(fontSize=8, textColor=GRAY_MID, alignment=TA_CENTER)),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[W / 3, W / 3, W / 3])
    sig_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(KeepTogether([sig_table]))

    # ── Terms ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT))
    story.append(Spacer(1, 2 * mm))
    terms_text = (
        "<b>Terms &amp; Conditions:</b> 1. Please present this invoice at collection. "
        "2. Uncollected orders after 60 days will not be the shop's responsibility. "
        "3. Alterations supported within 7 days of delivery. "
        "4. Advance paid is non-refundable for cancelled orders."
    )
    story.append(Paragraph(terms_text, style(fontSize=7, textColor=GRAY_MID, leading=10)))

    # ── Build PDF ──────────────────────────────────────────────────────────
    doc.build(
        story,
        canvasmaker=lambda *a, **kw: _InvoiceCanvas(*a, order_meta=order, **kw),
    )

    return pdf_path


def open_pdf(pdf_path: str):
    """Open the PDF with the default system viewer."""
    try:
        if sys.platform == "win32":
            os.startfile(pdf_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", pdf_path])
        else:
            subprocess.Popen(["xdg-open", pdf_path])
    except Exception as exc:
        print(f"[pdf_service] Could not open PDF: {exc}")
