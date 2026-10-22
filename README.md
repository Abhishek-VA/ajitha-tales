# Ajitha Tailors — Billing & Order Management ERP

A **production-grade, offline-first** Desktop ERP built in Python for **Ajitha Tailors**.  
Runs 100% locally with no internet connection required. Compilable to a standalone Windows `.exe`.

---

## ✨ Features

| Feature | Details |
|---|---|
| 👤 **Customer Auto-Lookup** | Type a 10-digit mobile → auto-fills name, address, past data |
| 🧵 **Multi-Item Orders** | Add multiple garments per order with individual rates |
| 📐 **Dynamic Measurements** | Garment-specific fields (Blouse, Kurti, Salwar, Gown, Shirt…) |
| 🖨️ **PDF Invoice** | Professional branded invoice, auto-opens on save |
| ✏️ **Full Order Editing** | Double-click any order to load & edit in the form |
| 🔍 **Omni-Search** | Filter by name, mobile, or order ID in real time |
| 📅 **Date Filters** | Due Today / Due Tomorrow / This Week / Overdue |
| 🏷️ **Status Transitions** | Right-click → Quick status change |
| 📊 **Excel/CSV Export** | Full order export with formatting |
| 💰 **Billing Math** | Auto-calculates Total, Advance, Balance Due |
| 🗄️ **SQLite Database** | Robust local database with WAL mode |
| 📦 **Portable EXE** | PyInstaller-based standalone Windows build |

---

## 🗂️ Project Structure

```
ajitha-tailors-billing/
├── main.py                      # Entry point
├── build_exe.py                 # PyInstaller packaging script
├── requirements.txt
├── assets/                      # Icons, logo
├── data/                        # SQLite database (auto-created)
├── invoices/                    # PDF invoices (auto-created)
├── exports/                     # CSV/Excel exports (auto-created)
├── database/
│   └── db_manager.py            # Schema, migrations, all queries
├── services/
│   ├── pdf_service.py           # ReportLab PDF generator
│   └── export_service.py        # CSV/Excel export
└── ui/
    ├── app.py                   # Main window
    ├── styles.py                # Theme & design system
    └── components/
        ├── order_entry.py       # Left pane: Order form + cart
        ├── dashboard.py         # Right pane: Table + filters
        └── measurement_modal.py # Measurement popup
```

---

## 🚀 Installation & Running

### Prerequisites
- Python 3.10+ (64-bit recommended)
- pip

### Step 1 — Create virtual environment
```bash
cd ajitha-tailors-billing
python -m venv .venv
.venv\Scripts\activate        # Windows
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run the application
```bash
python main.py
```

---

## 📦 Build Standalone Windows EXE

```bash
# Activate venv first
.venv\Scripts\activate

# Run build script
python build_exe.py
```

Output will be in `dist/AjithaTailors/`.  
Copy the entire `AjithaTailors/` folder to any Windows machine — **no Python required**.

> **Note:** The `data/`, `invoices/`, and `exports/` folders are auto-created next to the `.exe` on first run.

---

## 🎯 Usage Guide

### Creating an Order
1. Enter the customer's **10-digit mobile** — existing customers auto-fill
2. Fill in customer name and delivery date
3. Select a garment type → click **"Add Measurements"** for detailed specs
4. Enter the item rate → **"Add Item to Order"**
5. Repeat for multiple items
6. Enter advance payment amount
7. Click **"Save & Print Invoice"** — PDF opens automatically

### Editing an Order
- **Double-click** any order row in the dashboard
- The form loads with all existing data
- Make changes → click **"Update Order #ID"**

### Quick Status Change
- **Right-click** any order row → select status

### Keyboard Shortcuts
- `Enter` on selected row → Opens for editing

---

## 🗄️ Database

Located at: `data/tailor_shop.db`

Tables:
- `customers` — Customer master
- `orders` — Order header with payment & status
- `order_items` — Individual garment items with measurements (JSON)

---

## 🖨️ PDF Invoices

Saved to: `invoices/AjithaTailors_{Name}_{Mobile}_Order{ID}.pdf`

Features:
- Shop header with name, address, GST
- Itemized garment table with measurements
- Payment block: Total / Advance / Balance Due
- Amount in words
- Terms & conditions
- Signature area

---

## 📊 Export

Exports saved to: `exports/`
- **CSV** — Plain data for any spreadsheet
- **Excel** — Formatted with colour-coded statuses, totals row, freeze panes

---

## 🔧 Configuration

Edit `ui/styles.py` to change colors and fonts.  
Edit `services/pdf_service.py` header section to update shop details (address, phone, GST).

---

## 📋 Git Setup

```bash
cd ajitha-tailors-billing
git init
git add .
git commit -m "feat: initial Ajitha Tailors ERP"

# Create a GitHub repo, then:
git remote add origin https://github.com/YOUR_USERNAME/ajitha-tailors-billing.git
git branch -M main
git push -u origin main
```

---

## 📄 License

Private use only — Ajitha Tailors.
