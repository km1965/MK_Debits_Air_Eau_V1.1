"""Import d'un fichier de vérification .xlsx externe.

L'utilisateur peut importer un classeur Excel contenant les données d'entrée
d'un dossier de vérification (cotes, diamètres, longueurs, pentes, coefficients…).
L'application remplit les données partagées (:class:`debits_ae.models.DonneesProjet`)
et relance les calculs avec ses propres formules (F1 → F11), afin de vérifier
le fichier externe par le moteur de MK_Debits_Air_Eau.

Le mapping des colonnes est volontairement souple : plusieurs alias sont acceptés
pour chaque champ (ex. "Diamètre conduit", "D (m)", "diam_conduit").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from debits_ae.models import DonneesProjet, Projet, VidangeResult, VentouseResult
from debits_ae.models import VidangeInputs, VentouseInputs
from debits_ae import calcul_vidange, calcul_ventouse


# ---------------------------------------------------------------------------
# Alias de champs : nom interne -> liste de libellés acceptés dans le XLSX
# ---------------------------------------------------------------------------
_ALIAS: dict[str, list[str]] = {
    "nom": ["nom", "projet", "intitulé", "intitule", "dossier"],
    "reference": ["reference", "référence", "ref"],
    "site": ["site", "lieu", "adduction"],
    "diam_conduit": ["diamètre conduit", "diam conduit", "d conduit", "diam_conduit", "d (m)", "diamètre (m)"],
    "longueur_troncon": ["longueur tronçon", "longueur troncon", "l tronçon", "l troncon", "longueur (m)", "longueur_troncon", "L (m)"],
    "hauteur_eau": ["hauteur eau", "hauteur moyenne", "h (m)", "hauteur_eau", "h eau"],
    "pente": ["pente", "i (m/m)", "pente (m/m)", "ligne d'energie", "ligne d'énergie"],
    "cote_ventouse": ["cote ventouse", "côte ventouse", "z ventouse", "cote_ventouse", "cote (m) ventouse"],
    "cote_vidange": ["cote vidange", "côte vidange", "z vidange", "cote_vidange", "cote (m) vidange"],
    "coeff_rugosite": ["coeff rugosite", "coefficient rugosite", "k strickler", "strickler", "coeff_rugosite", "k (m^(1/3)/s)"],
    "coeff_singularites": ["coeff singularites", "coefficient singularites", "xi", "ξ", "pertes singularites", "coeff_singularites"],
    "temps_vidange_h": ["temps vidange", "temps de vidange", "duree vidange", "durée vidange", "temps_vidange_h", "t vidange (h)", "vidange (h)"],
    "vitesse_remplissage": ["vitesse remplissage", "v (m/s)", "vitesse (m/s)", "vitesse_remplissage"],
    "debit_nominal": ["debit nominal", "débit nominal", "q nominal", "qn", "debit_nominal", "Q nominal (m3/s)"],
    "degazage_pct_qnom": ["degazage %", "dégazage %", "pct qnom", "degazage_pct_qnom", "% qnom"],
    "delta_h_max": ["delta h", "Δh", "dh", "delta_h_max", "suppression (m)", "ΔH (m)"],
    "p2_pression_absolue_mce": ["p2", "pression absolue", "p2 (mce)", "p2_pression_absolue_mce"],
    "epaisseur_conduite": ["epaisseur", "épaisseur", "e (m)", "e (mm)", "epaisseur_conduite"],
    "materiau": ["materiau", "matériau", "matière", "materiau_conduite"],
    "coeff_allievi": ["coeff allievi", "k allievi", "allievi k", "coeff_allievi"],
    "celerite_a": ["celerite a", "célérité a", "a (m/s)", "celerite_a"],
}


def _normalise_texte(texte: str) -> str:
    """Minuscule, sans accent, sans espace multiple."""
    t = texte.lower().strip()
    t = re.sub(r"[àâä]", "a", t)
    t = re.sub(r"[éèêë]", "e", t)
    t = re.sub(r"[îï]", "i", t)
    t = re.sub(r"[ôö]", "o", t)
    t = re.sub(r"[ùûü]", "u", t)
    t = re.sub(r"[^a-z0-9%^()/.,\- ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _nombre(valeur: Any) -> float | None:
    """Convertit une cellule en float, gère les virgules et les textes."""
    if valeur is None:
        return None
    if isinstance(valeur, bool):
        return None
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip()
    if not texte:
        return None
    texte = texte.replace(" ", "").replace(",", ".")
    texte = re.sub(r"[^0-9.\-+eE]", "", texte)
    try:
        return float(texte)
    except ValueError:
        return None


@dataclass
class ImportResult:
    """Résultat de l'import d'un XLSX externe."""

    donnees_lues: dict[str, Any] = field(default_factory=dict)
    feuilles_parcourues: list[str] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    donnees: DonneesProjet | None = None
    projet: Projet | None = None


def _extraire_paires_cle_valeur(feuille) -> dict[str, Any]:
    """Lit une feuille sous forme de paires clé|valeur (col A = clé, col B = valeur)."""
    donnees: dict[str, Any] = {}
    for row in feuille.iter_rows(values_only=True):
        if not row or len(row) < 2:
            continue
        cle = _normalise_texte(str(row[0])) if row[0] is not None else ""
        if not cle:
            continue
        valeur = _nombre(row[1])
        if valeur is None:
            continue
        donnees[cle] = valeur
    return donnees


def _extraire_tableau_en_tetes(feuille) -> list[dict[str, Any]]:
    """Lit une feuille comme un tableau : première ligne = en-têtes."""
    rows = list(feuille.iter_rows(values_only=True))
    if len(rows) < 2:
        return []
    en_tetes = [_normalise_texte(str(h)) for h in rows[0] if h is not None]
    if not en_tetes:
        return []
    lignes: list[dict[str, Any]] = []
    for row in rows[1:]:
        ligne: dict[str, Any] = {}
        for i, entete in enumerate(en_tetes):
            if i < len(row) and row[i] is not None:
                val = _nombre(row[i])
                if val is not None:
                    ligne[entete] = val
        if ligne:
            lignes.append(ligne)
    return lignes


def _resoudre_donnees(donnees_brutes: dict[str, Any]) -> dict[str, Any]:
    """Mappe les clés lues (aliases) vers les noms internes de DonneesProjet."""
    resolues: dict[str, Any] = {}
    for cle, valeur in donnees_brutes.items():
        for interne, aliases in _ALIAS.items():
            if cle in ( _normalise_texte(a) for a in aliases ) or cle == interne:
                resolues[interne] = valeur
                break
    return resolues


def _inferer_nom_projet(donnees_brutes: dict[str, Any], chemin: Path) -> str:
    for cle in ("nom", "projet", "intitule", "intitulé", "dossier"):
        if cle in donnees_brutes:
            return str(donnees_brutes[cle])
    return chemin.stem


def importer_xlsx(chemin: str | Path) -> ImportResult:
    """Lit un fichier .xlsx externe et remplit un objet Projet.

    Returns
    -------
    ImportResult
        Contient les données lues, le projet rempli et les résultats de calcul.
    """
    chemin = Path(chemin)
    resultat = ImportResult()

    try:
        wb = load_workbook(chemin, data_only=True, read_only=True)
    except Exception as exc:  # fichier illisible
        resultat.avertissements.append(f"Impossible d'ouvrir le classeur : {exc}")
        return resultat

    toutes_donnees: dict[str, Any] = {}
    for nom_feuille in wb.sheetnames:
        feuille = wb[nom_feuille]
        resultat.feuilles_parcourues.append(nom_feuille)

        # 1) paires clé|valeur
        paires = _extraire_paires_cle_valeur(feuille)
        toutes_donnees.update(paires)

        # 2) tableaux avec en-têtes (on fusionne ligne par ligne)
        for ligne in _extraire_tableau_en_tetes(feuille):
            toutes_donnees.update(ligne)

    wb.close()

    resultat.donnees_lues = toutes_donnees

    # Résolution vers les noms internes
    resolues = _resoudre_donnees(toutes_donnees)

    # Construction des DonneesProjet
    donnees = DonneesProjet()
    donnees.nom = _inferer_nom_projet(toutes_donnees, chemin)
    for cle, valeur in resolues.items():
        if hasattr(donnees, cle):
            setattr(donnees, cle, valeur)

    # Unités : si l'épaisseur est en mm (valeur > 1), convertir en m.
    if donnees.epaisseur_conduite and donnees.epaisseur_conduite > 1:
        donnees.epaisseur_conduite = donnees.epaisseur_conduite / 1000.0

    resultat.donnees = donnees

    # --- Recalcul avec les formules de l'app ---
    projet = Projet(donnees=donnees)

    # Vidange (points bas) si les données sont présentes
    if donnees.diam_conduit > 0 and donnees.longueur_troncon > 0:
        try:
            vidange_inputs = VidangeInputs(
                longueur_troncon=donnees.longueur_troncon,
                diam_conduit=donnees.diam_conduit,
                hauteur_eau=donnees.hauteur_eau,
                coeff_debit=donnees.coeff_debit_vidange,
                temps_vidange_cible=donnees.temps_vidange_h * 3600.0,
            )
            projet.vidange = calcul_vidange(vidange_inputs)
        except Exception as exc:  # ne bloque pas l'import
            resultat.avertissements.append(f"Calcul vidange impossible : {exc}")

    # Ventouse (points hauts) si les données sont présentes
    if donnees.diam_conduit > 0 and donnees.longueur_troncon > 0:
        try:
            ventouse_inputs = VentouseInputs(
                celerite_a=donnees.celerite_a,
                diam_conduit=donnees.diam_conduit,
                epaisseur_conduite=donnees.epaisseur_conduite,
                coeff_rugosite=donnees.coeff_rugosite,
                k_allievi=donnees.coeff_allievi,
                delta_h_max=donnees.delta_h_max,
                section_conduite=None,
                vitesse_remplissage=donnees.vitesse_remplissage,
                pente=donnees.pente,
                longueur_troncon=donnees.longueur_troncon,
                cote_ventouse=donnees.cote_ventouse,
                cote_vidange=donnees.cote_vidange,
                coeff_singularites=donnees.coeff_singularites,
                p2_pression_absolue_mce=donnees.p2_pression_absolue_mce,
            )
            projet.ventouse = calcul_ventouse(ventouse_inputs)
        except Exception as exc:
            resultat.avertissements.append(f"Calcul ventouse impossible : {exc}")

    resultat.projet = projet
    return resultat
