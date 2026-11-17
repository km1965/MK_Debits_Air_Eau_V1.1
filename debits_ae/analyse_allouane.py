"""Analyse comparative : méthode Allouane vs méthode de l'app (F10).

Ce module :
1. Extrait les données du document ``rapport_allouane_BR3_TR2.docx`` (étude de casse
   franche par la méthode A. ALLOUANE 2026, approuvée).
2. Recalcule les débits d'air avec la formule de l'application (F10 : Bernoulli +
   Strickler, coefficient 0,000587 pour K=104, ξ=2).
3. Compare les résultats et génère un rapport d'écart.

Formule de l'app (F10, audit BR3_LOT8) :
    Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ]   (K = 104, ξ = 2)
    forme générale : v = √[ H / ( ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ) ]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx import Document

from debits_ae import qair_admission_casse, hauteur_motriere, G


# ---------------------------------------------------------------------------
# Données extraites du rapport Allouane BR3_TR2
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DonneesAllouane:
    """Données du tronçon BR3_TR2 issues du rapport Allouane."""

    # Conduite
    dn_nominal: float = 2000.0  # mm
    diametre_interieur: float = 2.0000  # m
    section: float = 3.1416  # m²
    rugosite_k: float = 0.0005  # m
    k_over_d: float = 2.500e-04  # —
    temperature: float = 15.0  # °C
    viscosite: float = 1.139e-06  # m²/s
    depression_admissible: float = 3.0  # mCE

    # Profil en long (schéma 3A)
    altitude_ve: float = 103.42  # m NGM (point haut)
    altitude_vi1: float = 4.87  # m NGM (vidange amont)
    altitude_vi2: float = 99.2  # m NGM (vidange aval)
    delta_h_brut: float = 98.55  # m (Ve − Vi1)
    longueur_l1: float = 351.01  # m (Vi1 → Ve)
    longueur_l2: float = 266.83  # m (Ve → Vi2)

    # Résultats de la méthode Allouane (référence approuvée)
    q_allouane_amont: float = 308173.4  # m³/h (ALLOUANE(ΔH=95.55, L=351.01))
    q_allouane_aval: float = 39763.0  # m³/h (ALLOUANE(ΔH=1.22, L=266.83))
    q_allouane_max: float = 308173.4  # m³/h = max(amont, aval)

    # Équipements proposés (client)
    nb_ventouses_dn200: int = 2
    nb_purgeurs_dn1500: int = 1
    nb_clapets_dn350_amont: int = 4
    nb_clapets_dn350_aval: int = 5

    # Capacités installées (m³/h à −3 mCE)
    cap_ventouses_total: float = 34000.0
    cap_clapets_amont: float = 138400.0
    cap_clapets_aval: float = 173000.0
    cap_purgeurs: float = 144.0
    capa_installee_totale: float = 345544.0

    # Verdict Allouane
    fs_allouane: float = 1.12  # Capacité installée / Demande


DONNEES_ALLOUANE = DonneesAllouane()


# ---------------------------------------------------------------------------
# Recalcul avec la méthode de l'app (F10)
# ---------------------------------------------------------------------------
@dataclass
class ResultatRecalcul:
    """Résultat d'un recalcul F10 pour un tronçon."""

    nom: str
    h_motrice: float  # m (net, après déduction des 3 mCE)
    longueur: float  # m
    diametre: float  # m
    coeff_rugosite: float  # K Strickler
    xi: float  # pertes singulières
    vitesse: float  # m/s
    debit_m3s: float  # m³/s
    debit_m3h: float  # m³/h
    alerte: bool


def recalculer_tronçon(
    nom: str,
    h_brut: float,
    longueur: float,
    diametre: float = 2.0,
    coeff_rugosite: float = 104.0,
    xi: float = 2.0,
    depression_admissible: float = 3.0,
) -> ResultatRecalcul:
    """Recalcule un tronçon avec la formule F10 de l'application.

    H_net = H_brut − dépression admissible (3 mCE)
    """
    h_net = max(0.0, h_brut - depression_admissible)
    v, q, _, alerte = qair_admission_casse(
        hauteur_motrice=h_net,
        longueur_troncon=longueur,
        diametre_conduit=diametre,
        coeff_rugosite=coeff_rugosite,
        coeff_singularites=xi,
    )
    return ResultatRecalcul(
        nom=nom,
        h_motrice=h_net,
        longueur=longueur,
        diametre=diametre,
        coeff_rugosite=coeff_rugosite,
        xi=xi,
        vitesse=v,
        debit_m3s=q,
        debit_m3h=q * 3600.0,
        alerte=alerte,
    )


def recalculer_tous_tronçons(
    donnees: DonneesAllouane = DONNEES_ALLOUANE,
) -> tuple[ResultatRecalcul, ResultatRecalcul]:
    """Recalcule les deux tronçons (amont et aval) avec F10."""
    amont = recalculer_tronçon(
        nom="Tronçon amont (Vi1 → Ve)",
        h_brut=donnees.delta_h_brut,
        longueur=donnees.longueur_l1,
        diametre=donnees.diametre_interieur,
        coeff_rugosite=donnees.rugosite_k and 104.0,  # PRV par défaut
        xi=2.0,
        depression_admissible=donnees.depression_admissible,
    )
    aval = recalculer_tronçon(
        nom="Tronçon aval (Ve → Vi2)",
        h_brut=donnees.altitude_ve - donnees.altitude_vi2,
        longueur=donnees.longueur_l2,
        diametre=donnees.diametre_interieur,
        coeff_rugosite=104.0,
        xi=2.0,
        depression_admissible=donnees.depression_admissible,
    )
    return amont, aval


# ---------------------------------------------------------------------------
# Comparaison Allouane vs App
# ---------------------------------------------------------------------------
@dataclass
class ComparaisonResultat:
    """Un résultat de comparaison pour un tronçon."""

    nom: str
    q_allouane_m3h: float
    q_app_m3h: float
    ecart_abs_m3h: float
    ecart_pct: float
    statut: str  # "CONFORME", "ÉCART", "SOUS-ÉVALUÉ", "SUR-ÉVALUÉ"


def comparer_allouane_vs_app(
    amont: ResultatRecalcul,
    aval: ResultatRecalcul,
    donnees: DonneesAllouane = DONNEES_ALLOUANE,
) -> list[ComparaisonResultat]:
    """Compare les résultats Allouane avec ceux de l'application."""
    resultats: list[ComparaisonResultat] = []

    # Amont
    q_all = donnees.q_allouane_amont
    q_app = amont.debit_m3h
    ecart_abs = q_app - q_all
    ecart_pct = 100.0 * ecart_abs / q_all if q_all > 0 else 0.0
    if abs(ecart_pct) <= 5.0:
        statut = "CONFORME"
    elif q_app < q_all:
        statut = "SOUS-ÉVALUÉ"
    else:
        statut = "SUR-ÉVALUÉ"
    resultats.append(
        ComparaisonResultat(
            nom=amont.nom,
            q_allouane_m3h=q_all,
            q_app_m3h=q_app,
            ecart_abs_m3h=ecart_abs,
            ecart_pct=ecart_pct,
            statut=statut,
        )
    )

    # Aval
    q_all = donnees.q_allouane_aval
    q_app = aval.debit_m3h
    ecart_abs = q_app - q_all
    ecart_pct = 100.0 * ecart_abs / q_all if q_all > 0 else 0.0
    if abs(ecart_pct) <= 5.0:
        statut = "CONFORME"
    elif q_app < q_all:
        statut = "SOUS-ÉVALUÉ"
    else:
        statut = "SUR-ÉVALUÉ"
    resultats.append(
        ComparaisonResultat(
            nom=aval.nom,
            q_allouane_m3h=q_all,
            q_app_m3h=q_app,
            ecart_abs_m3h=ecart_abs,
            ecart_pct=ecart_pct,
            statut=statut,
        )
    )

    return resultats


# ---------------------------------------------------------------------------
# Rapport texte
# ---------------------------------------------------------------------------
_FORMULES_REFERENCES = [
    {
        "nom": "F10 — Débit d'air admission (casse franche)",
        "origine": "Audit BR3_LOT 8 — PDF page 5 (méthode de l'application)",
        "reference": "Audit_et_Correction_Note_BR3_LOT8.docx, Partie 2.4",
        "formule_clair": "Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ] pour K = 104 et ξ = 2",
        "formule_generale": "v = √[ H / ( ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ) ] ; Qair = Qeau = v·πD²/4",
        "commentaires": "0,102 = 1/g ; 0,000587 = 4^(4/3)/104². L'audit retient ξ = 2 (mention « k = 2 »).",
    },
    {
        "nom": "F11 — Hauteur motrice nette",
        "origine": "Audit BR3_LOT 8 — page 6 (méthode de l'application)",
        "reference": "Audit_et_Correction_Note_BR3_LOT8.docx, Partie 1.3",
        "formule_clair": "H = max(0 ; cote_ventouse − 3 − cote_vidange)",
        "formule_generale": "H = max(0 ; z_ventouse − dépression_max − z_vidange)",
        "commentaires": "Dépression max = 3 mCE (NF EN 805). La borne à 0 évite une hauteur négative.",
    },
    {
        "nom": "F8 — Débit d'eau / ligne d'énergie (Strickler)",
        "origine": "Audit BR3_LOT 8 — forme corrigée (méthode de l'application)",
        "reference": "Audit_et_Correction_Note_BR3_LOT8.docx, Partie 1.2",
        "formule_clair": "Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5 = 0,3117 · K · D^(8/3) · i^0,5",
        "formule_generale": "j = 4^(4/3) · v² / (K² · D^(4/3)) ; H = j·L + ξ·v²/(2g)",
        "commentaires": "Conduite pleine, rayon hydraulique R = D/4. K = 104 (PRV) ou 100 (fonte).",
    },
    {
        "nom": "Méthode A. ALLOUANE (référence)",
        "origine": "Document de vérification approuvé",
        "reference": "rapport_allouane_BR3_TR2.docx — Référence NC_allouane_2026-BR3-TR2",
        "formule_clair": "Q_Ve = ALLOUANE(ΔH, L) — formule explicite Darcy-Weisbach / Colebrook-White",
        "formule_generale": "Q_Ve (m³/h) fonction de ΔH (m) et L (m) — voir document source",
        "commentaires": "Validité : Re > 4000 et k/D ∈ [10⁻⁶ ; 10⁻²]. Résultat approuvé par le contrôleur.",
    },
]


def _section_formules_ref() -> list[str]:
    """Génère la section « Formules de calcul — origines et références »."""
    lignes: list[str] = []
    lignes.append("")
    lignes.append("FORMULES DE CALCUL — ORIGINES ET RÉFÉRENCES")
    lignes.append("=" * 80)
    lignes.append("")
    for f in _FORMULES_REFERENCES:
        lignes.append(f"• {f['nom']}")
        lignes.append(f"  Origine : {f['origine']}")
        lignes.append(f"  Référence : {f['reference']}")
        lignes.append(f"  Formule : {f['formule_clair']}")
        lignes.append(f"  Forme générale : {f['formule_generale']}")
        lignes.append(f"  Commentaires : {f['commentaires']}")
        lignes.append("")
    return lignes


def generer_rapport_texte(
    donnees: DonneesAllouane = DONNEES_ALLOUANE,
) -> str:
    """Génère un rapport de comparaison complet en français."""
    amont, aval = recalculer_tous_tronçons(donnees)
    comparaisons = comparer_allouane_vs_app(amont, aval, donnees)

    lignes: list[str] = []
    lignes.append("=" * 80)
    lignes.append("COMPARATIF : MÉTHODE ALLOUANE vs MÉTHODE DE L'APPLICATION (F10)")
    lignes.append("Document : rapport_allouane_BR3_TR2.docx — Casse franche, méthode A. ALLOUANE 2026")
    lignes.append("Tronçon : BR3_TR2 · Schéma de vidange 3A")
    lignes.append("=" * 80)
    lignes.append("")

    # 1. Données d'entrée
    lignes.append("1. DONNÉES D'ENTRÉE (rapport Allouane)")
    lignes.append("-" * 80)
    lignes.append(f"  Diamètre nominal : {donnees.dn_nominal} mm")
    lignes.append(f"  Diamètre intérieur : {donnees.diametre_interieur} m")
    lignes.append(f"  Rugosité k : {donnees.rugosite_k} m (k/D = {donnees.k_over_d:.2e})")
    lignes.append(f"  Dépression admissible : {donnees.depression_admissible} mCE")
    lignes.append(f"  Altitude point haut Ve : {donnees.altitude_ve} m NGM")
    lignes.append(f"  Altitude vidange amont Vi1 : {donnees.altitude_vi1} m NGM")
    lignes.append(f"  Altitude vidange aval Vi2 : {donnees.altitude_vi2} m NGM")
    lignes.append(f"  ΔH brut (Ve − Vi1) : {donnees.delta_h_brut} m")
    lignes.append(f"  Longueur L1 (Vi1 → Ve) : {donnees.longueur_l1} m")
    lignes.append(f"  Longueur L2 (Ve → Vi2) : {donnees.longueur_l2} m")
    lignes.append("")

    # 2. Résultats Allouane (référence)
    lignes.append("2. RÉFÉRENCE : MÉTHODE ALLOUANE 2026 (résultats approuvés)")
    lignes.append("-" * 80)
    lignes.append(f"  Q_allouane amont  = {donnees.q_allouane_amont:,.1f} m³/h (ΔH=95.55 m, L=351.01 m)")
    lignes.append(f"  Q_allouane aval   = {donnees.q_allouane_aval:,.1f} m³/h (ΔH=1.22 m, L=266.83 m)")
    lignes.append(f"  Q_Ve (max)        = {donnees.q_allouane_max:,.1f} m³/h")
    lignes.append(f"  Capacité installée = {donnees.capa_installee_totale:,.0f} m³/h")
    lignes.append(f"  Fs Allouane       = {donnees.fs_allouane:.2f}")
    lignes.append("")

    # 3. Recalcul avec l'app (F10)
    lignes.append("3. RECALCUL AVEC LA MÉTHODE DE L'APPLICATION (F10 — Bernoulli + Strickler)")
    lignes.append("-" * 80)
    lignes.append(f"  Formule : Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ]")
    lignes.append(f"            K = 104 (PRV), ξ = 2 (pertes singulières, audit BR3_LOT8)")
    lignes.append("")
    for r in (amont, aval):
        lignes.append(f"  {r.nom} :")
        lignes.append(f"    H motrice net   = {r.h_motrice:.2f} m")
        lignes.append(f"    Longueur        = {r.longueur:.2f} m")
        lignes.append(f"    Vitesse v       = {r.vitesse:.3f} m/s")
        lignes.append(f"    Débit Qair      = {r.debit_m3h:,.1f} m³/h ({r.debit_m3s:.3f} m³/s)")
        lignes.append("")
    q_total_app = amont.debit_m3h + aval.debit_m3h
    lignes.append(f"  Q_total app (amont + aval) = {q_total_app:,.1f} m³/h")
    lignes.append("")

    # 4. Comparaison
    lignes.append("4. COMPARAISON ALLOUANE vs APPLICATION")
    lignes.append("-" * 80)
    for c in comparaisons:
        lignes.append(f"  {c.nom} :")
        lignes.append(f"    Allouane : {c.q_allouane_m3h:,.1f} m³/h")
        lignes.append(f"    App      : {c.q_app_m3h:,.1f} m³/h")
        lignes.append(f"    Écart    : {c.ecart_abs_m3h:+,.1f} m³/h ({c.ecart_pct:+.1f} %)")
        lignes.append(f"    Statut   : {c.statut}")
        lignes.append("")
    lignes.append("")

    # 5. Verdict équipements
    lignes.append("5. VÉRIFICATION DES ÉQUIPEMENTS (besoin recalculé par l'app)")
    lignes.append("-" * 80)
    q_besoin_app = max(amont.debit_m3h, aval.debit_m3h)
    fs_app = donnees.capa_installee_totale / q_besoin_app if q_besoin_app > 0 else 0.0
    lignes.append(f"  Besoin réel (max amont/avail, app) = {q_besoin_app:,.1f} m³/h")
    lignes.append(f"  Capacité installée                  = {donnees.capa_installee_totale:,.0f} m³/h")
    lignes.append(f"  Fs (app)                            = {fs_app:.2f}")
    verdict = "COUVERT" if fs_app >= 1.0 else "SOUS-DIMENSIONNÉ"
    lignes.append(f"  Verdict                             = {verdict} (Fs {'≥' if fs_app >= 1.0 else '<'} 1,00)")
    lignes.append("")

    # 6. Conclusion
    lignes.append("6. CONCLUSION")
    lignes.append("-" * 80)
    for c in comparaisons:
        lignes.append(f"  {c.nom} : {c.statut} (écart {c.ecart_pct:+.1f} %)")
    lignes.append("")

    # 7. Formules de calcul — origines et références
    lignes.extend(_section_formules_ref())

    lignes.append("=" * 80)

    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Rapport DOCX détaillé
# ---------------------------------------------------------------------------
def generer_rapport_allouane_docx(
    chemin: str | Path,
    donnees: DonneesAllouane = DONNEES_ALLOUANE,
    amont: ResultatRecalcul | None = None,
    aval: ResultatRecalcul | None = None,
    comparaisons: list[ComparaisonResultat] | None = None,
) -> Path:
    """Génère un rapport Word .docx détaillé de l'analyse comparative Allouane vs App.

    Contient :
    1. En-tête et identifiant du projet
    2. Données d'entrée du tronçon
    3. Référence Allouane (résultats approuvés)
    4. Recalcul F10 détaillé (méthode de l'application)
    5. Comparaison Allouane vs Application
    6. Vérification des équipements (Fs)
    7. Formules de calcul — origines et références
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    if amont is None or aval is None:
        amont, aval = recalculer_tous_tronçons(donnees)
    if comparaisons is None:
        comparaisons = comparer_allouane_vs_app(amont, aval, donnees)

    doc = Document()

    # Style par défaut
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(11)

    COULEUR_TITRE = RGBColor(0x1F, 0x3B, 0x5C)
    COULEUR_ALERTE = RGBColor(0xB0, 0x00, 0x00)
    COULEUR_OK = RGBColor(0x1E, 0x6B, 0x1E)

    def _titre(texte: str, niveau: int = 0) -> None:
        p = doc.add_heading(texte, level=niveau)
        for run in p.runs:
            run.font.color.rgb = COULEUR_TITRE
        return p

    def _paragraphe(
        texte: str, gras: bool = False, taille: int = 11, couleur: RGBColor | None = None
    ) -> None:
        p = doc.add_paragraph()
        run = p.add_run(texte)
        run.bold = gras
        run.font.size = Pt(taille)
        if couleur is not None:
            run.font.color.rgb = couleur
        return p

    def _tableau(entetes: list[str], lignes: list[list[str]]) -> None:
        table = doc.add_table(rows=1, cols=len(entetes))
        table.style = "Light Grid Accent 1"
        for i, h in enumerate(entetes):
            cell = table.rows[0].cells[i]
            cell.text = h
            for pr in cell.paragraphs:
                for run in pr.runs:
                    run.bold = True
                    run.font.size = Pt(10)
        for ligne in lignes:
            cells = table.add_row().cells
            for i, val in enumerate(ligne):
                cells[i].text = str(val)
                for pr in cells[i].paragraphs:
                    for run in pr.runs:
                        run.font.size = Pt(10)

    # =========================================================================
    # En-tête
    # =========================================================================
    titre = doc.add_heading("Rapport d'analyse comparative — Allouane vs Application", level=0)
    for run in titre.runs:
        run.font.color.rgb = COULEUR_TITRE
        run.font.size = Pt(20)

    _paragraphe(
        f"Projet : BR3_TR2 (DN {donnees.dn_nominal} mm)", gras=True, taille=12
    )
    _paragraphe(
        "Référence du document source : rapport_allouane_BR3_TR2.docx", taille=11
    )
    _paragraphe(
        f"Date de génération : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        taille=10,
        couleur=RGBColor(0x80, 0x80, 0x80),
    )
    doc.add_paragraph()

    # =========================================================================
    # 1. Données d'entrée
    # =========================================================================
    _titre("1. Données d'entrée du tronçon (rapport Allouane)", 1)
    _paragraphe(
        f"Diamètre nominal : {donnees.dn_nominal} mm", taille=10
    )
    _paragraphe(
        f"Diamètre intérieur D : {donnees.diametre_interieur} m", taille=10
    )
    _paragraphe(
        f"Section S = π/4·D² : {donnees.section} m²", taille=10
    )
    _paragraphe(
        f"Rugosité k : {donnees.rugosite_k} m (k/D = {donnees.k_over_d:.2e})", taille=10
    )
    _paragraphe(
        f"Dépression admissible : {donnees.depression_admissible} mCE (NF EN 805)", taille=10
    )
    _paragraphe(
        f"Température : {donnees.temperature} °C — Viscosité ν : {donnees.viscosite} m²/s", taille=10
    )
    doc.add_paragraph()

    _titre("1.1 Profil en long (schéma 3A)", 2)
    _paragraphe(
        f"Altitude point haut Ve : {donnees.altitude_ve} m NGM", taille=10
    )
    _paragraphe(
        f"Altitude vidange amont Vi1 : {donnees.altitude_vi1} m NGM", taille=10
    )
    _paragraphe(
        f"Altitude vidange aval Vi2 : {donnees.altitude_vi2} m NGM", taille=10
    )
    _paragraphe(
        f"ΔH brut (Ve − Vi1) : {donnees.delta_h_brut} m", taille=10
    )
    _paragraphe(
        f"Longueur L1 (Vi1 → Ve) : {donnees.longueur_l1} m", taille=10
    )
    _paragraphe(
        f"Longueur L2 (Ve → Vi2) : {donnees.longueur_l2} m", taille=10
    )
    doc.add_paragraph()

    # =========================================================================
    # 2. Référence Allouane
    # =========================================================================
    _titre("2. Référence — Méthode A. ALLOUANE 2026 (résultats approuvés)", 1)
    _paragraphe(
        f"Q Allouane amont  = {donnees.q_allouane_amont:,.1f} m³/h "
        f"(ΔH=95,55 m, L=351,01 m)", taille=10
    )
    _paragraphe(
        f"Q Allouane aval   = {donnees.q_allouane_aval:,.1f} m³/h "
        f"(ΔH=1,22 m, L=266,83 m)", taille=10
    )
    _paragraphe(
        f"Q_Ve (max)        = {donnees.q_allouane_max:,.1f} m³/h", taille=10
    )
    _paragraphe(
        f"Capacité installée  = {donnees.capa_installee_totale:,.0f} m³/h", taille=10
    )
    _paragraphe(
        f"Fs Allouane         = {donnees.fs_allouane:.2f}", taille=10
    )
    _paragraphe(
        "Source : rapport_allouane_BR3_TR2.docx — Référence NC_allouane_2026-BR3-TR2",
        taille=9,
        couleur=RGBColor(0x80, 0x80, 0x80),
    )
    doc.add_paragraph()

    # =========================================================================
    # 3. Recalcul F10 (méthode de l'application)
    # =========================================================================
    _titre("3. Recalcul avec la méthode de l'application (F10)", 1)
    _paragraphe(
        "Formule F10 (audit BR3_LOT 8) : Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ]",
        taille=10,
    )
    _paragraphe(
        "Forme générale : v = √[ H / ( ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ) ], Qair = Qeau = v·πD²/4",
        taille=10,
    )
    _paragraphe(
        "K = 104 (PRV), ξ = 2 (pertes singulières, retenue par l'audit), 0,102 = 1/g",
        taille=10,
    )
    doc.add_paragraph()

    for r in (amont, aval):
        _titre(f"3.1 {r.nom}", 2)
        _paragraphe(f"H motrice net   = {r.h_motrice:.2f} m", taille=10)
        _paragraphe(f"Longueur        = {r.longueur:.2f} m", taille=10)
        _paragraphe(f"Diamètre        = {r.diametre} m", taille=10)
        _paragraphe(f"K Strickler     = {r.coeff_rugosite}", taille=10)
        _paragraphe(f"ξ (pertes sing.) = {r.xi}", taille=10)
        _paragraphe(f"Vitesse v       = {r.vitesse:.3f} m/s", taille=10)
        _paragraphe(f"Débit Qair      = {r.debit_m3h:,.1f} m³/h ({r.debit_m3s:.3f} m³/s)", taille=10)
        doc.add_paragraph()

    q_total_app = amont.debit_m3h + aval.debit_m3h
    _paragraphe(
        f"Q_total app (amont + aval) = {q_total_app:,.1f} m³/h",
        gras=True,
        taille=10,
    )
    doc.add_paragraph()

    # =========================================================================
    # 4. Comparaison
    # =========================================================================
    _titre("4. Comparaison Allouane vs Application", 1)
    _tableau(
        ["Tronçon", "Q Allouane (m³/h)", "Q App (m³/h)", "Écart absolu (m³/h)", "Écart (%)", "Statut"],
        [
            [
                c.nom,
                f"{c.q_allouane_m3h:,.1f}",
                f"{c.q_app_m3h:,.1f}",
                f"{c.ecart_abs_m3h:+,.1f}",
                f"{c.ecart_pct:+.1f} %",
                c.statut,
            ]
            for c in comparaisons
        ],
    )
    doc.add_paragraph()

    for c in comparaisons:
        _paragraphe(
            f"{c.nom} : Allouane = {c.q_allouane_m3h:,.1f} m³/h ; "
            f"App = {c.q_app_m3h:,.1f} m³/h ; écart = {c.ecart_pct:+.1f} % ; "
            f"statut = {c.statut}",
            taille=10,
        )
    doc.add_paragraph()

    # =========================================================================
    # 5. Vérification équipements
    # =========================================================================
    _titre("5. Vérification des équipements (besoin recalculé par l'app)", 1)
    q_besoin_app = max(amont.debit_m3h, aval.debit_m3h)
    capa = donnees.capa_installee_totale
    fs_app = capa / q_besoin_app if q_besoin_app > 0 else 0.0
    verdict = "COUVERT" if fs_app >= 1.0 else "SOUS-DIMENSIONNÉ"
    couleur_verdict = COULEUR_OK if fs_app >= 1.0 else COULEUR_ALERTE

    _paragraphe(f"Besoin réel (max amont/aval, app) = {q_besoin_app:,.1f} m³/h", taille=10)
    _paragraphe(f"Capacité installée                = {capa:,.0f} m³/h", taille=10)
    _paragraphe(f"Fs (app)                          = {fs_app:.2f}", taille=10)
    _paragraphe(
        f"Verdict                           = {verdict} "
        f"(Fs {'≥' if fs_app >= 1.0 else '<'} 1,00)",
        gras=True,
        taille=10,
        couleur=couleur_verdict,
    )
    doc.add_paragraph()

    # =========================================================================
    # 6. Conclusion
    # =========================================================================
    _titre("6. Conclusion", 1)
    for c in comparaisons:
        _paragraphe(
            f"{c.nom} : {c.statut} (écart {c.ecart_pct:+.1f} %)",
            taille=10,
        )
    doc.add_paragraph()

    # =========================================================================
    # 7. Formules — origines et références
    # =========================================================================
    _titre("7. Formules de calcul — origines et références", 1)
    for f in _FORMULES_REFERENCES:
        _paragraphe(f"• {f['nom']}", gras=True, taille=10)
        _paragraphe(f"  Origine : {f['origine']}", taille=9)
        _paragraphe(f"  Référence : {f['reference']}", taille=9)
        _paragraphe(f"  Formule : {f['formule_clair']}", taille=9)
        _paragraphe(f"  Forme générale : {f['formule_generale']}", taille=9)
        _paragraphe(f"  Commentaires : {f['commentaires']}", taille=9)
        doc.add_paragraph()

    doc.add_paragraph()
    _paragraphe(
        "Fin du rapport. Généré par l'application MK_Debits_Air_Eau (onglet Allouane).",
        taille=9,
        couleur=RGBColor(0x80, 0x80, 0x80),
    )

    doc.save(str(chemin))
    return chemin


# =============================================================================
# Point d'entrée CLI
# =============================================================================
if __name__ == "__main__":
    print(generer_rapport_texte())
