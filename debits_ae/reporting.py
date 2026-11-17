"""Génération de rapports .docx et .xlsx pour l'application MK_Debits_Air_Eau.

Dependances : python-docx, openpyxl, matplotlib (deja presentes dans l'environnement).
Les graphiques sont generes en PNG a cote du rapport puis inseres dans les deux formats.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage

from .models import (
    VidangeResult,
    VentouseResult,
    EquipementChoice,
    VerificationResult,
    DonneesProjet,
)
from .formulas import (
    verifier_formules,
    FormuleVerifiee,
    qair_admission_casse,
    K_STRICKLER_PRC_DEFAUT,
)
from .charts import generer_tous_graphiques
from . import audit as audit_data
from .tables import TABLE_PAM, TABLE_SNH
from .import_tableau import ResultatImportTableau


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
_COULEUR_TITRE = RGBColor(0x1F, 0x3B, 0x5C)  # bleu foncé
_COULEUR_ALERTE = RGBColor(0xB0, 0x00, 0x00)  # rouge
_COULEUR_OK = RGBColor(0x1E, 0x6B, 0x1E)  # vert
_COULEUR_GRIS = RGBColor(0x80, 0x80, 0x80)


def _changer_orientation(doc: Document, paysage: bool):
    """Ajoute une nouvelle section et fixe son orientation (paysage/portrait)."""
    from docx.enum.section import WD_ORIENT, WD_SECTION

    section = doc.add_section(WD_SECTION.NEW_PAGE)
    largeur, hauteur = section.page_width, section.page_height
    if largeur is None or hauteur is None:
        largeur, hauteur = Cm(21.0), Cm(29.7)
    if paysage:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = max(largeur, hauteur)
        section.page_height = min(largeur, hauteur)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = min(largeur, hauteur)
        section.page_height = max(largeur, hauteur)
    for cote in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, cote, Cm(1.5))
    return section


def _ajouter_titre(doc: Document, texte: str, niveau: int = 0) -> None:
    p = doc.add_heading(texte, level=niveau)
    for run in p.runs:
        run.font.color.rgb = _COULEUR_TITRE
    return p


def _ajouter_paragraphe(
    doc: Document,
    texte: str,
    gras: bool = False,
    taille: int = 11,
    couleur: RGBColor | None = None,
) -> None:
    p = doc.add_paragraph()
    run = p.add_run(texte)
    run.bold = gras
    run.font.size = Pt(taille)
    if couleur is not None:
        run.font.color.rgb = couleur


def _ajouter_table_docx(doc: Document, en_tetes: list[str], lignes: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(en_tetes))
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(en_tetes):
        hdr[i].text = h
        for pr in hdr[i].paragraphs:
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


# ---------------------------------------------------------------------------
# Texte des formules F10 (écrit en clair, français)
# ---------------------------------------------------------------------------
def _texte_formule_f11(hauteur_motrice: float) -> str:
    return (
        f"F11 — Hauteur motrice H : H = max(0 ; cote de la ventouse − 3 m − cote de la vidange). "
        f"Dans ce projet, H = {hauteur_motrice:.3f} m. La borne à 0 évite une hauteur négative "
        f"lorsque la chute disponible est inférieure à la dépression de 3 mCE."
    )


def _texte_formule_f8() -> str:
    return (
        "F8 — Débit d'eau et ligne d'énergie (Strickler, conduite pleine, R = D/4) : "
        "Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5 = 0,3117 · K · D^(8/3) · i^0,5, "
        "soit j = 4^(4/3) · v² / (K² · D^(4/3)). K = 104 pour le PRV, 100 pour la fonte. "
        "Cette forme est cohérente avec le coefficient 0,000587 de F10."
    )


def _texte_formule_f10() -> str:
    return (
        "F10 — Débit d'air à admettre en casse franche (formule de l'audit) : la vitesse v se calcule "
        "en divisant la hauteur motrice H par la somme de (ξ divisé par 2g) et de "
        "(4^(4/3) fois L divisé par K² fois D^(4/3)). Le débit d'air Qair est alors égal à v multiplié "
        "par la section de la conduite (π·D²/4). Pour K = 104 et ξ = 2, cela s'écrit : "
        "Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ]. "
        "ξ = 1 correspond à l'équation écrite (v²/2g) ; ξ = 2 correspond à la mention « k = 2 » "
        "retenue par l'audit. Le choix de ξ reste exposé dans l'interface."
    )


def _ajouter_section_equipements_admission_docx(
    doc: Document, ventouse: VentouseResult, donnees: DonneesProjet
) -> None:
    """Ajoute la section récapitulatif équipements admission d'air (F10) au DOCX."""
    _ajouter_titre(doc, "5. Récapitulatif équipements — Admission d'air (F10)", 1)

    _ajouter_paragraphe(doc, "Formules utilisées (écrites en clair) :", gras=True, taille=11)
    _ajouter_paragraphe(doc, _texte_formule_f11(ventouse.hauteur_motrice), taille=10)
    _ajouter_paragraphe(doc, _texte_formule_f8(), taille=10)
    _ajouter_paragraphe(doc, _texte_formule_f10(), taille=10)
    doc.add_paragraph()

    _ajouter_paragraphe(
        doc,
        "Deux cas de calcul selon l'interprétation des pertes singulières (ξ) :",
        gras=True,
        taille=11,
    )

    v1, q1, _, _ = qair_admission_casse(
        ventouse.hauteur_motrice,
        donnees.longueur_troncon,
        donnees.diam_conduit,
        coeff_rugosite=donnees.coeff_rugosite,
        coeff_singularites=1.0,
    )
    v2, q2, _, _ = qair_admission_casse(
        ventouse.hauteur_motrice,
        donnees.longueur_troncon,
        donnees.diam_conduit,
        coeff_rugosite=donnees.coeff_rugosite,
        coeff_singularites=2.0,
    )

    _ajouter_table_docx(
        doc,
        ["Cas", "ξ", "Vitesse v (m/s)", "Débit air Qair (m³/s)"],
        [
            ["Équation écrite (v²/2g)", "1", f"{v1:.3f}", f"{q1:.4f}"],
            ["Mention k = 2 (v²/g)", "2", f"{v2:.3f}", f"{q2:.4f}"],
        ],
    )
    doc.add_paragraph()

    _ajouter_paragraphe(
        doc,
        "Ventouses triple fonction PAM — caractéristiques réelles (page 6 de la note) :",
        gras=True,
        taille=11,
    )
    lignes_pam = []
    for car in TABLE_PAM:
        converti = car.debit_admission_converti_m3s
        lignes_pam.append(
            [
                car.dn,
                f"{car.debit_admission_depression_3m_m3h:.0f}"
                if car.debit_admission_depression_3m_m3h is not None
                else "—",
                f"{car.debit_admission_depression_3m_m3s:.3f}"
                if car.debit_admission_depression_3m_m3s is not None
                else "—",
                f"{converti:.3f}" if converti is not None else "—",
                f"{car.debit_evacuation_surpression_1m_m3h:.0f}"
                if car.debit_evacuation_surpression_1m_m3h is not None
                else "—",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q1 else "Non",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q2 else "Non",
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "DN",
            "Admission 3 m (m³/h)",
            "Valeur imprimée (m³/s)",
            "Conversion exacte (m³/s)",
            "Évacuation 1 m (m³/h)",
            f"Couvre ξ = 1 ({q1:.2f} m³/s)",
            f"Couvre ξ = 2 ({q2:.2f} m³/s)",
        ],
        lignes_pam,
    )
    doc.add_paragraph()

    _ajouter_paragraphe(
        doc,
        "Clapets d'entrée d'air SNH — caractéristiques réelles (page 6 de la note) :",
        gras=True,
        taille=11,
    )
    lignes_snh = []
    for car in TABLE_SNH:
        lignes_snh.append(
            [
                car.dn,
                f"{car.debit_admission_depression_3m_m3h:.0f}"
                if car.debit_admission_depression_3m_m3h is not None
                else "—",
                f"{car.debit_admission_depression_3m_m3s:.2f}"
                if car.debit_admission_depression_3m_m3s is not None
                else "—",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q1 else "Non",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q2 else "Non",
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "DN",
            "Admission 3 m (m³/h)",
            "Admission (m³/s)",
            f"Couvre ξ = 1 ({q1:.2f} m³/s)",
            f"Couvre ξ = 2 ({q2:.2f} m³/s)",
        ],
        lignes_snh,
    )
    doc.add_paragraph()

    _ajouter_paragraphe(
        doc,
        "Combinaisons d'équipements réelles (aucune référence « PAM 800 » ou « SNH 800 » "
        "n'existe dans la note) :",
        gras=True,
        taille=11,
    )
    lignes_combinaisons = []
    for combo in audit_data.COMBINAISONS_EQUIPEMENTS:
        capacite = combo.capacite_m3s
        lignes_combinaisons.append(
            [
                combo.libelle,
                f"{capacite:.3f}",
                "Oui" if capacite >= q1 else "Non",
                "Oui" if capacite >= q2 else "Non",
                "Oui" if capacite >= ventouse.qair_admission else "Non",
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "Combinaison",
            "Capacité (m³/s)",
            f"Couvre ξ = 1 ({q1:.2f})",
            f"Couvre ξ = 2 ({q2:.2f})",
            f"Couvre le projet ({ventouse.qair_admission:.2f} m³/s)",
        ],
        lignes_combinaisons,
    )
    doc.add_paragraph()

    _ajouter_paragraphe(
        doc,
        "Signalement — conversion PAM DN200 : le tableau imprimé indique 14 454 m³/h et 4,165 m³/s, "
        "alors que 14 454 / 3600 = 4,015 m³/s (4,165 m³/s correspond à 14 994 m³/h). L'écart de "
        "0,150 m³/s (environ 3,7 %) n'est pas masqué : les combinaisons de l'audit utilisent la "
        "valeur imprimée 4,165 m³/s, et la conversion exacte est affichée en regard. Cet écart doit "
        "être tranché avec le fournisseur avant commande. Le choix entre ξ = 1 et ξ = 2 reste à "
        "valider par le bureau d'études.",
        taille=10,
        couleur=_COULEUR_ALERTE,
    )


# ---------------------------------------------------------------------------
# Section 8 — Audit et comparatif note initiale / note corrigée
# ---------------------------------------------------------------------------
def _ajouter_section_audit_docx(doc: Document) -> None:
    """Ajoute le comparatif « note initiale / note corrigée » issu de l'audit."""
    _ajouter_titre(doc, "8. Audit et comparatif note initiale / note corrigée", 1)
    _ajouter_paragraphe(
        doc,
        "Source : Audit_et_Correction_Note_BR3_LOT8.docx. Cette section reprend les erreurs "
        "relevées dans la note initiale, les corrections retenues et les tableaux recalculés "
        "des Annexes 1 (points hauts) et 2 (vidanges). Les valeurs de la note initiale sont "
        "conservées pour comparaison ; elles ne doivent plus servir de base de dimensionnement.",
        taille=10,
    )
    doc.add_paragraph()

    _ajouter_titre(doc, "8.1 Corrections de l'audit prises en compte", 2)
    lignes_corrections = [
        [
            c.code,
            c.domaine,
            c.constat,
            c.correction,
            c.application,
            "Appliquée" if c.appliquee else "À traiter",
        ]
        for c in audit_data.CORRECTIONS_AUDIT
    ]
    _ajouter_table_docx(
        doc,
        ["Code", "Domaine", "Constat de l'audit", "Correction retenue", "Application", "Statut"],
        lignes_corrections,
    )
    doc.add_paragraph()

    resume = audit_data.resume_points_hauts()
    sous_equipes = audit_data.points_hauts_sous_equipes()
    non_couverts = audit_data.points_hauts_non_couverts_apres_correction()
    liste_sous_equipes = ", ".join(ligne.pm for ligne in sous_equipes)
    _ajouter_paragraphe(
        doc,
        f"Bilan des points hauts : {resume['sous_equipes_note']} point(s) sur "
        f"{resume['total']} étaient sous-équipés dans la note initiale ({liste_sous_equipes}). "
        f"Après correction, {resume['non_couverts_apres_correction']} point(s) restent non "
        f"couverts. Les quatre points hauts signalés par l'audit sont donc bien traités.",
        gras=True,
        taille=10,
        couleur=_COULEUR_OK if not non_couverts else _COULEUR_ALERTE,
    )
    doc.add_paragraph()

    # Tableaux larges : passage en paysage
    _changer_orientation(doc, paysage=True)

    _ajouter_titre(doc, "8.2 Annexe 1 — Comparatif des équipements des points hauts", 2)
    _ajouter_paragraphe(
        doc,
        "Diamètre de conduite : 2,0 m, sauf PM 57 121,59 (1,6 m). Une capacité est jugée "
        "« Couvre » lorsqu'elle est supérieure ou égale au débit maximal de casse franche, "
        "à la tolérance d'arrondi près.",
        taille=9,
        couleur=_COULEUR_GRIS,
    )
    lignes_points_hauts = []
    for ligne in audit_data.COMPARATIF_POINTS_HAUTS:
        lignes_points_hauts.append(
            [
                ligne.pm,
                f"{ligne.qair_note:.2f}",
                ligne.equipement_note,
                f"{ligne.capacite_note:.2f}",
                f"{ligne.qair_corrige:.2f}",
                ligne.equipement_corrige,
                f"{ligne.capacite_corrigee:.2f}",
                ligne.verdict_note,
                ligne.verdict_corrige,
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "PM",
            "Qair note (m³/s)",
            "Équipement note initiale (à vérifier)",
            "Capacité note (m³/s)",
            "Qair corrigé (m³/s)",
            "Équipement corrigé (audit)",
            "Capacité corrigée (m³/s)",
            "Verdict note",
            "Verdict corrigé",
        ],
        lignes_points_hauts,
    )
    doc.add_paragraph()
    _ajouter_paragraphe(
        doc,
        "Lecture : les deux premiers points hauts de la note (PM 51 041,59 et 53 561,59) ne "
        "disposaient que d'un purgeur sonique PSA250, sans ventouse triple fonction : le "
        "remplacement par une ventouse DN200 + un clapet DN250 porte la capacité de 13,00 à "
        "17,17 m³/s. Le PM 51 801,59 passe de 4,17 à 8,33 m³/s, et le PM 57 121,59 de 43,17 à "
        "47,33 m³/s. Réserve : l'audit calcule le PM 57 121,59 avec la cote aval 5,6 m "
        "(probable coquille pour 95,6 m) ; la valeur 43,96 m³/s est reprise telle quelle. "
        "Avec 95,6 m, la hauteur motrice chuterait et l'équipement proposé resterait très "
        "largement couvrant. Cette cote doit être vérifiée sur le profil en long.",
        taille=9,
        couleur=_COULEUR_ALERTE,
    )
    doc.add_paragraph()

    _ajouter_titre(doc, "8.3 Annexe 2 — Comparatif des vidanges", 2)
    _ajouter_paragraphe(
        doc,
        "La note initiale uniformisait le DN 400 mm. Le diamètre exact est recalculé avec le "
        "coefficient 6,69 (au lieu de 13,39 dans le texte et 9,47 en Annexe 2) et la hauteur "
        "moyenne pondérée des deux branches.",
        taille=9,
        couleur=_COULEUR_GRIS,
    )
    lignes_vidanges = []
    for ligne in audit_data.COMPARATIF_VIDANGES:
        lignes_vidanges.append(
            [
                ligne.pm,
                f"{ligne.longueur_totale_m:.2f}",
                f"{ligne.diametre_note_mm:.2f}",
                f"{ligne.diametre_corrige_mm:.1f}",
                f"{ligne.ecart_mm:+.1f}",
                ligne.dn_corrige,
                ligne.statut,
                ligne.commentaire,
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "PM vidange",
            "L totale (m)",
            "d note (mm)",
            "d exact 2 h (mm)",
            "Écart (mm)",
            "DN corrigé",
            "Statut note",
            "Commentaire d'exploitation",
        ],
        lignes_vidanges,
    )
    doc.add_paragraph()
    resume_v = audit_data.resume_vidanges()
    _ajouter_paragraphe(
        doc,
        f"Bilan des vidanges : {resume_v['total']} points bas. Cas critiques : PM 52 621,59 "
        f"(DN 400 trop petit, environ 3 h 10 de vidange) et PM 58 721,59 (DN 400 légèrement "
        f"juste, environ 2 h 12). Le PM 56 845,25 est surdimensionné en DN 400 (forte charge "
        f"de 90 m : préférer DN 150-200). Le PM 59 701,59 illustre l'erreur de formule de la "
        f"note : 442,29 mm au lieu de 312,7 mm, soit un écart de 129,6 mm.",
        taille=9,
        couleur=_COULEUR_ALERTE,
    )

    # Retour au portrait pour la fin du rapport
    _changer_orientation(doc, paysage=False)


def _ajouter_section_tableaux_importes_docx(
    doc: Document, resultat: ResultatImportTableau
) -> None:
    """Ajoute la section des tableaux de dimensionnement importés au DOCX."""
    _ajouter_titre(doc, "Tableaux de dimensionnement importés", 1)
    _ajouter_paragraphe(
        doc,
        f"Modèle importé : {resultat.modele}. "
        f"{resultat.lignes_traitees} ligne(s) traitée(s) sur {resultat.lignes_lues} lue(s). "
        "Les colonnes grises sont calculées automatiquement par l'application.",
        taille=10,
        couleur=_COULEUR_GRIS,
    )
    doc.add_paragraph()

    # Passage en paysage pour les tableaux larges
    _changer_orientation(doc, paysage=True)

    if "ventouse" in resultat.modele.lower():
        _ajouter_titre(doc, "Tableau de dimensionnement des ventouses (Annexe 1)", 2)
        lignes = []
        for l in resultat.lignes_ventouse:
            lignes.append(
                [
                    l.pm or "",
                    f"{l.cote_projet:.2f}" if l.cote_projet is not None else "",
                    l.pm_am or "",
                    f"{l.cote_amont:.2f}" if l.cote_amont is not None else "",
                    l.pm_aval or "",
                    f"{l.cote_aval:.2f}" if l.cote_aval is not None else "",
                    f"{l.dn_conduite:.2f}" if l.dn_conduite is not None else "",
                    f"{l.longueur_amont:.1f}" if l.longueur_amont is not None else "",
                    f"{l.longueur_aval:.1f}" if l.longueur_aval is not None else "",
                    l.equipement or "",
                    f"{l.debit_admis_equipe:.2f}" if l.debit_admis_equipe is not None else "",
                    f"{l.denivelee_amont:.2f}" if l.denivelee_amont is not None else "",
                    f"{l.denivelee_aval:.2f}" if l.denivelee_aval is not None else "",
                    f"{l.pente_amont:.5f}" if l.pente_amont is not None else "",
                    f"{l.pente_aval:.5f}" if l.pente_aval is not None else "",
                    f"{l.qair_amont:.3f}" if l.qair_amont is not None else "",
                    f"{l.qair_aval:.3f}" if l.qair_aval is not None else "",
                    f"{l.qair_max:.3f}" if l.qair_max is not None else "",
                ]
            )
        _ajouter_table_docx(
            doc,
            [
                "PM", "Cote ventouse", "PM Am", "Cote amont", "PM aval", "Cote aval",
                "DN (m)", "L amont (m)", "L aval (m)", "Équipement", "Débit admis (m³/s)",
                "Déniv. amont (m)", "Déniv. aval (m)", "Pente amont", "Pente aval",
                "Qair amont (m³/s)", "Qair aval (m³/s)", "Qair max (m³/s)",
            ],
            lignes,
        )
    else:
        _ajouter_titre(doc, "Tableau de dimensionnement des vidanges (Annexe 2)", 2)
        lignes = []
        for l in resultat.lignes_vidange:
            lignes.append(
                [
                    l.pm_am or "",
                    f"{l.cprojet_am:.2f}" if l.cprojet_am is not None else "",
                    l.pm_ventouse_am or "",
                    f"{l.cprojet_ventouse_am:.2f}" if l.cprojet_ventouse_am is not None else "",
                    l.pm_ventouse_av or "",
                    f"{l.cprojet_ventouse_av:.2f}" if l.cprojet_ventouse_av is not None else "",
                    f"{l.dn_conduite:.2f}" if l.dn_conduite is not None else "",
                    f"{l.longueur_amont:.1f}" if l.longueur_amont is not None else "",
                    f"{l.longueur_aval:.1f}" if l.longueur_aval is not None else "",
                    f"{l.denivelee_amont:.2f}" if l.denivelee_amont is not None else "",
                    f"{l.denivelee_aval:.2f}" if l.denivelee_aval is not None else "",
                    f"{l.diametre_t1h:.1f}" if l.diametre_t1h is not None else "",
                    f"{l.diametre_t2h:.1f}" if l.diametre_t2h is not None else "",
                    f"{l.diametre_retenu_t2h:.1f}" if l.diametre_retenu_t2h is not None else "",
                    f"{l.diametre_vidange:.1f}" if l.diametre_vidange is not None else "",
                ]
            )
        _ajouter_table_docx(
            doc,
            [
                "PM Am", "Cprojet Am", "PM ventouse am", "Cprojet ventouse am",
                "PM ventouse av", "Cprojet ventouse av", "DN (m)", "L amont (m)", "L aval (m)",
                "Déniv. amont (m)", "Déniv. aval (m)", "Ø t=1h (mm)", "Ø t=2h (mm)",
                "Ø retenu T=2h (mm)", "Ø vidange (mm)",
            ],
            lignes,
        )

    doc.add_paragraph()

    # Retour au portrait pour la suite du rapport (audit)
    _changer_orientation(doc, paysage=False)


def _ajouter_section_catalogue_mcp_docx(doc, resultat) -> None:
    """Section « Catalogue MCP » adaptée aux débits d'air calculés."""
    from .catalogue_mcp import (
        VENTOUSES_MCP,
        SOURCE_PDF,
        FONCTIONS_MCP,
        CARACTERISTIQUES_MCP,
        resume_mcp,
    )

    _ajouter_titre(doc, "Catalogue MCP — adaptation aux débits d'air calculés", 1)
    _ajouter_paragraphe(
        doc,
        f"Source : {SOURCE_PDF}. Gamme {CARACTERISTIQUES_MCP['gamme']}, "
        f"{CARACTERISTIQUES_MCP['pression']}, revêtement "
        f"{CARACTERISTIQUES_MCP['revêtement']}. Pression minimale de service "
        f"pour l'étanchéité du flotteur : "
        f"{CARACTERISTIQUES_MCP['pression_min_étanchéité_bar']} bar. "
        f"Domaine d'application : conduites DN "
        f"{CARACTERISTIQUES_MCP['domaine_conduite_mm']} mm.",
        taille=10,
    )
    _ajouter_paragraphe(doc, "Fonctions :", taille=10, gras=True)
    for fonction in FONCTIONS_MCP:
        _ajouter_paragraphe(doc, f"• {fonction}", taille=9)

    if resultat is not None:
        _ajouter_paragraphe(doc, resume_mcp(resultat), taille=10, gras=True)
        _ajouter_table_docx(
            doc,
            ["Paramètre", "Valeur"],
            [
                ["Débit d'air à couvrir", f"{resultat.debit_m3s:.4f} m³/s"],
                ["Fonction", resultat.mode],
                [
                    "DN conduite",
                    f"{resultat.dn_conduit_mm:g} mm" if resultat.dn_conduit_mm else "—",
                ],
                [
                    "DN MCP installables",
                    ", ".join(resultat.dns_series) if resultat.dns_series else "—",
                ],
                ["DN MCP proposé", resultat.dn_propose or "—"],
                [
                    "Capacité unitaire",
                    f"{resultat.capacite_unitaire_m3s:.4f} m³/s",
                ],
                ["Nombre d'unités", str(resultat.nombre)],
                [
                    "Couverture",
                    "OUI" if resultat.couvert else "NON",
                ],
            ],
        )
        if resultat.avertissement:
            _ajouter_paragraphe(
                doc, "Avertissement : " + resultat.avertissement,
                taille=9, couleur=_COULEUR_ALERTE,
            )

    lignes = []
    for ventouse in VENTOUSES_MCP:
        lignes.append(
            [
                ventouse.dn,
                ventouse.serie,
                f"{ventouse.orifice_mm:g}",
                f"{ventouse.q_admission_m3s:.2f}",
                f"{ventouse.q_evacuation_m3s:.2f}",
                f"{ventouse.q_critique_m3s:.2f}",
                ventouse.origine_capacite,
            ]
        )
    _ajouter_table_docx(
        doc,
        [
            "DN", "Série fabricant", "Orifice (mm)",
            "Admission 0,3 bar (m³/s)", "Évacuation 0,3 bar (m³/s)",
            "Critique 0,92 bar (m³/s)", "Origine",
        ],
        lignes,
    )
    _ajouter_paragraphe(
        doc,
        "Les valeurs DN80 et DN100 proviennent du relevé des courbes "
        "constructeur (46 et 93 Nm³/min en évacuation ; 37 et 72 Nm³/min en "
        "admission). Les autres DN sont extrapolés selon la surface d'orifice "
        "et doivent être confirmés par le fabricant.",
        taille=9,
        couleur=_COULEUR_GRIS,
    )

    from .resources import chemin_ressource

    courbe = chemin_ressource("assets", "catalogue_mcp_courbe_grand_orifice.png")
    if courbe:
        _ajouter_paragraphe(
            doc, "Courbe caractéristique grand orifice (extrait du catalogue) :",
            taille=9, gras=True,
        )
        doc.add_picture(str(courbe), width=Cm(16))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()


def _ajouter_section_configurations_air_docx(doc, configuration_equipements) -> None:
    """Section « Configurations d'équipement » avec choix de l'utilisateur."""
    from .catalogue_ceai import (
        SOURCE_DOCX,
        ORIGINE_FIRM,
        PRESSION_REFERENCE,
        CONFIG_AUDIT,
        CONFIGURATIONS,
        VENTOUSES_TRIFON_CEAI,
        CLAPETS_CEAI,
        PURGEURS_SONIQUES_SNH,
        resume_configuration,
    )

    if isinstance(configuration_equipements, dict):
        choix = configuration_equipements.get("choix", CONFIG_AUDIT)
        configs = configuration_equipements.get(
            "configurations", configuration_equipements
        )
    else:
        configs, choix = configuration_equipements, CONFIG_AUDIT
    if not configs:
        return

    _ajouter_titre(
        doc, "Configurations d'équipement — grands DN (choix utilisateur)", 1
    )
    _ajouter_paragraphe(
        doc,
        f"Source : {SOURCE_DOCX}. Capacités d'air admis en m³/h à la "
        f"dépression nominale de {PRESSION_REFERENCE} ; origine {ORIGINE_FIRM} "
        "pour les organes CEAI / TRIFON. Les configurations sont comparées "
        "côte à côte ; la configuration retenue est signalée par « ★ RETENU ».",
        taille=10,
    )
    _ajouter_paragraphe(
        doc, f"Configuration retenue : {choix}", taille=11, gras=True
    )

    lignes = []
    for nom in CONFIGURATIONS:
        resultat = configs.get(nom)
        if resultat is None:
            continue
        v, c = resultat.ventouse, resultat.clapet
        lignes.append([
            ("★ RETENU — " if nom == choix else "") + nom,
            f"{resultat.debit_m3s:.3f}",
            f"{v.famille} {v.dn} ×{v.nombre}",
            f"{v.capacite_totale_m3s:.3f}",
            f"{c.famille} {c.dn} ×{c.nombre}",
            f"{c.capacite_totale_m3s:.3f}",
            "OUI" if resultat.couvert else "NON",
        ])
    _ajouter_table_docx(
        doc,
        [
            "Configuration", "Qair (m³/s)", "Ventouse", "Capacité ventouse (m³/s)",
            "Clapet", "Capacité clapet (m³/s)", "Couverture",
        ],
        lignes,
    )

    for nom in CONFIGURATIONS:
        resultat = configs.get(nom)
        if resultat is not None:
            _ajouter_paragraphe(
                doc, resume_configuration(resultat),
                taille=9,
                couleur=_COULEUR_GRIS if nom != choix else None,
            )

    _ajouter_paragraphe(
        doc, "Détail des capacités catalogues (m³/h à 3 mCE) :",
        taille=10, gras=True,
    )
    for titre, table in (
        ("Ventouses TRIFON (CEAI)", VENTOUSES_TRIFON_CEAI),
        ("Clapets d'admission CEAI", CLAPETS_CEAI),
        ("Purgeurs soniques SNH — référence purge continue", PURGEURS_SONIQUES_SNH),
    ):
        _ajouter_paragraphe(doc, titre, taille=9, gras=True)
        _ajouter_table_docx(
            doc,
            ["DN", "Capacité (m³/h)", "Capacité (m³/s)", "Retenu", "Origine"],
            [
                [
                    o.dn, f"{o.capacite_m3h:g}", f"{o.capacite_m3s:.4f}",
                    o.retenu, o.origine,
                ]
                for o in table
            ],
        )
    _ajouter_paragraphe(
        doc,
        "Le purgeur sonique SNH assure la purge continue aux points hauts ; "
        "son débit très faible ne doit pas être confondu avec les capacités "
        "d'admission en grand débit des ventouses et clapets.",
        taille=9,
        couleur=_COULEUR_GRIS,
    )
    doc.add_paragraph()


# ===========================================================================
# RAPPORT DOCX
# ===========================================================================
def generer_rapport_docx(
    chemin: str | Path,
    *,
    projet: str = "MK_Debits_Air_Eau",
    note_source: str = "Calcul des débits points bas et hauts.pdf",
    vidange: VidangeResult | None = None,
    ventouse: VentouseResult | None = None,
    equipements: Iterable[EquipementChoice] | None = None,
    verification: VerificationResult | None = None,
    donnees: DonneesProjet | None = None,
    inputs_resume: str | None = None,
    tableau_import: "ResultatImportTableau | None" = None,
    catalogue_mcp=None,
    configuration_equipements=None,
) -> Path:
    """Génère un rapport Word .docx récapitulant les calculs, vérifications et graphiques."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if catalogue_mcp is None and donnees is not None and donnees.debit_air_equipement > 0:
        from .catalogue_mcp import analyser_mcp

        catalogue_mcp = analyser_mcp(
            donnees.debit_air_equipement,
            donnees.diam_conduit * 1000 if donnees.diam_conduit else None,
            "admission",
        )
    if (
        configuration_equipements is None
        and donnees is not None
        and donnees.debit_air_equipement > 0
    ):
        from .catalogue_ceai import CONFIG_AUDIT, analyser_configurations

        configuration_equipements = {
            "choix": CONFIG_AUDIT,
            "configurations": analyser_configurations(donnees.debit_air_equipement),
        }

    # Graphiques (PNG a cote du rapport)
    graphes = generer_tous_graphiques(
        chemin,
        vidange=vidange,
        ventouse=ventouse,
        equipements=equipements,
        verification=verification,
    )

    doc = Document()

    # Titre principal
    titre = doc.add_heading("Rapport de calcul — Débits air et eau", level=0)
    for run in titre.runs:
        run.font.color.rgb = _COULEUR_TITRE
        run.font.size = Pt(20)

    _ajouter_paragraphe(doc, f"Projet : {projet}", gras=True, taille=12)
    _ajouter_paragraphe(doc, f"Document de référence : {note_source}", taille=11)
    _ajouter_paragraphe(
        doc,
        f"Date de génération : {_dt.datetime.now().strftime('%d/%m/%Y %H:%M')}",
        taille=10,
        couleur=_COULEUR_GRIS,
    )
    doc.add_paragraph()

    if inputs_resume:
        _ajouter_titre(doc, "1. Synthèse des entrées", 1)
        _ajouter_paragraphe(doc, inputs_resume)
        doc.add_paragraph()

    # --- Vidanges (points bas) ---
    if vidange is not None:
        _ajouter_titre(doc, "2. Vidanges — Points bas", 1)
        _ajouter_table_docx(
            doc,
            ["Paramètre", "Valeur", "Unité", "Statut"],
            [
                ["Section de conduite (π/4·D²)", f"{vidange.section:.6f}", "m²", "—"],
                ["Débit de décharge Q (F1)", f"{vidange.debit_decharge:.6f}", "m³/s", "OK"],
                [
                    "Diamètre de vidange d (F2)",
                    f"{vidange.diametre_vidange:.2f}",
                    "mm",
                    "SUSPECT" if vidange.formule_f2_alerte else "OK",
                ],
                ["Section de vidange associée", f"{vidange.section_vidange:.6f}", "m²", "—"],
                ["Volume du tronçon", f"{vidange.volume_troncon:.2f}", "m³", "—"],
                ["Débit nécessaire (vidange 2 h)", f"{vidange.debit_necessaire:.6f}", "m³/s", "—"],
            ],
        )
        if graphes["vidange"]:
            doc.add_picture(graphes["vidange"], width=Cm(15))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if vidange.formule_f2_alerte:
            _ajouter_paragraphe(
                doc,
                "Alerte : la formule F2 (diamètre de vidange) est marquée SUSPECT dans le document source. "
                "Résultat à confirmer avec le bureau d'études.",
                taille=10,
                couleur=_COULEUR_ALERTE,
            )
        doc.add_paragraph()

    # --- Ventouse (points hauts) ---
    if ventouse is not None:
        _ajouter_titre(doc, "3. Ventouse — Points hauts (3 fonctions)", 1)

        _ajouter_titre(doc, "3.1 Première fonction — Dégazage (coup de bélier)", 2)
        _ajouter_table_docx(
            doc,
            ["Paramètre", "Valeur", "Unité", "Statut"],
            [
                ["Célérité d'Allievi a (F3)", f"{ventouse.celerite_a:.3f}", "m/s", "OK"],
                ["Débit d'air dégazage Qair (F4)", f"{ventouse.qair_degazage:.6f}", "m³/s", "OK"],
                [
                    "Suppression ΔH (F4)",
                    f"{ventouse.delta_h:.2f}",
                    "m",
                    "Conforme" if ventouse.delta_h <= 10 else "NON CONFORME (>10 m)",
                ],
                [
                    "Diamètre orifice dégazage d1 (F6)",
                    f"{ventouse.diametre_orifice_degazage * 1000:.3f}",
                    "mm",
                    "COHÉRENT (F6)",
                ],
            ],
        )
        if not ventouse.degazage_conforme:
            _ajouter_paragraphe(
                doc,
                "Alerte : le dégazage n'est pas conforme (ΔH > 10 m ou célérité non calculable).",
                taille=10,
                couleur=_COULEUR_ALERTE,
            )
        doc.add_paragraph()

        _ajouter_titre(doc, "3.2 Deuxième fonction — Remplissage de la conduite", 2)
        _ajouter_table_docx(
            doc,
            ["Paramètre", "Valeur", "Unité", "Statut"],
            [
                ["Débit eau de remplissage Qeau (F7)", f"{ventouse.q_eau_remplissage:.6f}", "m³/s", "OK"],
                ["Débit air évacuation Qair (F7)", f"{ventouse.qair_remplissage:.6f}", "m³/s", "OK (F7)"],
                [
                    "Diamètre orifice d2 (F7)",
                    f"{ventouse.diametre_orifice_remplissage * 1000:.3f}",
                    "mm",
                    "OK (F7)",
                ],
            ],
        )
        doc.add_paragraph()

        _ajouter_titre(doc, "3.3 Troisième fonction — Admission d'air (vidange / casse franche)", 2)
        _ajouter_table_docx(
            doc,
            ["Paramètre", "Valeur", "Unité", "Statut"],
            [
                ["Hauteur motrice H (F11)", f"{ventouse.hauteur_motrice:.3f}", "m", "OK"],
                ["Vitesse de vidange v", f"{ventouse.vitesse_vidange:.3f}", "m/s", "Cohérent (F8/F9/F10)"],
                ["Débit eau de vidange Qeau", f"{ventouse.q_eau_vidange:.6f}", "m³/s", "Cohérent (F8/F10)"],
                ["Débit air admission Qair (F10)", f"{ventouse.qair_admission:.6f}", "m³/s", "Cohérent (F10)"],
                [
                    "Pertes singulières ξ (F10)",
                    f"{ventouse.coeff_singularites:g}",
                    "× v²/2g",
                    "Hypothèse à confirmer",
                ],
            ],
        )
        doc.add_paragraph(
            "F10 est la formule de l'audit (et du PDF page 5) : Qair = (π·D²/4) · "
            "√[ H / (0,102 + 0,000587 · L / D^(4/3)) ] pour K = 104 et ξ = 2. "
            "Forme générale : v = √[ H / ( ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ) ] "
            "et Qair = Qeau = v·πD²/4. ξ = 1 correspond à l'équation écrite ; "
            "ξ = 2 correspond à la mention « k = 2 » retenue par l'audit. Le choix "
            "de ξ reste exposé dans l'interface et à valider par le bureau d'études."
        )
        doc.add_paragraph()

        if graphes["ventouse"]:
            doc.add_picture(graphes["ventouse"], width=Cm(13))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

    # --- Sélection équipement ---
    if equipements:
        _ajouter_titre(doc, "4. Sélection d'équipement (tables PAM / SNH)", 1)
        lignes = []
        for eq in equipements:
            lignes.append(
                [
                    eq.type_equipement,
                    eq.dn,
                    f"{eq.debit_admis:.4f}",
                    f"{eq.marge:+.4f}",
                    eq.fonction,
                ]
            )
        _ajouter_table_docx(
            doc,
            ["Équipement", "DN", "Débit admis (m³/s)", "Marge (m³/s)", "Fonction"],
            lignes,
        )
        if graphes["equipement"]:
            doc.add_picture(graphes["equipement"], width=Cm(15))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

    # --- Récapitulatif équipements admission d'air (F10) ---
    if ventouse is not None and donnees is not None:
        _ajouter_section_equipements_admission_docx(doc, ventouse, donnees)
        doc.add_paragraph()

    # --- Vérifications ---
    if verification is not None:
        _ajouter_titre(doc, "6. Vérifications de fonctionnement (page 6 du PDF)", 1)
        _ajouter_table_docx(
            doc,
            ["Vérification", "Valeur", "Unité", "Statut"],
            [
                [
                    "Vitesse de remplissage admise",
                    f"{verification.vitesse_remplissage_admise:.2f}",
                    "m/s",
                    "Référence",
                ],
                [
                    "Débit de remplissage référence",
                    f"{verification.debit_remplissage_reference:.4f}",
                    "m³/s",
                    "—",
                ],
                [
                    "Débit de remplissage référence",
                    f"{verification.debit_remplissage_reference_m3h:.0f}",
                    "m³/h",
                    "—",
                ],
                [
                    "Dégazage ≈ % du débit nominal",
                    f"{verification.degazage_pourcentage_qnom:.0f}",
                    "%",
                    "Référence",
                ],
                [
                    "Débit dégazage vérification",
                    f"{verification.debit_degazage_verification:.0f}",
                    "m³/h",
                    "—",
                ],
                [
                    "Débit nominal de la conduite",
                    f"{verification.debit_nominal:.4f}",
                    "m³/s",
                    "—",
                ],
                [
                    "Résultat global",
                    "Conforme" if verification.tous_conformes else "NON CONFORME",
                    "",
                    "—",
                ],
            ],
        )
        for msg in verification.messages:
            _ajouter_paragraphe(doc, f"• {msg}", taille=10)
        if graphes["verification"]:
            doc.add_picture(graphes["verification"], width=Cm(13))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

    # --- Registre des formules ---
    _ajouter_titre(doc, "7. Registre de vérification des formules", 1)
    _ajouter_paragraphe(
        doc,
        "Chaque formule extraite du document PDF est affichée avec son statut de vérification. "
        "Les formules marquées SUSPECT / EMPIRIQUE / À VÉRIFIER / ILLISIBLE ne doivent pas "
        "servir à un dimensionnement définitif sans validation du bureau d'études.",
        taille=10,
    )
    lignes_formules = []
    for f in verifier_formules():
        lignes_formules.append([f.nom, f.statut, f.commentaire, f.formule_clair])
    _ajouter_table_docx(
        doc,
        ["Formule", "Statut", "Commentaire", "Équation"],
        lignes_formules,
    )

    # --- Tableaux de dimensionnement importés ---
    if tableau_import is not None:
        _ajouter_section_tableaux_importes_docx(doc, tableau_import)
        doc.add_paragraph()

    # --- Catalogue MCP ---
    if catalogue_mcp is not None:
        _ajouter_section_catalogue_mcp_docx(doc, catalogue_mcp)

    # --- Configurations équipements (choix utilisateur) ---
    if configuration_equipements is not None:
        _ajouter_section_configurations_air_docx(doc, configuration_equipements)

    # --- Audit et comparatif note initiale / note corrigée ---
    _ajouter_section_audit_docx(doc)

    doc.add_paragraph()
    _ajouter_paragraphe(
        doc,
        "Fin du rapport. Généré par l'application MK_Debits_Air_Eau.",
        taille=9,
        couleur=_COULEUR_GRIS,
    )

    doc.save(str(chemin))
    return chemin


# ===========================================================================
# RAPPORT XLSX
# ===========================================================================
def _style_cellule_en_tete(cell):
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = PatternFill("solid", fgColor="1F3B5C")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )


def _style_cellule_donnee(cell, align_center: bool = True):
    cell.font = Font(size=10)
    cell.alignment = Alignment(horizontal="center" if align_center else "left", vertical="center")
    cell.border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )


def generer_rapport_xlsx(
    chemin: str | Path,
    *,
    projet: str = "MK_Debits_Air_Eau",
    note_source: str = "Calcul des débits points bas et hauts.pdf",
    vidange: VidangeResult | None = None,
    ventouse: VentouseResult | None = None,
    equipements: Iterable[EquipementChoice] | None = None,
    verification: VerificationResult | None = None,
    donnees: DonneesProjet | None = None,
    inputs_resume: str | None = None,
    tableau_import: "ResultatImportTableau | None" = None,
    catalogue_mcp=None,
    configuration_equipements=None,
) -> Path:
    """Génère un rapport Excel .xlsx avec feuilles de données et une feuille Graphiques."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if catalogue_mcp is None and donnees is not None and donnees.debit_air_equipement > 0:
        from .catalogue_mcp import analyser_mcp

        catalogue_mcp = analyser_mcp(
            donnees.debit_air_equipement,
            donnees.diam_conduit * 1000 if donnees.diam_conduit else None,
            "admission",
        )
    if (
        configuration_equipements is None
        and donnees is not None
        and donnees.debit_air_equipement > 0
    ):
        from .catalogue_ceai import CONFIG_AUDIT, analyser_configurations

        configuration_equipements = {
            "choix": CONFIG_AUDIT,
            "configurations": analyser_configurations(donnees.debit_air_equipement),
        }

    # Graphiques (PNG a cote du rapport)
    graphes = generer_tous_graphiques(
        chemin,
        vidange=vidange,
        ventouse=ventouse,
        equipements=equipements,
        verification=verification,
    )

    wb = Workbook()

    # ---- Feuille Synthèse ----
    ws = wb.active
    ws.title = "Synthèse"
    ws["A1"] = "Rapport de calcul — Débits air et eau"
    ws["A1"].font = Font(bold=True, size=14, color="1F3B5C")
    ws["A2"] = f"Projet : {projet}"
    ws["A3"] = f"Document de référence : {note_source}"
    ws["A4"] = f"Date de génération : {_dt.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    for r in (2, 3, 4):
        ws[f"A{r}"].font = Font(size=10)
    ws["A6"] = "Synthèse des entrées :"
    ws["A6"].font = Font(bold=True, size=11)
    ws["A7"] = inputs_resume or "—"
    ws["A7"].font = Font(size=10)
    ws["A7"].alignment = Alignment(wrap_text=True, vertical="top")

    # ---- Feuille Vidanges ----
    if vidange is not None:
        ws2 = wb.create_sheet("Vidanges")
        entetes = ["Paramètre", "Valeur", "Unité", "Statut"]
        lignes_vidanges = [
            ["Section de conduite (π/4·D²)", vidange.section, "m²", "—"],
            ["Débit de décharge Q (F1)", vidange.debit_decharge, "m³/s", "OK"],
            [
                "Diamètre de vidange d (F2)",
                vidange.diametre_vidange,
                "mm",
                "SUSPECT" if vidange.formule_f2_alerte else "OK",
            ],
            ["Section de vidange associée", vidange.section_vidange, "m²", "—"],
            ["Volume du tronçon", vidange.volume_troncon, "m³", "—"],
            ["Débit nécessaire (vidange 2 h)", vidange.debit_necessaire, "m³/s", "—"],
        ]
        for c, h in enumerate(entetes, start=1):
            _style_cellule_en_tete(ws2.cell(row=1, column=c, value=h))
        for r, ligne in enumerate(lignes_vidanges, start=2):
            for c, val in enumerate(ligne, start=1):
                cell = ws2.cell(row=r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c != 1))
        for c, width in enumerate([42, 16, 10, 16], start=1):
            ws2.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Ventouse ----
    if ventouse is not None:
        ws3 = wb.create_sheet("Ventouse")
        lignes = [
            ["Section", "Paramètre", "Valeur", "Unité", "Statut"],
            ["1 — Dégazage", "Célérité a (F3)", ventouse.celerite_a, "m/s", "OK"],
            ["1 — Dégazage", "Débit air Qair (F4)", ventouse.qair_degazage, "m³/s", "OK"],
            ["1 — Dégazage", "Suppression ΔH", ventouse.delta_h, "m", "Conforme" if ventouse.delta_h <= 10 else "NON CONFORME"],
            ["1 — Dégazage", "Ø orifice dégazage d1 (F6)", ventouse.diametre_orifice_degazage * 1000, "mm", "COHÉRENT (F6)"],
            ["2 — Remplissage", "Débit eau Qeau (F7)", ventouse.q_eau_remplissage, "m³/s", "OK"],
            ["2 — Remplissage", "Débit air Qair (F7)", ventouse.qair_remplissage, "m³/s", "OK (F7)"],
            ["2 — Remplissage", "Ø orifice d2 (F7)", ventouse.diametre_orifice_remplissage * 1000, "mm", "OK (F7)"],
            ["3 — Admission", "Hauteur motrice H (F11)", ventouse.hauteur_motrice, "m", "OK"],
            ["3 — Admission", "Vitesse de vidange v", ventouse.vitesse_vidange, "m/s", "Cohérent (F8/F9/F10)"],
            ["3 — Admission", "Débit eau Qeau", ventouse.q_eau_vidange, "m³/s", "Cohérent (F8/F10)"],
            ["3 — Admission", "Débit air Qair (F10)", ventouse.qair_admission, "m³/s", "Cohérent (F10)"],
            ["3 — Admission", "Pertes singulières ξ (F10)", ventouse.coeff_singularites, "× v²/2g", "Hypothèse à confirmer"],
        ]
        for c, h in enumerate(lignes[0], start=1):
            _style_cellule_en_tete(ws3.cell(row=1, column=c, value=h))
        for r, ligne in enumerate(lignes[1:], start=2):
            for c, val in enumerate(ligne, start=1):
                cell = ws3.cell(row=r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c not in (1, 2)))
        for c, width in enumerate([14, 34, 20, 10, 22], start=1):
            ws3.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Equipements ----
    if equipements:
        ws4 = wb.create_sheet("Equipements")
        entetes = ["Équipement", "DN", "Débit admis (m³/s)", "Marge (m³/s)", "Fonction"]
        lignes_equipements = [
            [eq.type_equipement, eq.dn, eq.debit_admis, eq.marge, eq.fonction]
            for eq in equipements
        ]
        for c, h in enumerate(entetes, start=1):
            _style_cellule_en_tete(ws4.cell(row=1, column=c, value=h))
        for r, ligne in enumerate(lignes_equipements, start=2):
            for c, val in enumerate(ligne, start=1):
                cell = ws4.cell(row=r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c not in (1, 5)))
        for c, width in enumerate([20, 10, 20, 18, 14], start=1):
            ws4.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Equipements Admission (F10) ----
    if ventouse is not None and donnees is not None:
        ws8 = wb.create_sheet("Equipements Admission")
        ws8["A1"] = "Récapitulatif équipements — Admission d'air (F10)"
        ws8["A1"].font = Font(bold=True, size=12, color="1F3B5C")

        ligne = 3
        ws8.cell(row=ligne, column=1, value="Formules utilisées (écrites en clair) :").font = Font(bold=True, size=10, color="1F3B5C")
        ligne += 1
        for texte in [
            _texte_formule_f11(ventouse.hauteur_motrice),
            _texte_formule_f8(),
            _texte_formule_f10(),
        ]:
            ws8.cell(row=ligne, column=1, value=texte).font = Font(size=9)
            ws8.cell(row=ligne, column=1).alignment = Alignment(wrap_text=True, vertical="top")
            ws8.row_dimensions[ligne].height = 42
            ligne += 1
        ligne += 1

        ws8.cell(row=ligne, column=1, value="Deux cas de calcul selon ξ (pertes singulières) :").font = Font(bold=True, size=10, color="1F3B5C")
        ligne += 1

        v1, q1, _, _ = qair_admission_casse(
            ventouse.hauteur_motrice,
            donnees.longueur_troncon,
            donnees.diam_conduit,
            coeff_rugosite=donnees.coeff_rugosite,
            coeff_singularites=1.0,
        )
        v2, q2, _, _ = qair_admission_casse(
            ventouse.hauteur_motrice,
            donnees.longueur_troncon,
            donnees.diam_conduit,
            coeff_rugosite=donnees.coeff_rugosite,
            coeff_singularites=2.0,
        )

        entetes_cas = ["Cas", "ξ", "Vitesse v (m/s)", "Débit air Qair (m³/s)"]
        for c, h in enumerate(entetes_cas, start=1):
            _style_cellule_en_tete(ws8.cell(row=ligne, column=c, value=h))
        donnees_cas = [
            ["Équation écrite (v²/2g)", 1, round(v1, 3), round(q1, 4)],
            ["Mention k = 2 (v²/g)", 2, round(v2, 3), round(q2, 4)],
        ]
        for r, ligne_donnees in enumerate(donnees_cas, start=1):
            for c, val in enumerate(ligne_donnees, start=1):
                cell = ws8.cell(row=ligne + r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c != 1))
        ligne += len(donnees_cas) + 2

        # Tableau PAM réel
        ws8.cell(row=ligne, column=1, value="Ventouses triple fonction PAM — caractéristiques réelles (page 6) :").font = Font(bold=True, size=10, color="1F3B5C")
        ligne += 1
        entetes_pam = [
            "DN",
            "Admission 3 m (m³/h)",
            "Valeur imprimée (m³/s)",
            "Conversion exacte (m³/s)",
            "Évacuation 1 m (m³/h)",
            f"Couvre ξ = 1 ({q1:.2f} m³/s)",
            f"Couvre ξ = 2 ({q2:.2f} m³/s)",
        ]
        for c, h in enumerate(entetes_pam, start=1):
            _style_cellule_en_tete(ws8.cell(row=ligne, column=c, value=h))
        ligne += 1
        for car in TABLE_PAM:
            converti = car.debit_admission_converti_m3s
            valeurs = [
                car.dn,
                car.debit_admission_depression_3m_m3h,
                car.debit_admission_depression_3m_m3s,
                round(converti, 3) if converti is not None else None,
                car.debit_evacuation_surpression_1m_m3h,
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q1 else "Non",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q2 else "Non",
            ]
            for c, val in enumerate(valeurs, start=1):
                cell = ws8.cell(row=ligne, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c != 1))
            ligne += 1
        ligne += 1

        # Tableau SNH réel
        ws8.cell(row=ligne, column=1, value="Clapets d'entrée d'air SNH — caractéristiques réelles (page 6) :").font = Font(bold=True, size=10, color="1F3B5C")
        ligne += 1
        entetes_snh = [
            "DN",
            "Admission 3 m (m³/h)",
            "Admission (m³/s)",
            f"Couvre ξ = 1 ({q1:.2f} m³/s)",
            f"Couvre ξ = 2 ({q2:.2f} m³/s)",
        ]
        for c, h in enumerate(entetes_snh, start=1):
            _style_cellule_en_tete(ws8.cell(row=ligne, column=c, value=h))
        ligne += 1
        for car in TABLE_SNH:
            valeurs = [
                car.dn,
                car.debit_admission_depression_3m_m3h,
                car.debit_admission_depression_3m_m3s,
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q1 else "Non",
                "Oui" if (car.debit_admission_depression_3m_m3s or 0.0) >= q2 else "Non",
            ]
            for c, val in enumerate(valeurs, start=1):
                cell = ws8.cell(row=ligne, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c != 1))
            ligne += 1
        ligne += 1

        # Combinaisons réelles
        ws8.cell(row=ligne, column=1, value="Combinaisons d'équipements réelles (aucune référence « PAM 800 / SNH 800 ») :").font = Font(bold=True, size=10, color="1F3B5C")
        ligne += 1
        entetes_combo = [
            "Combinaison",
            "Capacité (m³/s)",
            f"Couvre ξ = 1 ({q1:.2f} m³/s)",
            f"Couvre ξ = 2 ({q2:.2f} m³/s)",
            f"Couvre le projet ({ventouse.qair_admission:.2f} m³/s)",
        ]
        for c, h in enumerate(entetes_combo, start=1):
            _style_cellule_en_tete(ws8.cell(row=ligne, column=c, value=h))
        ligne += 1
        for combo in audit_data.COMBINAISONS_EQUIPEMENTS:
            capacite = combo.capacite_m3s
            valeurs = [
                combo.libelle,
                round(capacite, 3),
                "Oui" if capacite >= q1 else "Non",
                "Oui" if capacite >= q2 else "Non",
                "Oui" if capacite >= ventouse.qair_admission else "Non",
            ]
            for c, val in enumerate(valeurs, start=1):
                cell = ws8.cell(row=ligne, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c != 1))
            ligne += 1
        ligne += 1

        ws8.cell(
            row=ligne, column=1,
            value="Signalement — conversion PAM DN200 : le tableau indique 14 454 m³/h et 4,165 m³/s, "
                  "alors que 14 454 / 3600 = 4,015 m³/s (4,165 m³/s = 14 994 m³/h). L'écart de "
                  "0,150 m³/s (environ 3,7 %) est affiché, pas masqué ; les combinaisons de l'audit "
                  "utilisent 4,165 m³/s. Le choix entre ξ = 1 et ξ = 2 reste à valider par le bureau d'études.",
        ).font = Font(size=9, italic=True, color="B00000")

        for c, width in enumerate([40, 12, 22, 24, 24, 22, 22], start=1):
            ws8.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Verifications ----
    if verification is not None:
        ws5 = wb.create_sheet("Verifications")
        entetes = ["Vérification", "Valeur", "Unité", "Statut"]
        lignes_verifications = [
            ["Vitesse de remplissage admise", verification.vitesse_remplissage_admise, "m/s", "Référence"],
            ["Débit de remplissage référence", verification.debit_remplissage_reference, "m³/s", "—"],
            ["Débit de remplissage référence", verification.debit_remplissage_reference_m3h, "m³/h", "—"],
            ["Dégazage ≈ % du débit nominal", verification.degazage_pourcentage_qnom, "%", "Référence"],
            ["Débit dégazage vérification", verification.debit_degazage_verification, "m³/h", "—"],
            ["Débit nominal de la conduite", verification.debit_nominal, "m³/s", "—"],
            [
                "Résultat global",
                "Conforme" if verification.tous_conformes else "NON CONFORME",
                "",
                "—",
            ],
        ]
        for c, h in enumerate(entetes, start=1):
            _style_cellule_en_tete(ws5.cell(row=1, column=c, value=h))
        for r, ligne in enumerate(lignes_verifications, start=2):
            for c, val in enumerate(ligne, start=1):
                cell = ws5.cell(row=r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c not in (1, 4)))
        r_msg = len(lignes_verifications) + 3
        ws5.cell(row=r_msg, column=1, value="Messages :").font = Font(bold=True, size=10)
        for i, msg in enumerate(verification.messages, start=1):
            ws5.cell(row=r_msg + i, column=1, value=f"• {msg}").font = Font(size=9)
        for c, width in enumerate([42, 16, 10, 22], start=1):
            ws5.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Graphiques ----
    ws6 = wb.create_sheet("Graphiques")
    ws6["A1"] = "Graphiques du rapport"
    ws6["A1"].font = Font(bold=True, size=12, color="1F3B5C")

    ligne_curseur = 3
    for cle, libelle in [
        ("vidange", "Vidanges — débit nécessaire vs débit de décharge"),
        ("ventouse", "Ventouse — débits d'air par fonction"),
        ("equipement", "Équipements — débit admis vs marge"),
        ("verification", "Vérifications — vitesse de remplissage"),
    ]:
        chemin_png = graphes.get(cle)
        if chemin_png and Path(chemin_png).exists():
            ws6.cell(row=ligne_curseur, column=1, value=libelle).font = Font(bold=True, size=10, color="1F3B5C")
            img = XLImage(chemin_png)
            img.width = 600
            img.height = 240
            ws6.add_image(img, f"A{ligne_curseur + 1}")
            ligne_curseur += 22  # espace pour l'image + titre suivant
        else:
            ws6.cell(row=ligne_curseur, column=1, value=f"{libelle} : non disponible").font = Font(size=9, italic=True)
            ligne_curseur += 2

    # ---- Feuille Formules (registre) ----
    ws7 = wb.create_sheet("Formules")
    entetes = ["Formule", "Statut", "Commentaire", "Équation"]
    for c, h in enumerate(entetes, start=1):
        _style_cellule_en_tete(ws7.cell(row=1, column=c, value=h))
    for r, f in enumerate(verifier_formules(), start=2):
        valeurs = [f.nom, f.statut, f.commentaire, f.formule_clair]
        for c, val in enumerate(valeurs, start=1):
            cell = ws7.cell(row=r, column=c, value=val)
            _style_cellule_donnee(cell, align_center=(c in (1, 2)))
    for c, width in enumerate([38, 18, 80, 42], start=1):
        ws7.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Comparatif Points Hauts (audit) ----
    ws9 = wb.create_sheet("Comparatif Points Hauts")
    ws9["A1"] = "Comparatif Annexe 1 — note initiale (à vérifier) / note corrigée (audit)"
    ws9["A1"].font = Font(bold=True, size=12, color="1F3B5C")
    ws9["A2"] = (
        "DN de conduite : 2,0 m, sauf PM 57 121,59 (1,6 m). La note initiale est conservée "
        "pour comparaison et ne doit plus servir de base de dimensionnement."
    )
    ws9["A2"].font = Font(size=9, italic=True)
    entetes_ph = [
        "PM",
        "DN (m)",
        "Qair note (m³/s)",
        "Équipement note initiale (à vérifier)",
        "Capacité note (m³/s)",
        "Marge note (m³/s)",
        "Qair corrigé (m³/s)",
        "Équipement corrigé (audit)",
        "Capacité corrigée (m³/s)",
        "Marge corrigée (m³/s)",
        "Verdict note",
        "Verdict corrigé",
    ]
    for c, h in enumerate(entetes_ph, start=1):
        _style_cellule_en_tete(ws9.cell(row=4, column=c, value=h))
    for r, ligne in enumerate(audit_data.COMPARATIF_POINTS_HAUTS, start=5):
        valeurs = [
            ligne.pm,
            ligne.dn_m,
            ligne.qair_note,
            ligne.equipement_note,
            ligne.capacite_note,
            round(ligne.marge_note, 2),
            ligne.qair_corrige,
            ligne.equipement_corrige,
            ligne.capacite_corrigee,
            round(ligne.marge_corrigee, 2),
            ligne.verdict_note,
            ligne.verdict_corrige,
        ]
        for c, val in enumerate(valeurs, start=1):
            cell = ws9.cell(row=r, column=c, value=val)
            _style_cellule_donnee(cell, align_center=(c not in (4, 8)))
    for c, width in enumerate([12, 8, 14, 34, 16, 14, 14, 38, 18, 16, 14, 14], start=1):
        ws9.column_dimensions[get_column_letter(c)].width = width
    resume_ph = audit_data.resume_points_hauts()
    ws9.cell(
        row=5 + len(audit_data.COMPARATIF_POINTS_HAUTS) + 1,
        column=1,
        value=(
            f"Bilan : {resume_ph['sous_equipes_note']} point(s) sous-équipé(s) dans la note "
            f"initiale ; {resume_ph['non_couverts_apres_correction']} point(s) non couvert(s) "
            f"après correction."
        ),
    ).font = Font(bold=True, size=10, color="1E6B1E")

    # ---- Feuille Comparatif Vidanges (audit) ----
    ws10 = wb.create_sheet("Comparatif Vidanges")
    ws10["A1"] = "Comparatif Annexe 2 — note initiale (à vérifier) / note corrigée (audit)"
    ws10["A1"].font = Font(bold=True, size=12, color="1F3B5C")
    ws10["A2"] = (
        "La note initiale uniformisait le DN 400. Diamètre exact recalculé avec le coefficient "
        "6,69 (au lieu de 13,39 dans le texte et 9,47 en Annexe 2) et la hauteur moyenne pondérée."
    )
    ws10["A2"].font = Font(size=9, italic=True)
    entetes_v = [
        "PM vidange",
        "DN conduite (m)",
        "L totale (m)",
        "d note (mm)",
        "d exact 2 h (mm)",
        "Écart (mm)",
        "Écart (%)",
        "DN note",
        "DN corrigé",
        "Statut note",
        "Commentaire d'exploitation",
    ]
    for c, h in enumerate(entetes_v, start=1):
        _style_cellule_en_tete(ws10.cell(row=4, column=c, value=h))
    for r, ligne in enumerate(audit_data.COMPARATIF_VIDANGES, start=5):
        valeurs = [
            ligne.pm,
            ligne.dn_m,
            ligne.longueur_totale_m,
            ligne.diametre_note_mm,
            ligne.diametre_corrige_mm,
            round(ligne.ecart_mm, 1),
            round(ligne.ecart_pct, 1),
            ligne.dn_note,
            ligne.dn_corrige,
            ligne.statut,
            ligne.commentaire,
        ]
        for c, val in enumerate(valeurs, start=1):
            cell = ws10.cell(row=r, column=c, value=val)
            _style_cellule_donnee(cell, align_center=(c not in (8, 9, 10, 11)))
    for c, width in enumerate([14, 12, 12, 14, 16, 12, 10, 10, 18, 18, 46], start=1):
        ws10.column_dimensions[get_column_letter(c)].width = width
    resume_v = audit_data.resume_vidanges()
    ws10.cell(
        row=5 + len(audit_data.COMPARATIF_VIDANGES) + 1,
        column=1,
        value=(
            f"Bilan : {resume_v['total']} vidanges ; "
            f"{resume_v.get('Sous-dimensionné', 0)} sous-dimensionnée(s), "
            f"{resume_v.get('Limite', 0)} limite(s), "
            f"{resume_v.get('Surdimensionné', 0)} surdimensionnée(s)."
        ),
    ).font = Font(bold=True, size=10, color="B00000")

    # ---- Feuille Corrections Audit ----
    ws11 = wb.create_sheet("Corrections Audit")
    ws11["A1"] = "Corrections de l'audit prises en compte par l'application"
    ws11["A1"].font = Font(bold=True, size=12, color="1F3B5C")
    ws11["A2"] = "Source : Audit_et_Correction_Note_BR3_LOT8.docx"
    ws11["A2"].font = Font(size=9, italic=True)
    entetes_c = ["Code", "Domaine", "Constat de l'audit", "Correction retenue", "Application", "Statut"]
    for c, h in enumerate(entetes_c, start=1):
        _style_cellule_en_tete(ws11.cell(row=4, column=c, value=h))
    for r, corr in enumerate(audit_data.CORRECTIONS_AUDIT, start=5):
        valeurs = [
            corr.code,
            corr.domaine,
            corr.constat,
            corr.correction,
            corr.application,
            "Appliquée" if corr.appliquee else "À traiter",
        ]
        for c, val in enumerate(valeurs, start=1):
            cell = ws11.cell(row=r, column=c, value=val)
            _style_cellule_donnee(cell, align_center=(c in (1, 6)))
    for c, width in enumerate([8, 24, 60, 52, 52, 12], start=1):
        ws11.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Tableaux importés ----
    if tableau_import is not None:
        ws12 = wb.create_sheet("Tableaux importés")
        ws12["A1"] = f"Tableaux de dimensionnement importés — {tableau_import.modele}"
        ws12["A1"].font = Font(bold=True, size=12, color="1F3B5C")
        ws12["A2"] = (
            f"{tableau_import.lignes_traitees} ligne(s) traitée(s) sur "
            f"{tableau_import.lignes_lues} lue(s). Colonnes grises : calculées par l'application."
        )
        ws12["A2"].font = Font(size=9, italic=True, color="808080")

        if "ventouse" in tableau_import.modele.lower():
            entetes = [
                "PM", "Cote ventouse", "PM Am", "Cote amont", "PM aval", "Cote aval",
                "DN (m)", "L amont (m)", "L aval (m)", "Équipement", "Débit admis (m³/s)",
                "Déniv. amont (m)", "Déniv. aval (m)", "Pente amont", "Pente aval",
                "Qair amont (m³/s)", "Qair aval (m³/s)", "Qair max (m³/s)",
            ]
            lignes = []
            for l in tableau_import.lignes_ventouse:
                lignes.append([
                    l.pm or "",
                    l.cote_projet,
                    l.pm_am or "",
                    l.cote_amont,
                    l.pm_aval or "",
                    l.cote_aval,
                    l.dn_conduite,
                    l.longueur_amont,
                    l.longueur_aval,
                    l.equipement or "",
                    l.debit_admis_equipe,
                    l.denivelee_amont,
                    l.denivelee_aval,
                    l.pente_amont,
                    l.pente_aval,
                    l.qair_amont,
                    l.qair_aval,
                    l.qair_max,
                ])
        else:
            entetes = [
                "PM Am", "Cprojet Am", "PM ventouse am", "Cprojet ventouse am",
                "PM ventouse av", "Cprojet ventouse av", "DN (m)", "L amont (m)", "L aval (m)",
                "Déniv. amont (m)", "Déniv. aval (m)", "Ø t=1h (mm)", "Ø t=2h (mm)",
                "Ø retenu T=2h (mm)", "Ø vidange (mm)",
            ]
            lignes = []
            for l in tableau_import.lignes_vidange:
                lignes.append([
                    l.pm_am or "",
                    l.cprojet_am,
                    l.pm_ventouse_am or "",
                    l.cprojet_ventouse_am,
                    l.pm_ventouse_av or "",
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
                ])

        for c, h in enumerate(entetes, start=1):
            _style_cellule_en_tete(ws12.cell(row=4, column=c, value=h))
        for r, ligne in enumerate(lignes, start=5):
            for c, val in enumerate(ligne, start=1):
                cell = ws12.cell(row=r, column=c, value=val)
                _style_cellule_donnee(cell, align_center=(c not in (10,)))
        for c, width in enumerate([14, 12, 14, 12, 14, 12, 10, 12, 12, 34, 16, 14, 14, 12, 12, 16, 16, 14], start=1):
            ws12.column_dimensions[get_column_letter(c)].width = width

    # ---- Feuille Catalogue MCP ----
    if catalogue_mcp is not None:
        from .catalogue_mcp import (
            VENTOUSES_MCP, SOURCE_PDF, CARACTERISTIQUES_MCP, resume_mcp,
        )

        wsm = wb.create_sheet("Catalogue MCP")
        wsm["A1"] = "Catalogue MCP — adaptation aux débits d'air calculés"
        wsm["A1"].font = Font(bold=True, size=13, color="1F3B5C")
        wsm["A2"] = (
            f"Source : {SOURCE_PDF} — Domaine d'application : conduites DN "
            f"{CARACTERISTIQUES_MCP['domaine_conduite_mm']} mm."
        )
        wsm["A3"] = resume_mcp(catalogue_mcp)
        wsm["A3"].alignment = Alignment(wrap_text=True)
        wsm.merge_cells("A3:G3")
        wsm.row_dimensions[3].height = 32

        entetes_mcp = [
            "DN", "Série fabricant", "Orifice (mm)",
            "Admission 0,3 bar (m³/s)", "Évacuation 0,3 bar (m³/s)",
            "Critique 0,92 bar (m³/s)", "Origine capacité",
        ]
        for c, h in enumerate(entetes_mcp, start=1):
            _style_cellule_en_tete(wsm.cell(row=5, column=c, value=h))
        for r, ventouse in enumerate(VENTOUSES_MCP, start=6):
            valeurs = [
                ventouse.dn, ventouse.serie, ventouse.orifice_mm,
                ventouse.q_admission_m3s, ventouse.q_evacuation_m3s,
                ventouse.q_critique_m3s, ventouse.origine_capacite,
            ]
            for c, val in enumerate(valeurs, start=1):
                _style_cellule_donnee(wsm.cell(row=r, column=c, value=val), align_center=(c != 7))
        for c, width in enumerate([12, 20, 14, 24, 24, 24, 42], start=1):
            wsm.column_dimensions[get_column_letter(c)].width = width

        ligne_resume = 6 + len(VENTOUSES_MCP) + 1
        wsm.cell(row=ligne_resume, column=1, value="Débit à couvrir (m³/s)").font = Font(bold=True)
        wsm.cell(row=ligne_resume, column=2, value=catalogue_mcp.debit_m3s)
        wsm.cell(row=ligne_resume + 1, column=1, value="DN proposé").font = Font(bold=True)
        wsm.cell(row=ligne_resume + 1, column=2, value=catalogue_mcp.dn_propose or "—")
        wsm.cell(row=ligne_resume + 2, column=1, value="Nombre d'unités").font = Font(bold=True)
        wsm.cell(row=ligne_resume + 2, column=2, value=catalogue_mcp.nombre)
        wsm.cell(row=ligne_resume + 3, column=1, value="Couverture").font = Font(bold=True)
        wsm.cell(row=ligne_resume + 3, column=2, value="OUI" if catalogue_mcp.couvert else "NON")
        if catalogue_mcp.avertissement:
            wsm.cell(row=ligne_resume + 4, column=1, value="Avertissement").font = Font(bold=True)
            wsm.cell(row=ligne_resume + 4, column=2, value=catalogue_mcp.avertissement)

    # ---- Feuille Configurations Air ----
    if configuration_equipements is not None:
        from .catalogue_ceai import (
            SOURCE_DOCX,
            ORIGINE_FIRM,
            PRESSION_REFERENCE,
            CONFIG_AUDIT,
            CONFIGURATIONS,
            VENTOUSES_TRIFON_CEAI,
            CLAPETS_CEAI,
            PURGEURS_SONIQUES_SNH,
            resume_configuration,
        )

        if isinstance(configuration_equipements, dict):
            choix = configuration_equipements.get("choix", CONFIG_AUDIT)
            configs = configuration_equipements.get(
                "configurations", configuration_equipements
            )
        else:
            configs, choix = configuration_equipements, CONFIG_AUDIT

        wsc = wb.create_sheet("Configurations Air")
        wsc["A1"] = "Configurations d'équipement — grands DN (choix utilisateur)"
        wsc["A1"].font = Font(bold=True, size=13, color="1F3B5C")
        wsc["A2"] = (
            f"Source : {SOURCE_DOCX} — capacités en m³/h à {PRESSION_REFERENCE} "
            f"; origine CEAI / TRIFON : {ORIGINE_FIRM}."
        )
        wsc["A3"] = f"Configuration retenue : {choix}"
        wsc["A3"].font = Font(bold=True, color="1B5E20")

        entetes_cfg = [
            "Configuration", "Qair (m³/s)", "Ventouse", "Cap. ventouse (m³/s)",
            "Clapet", "Cap. clapet (m³/s)", "Couverture", "Résumé",
        ]
        for c, h in enumerate(entetes_cfg, start=1):
            _style_cellule_en_tete(wsc.cell(row=5, column=c, value=h))
        ligne = 6
        for nom in CONFIGURATIONS:
            resultat = configs.get(nom)
            if resultat is None:
                continue
            v, c = resultat.ventouse, resultat.clapet
            valeurs = [
                ("★ RETENU — " if nom == choix else "") + nom,
                resultat.debit_m3s,
                f"{v.famille} {v.dn} ×{v.nombre}",
                v.capacite_totale_m3s,
                f"{c.famille} {c.dn} ×{c.nombre}",
                c.capacite_totale_m3s,
                "OUI" if resultat.couvert else "NON",
                resume_configuration(resultat),
            ]
            for col, val in enumerate(valeurs, start=1):
                _style_cellule_donnee(
                    wsc.cell(row=ligne, column=col, value=val),
                    align_center=(col != 8),
                )
            ligne += 1

        ligne += 1

        def _ecrire_table_organes(titre, table, ligne_depart):
            cellule = wsc.cell(row=ligne_depart, column=1, value=titre)
            cellule.font = Font(bold=True, size=11, color="1F3B5C")
            entetes = ["DN", "Capacité (m³/h)", "Capacité (m³/s)", "Retenu", "Origine"]
            for c, h in enumerate(entetes, start=1):
                _style_cellule_en_tete(wsc.cell(row=ligne_depart + 1, column=c, value=h))
            for r, organe in enumerate(table, start=ligne_depart + 2):
                valeurs = [
                    organe.dn,
                    organe.capacite_m3h,
                    organe.capacite_m3s,
                    organe.retenu,
                    organe.origine,
                ]
                for c, val in enumerate(valeurs, start=1):
                    _style_cellule_donnee(wsc.cell(row=r, column=c, value=val))
            return ligne_depart + 2 + len(table) + 1

        for titre, table in (
            ("Ventouses TRIFON (CEAI)", VENTOUSES_TRIFON_CEAI),
            ("Clapets d'admission CEAI", CLAPETS_CEAI),
            ("Purgeurs soniques SNH — référence purge continue", PURGEURS_SONIQUES_SNH),
        ):
            ligne = _ecrire_table_organes(titre, table, ligne)

        for c, width in enumerate([34, 18, 30, 22, 30, 22, 14, 90], start=1):
            wsc.column_dimensions[get_column_letter(c)].width = width

    wb.save(str(chemin))
    return chemin
