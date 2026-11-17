"""Localisation des ressources locales et embarquées (PyInstaller).

En développement, les ressources sont cherchées à la racine du projet.
Dans l'exécutable « onefile », PyInstaller les extrait dans `sys._MEIPASS`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def dossier_ressources() -> Path:
    """Dossier racine des ressources, en développement comme en exécutable."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


def chemin_ressource(*parties: str) -> Path | None:
    """Retourne le chemin d'une ressource si elle existe, sinon `None`."""
    chemin = dossier_ressources().joinpath(*parties)
    return chemin if chemin.exists() else None
