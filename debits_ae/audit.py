"""Données de l'audit technique et comparatif « note initiale / note corrigée ».

Source : ``Audit_et_Correction_Note_BR3_LOT8.docx`` (BR3_LOT 8).
Ce module ne réalise aucun calcul hydraulique : il rassemble les valeurs
relevées dans la note initiale, les valeurs recalculées par l'audit et les
corrections de formules, afin que les rapports DOCX/XLSX et l'interface
puissent présenter un comparatif honnête et traçable.

Les valeurs de l'Annexe 1 (points hauts) et de l'Annexe 2 (vidanges) sont
celles des tableaux corrigés de l'audit. Les valeurs « note » proviennent de
l'Annexe 1/2 d'origine (``Calcul des debits points bas et  hauts.pdf``).

Conventions :
    * débits en m³/s, diamètres de conduite en m, diamètres d'équipement en mm ;
    * une capacité d'équipement est comparée au débit à couvrir avec une
      tolérance de 1·10⁻⁹ pour éviter les faux négatifs d'arrondi.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tables import TABLE_PAM, TABLE_SNH

# ---------------------------------------------------------------------------
# Constantes de l'audit
# ---------------------------------------------------------------------------
# F2 - diamètre de vidange pour t = 2 h, K = 0,7, g = 9,81
COEFF_VIDANGE_TEXTE_NOTE: float = 13.39  # formule écrite page 2 (en fait 30 min)
COEFF_VIDANGE_ANNEXE_NOTE: float = 9.47  # coefficient réellement appliqué en Annexe 2
COEFF_VIDANGE_AUDIT: float = 6.69  # valeur exacte pour une vidange en 2 h

# F10 - coefficient de perte de charge linéaire pour K = 104 (PRV)
COEFF_F10_AUDIT: float = 0.000587  # = 4^(4/3) / 104²
COEFF_F10_XI_AUDIT: float = 2.0  # k = 2 retenu par l'audit

# Vérification du dégazage en service (page 6)
DEGAZAGE_NOTE_M3H: float = 360.0  # 2 % × 5,3 × 3600 mal calculé
DEGAZAGE_AUDIT_M3H: float = 381.6  # 2 % × 5,3 × 3600 = 381,6

# Conversion de la ventouse PAM DN200 (tableau page 6)
PAM_DN200_M3H: float = 14454.0
PAM_DN200_TABLE_M3S: float = 4.165  # valeur imprimée dans le tableau
PAM_DN200_CONVERTI_M3S: float = PAM_DN200_M3H / 3600.0  # 4,015 m³/s exact

# Débit de remplissage à évacuer pour DN 2000 à 0,5 m/s
DEBIT_REMPLISSAGE_DN2000_M3H: float = 5655.0
PAM_DN200_EVACUATION_M3H: float = 5300.0  # sous 1 mCE de surpression

TOLERANCE_M3S: float = 1.0e-9

# Capacités unitaires reprises des tables constructeur (page 6)
_CAPACITE_PAM = {
    car.dn: car.debit_admission_depression_3m_m3s
    for car in TABLE_PAM
    if car.debit_admission_depression_3m_m3s is not None
}
_CAPACITE_SNH = {
    car.dn: car.debit_admission_depression_3m_m3s
    for car in TABLE_SNH
    if car.debit_admission_depression_3m_m3s is not None
}


# ---------------------------------------------------------------------------
# Corrections de l'audit
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CorrectionAudit:
    """Une erreur relevée par l'audit et la façon dont l'application la traite."""

    code: str
    domaine: str
    constat: str
    correction: str
    application: str
    appliquee: bool = True


CORRECTIONS_AUDIT: list[CorrectionAudit] = [
    CorrectionAudit(
        code="C1",
        domaine="Vidanges — F2",
        constat="Coefficient 13,39 pour une vidange en 2 h (page 2).",
        correction="Coefficient exact 6,69 pour t = 2 h, K = 0,7, g = 9,81 m/s².",
        application="F2 utilise 6,69 (13,39 = 2 × 6,69 correspond à 30 min).",
    ),
    CorrectionAudit(
        code="C2",
        domaine="Vidanges — Annexe 2",
        constat="Coefficient 9,47 au lieu de 13,39, somme des longueurs et hauteur moyenne biaisée ; "
        "formule non adaptée au tronçon amont seul (PM 59 701,59 : 442,29 mm au lieu de 312,7 mm).",
        correction="Coefficient unique 6,69 et hauteur moyenne pondérée des deux branches.",
        application="Le comparatif Annexe 2 reprend les diamètres corrigés ; "
        "l'application signale l'écart avec la note initiale.",
    ),
    CorrectionAudit(
        code="C3",
        domaine="Vidanges — DN",
        constat="Uniformisation en DN 400 mm sur tous les points bas.",
        correction="Retenir le DN théorique exact par point bas (DN 150 à DN 500).",
        application="Le comparatif propose le DN normalisé exact ; les cas "
        "PM 52 621,59 et PM 58 721,59 sont signalés comme critiques.",
    ),
    CorrectionAudit(
        code="C4",
        domaine="Ventouse — F3 Allievi",
        constat="a = 1/[(ρ/g)(k/10^9 + d·E·e/10^9)] : racine oubliée, division par g, "
        "produit d·E·e au numérateur.",
        correction="a = 1/√[ρ·(1/K_eau + d/(E·e))], avec k = 10^11/E.",
        application="F3 implémente la forme exacte ; le facteur 10^11 est retenu.",
    ),
    CorrectionAudit(
        code="C5",
        domaine="Ventouse — F5 Saint-Venant",
        constat="Qair = 195 × (P1/P2)^0,714 × s : terme moteur √(1 − (P1/P2)^0,286) manquant.",
        correction="Qair = 499·s·(P1/P2)^0,714·√[1 − (P1/P2)^0,286] si P2 < 19,55 mCE ; "
        "Qair = 129·s si P2 ≥ 19,55 mCE.",
        application="F5 corrigée (499/129) ; l'ancienne constante 195 est rejetée.",
    ),
    CorrectionAudit(
        code="C6",
        domaine="Ventouse — d1/d",
        constat="d1/d = (ΔH/(19,9·a))^0,5 suppose une vitesse d'air de 195 m/s.",
        correction="Inverser la loi de Saint-Venant validée pour obtenir d1.",
        application="F6 inverse F5 puis d1 = 2·√(s/π) ; l'ancienne relation est abandonnée.",
    ),
    CorrectionAudit(
        code="C7",
        domaine="Ventouse — remplissage",
        constat="Vitesse de remplissage 1 m/s (page 5) contre 0,5 m/s (page 6).",
        correction="Retenir 0,5 m/s pour la vérification de l'évacuation d'air.",
        application="La vérification utilise 0,5 m/s (5 655 m³/h pour DN 2000).",
    ),
    CorrectionAudit(
        code="C8",
        domaine="Ventouse — équipement",
        constat="Une seule ventouse PAM DN200 évacue 5 300 m³/h < 5 655 m³/h.",
        correction="Prévoir au moins 2 ventouses DN200 (ou 1 DN200 + 1 clapet DN150) "
        "aux points concernés.",
        application="Les combinaisons d'équipements réelles sont présentées dans le rapport.",
    ),
    CorrectionAudit(
        code="C9",
        domaine="Ventouse — dégazage",
        constat="2 % × 5,3 × 3600 = 360 m³/h.",
        correction="Résultat exact : 381,6 m³/h (360 correspond à 5,0 m³/s).",
        application="Le calcul de vérification donne 381,6 m³/h.",
    ),
    CorrectionAudit(
        code="C10",
        domaine="Ventouse — conversion",
        constat="Tableau PAM DN200 : « 14 454 (4,165 m³/s) ».",
        correction="14 454 m³/h = 4,015 m³/s ; 4,165 m³/s = 14 994 m³/h.",
        application="L'écart est signalé, pas masqué : les deux valeurs sont affichées. "
        "Les combinaisons de l'audit utilisent 4,165 m³/s.",
    ),
    CorrectionAudit(
        code="C11",
        domaine="Points hauts — F11",
        constat="H = cote ventouse − 3 m − cote vidange appliqué seulement sur 4 lignes ; "
        "soustractions arbitraires de 2,0 / 1,0 / 0,5 m ailleurs.",
        correction="Appliquer H = max(0 ; cote_ventouse − 3 − cote_vidange) partout.",
        application="F11 borne H à 0 et l'applique uniformément.",
    ),
    CorrectionAudit(
        code="C12",
        domaine="Points hauts — équipement",
        constat="4 points hauts sous-équipés : PM 51 041,59 ; 51 801,59 ; 53 561,59 ; 57 121,59.",
        correction="Remplacer les purgeurs seuls par des ventouses triple fonction et "
        "dimensionner chaque point sur son débit de casse franche.",
        application="Le comparatif vérifie que chaque équipement corrigé couvre le débit.",
    ),
]


# ---------------------------------------------------------------------------
# Comparatif Annexe 1 — points hauts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComparatifPointHaut:
    """Une ligne de l'Annexe 1 : note initiale contre note corrigée."""

    pm: str
    dn_m: float
    qair_note: float
    equipement_note: str
    capacite_note: float
    qair_corrige: float
    equipement_corrige: str
    capacite_corrigee: float

    @property
    def marge_note(self) -> float:
        return self.capacite_note - self.qair_note

    @property
    def marge_corrigee(self) -> float:
        return self.capacite_corrigee - self.qair_corrige

    @property
    def couvre_note(self) -> bool:
        return self.capacite_note + TOLERANCE_M3S >= self.qair_note

    @property
    def couvre_corrige(self) -> bool:
        return self.capacite_corrigee + TOLERANCE_M3S >= self.qair_corrige

    @property
    def verdict_note(self) -> str:
        return "Couvre" if self.couvre_note else "Sous-équipé"

    @property
    def verdict_corrige(self) -> str:
        return "Couvre" if self.couvre_corrige else "Sous-équipé"


COMPARATIF_POINTS_HAUTS: list[ComparatifPointHaut] = [
    ComparatifPointHaut(
        pm="50 529,89", dn_m=2.0,
        qair_note=19.80, equipement_note="2 ventouses DN200 + 1 clapet DN250",
        capacite_note=21.33,
        qair_corrige=18.89, equipement_corrige="2 ventouses DN200 + 1 clapet DN250",
        capacite_corrigee=21.33,
    ),
    ComparatifPointHaut(
        pm="51 041,59", dn_m=2.0,
        qair_note=13.20, equipement_note="1 purgeur sonique PSA250 + 1 clapet DN250",
        capacite_note=13.00,
        qair_corrige=10.63, equipement_corrige="1 ventouse DN200 + 1 clapet DN250",
        capacite_corrigee=17.17,
    ),
    ComparatifPointHaut(
        pm="51 801,59", dn_m=2.0,
        qair_note=8.00, equipement_note="1 ventouse DN200",
        capacite_note=4.17,
        qair_corrige=8.01, equipement_corrige="2 ventouses DN200 (ou 1 DN200 + 1 clapet DN150)",
        capacite_corrigee=8.33,
    ),
    ComparatifPointHaut(
        pm="53 561,59", dn_m=2.0,
        qair_note=13.60, equipement_note="1 purgeur sonique PSA250 + 1 clapet DN250",
        capacite_note=13.00,
        qair_corrige=10.03, equipement_corrige="1 ventouse DN200 + 1 clapet DN250",
        capacite_corrigee=17.17,
    ),
    ComparatifPointHaut(
        pm="54 264,59", dn_m=2.0,
        qair_note=10.10, equipement_note="1 ventouse DN200 + 1 clapet DN200",
        capacite_note=11.97,
        qair_corrige=5.90, equipement_corrige="2 ventouses DN200 (ou 1 DN200 + 1 clapet DN150)",
        capacite_corrigee=8.33,
    ),
    ComparatifPointHaut(
        pm="54 783,45", dn_m=2.0,
        qair_note=16.00, equipement_note="1 ventouse DN200 + 1 clapet DN250",
        capacite_note=16.00,
        qair_corrige=15.87, equipement_corrige="2 ventouses DN200 + 1 clapet DN250",
        capacite_corrigee=21.33,
    ),
    ComparatifPointHaut(
        pm="55 241,59", dn_m=2.0,
        qair_note=13.70, equipement_note="1 ventouse DN200 + 1 clapet DN250",
        capacite_note=17.17,
        qair_corrige=13.80, equipement_corrige="2 ventouses DN200 + 1 clapet DN250",
        capacite_corrigee=21.33,
    ),
    ComparatifPointHaut(
        pm="56 201,59", dn_m=2.0,
        qair_note=14.80, equipement_note="1 ventouse DN200 + 1 clapet DN250",
        capacite_note=17.17,
        qair_corrige=14.83, equipement_corrige="2 ventouses DN200 + 1 clapet DN250",
        capacite_corrigee=21.33,
    ),
    ComparatifPointHaut(
        pm="57 121,59", dn_m=1.6,
        qair_note=43.90, equipement_note="1 ventouse DN200 + 3 clapets DN250",
        capacite_note=43.17,
        qair_corrige=43.96, equipement_corrige="2 ventouses DN200 + 3 clapets DN250",
        capacite_corrigee=47.33,
    ),
    ComparatifPointHaut(
        pm="58 961,59", dn_m=2.0,
        qair_note=10.70, equipement_note="1 ventouse DN200 + 1 clapet DN200",
        capacite_note=11.97,
        qair_corrige=6.53, equipement_corrige="2 ventouses DN200 (ou 1 DN200 + 1 clapet DN150)",
        capacite_corrigee=8.33,
    ),
]


# ---------------------------------------------------------------------------
# Comparatif Annexe 2 — vidanges
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComparatifVidange:
    """Une ligne de l'Annexe 2 : diamètre de la note contre diamètre exact."""

    pm: str
    dn_m: float
    longueur_totale_m: float
    diametre_note_mm: float
    diametre_corrige_mm: float
    dn_corrige: str
    statut: str
    commentaire: str
    dn_note: str = "DN 400"

    @property
    def ecart_mm(self) -> float:
        return self.diametre_note_mm - self.diametre_corrige_mm

    @property
    def ecart_pct(self) -> float:
        if self.diametre_corrige_mm <= 0:
            return 0.0
        return 100.0 * self.ecart_mm / self.diametre_corrige_mm


COMPARATIF_VIDANGES: list[ComparatifVidange] = [
    ComparatifVidange(
        pm="50 741,59", dn_m=2.0, longueur_totale_m=511.70,
        diametre_note_mm=369.05, diametre_corrige_mm=316.1,
        dn_corrige="DN 350 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h)",
    ),
    ComparatifVidange(
        pm="52 621,59", dn_m=2.0, longueur_totale_m=2520.00,
        diametre_note_mm=588.34, diametre_corrige_mm=477.6,
        dn_corrige="DN 500", statut="Sous-dimensionné",
        commentaire="DN 400 trop petit (~3 h 10 de vidange)",
    ),
    ComparatifVidange(
        pm="54 041,59", dn_m=2.0, longueur_totale_m=703.00,
        diametre_note_mm=348.76, diametre_corrige_mm=288.9,
        dn_corrige="DN 300 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h)",
    ),
    ComparatifVidange(
        pm="54 661,59", dn_m=2.0, longueur_totale_m=518.86,
        diametre_note_mm=330.25, diametre_corrige_mm=279.8,
        dn_corrige="DN 300 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h)",
    ),
    ComparatifVidange(
        pm="55 081,59", dn_m=2.0, longueur_totale_m=458.14,
        diametre_note_mm=253.45, diametre_corrige_mm=210.9,
        dn_corrige="DN 250 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h)",
    ),
    ComparatifVidange(
        pm="55 781,59", dn_m=2.0, longueur_totale_m=960.00,
        diametre_note_mm=411.07, diametre_corrige_mm=340.3,
        dn_corrige="DN 350 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h)",
    ),
    ComparatifVidange(
        pm="56 845,25", dn_m=1.6, longueur_totale_m=920.00,
        diametre_note_mm=147.78, diametre_corrige_mm=124.6,
        dn_corrige="DN 150", statut="Surdimensionné",
        commentaire="Forte charge (90 m) : préférer DN 150-200",
    ),
    ComparatifVidange(
        pm="58 721,59", dn_m=2.0, longueur_totale_m=1840.00,
        diametre_note_mm=562.61, diametre_corrige_mm=419.2,
        dn_corrige="DN 450", statut="Limite",
        commentaire="DN 400 légèrement juste (~2 h 12)",
    ),
    ComparatifVidange(
        pm="59 701,59", dn_m=2.0, longueur_totale_m=740.00,
        diametre_note_mm=442.29, diametre_corrige_mm=312.7,
        dn_corrige="DN 350 (ou 400)", statut="Conforme",
        commentaire="DN 400 conforme (< 2 h) ; d de la note surévalué (tronçon amont seul)",
    ),
]


# ---------------------------------------------------------------------------
# Combinaisons d'équipements réelles (aucune table « PAM 800 / SNH 800 »)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CombinaisonEquipement:
    """Combinaison de ventouses PAM DN200 et de clapets SNH DN250."""

    libelle: str
    nb_pam_dn200: int = 0
    nb_snh_dn250: int = 0

    @property
    def capacite_m3s(self) -> float:
        return (
            self.nb_pam_dn200 * (_CAPACITE_PAM.get("DN200") or 0.0)
            + self.nb_snh_dn250 * (_CAPACITE_SNH.get("DN250") or 0.0)
        )


COMBINAISONS_EQUIPEMENTS: list[CombinaisonEquipement] = [
    CombinaisonEquipement("2 ventouses PAM DN200 + 1 clapet SNH DN250", 2, 1),
    CombinaisonEquipement("2 ventouses PAM DN200 + 3 clapets SNH DN250", 2, 3),
    CombinaisonEquipement("1 ventouse PAM DN200 + 1 clapet SNH DN250", 1, 1),
    CombinaisonEquipement("2 ventouses PAM DN200", 2, 0),
    CombinaisonEquipement("1 ventouse PAM DN200", 1, 0),
    CombinaisonEquipement("1 clapet SNH DN250", 0, 1),
]


# ---------------------------------------------------------------------------
# Résumés
# ---------------------------------------------------------------------------
def points_hauts_sous_equipes() -> list[ComparatifPointHaut]:
    """Points hauts dont l'équipement de la note ne couvre pas son propre débit."""
    return [ligne for ligne in COMPARATIF_POINTS_HAUTS if not ligne.couvre_note]


def points_hauts_non_couverts_apres_correction() -> list[ComparatifPointHaut]:
    """Points hauts encore sous-équipés après la correction de l'audit."""
    return [ligne for ligne in COMPARATIF_POINTS_HAUTS if not ligne.couvre_corrige]


def resume_points_hauts() -> dict[str, float | int]:
    """Indicateurs du comparatif Annexe 1."""
    total = len(COMPARATIF_POINTS_HAUTS)
    sous_equipes = len(points_hauts_sous_equipes())
    non_couverts = len(points_hauts_non_couverts_apres_correction())
    return {
        "total": total,
        "sous_equipes_note": sous_equipes,
        "couverts_note": total - sous_equipes,
        "non_couverts_apres_correction": non_couverts,
        "couverts_apres_correction": total - non_couverts,
    }


def resume_vidanges() -> dict[str, int]:
    """Indicateurs du comparatif Annexe 2."""
    resume: dict[str, int] = {"total": len(COMPARATIF_VIDANGES)}
    for ligne in COMPARATIF_VIDANGES:
        resume[ligne.statut] = resume.get(ligne.statut, 0) + 1
    return resume


def corrections_non_appliquees() -> list[CorrectionAudit]:
    """Corrections de l'audit qui ne seraient pas encore prises en compte."""
    return [c for c in CORRECTIONS_AUDIT if not c.appliquee]
