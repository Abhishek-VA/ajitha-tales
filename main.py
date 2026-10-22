"""
main.py
Application entry point for Ajitha Tailors Billing & Order ERP.
"""

import sys
import os

# Ensure the project root is in sys.path (needed for PyInstaller onefile mode)
if getattr(sys, "frozen", False):
    # Running as PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add project root to path
sys.path.insert(0, BASE_DIR)

# Ensure required runtime directories exist next to exe/script
for folder in ("data", "invoices", "exports"):
    os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)


def main():
    # Initialise database (creates tables if they don't exist)
    from database.db_manager import initialize_database
    initialize_database()

    # Launch the app
    from ui.app import AjithaTailorsApp
    app = AjithaTailorsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
