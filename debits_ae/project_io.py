"""Sauvegarde et chargement d'un dossier projet MK_Debits_Air_Eau.

Le format `.mkprojet` est un fichier JSON lisible qui contient l'identité du
projet, les données hydrauliques partagées et tous les résultats calculés.
Il permet de reprendre un dossier sans ressaisie et sans perte de résultats.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Projet

EXTENSION_PROJET = ".mkprojet"


def sauvegarder_projet(projet: Projet, chemin: str | Path) -> Path:
    """Écrit le projet au format JSON `.mkprojet` et retourne le chemin final."""
    chemin = Path(chemin)
    if chemin.suffix.lower() != EXTENSION_PROJET:
        chemin = chemin.with_suffix(EXTENSION_PROJET)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(projet.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chemin


def charger_projet(chemin: str | Path) -> Projet:
    """Lit un fichier `.mkprojet` (ou `.json`) et reconstruit l'objet `Projet`."""
    chemin = Path(chemin)
    data = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "donnees" not in data:
        raise ValueError(
            "Fichier projet invalide : la clé « donnees » est absente."
        )
    return Projet.from_dict(data)
