"""Import des tableaux de dimensionnement (ventouses / vidanges).

L'utilisateur importe un fichier .xlsx calqué sur les modèles déposés à la
racine (*Tableau dimensionnement ventouses.png* / *vidanges.png*).
Les colonnes saisies par l'utilisateur sont lues ; les colonnes calculées
(dénivelée, pentes, Q air pour les ventouses ; dénivelée, diamètres pour les
vidanges) sont remplies automatiquement par Python avec les formules de l'app.

Le fichier résultat peut ensuite être ré-exporté comme rapport XLSX classique.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from debits_ae.tableau_modele import (
    LigneVentouse,
    LigneVidange,
    COLONNES_VENTOUSE_TOUTES,
    COLONNES_VIDANGE_TOUTES,
    MODELES_DISPONIBLES,
)
from debits_ae.models import DonneesProjet
from . import audit as audit_data


# ---------------------------------------------------------------------------
# Alias de colonnes pour le matching souple
# ---------------------------------------------------------------------------
_ALIAS_VENTOUSE: dict[str, list[str]] = {
    "pm": ["pm", "point haut", "pm projet"],
    "cote projet (ventouse)": ["cote projet", "cote ventouse", "cote projet (ventouse)"],
    "pm am": ["pm am", "pm amont", "vidange amont"],
    "cote projet (amont)": ["cote projet (amont)", "cote amont"],
    "pm aval": ["pm aval", "vidange aval"],
    "cote projet (aval)": ["cote projet (aval)", "cote aval"],
    "dn conduite (m)": ["dn conduite", "dn", "diametre conduite", "diametre conduite (m)"],
    "longueur tronçon amont (m)": [
        "longueur tronçon amont", "longueur troncon amont", "l amont",
    ],
    "longueur tronçon aval (m)": [
        "longueur tronçon aval", "longueur troncon aval", "l aval",
    ],
    "equipement du point haut": ["equipement", "equipement du point haut", "materiel"],
    "debit d'air admis équipé (m3/s)": [
        "debit d'air admis", "debit admis equipe", "q admis equipe",
    ],
}

_ALIAS_VIDANGE: dict[str, list[str]] = {
    "pm am": ["pm am", "pm amont", "vidange"],
    "cprojet am": ["cprojet am", "cote projet am", "cote amont"],
    "pm (ventouse amont)": ["pm (ventouse amont)", "pm ventouse amont"],
    "cprojet (ventouse amont)": ["cprojet (ventouse amont)", "cote projet ventouse amont"],
    "pm (ventouse aval)": ["pm (ventouse aval)", "pm ventouse aval"],
    "cprojet (ventouse aval)": ["cprojet (ventouse aval)", "cote projet ventouse aval"],
    "dn conduite (m)": ["dn conduite", "dn", "diametre conduite", "diametre conduite (m)"],
    "longueur tronçon amont (m)": ["longueur tronçon amont", "longueur troncon amont", "l amont"],
    "longueur tronçon aval (m)": ["longueur tronçon aval", "longueur troncon aval", "l aval"],
}


def _norm(texte: str) -> str:
    if texte is None:
        return ""
    t = str(texte).lower().strip()
    t = t.replace("à", "a").replace("â", "a").replace("ä", "a")
    t = t.replace("é", "e").replace("è", "e").replace("ê", "e").replace("ë", "e")
    t = t.replace("î", "i").replace("ï", "i")
    t = t.replace("ô", "o").replace("ö", "o")
    t = t.replace("ù", "u").replace("û", "u").replace("ü", "u")
    t = t.replace("ç", "c")
    t = t.replace("œ", "oe").replace("æ", "ae")
    t = t.replace("ξ", "xi").replace("√", "sqrt")
    t = t.replace("é", "e")
    import re
    t = re.sub(r"[^a-z0-9%/\-(). ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _nombre(valeur: Any) -> float | None:
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
    import re
    texte = re.sub(r"[^0-9.\-+eE]", "", texte)
    try:
        return float(texte)
    except ValueError:
        return None


def _texte(valeur: Any) -> str:
    if valeur is None:
        return ""
    return str(valeur).strip()


# ---------------------------------------------------------------------------
# Résultat d'import
# ---------------------------------------------------------------------------
@dataclass
class ResultatImportTableau:
    modele: str
    lignes_lues: int = 0
    lignes_traitees: int = 0
    avertissements: list[str] = field(default_factory=list)
    donnees_brutes: list[dict[str, Any]] = field(default_factory=list)
    lignes_ventouse: list[LigneVentouse] = field(default_factory=list)
    lignes_vidange: list[LigneVidange] = field(default_factory=list)


def _match_colonnes(
    en_tetes: list[str], aliases: dict[str, list[str]]
) -> dict[str, int]:
    """Associe chaque nom interne à l'index de colonne trouvé dans le fichier."""
    mapping: dict[str, int] = {}
    for interne, liste_aliases in aliases.items():
        norm_interne = _norm(interne)
        for i, entete in enumerate(en_tetes):
            norm_entete = _norm(entete)
            if norm_entete == norm_interne or norm_entete in [_norm(a) for a in liste_aliases]:
                mapping[interne] = i
                break
    return mapping


def detecter_modele(en_tetes: list[str]) -> str | None:
    """Détermine automatiquement si un en-tête correspond à un modèle ventouse ou vidange.

    Retourne le nom du modèle ou ``None`` si aucun ne correspond.
    """
    score_ventouse = 0
    score_vidange = 0
    for entete in en_tetes:
        norm = _norm(entete)
        if any(mot in norm for mot in ["ventouse", "pm", "cote projet", "equipement", "qair", "pente"]):
            score_ventouse += 1
        if any(mot in norm for mot in ["vidange", "diametre", "cprojet", "dno conduite"]):
            score_vidange += 1

    if score_ventouse > score_vidange and score_ventouse > 0:
        return MODELES_DISPONIBLES[0].nom
    if score_vidange > score_ventouse and score_vidange > 0:
        return MODELES_DISPONIBLES[1].nom
    return None


def importer_tableau(
    chemin: str | Path,
    modele_nom: str | None = None,
    donnees: DonneesProjet | None = None,
) -> ResultatImportTableau:
    """Importe un fichier .xlsx et calcule les colonnes automatiques.

    Si ``modele_nom`` est ``None``, le modèle est détecté automatiquement
    à partir des en-têtes du fichier.

    Parameters
    ----------
    chemin : chemin du fichier .xlsx à importer.
    modele_nom : nom du modèle (optionnel, détection automatique si omis).
    donnees : données partagées du projet (pour K, ξ, D, etc.).
    """
    chemin = Path(chemin)
    if donnees is None:
        donnees = DonneesProjet()

    # Lecture rapide des en-têtes pour la détection automatique
    try:
        wb_test = load_workbook(chemin, data_only=True, read_only=True)
        feuille_test = None
        for nom in wb_test.sheetnames:
            f = wb_test[nom]
            if f.max_row > 1:
                feuille_test = f
                break
        en_tetes_test = []
        if feuille_test is not None:
            en_tetes_test = [
                _norm(str(c)) if c is not None else ""
                for c in list(feuille_test.iter_rows(values_only=True))[0]
            ]
        wb_test.close()
    except Exception:
        en_tetes_test = []

    if modele_nom is None:
        modele_nom = detecter_modele(en_tetes_test)

    resultat = ResultatImportTableau(modele=modele_nom or "Inconnu")

    if modele_nom is None:
        resultat.avertissements.append(
            "Modèle non reconnu : le fichier ne correspond ni à un tableau "
            "ventouse ni à un tableau vidange."
        )
        return resultat

    modele = next(
        (m for m in MODELES_DISPONIBLES if m.nom == modele_nom), None
    )
    if modele is None:
        resultat.avertissements.append(f"Modèle inconnu : {modele_nom}")
        return resultat

    try:
        wb = load_workbook(chemin, data_only=True, read_only=True)
    except Exception as exc:
        resultat.avertissements.append(f"Impossible d'ouvrir le classeur : {exc}")
        return resultat

    # On prend la première feuille contenant des données
    feuille = None
    for nom in wb.sheetnames:
        f = wb[nom]
        if f.max_row > 1:
            feuille = f
            break
    if feuille is None:
        wb.close()
        resultat.avertissements.append("Aucune feuille avec données trouvée.")
        return resultat

    lignes = list(feuille.iter_rows(values_only=True))
    wb.close()

    if len(lignes) < 2:
        resultat.avertissements.append("Le fichier ne contient qu'une ligne d'en-tête.")
        return resultat

    en_tetes = [_norm(str(c)) if c is not None else "" for c in lignes[0]]

    if "ventouse" in modele_nom.lower():
        mapping = _match_colonnes(en_tetes, _ALIAS_VENTOUSE)
        resultat.lignes_ventouse = _traiter_ventouses(
            lignes[1:], mapping, donnees, resultat
        )
    else:
        mapping = _match_colonnes(en_tetes, _ALIAS_VIDANGE)
        resultat.lignes_vidange = _traiter_vidanges(
            lignes[1:], mapping, donnees, resultat
        )

    resultat.lignes_lues = len(lignes) - 1
    resultat.lignes_traitees = (
        len(resultat.lignes_ventouse) + len(resultat.lignes_vidange)
    )
    return resultat


# ---------------------------------------------------------------------------
# Traitement VENTOUSES
# ---------------------------------------------------------------------------
def _traiter_ventouses(
    lignes: list[tuple],
    mapping: dict[str, int],
    donnees: DonneesProjet,
    resultat: ResultatImportTableau,
) -> list[LigneVentouse]:
    sorties: list[LigneVentouse] = []
    for idx, row in enumerate(lignes, start=2):
        def val(cle: str) -> Any:
            i = mapping.get(cle)
            if i is None or i >= len(row):
                return None
            return row[i]

        ligne = LigneVentouse(
            pm=_texte(val("pm")),
            cote_projet=_nombre(val("cote projet (ventouse)")),
            pm_am=_texte(val("pm am")),
            cote_amont=_nombre(val("cote projet (amont)")),
            pm_aval=_texte(val("pm aval")),
            cote_aval=_nombre(val("cote projet (aval)")),
            dn_conduite=_nombre(val("dn conduite (m)")),
            longueur_amont=_nombre(val("longueur tronçon amont (m)")),
            longueur_aval=_nombre(val("longueur tronçon aval (m)")),
            equipement=_texte(val("equipement du point haut")),
            debit_admis_equipe=_nombre(val("debit d'air admis équipé (m3/s)")),
        )

        if not ligne.pm and ligne.cote_projet is None:
            continue  # ligne vide

        resultat.donnees_brutes.append(
            {
                "ligne": idx,
                "pm": ligne.pm,
                "cote_projet": ligne.cote_projet,
            }
        )

        # Calcul automatique
        ligne.calculer(
            cote_ventouse=donnees.cote_ventouse,
            cote_vidange=donnees.cote_vidange,
            longueur_troncon=donnees.longueur_troncon,
            diametre_conduit=donnees.diam_conduit or (ligne.dn_conduite or 0.0),
            coeff_rugosite=donnees.coeff_rugosite,
            coeff_singularites=donnees.coeff_singularites,
        )
        sorties.append(ligne)

    return sorties


# ---------------------------------------------------------------------------
# Traitement VIDANGES
# ---------------------------------------------------------------------------
def _traiter_vidanges(
    lignes: list[tuple],
    mapping: dict[str, int],
    donnees: DonneesProjet,
    resultat: ResultatImportTableau,
) -> list[LigneVidange]:
    sorties: list[LigneVidange] = []
    for idx, row in enumerate(lignes, start=2):
        def val(cle: str) -> Any:
            i = mapping.get(cle)
            if i is None or i >= len(row):
                return None
            return row[i]

        ligne = LigneVidange(
            pm_am=_texte(val("pm am")),
            cprojet_am=_nombre(val("cprojet am")),
            pm_ventouse_am=_texte(val("pm (ventouse amont)")),
            cprojet_ventouse_am=_nombre(val("cprojet (ventouse amont)")),
            pm_ventouse_av=_texte(val("pm (ventouse aval)")),
            cprojet_ventouse_av=_nombre(val("cprojet (ventouse aval)")),
            dn_conduite=_nombre(val("dn conduite (m)")),
            longueur_amont=_nombre(val("longueur tronçon amont (m)")),
            longueur_aval=_nombre(val("longueur tronçon aval (m)")),
        )

        if not ligne.pm_am and ligne.cprojet_am is None:
            continue

        resultat.donnees_brutes.append(
            {
                "ligne": idx,
                "pm_am": ligne.pm_am,
                "cprojet_am": ligne.cprojet_am,
            }
        )

        ligne.calculer(
            coeff_debit=donnees.coeff_debit_vidange,
            temps_vidange_h=donnees.temps_vidange_h,
            diametre_conduit=donnees.diam_conduit or (ligne.dn_conduite or 0.0),
        )
        sorties.append(ligne)

    return sorties


# ---------------------------------------------------------------------------
# Export du résultat vers un nouveau XLSX (avec colonnes calculées remplies)
# ---------------------------------------------------------------------------
def exporter_resultat_tableau(
    resultat: ResultatImportTableau,
    chemin_sortie: str | Path,
) -> Path:
    """Écrit le résultat de l'import dans un nouveau fichier .xlsx."""
    chemin_sortie = Path(chemin_sortie)
    wb = Workbook()

    if "ventouse" in resultat.modele.lower():
        ws = wb.active
        ws.title = "Ventouses"
        entetes = COLONNES_VENTOUSE_TOUTES
        lignes = []
        for l in resultat.lignes_ventouse:
            lignes.append(
                [
                    l.pm,
                    l.cote_projet,
                    l.pm_am,
                    l.cote_amont,
                    l.pm_aval,
                    l.cote_aval,
                    l.dn_conduite,
                    l.longueur_amont,
                    l.longueur_aval,
                    l.equipement,
                    l.debit_admis_equipe,
                    l.denivelee_amont,
                    l.denivelee_aval,
                    l.pente_amont,
                    l.pente_aval,
                    l.qair_amont,
                    l.qair_aval,
                    l.qair_max,
                ]
            )
    else:
        ws = wb.active
        ws.title = "Vidanges"
        entetes = COLONNES_VIDANGE_TOUTES
        lignes = []
        for l in resultat.lignes_vidange:
            lignes.append(
                [
                    l.pm_am,
                    l.cprojet_am,
                    l.pm_ventouse_am,
                    l.cprojet_ventouse_am,
                    l.pm_ventouse_av,
                    l.cprojet_ventouse_av,
                    l.dn_conduite,
                    l.longueur_amont,
                    l.longueur_aval,
                    l.denivelee_amont,
                    l.denivelee_aval,
                    l.diametre_t1h,
                    l.diametre_t2h,
                    l.diametre_retenu_t2h,
                    l.diametre_vidange,
                ]
            )

    # Style en-tête
    remplissage = PatternFill("solid", fgColor="1F3B5C")
    police = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(entetes, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = remplissage
        cell.font = police
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Données
    for r, ligne in enumerate(lignes, start=2):
        for c, val in enumerate(ligne, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Largeurs
    for c in range(1, len(entetes) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 22

    wb.save(chemin_sortie)
    return chemin_sortie


# ---------------------------------------------------------------------------
# Vérification contre l'audit
# ---------------------------------------------------------------------------
@dataclass
class EcartAudit:
    """Un écart entre une valeur calculée et la référence de l'audit."""

    pm: str
    domaine: str  # "points_hauts" ou "vidanges"
    valeur_calculee: float
    valeur_reference: float
    ecart_absolu: float
    ecart_pct: float
    statut: str  # "OK", "ÉCART", "SOUS-ÉQUIPÉ"


def verifier_contre_audit(
    resultat: ResultatImportTableau,
) -> list[EcartAudit]:
    """Compare les valeurs calculées dans le tableau importé avec les références de l'audit.

    Returns
    -------
    list[EcartAudit]
        Liste des écarts détectés. Vide si tout correspond.
    """
    ecarts: list[EcartAudit] = []

    # Index de référence par PM
    ref_ph = {ligne.pm: ligne for ligne in audit_data.COMPARATIF_POINTS_HAUTS}
    ref_vid = {ligne.pm: ligne for ligne in audit_data.COMPARATIF_VIDANGES}

    # --- Vérification des points hauts (ventouses) ---
    for ligne in resultat.lignes_ventouse:
        ref = ref_ph.get(ligne.pm)
        if ref is None:
            continue

        # Comparer le Qair calculé (max des deux tronçons) avec la référence corrigée
        qair_calc = ligne.qair_max or 0.0
        qair_ref = ref.qair_corrige

        if qair_ref > 0:
            ecart_abs = qair_calc - qair_ref
            ecart_pct = 100.0 * ecart_abs / qair_ref
        else:
            ecart_abs = qair_calc
            ecart_pct = 0.0

        if abs(ecart_pct) <= 5.0:
            statut = "OK"
        elif qair_calc < qair_ref:
            statut = "SOUS-ÉQUIPÉ"
        else:
            statut = "ÉCART"

        ecarts.append(
            EcartAudit(
                pm=ligne.pm,
                domaine="points_hauts",
                valeur_calculee=round(qair_calc, 3),
                valeur_reference=round(qair_ref, 3),
                ecart_absolu=round(ecart_abs, 3),
                ecart_pct=round(ecart_pct, 1),
                statut=statut,
            )
        )

    # --- Vérification des vidanges ---
    for ligne in resultat.lignes_vidange:
        ref = ref_vid.get(ligne.pm_am)
        if ref is None:
            continue

        d_calc = ligne.diametre_t2h or 0.0
        d_ref = ref.diametre_corrige_mm

        if d_ref > 0:
            ecart_abs = d_calc - d_ref
            ecart_pct = 100.0 * ecart_abs / d_ref
        else:
            ecart_abs = d_calc
            ecart_pct = 0.0

        if abs(ecart_pct) <= 10.0:
            statut = "OK"
        elif d_calc < d_ref:
            statut = "SOUS-ÉQUIPÉ"
        else:
            statut = "ÉCART"

        ecarts.append(
            EcartAudit(
                pm=ligne.pm_am,
                domaine="vidanges",
                valeur_calculee=round(d_calc, 1),
                valeur_reference=round(d_ref, 1),
                ecart_absolu=round(ecart_abs, 1),
                ecart_pct=round(ecart_pct, 1),
                statut=statut,
            )
        )

    return ecarts
