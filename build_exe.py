"""
build_exe.py
Automated PyInstaller packaging script for Ajitha Tailors ERP.
Run: python build_exe.py

Produces a standalone Windows .exe in the dist/ directory.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
APP_NAME        = "AjithaTailors"
MAIN_SCRIPT     = "main.py"
ICON_PATH       = "assets/icon.ico"   # Replace with actual .ico if available
DIST_DIR        = "dist"
BUILD_DIR       = "build"
ONE_DIR         = True   # True = --onedir (faster startup), False = --onefile (single file)

# Additional data files to bundle (source_path, dest_in_bundle)
DATAS = [
    ("assets",   "assets"),
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS = [
    "customtkinter",
    "reportlab",
    "reportlab.graphics",
    "reportlab.pdfgen",
    "reportlab.platypus",
    "reportlab.lib.pagesizes",
    "openpyxl",
    "PIL",
    "PIL._imagingtk",
    "sqlite3",
    "tkinter",
    "tkinter.ttk",
    "tkcalendar",
    "babel.numbers",
]

# Packages to collect entirely (ensures all sub-modules are included)
COLLECT_ALL = [
    "customtkinter",
    "reportlab",
    "PIL",
]


def find_pyinstaller():
    """Locate the PyInstaller executable."""
    candidates = [
        os.path.join(os.path.dirname(sys.executable), "Scripts", "pyinstaller"),
        os.path.join(os.path.dirname(sys.executable), "Scripts", "pyinstaller.exe"),
        "pyinstaller",
    ]
    for c in candidates:
        if shutil.which(c):
            return c
    return "pyinstaller"   # fall back; will error clearly if not found


def build():
    print("=" * 60)
    print("  Ajitha Tailors ERP — PyInstaller Build")
    print("=" * 60)

    pyinstaller = find_pyinstaller()
    base = Path(__file__).parent.resolve()

    cmd = [
        pyinstaller,
        "--name", APP_NAME,
        "--noconfirm",
        "--clean",
        "--noconsole",         # No console window on Windows
        "--distpath", str(base / DIST_DIR),
        "--workpath", str(base / BUILD_DIR),
        "--specpath", str(base),
    ]

    # Mode
    if ONE_DIR:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    # Icon (only add if file exists)
    icon_full = base / ICON_PATH
    if icon_full.exists():
        cmd.extend(["--icon", str(icon_full)])
    else:
        print(f"  [WARN] Icon not found at {icon_full} — skipping icon")

    # Data files
    sep = ";" if sys.platform == "win32" else ":"
    for src, dst in DATAS:
        src_full = base / src
        if src_full.exists():
            cmd.extend(["--add-data", f"{src_full}{sep}{dst}"])

    # Hidden imports
    for hi in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", hi])

    # Collect all
    for pkg in COLLECT_ALL:
        cmd.extend(["--collect-all", pkg])

    # Main script
    cmd.append(str(base / MAIN_SCRIPT))

    print("\n  Running PyInstaller command...")
    print("  " + " ".join(cmd[:8]) + " …\n")

    result = subprocess.run(cmd, cwd=str(base))

    if result.returncode != 0:
        print("\n  [ERROR] Build failed! Check output above.")
        sys.exit(1)

    # ── Post-build: create runtime dirs next to exe ──────────────────────────
    if ONE_DIR:
        dist_app_dir = base / DIST_DIR / APP_NAME
    else:
        dist_app_dir = base / DIST_DIR

    for folder in ("data", "invoices", "exports"):
        (dist_app_dir / folder).mkdir(exist_ok=True)
        # Create a .gitkeep so the folder is visible
        gitkeep = dist_app_dir / folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("")

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("\n" + "=" * 60)
    print("  [SUCCESS] Build completed successfully!")
    print(f"  Output directory: {dist_app_dir}")
    if ONE_DIR:
        print(f"  Launch:  {dist_app_dir / (APP_NAME + '.exe')}")
    else:
        print(f"  Launch:  {base / DIST_DIR / (APP_NAME + '.exe')}")
    print("=" * 60)


if __name__ == "__main__":
    build()
