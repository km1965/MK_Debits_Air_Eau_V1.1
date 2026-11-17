"""Import de documents .docx de type étude de casse franche (ex. rapport Allouane).

Ce module extrait les données hydrauliques d'un document Word contenant des
tableaux de paramètres et des paragraphes de résultats, afin de les réinjecter
dans l'application pour recalcul avec la méthode F10.

Il cible les documents structurés comme ``rapport_allouane_BR3_TR2.docx`` :
* Tableau « Paramètre | Valeur | Unité » (données de conduite, cotes, longueurs…)
* Paragraphes de type « [amont] CAS DIRECT : Q_am = ALLOUANE(ΔH=…, L=…) = … m³/h »
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docx import Document

from debits_ae.models import DonneesProjet


# ---------------------------------------------------------------------------
# Résultat d'import DOCX
# ---------------------------------------------------------------------------
@dataclass
class ResultatImportDocx:
    """Données extraites d'un document .docx."""

    source: str
    donnees_brutes: dict[str, Any] = field(default_factory=dict)
    paragraphes_resultats: list[str] = field(default_factory=list)
    tableaux: list[list[list[str]]] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)

    donnees: DonneesProjet | None = None


def _nombre(texte: str) -> float | None:
    """Convertit un texte en float (gère virgules, espaces, unités collées)."""
    if texte is None:
        return None
    t = str(texte).strip()
    if not t:
        return None
    t = t.replace(" ", "").replace(",", ".")
    # Garde uniquement les caractères numériques valides
    t = re.sub(r"[^0-9.\-+eE]", "", t)
    if not t or t in (".", "-", "+"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _normalise_cle(texte: str) -> str:
    t = texte.lower().strip()
    t = t.replace("à", "a").replace("â", "a").replace("ä", "a")
    t = t.replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e")
    t = t.replace("î", "i").replace("ï", "i")
    t = t.replace("ô", "o").replace("ö", "o")
    t = t.replace("ù", "u").replace("û", "u").replace("ü", "u")
    t = t.replace("ç", "c")
    # Supprimer parenthèses et crochets pour faciliter le matching
    t = t.replace("(", " ").replace(")", " ")
    t = t.replace("[", " ").replace("]", " ")
    t = re.sub(r"[^a-z0-9%/\- .]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# Extraction depuis un DOCX
# ---------------------------------------------------------------------------
def extraire_tableaux_docx(chemin: str | Path) -> list[list[list[str]]]:
    """Extrait tous les tableaux d'un fichier .docx sous forme de listes de lignes."""
    chemin = Path(chemin)
    doc = Document(str(chemin))
    tableaux: list[list[list[str]]] = []
    for table in doc.tables:
        lignes: list[list[str]] = []
        for row in table.rows:
            lignes.append([cell.text.strip() for cell in row.cells])
        if lignes:
            tableaux.append(lignes)
    return tableaux


def extraire_paragraphes_docx(chemin: str | Path) -> list[str]:
    """Extrait tous les paragraphes non vides d'un fichier .docx."""
    chemin = Path(chemin)
    doc = Document(str(chemin))
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def _parse_tableau_parametres(tableau: list[list[str]]) -> dict[str, Any]:
    """Parse un tableau au format « Paramètre | Valeur | Unité »."""
    donnees: dict[str, Any] = {}
    if len(tableau) < 2:
        return donnees
    en_tete = [_normalise_cle(c) for c in tableau[0]]
    idx_param = en_tete.index("parametre") if "parametre" in en_tete else 0
    idx_val = en_tete.index("valeur") if "valeur" in en_tete else 1
    for row in tableau[1:]:
        if len(row) <= max(idx_param, idx_val):
            continue
        cle = _normalise_cle(row[idx_param])
        val = _nombre(row[idx_val])
        if cle and val is not None:
            donnees[cle] = val
    return donnees


def _parse_paragraphes_resultats(paragraphes: list[str]) -> dict[str, Any]:
    """Cherche les résultats de calcul dans les paragraphes (méthode Allouane)."""
    donnees: dict[str, Any] = {}
    for p in paragraphes:
        # Pattern : [amont] CAS DIRECT : Q_am = ALLOUANE(ΔH=95.55, L=351.01) = 308173.4 m³/h
        m = re.search(
            r"ALLOUANE\(([^)]*)\)\s*=\s*([\d\s,\.]+)\s*m.?³/h",
            p,
            flags=re.IGNORECASE,
        )
        if m:
            args = m.group(1)
            val = _nombre(m.group(2))
            if val is None:
                continue
            # Extrait ΔH et L des arguments
            dh = _nombre(re.search(r"ΔH\s*=\s*([\d,\.]+)", args).group(1)) if re.search(r"ΔH\s*=\s*([\d,\.]+)", args) else None
            lg = _nombre(re.search(r"L\s*=\s*([\d,\.]+)", args).group(1)) if re.search(r"L\s*=\s*([\d,\.]+)", args) else None
            cle = "q_allouane_amont" if "amont" in p.lower() else "q_allouane_aval"
            donnees[cle] = val
            if dh is not None:
                donnees[f"dh_{cle}"] = dh
            if lg is not None:
                donnees[f"l_{cle}"] = lg
    return donnees


def importer_docx(
    chemin: str | Path,
    donnees: DonneesProjet | None = None,
) -> ResultatImportDocx:
    """Importe un document .docx et en extrait les données hydrauliques.

    Parameters
    ----------
    chemin : chemin du fichier .docx à importer.
    donnees : données partagées du projet (optionnel, créées par défaut).
    """
    chemin = Path(chemin)
    resultat = ResultatImportDocx(source=str(chemin))
    if donnees is None:
        donnees = DonneesProjet()

    try:
        tableaux = extraire_tableaux_docx(chemin)
        paragraphes = extraire_paragraphes_docx(chemin)
    except Exception as exc:
        resultat.avertissements.append(f"Impossible de lire le document : {exc}")
        return resultat

    resultat.tableaux = tableaux
    resultat.paragraphes_resultats = paragraphes

    # Fusion des données depuis les tableaux (format Paramètre | Valeur | Unité)
    donnees_brutes: dict[str, Any] = {}
    for tableau in tableaux:
        donnees_brutes.update(_parse_tableau_parametres(tableau))

    # Données depuis les paragraphes de résultats
    donnees_brutes.update(_parse_paragraphes_resultats(paragraphes))
    resultat.donnees_brutes = donnees_brutes

    # Mapping vers DonneesProjet
    mapping: dict[str, str] = {
        "diametre interieur d": "diam_conduit",
        "diametre interieur": "diam_conduit",
        "diametre nominal dn": "diam_conduit",  # en mm -> /1000
        "longueur l1": "longueur_troncon",
        "distance l1 vi1 ve": "longueur_troncon",
        "longueur l2": "longueur_troncon_2",
        "distance l2 ve vi2": "longueur_troncon_2",
        "depression admissible": "delta_h_max",
        "delta h brut": "delta_h_brut",
        "delta h": "delta_h_brut",
        "depression admissible dh": "delta_h_max",
        "altitude ve (point haut)": "altitude_ve",
        "altitude ve point haut": "altitude_ve",
        "altitude vi1": "altitude_vi1",
        "altitude vi2": "altitude_vi2",
    }

    donnees.nom = chemin.stem
    for cle, val in donnees_brutes.items():
        cible = mapping.get(cle)
        if cible is None:
            continue
        if cible == "diam_conduit" and cle in ("diametre nominal dn",):
            val = val / 1000.0  # mm -> m
        if hasattr(donnees, cible):
            setattr(donnees, cible, val)

    # Calculer delta_h_brut depuis les altitudes si disponibles
    if donnees.altitude_ve and donnees.altitude_vi1:
        donnees.delta_h_brut = donnees.altitude_ve - donnees.altitude_vi1
        donnees_brutes["delta_h_brut"] = donnees.delta_h_brut
    elif donnees.altitude_ve and donnees.altitude_vi2:
        donnees.delta_h_brut = donnees.altitude_ve - donnees.altitude_vi2
        donnees_brutes["delta_h_brut"] = donnees.delta_h_brut

    # Si on a trouvé des longueurs L1 et L2 distinctes, garder L1 comme référence
    if "longueur_troncon_2" in donnees_brutes and "longueur_troncon" not in donnees_brutes:
        donnees.longueur_troncon = donnees_brutes["longueur_troncon_2"]

    # Résultat Allouane amont/avail si trouvé
    if "q_allouane_amont" in donnees_brutes:
        donnees.notes = f"Q Allouane amont : {donnees_brutes['q_allouane_amont']:,.0f} m³/h"
    if "q_allouane_aval" in donnees_brutes:
        if donnees.notes:
            donnees.notes += f" ; Q Allouane aval : {donnees_brutes['q_allouane_aval']:,.0f} m³/h"
        else:
            donnees.notes = f"Q Allouane aval : {donnees_brutes['q_allouane_aval']:,.0f} m³/h"

    resultat.donnees = donnees
    return resultat
