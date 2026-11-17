"""Point d'entrée de l'application MK_Debits_Air_Eau.

Lancement :
    python -m debits_ae
ou
    python debits_ae/main.py
"""

from __future__ import annotations

import os
import sys

# Permet aussi le lancement direct : python debits_ae/main.py
if __package__ in (None, ""):
    _RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _RACINE not in sys.path:
        sys.path.insert(0, _RACINE)

from debits_ae.ui.main_window import MainWindow


def main() -> int:
    app = MainWindow()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
