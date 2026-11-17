"""Modèles de données (entrées et résultats) pour le calcul des débits air/eau.

Toutes les unités sont du SI (m, m3/s, m/s, mce, kg/m3) sauf indication
contraire (diamètres d'équipement affichés en mm).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Constantes physiques du document
# ---------------------------------------------------------------------------
G: float = 9.81  # acceleration de la pesanteur (m/s2)
RHO_EAU: float = 1000.0  # masse volumique de l'eau (kg/m3)
K_VIDANGE_DEFAUT: float = 0.7  # coeff. de debit pour faibles charges (vidange, F1)
TEMPS_VIDANGE_CIBLE_DEFAUT: float = 2.0 * 3600.0  # 2 heures en secondes

# Coefficients de rugosite Strickler (F8) - doc: K=104 pour PRV, K=100 pour fonte
K_STRICKLER_PRC_DEFAUT: float = 104.0  # PRV (valeur par defaut)
K_STRICKLER_FONTE: float = 100.0  # Fonte

# Coefficients Allievi k pour la formule de celerite (Tableau 8 du document)
# k = 10^11 / E (E en Pa) ; valeurs par materiau selon le tableau :
#   Acier : 0,5  |  Fonte ductile : 0,6  |  Beton arme : 3,3 a 5,0
#   PVC rigide : 33,3  |  PEHD : 100 a 125
K_ALLIEVI_MATERIAU: dict[str, float] = {
    "Acier": 0.5,
    "Fonte ductile": 0.6,
    "Beton arme / precontraint": 4.0,
    "PVC rigide": 33.3,
    "Polyethylene HD": 112.5,
}
K_ALLIEVI_DEFAUT: float = K_ALLIEVI_MATERIAU["Fonte ductile"]  # 0,6

# Relation k = 10^11 / E (E en Pa) pour calcul a partir du module d'Young
K_ALLIEVI_FROM_E_FACTEUR: float = 1.0e11

# Constantes physiques de l'air (Loi de Saint-Venant, F5) - 20 degC
P1_ATMOSPHERIQUE_MCE: float = 10.33  # Pression atmosphérique absolue (mCE)
GAMMA_AIR: float = 1.4  # Coefficient adiabatique de l'air
R_AIR: float = 287.0  # Constante spécifique de l'air (J/(kg·K))
T_AIR_K: float = 293.0  # Température de l'air (K), 20 degC
CD_ORIFICE: float = 0.65  # Coefficient de débit d'orifice standard
SEUIL_SONIQUE_P2_MCE: float = 19.55  # Seuil pression absolue P2 au-delà duquel le débit se bloque (mCE)
P_RELATIVE_SEUIL_MCE: float = 9.2  # Seuil pression relative pour blocage sonique (mCE)

STATUT_OK = "OK"
STATUT_SUSPECT = "SUSPECT"
STATUT_EMPIRIQUE = "EMPIRIQUE"
STATUT_A_VERIFIER = "À VÉRIFIER"
STATUT_ILLISIBLE = "ILLISIBLE"
STATUT_COHERENT = "COHÉRENT"

# Statuts qui interdisent un dimensionnement définitif sans validation du BE.
STATUTS_A_RISQUE: frozenset[str] = frozenset(
    {STATUT_SUSPECT, STATUT_EMPIRIQUE, STATUT_A_VERIFIER, STATUT_ILLISIBLE}
)


# ---------------------------------------------------------------------------
# Vidanges (points bas) - Section 2 du PDF
# ---------------------------------------------------------------------------
@dataclass
class VidangeInputs:
    """Entrées pour le calcul d'un ouvrage de vidange.

    Attributes:
        longueur_troncon: L du tronçon contrôlé par la vidange (m).
        diam_conduit: diamètre intérieur de la conduite D (m).
        hauteur_eau: hauteur moyenne d'eau h dans le tronçon (m).
        coeff_debit: K, coefficient de débit (0,7 pour faibles charges).
        temps_vidange_cible: temps de vidange visé (s), défaut 7200 s (2 h).
    """

    longueur_troncon: float = 0.0
    diam_conduit: float = 0.0
    hauteur_eau: float = 0.0
    coeff_debit: float = K_VIDANGE_DEFAUT
    temps_vidange_cible: float = TEMPS_VIDANGE_CIBLE_DEFAUT


@dataclass
class VidangeResult:
    section: float = 0.0  # s de la vidange (m2) si on part d'un diamètre donné
    debit_decharge: float = 0.0  # Q dechantge (m3/s)
    diametre_vidange: float = 0.0  # d en mm via F2 (SUSPECT)
    section_vidange: float = 0.0  # section de la vidange associée à d (m2)
    volume_troncon: float = 0.0  # volume d'eau du tronçon (m3)
    debit_necessaire: float = 0.0  # Q nécessaire pour vidanger en temps cible (m3/s)
    formule_f2_alerte: bool = False


# ---------------------------------------------------------------------------
# Ventouses (points hauts) - Section 3 du PDF
# ---------------------------------------------------------------------------
@dataclass
class VentouseInputs:
    """Entrées pour le calcul des 3 fonctions d'une ventouse automatique."""

    # --- 1ère fonction : dégazage (coup de bélier) ---
    celerite_a: float | None = None  # a (m/s), si None -> calculée par Allievi (F3)
    masse_volumique: float = RHO_EAU
    module_elasticite_conduite: float = 20.0e9  # E (Pa), PRV = 20 GPa
    coeff_compressibilite_eau: float = 2.07e9  # k (Pa)
    diam_conduit: float = 0.0  # d (m), diamètre intérieur de la conduite
    epaisseur_conduite: float = 0.0  # e (m)
    coeff_ancrage: float = 1.0  # psi (coeff. d'ancrage, absent du PDF -> à vérifier)
    delta_h_max: float = 10.0  # ΔH suppression max admissible (m)
    section_conduite: float | None = None  # S0 (m2), si None -> π/4 * d^2

    # --- 2ème fonction : remplissage ---
    vitesse_remplissage: float = 1.0  # V (m/s), 1 m/s doc ; 0,5 m/s en vérification

    # --- 3ème fonction : admission d'air (vidange / casse franche) ---
    coeff_rugosite: float = K_STRICKLER_PRC_DEFAUT  # K Strickler (m^(1/3)/s) : 104 PRV / 100 fonte
    k_allievi: float = K_ALLIEVI_DEFAUT  # Coefficient Allievi k (fonte ductile par defaut, 0,6)
    module_young_e: float = 0.0  # Module d'Young E (Pa), si saisi k est recalcule : k = 10^11 / E
    p2_pression_absolue_mce: float = P1_ATMOSPHERIQUE_MCE  # Pression absolue P2 dans la conduite (mCE)
    pente: float = 0.0  # i (m/m)
    longueur_troncon: float = 0.0  # L (m)
    cote_ventouse: float = 0.0  # cote projet de la ventouse (m)
    cote_vidange: float = 0.0  # cote projet de la vidange (m)
    hauteur_motrice: float | None = None  # H (m), si None -> F11
    coeff_singularites: float = 1.0  # k_s pertes singulières (ambigu dans le PDF)


@dataclass
class VentouseResult:
    # 1ère fonction - dégazage
    celerite_a: float = 0.0
    qair_degazage: float = 0.0
    diametre_orifice_degazage: float = 0.0  # d1 (m)
    delta_h: float = 0.0
    degazage_conforme: bool = True

    # 2ème fonction - remplissage
    q_eau_remplissage: float = 0.0
    qair_remplissage: float = 0.0
    diametre_orifice_remplissage: float = 0.0  # d2 (m)

    # 3ème fonction - admission casse franche
    vitesse_vidange: float = 0.0
    q_eau_vidange: float = 0.0
    qair_admission: float = 0.0
    hauteur_motrice: float = 0.0
    coeff_singularites: float = 1.0  # ξ retenu pour F10 (1 = v²/2g, 2 = v²/g)


# ---------------------------------------------------------------------------
# Sélection d'équipement
# ---------------------------------------------------------------------------
@dataclass
class EquipementChoice:
    type_equipement: str  # "Ventouse PAM" ou "Clapet SNH"
    dn: str
    debit_admis: float  # m3/s
    marge: float  # débit admis - débit calculé (m3/s)
    fonction: str  # "admission" ou "evacuation"


# ---------------------------------------------------------------------------
# Vérifications (page 6 du PDF)
# ---------------------------------------------------------------------------
@dataclass
class VerificationResult:
    vitesse_remplissage_admise: float = 0.5  # m/s
    debit_remplissage_reference: float = 0.0  # m3/s
    debit_remplissage_reference_m3h: float = 0.0  # m3/h
    degazage_pourcentage_qnom: float = 2.0  # %
    debit_degazage_verification: float = 0.0  # m3/h
    debit_nominal: float = 0.0  # m3/s
    tous_conformes: bool = True
    messages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Projet partagé — source de vérité unique pour les 6 onglets
# ---------------------------------------------------------------------------
@dataclass
class DonneesProjet:
    """Données d'entrée communes à tous les onglets (unités SI).

    Les onglets lisent et écrivent ce même objet : une valeur saisie dans
    un onglet (diamètre, longueur, cote, matériau…) est immédiatement
    réutilisée par les autres, ce qui évite les incohérences de dossier.
    """

    # --- Identité du projet ---
    nom: str = "Adduction BR3_LOT 8"
    reference: str = "MK_Debits_Air_Eau"
    site: str = ""
    maitre_ouvrage: str = ""
    operateur: str = ""
    date_projet: str = ""
    notes: str = ""

    # --- Données hydrauliques partagées ---
    diam_conduit: float = 2.0  # D (m)
    longueur_troncon: float = 848.3  # L (m)
    hauteur_eau: float = 1.5  # h moyenne pour la vidange (m)
    pente: float = 0.0027  # i (m/m)
    coeff_debit_vidange: float = K_VIDANGE_DEFAUT  # K vidange
    temps_vidange_h: float = 2.0  # temps de vidange cible (h)
    epaisseur_conduite: float = 0.010  # e (m)
    materiau: str = "Fonte ductile"
    coeff_allievi: float = K_ALLIEVI_DEFAUT  # k Allievi
    celerite_a: float | None = None  # a (m/s) si imposée
    delta_h_max: float = 10.0  # ΔH de dégazage (m)
    p2_pression_absolue_mce: float = P1_ATMOSPHERIQUE_MCE  # P2 (mCE)
    vitesse_remplissage: float = 1.0  # V (m/s)
    coeff_rugosite: float = K_STRICKLER_PRC_DEFAUT  # K Strickler
    coeff_singularites: float = 1.0  # ξ (F9/F10) : pertes singulières en multiples de v²/2g
    cote_ventouse: float = 112.98  # (m)
    cote_vidange: float = 99.05  # (m)

    # --- Données Allouane (import depuis DOCX) ---
    altitude_ve: float = 0.0  # altitude point haut Ve (m NGM)
    altitude_vi1: float = 0.0  # altitude vidange amont Vi1 (m NGM)
    altitude_vi2: float = 0.0  # altitude vidange aval Vi2 (m NGM)
    longueur_troncon_2: float = 0.0  # longueur tronçon aval L2 (m)

    # --- Vérifications page 6 ---
    vitesse_remplissage_admise: float = 0.5  # m/s
    debit_nominal: float = 5.3  # m3/s
    degazage_pct_qnom: float = 2.0  # %

    # --- Sélection d'équipement ---
    debit_air_equipement: float = 0.0  # m3/s


@dataclass
class Projet:
    """Dossier complet : données partagées, résultats et traçabilité."""

    donnees: DonneesProjet = field(default_factory=DonneesProjet)
    vidange: VidangeResult | None = None
    ventouse: VentouseResult | None = None
    equipements: list[EquipementChoice] = field(default_factory=list)
    verification: VerificationResult | None = None
    horodatage: str = ""

    # -- Résumé / tableau de bord -------------------------------------------
    def etapes(self) -> dict[str, bool]:
        """État d'avancement des 6 étapes du workflow."""
        v = self.ventouse
        return {
            "Vidange (points bas)": self.vidange is not None,
            "Dégazage (ventouse)": bool(v and (v.qair_degazage > 0 or v.celerite_a > 0)),
            "Remplissage (ventouse)": bool(v and v.qair_remplissage > 0),
            "Admission d'air (ventouse)": bool(v and v.qair_admission > 0),
            "Sélection équipement": bool(self.equipements) or self.donnees.debit_air_equipement > 0,
            "Vérifications & rapport": self.verification is not None,
        }

    def prochaine_etape(self) -> str:
        for nom, fait in self.etapes().items():
            if not fait:
                return f"À faire : {nom}"
        return "Dossier complet — exporter le rapport consolidé."

    def resume_texte(self) -> str:
        """Synthèse lisible utilisée comme en-tête des rapports."""
        d = self.donnees
        lignes = [
            f"Projet : {d.nom}",
            f"Référence : {d.reference}",
        ]
        if d.site:
            lignes.append(f"Site : {d.site}")
        if d.maitre_ouvrage:
            lignes.append(f"Maître d'ouvrage : {d.maitre_ouvrage}")
        lignes.append(
            f"Conduite : D = {d.diam_conduit:.3f} m ; L = {d.longueur_troncon:.1f} m ; "
            f"matériau = {d.materiau} ; e = {d.epaisseur_conduite*1000:.1f} mm."
        )
        lignes.append(
            f"Cotes : ventouse = {d.cote_ventouse:.2f} m ; vidange = {d.cote_vidange:.2f} m ; "
            f"pente = {d.pente:.4f} m/m."
        )
        lignes.append(self.prochaine_etape())
        return "\n".join(lignes)

    # -- Sérialisation JSON -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "MK_Debits_Air_Eau",
            "version": 2,
            "horodatage": _dt.datetime.now().isoformat(timespec="seconds"),
            "donnees": asdict(self.donnees),
            "vidange": asdict(self.vidange) if self.vidange is not None else None,
            "ventouse": asdict(self.ventouse) if self.ventouse is not None else None,
            "equipements": [asdict(e) for e in self.equipements],
            "verification": (
                asdict(self.verification) if self.verification is not None else None
            ),
            "etapes": self.etapes(),
            "prochaine_etape": self.prochaine_etape(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Projet":
        donnees = DonneesProjet(**_filtrer(DonneesProjet, data.get("donnees") or {}))
        vidange = (
            VidangeResult(**_filtrer(VidangeResult, data["vidange"]))
            if data.get("vidange")
            else None
        )
        ventouse = (
            VentouseResult(**_filtrer(VentouseResult, data["ventouse"]))
            if data.get("ventouse")
            else None
        )
        equipements = [
            EquipementChoice(**_filtrer(EquipementChoice, e))
            for e in (data.get("equipements") or [])
        ]
        verification = (
            VerificationResult(**_filtrer(VerificationResult, data["verification"]))
            if data.get("verification")
            else None
        )
        return cls(
            donnees=donnees,
            vidange=vidange,
            ventouse=ventouse,
            equipements=equipements,
            verification=verification,
            horodatage=str(data.get("horodatage", "")),
        )


def _filtrer(classe: type, valeurs: dict[str, Any]) -> dict[str, Any]:
    """Ne conserve que les clés connues du dataclass (compatibilité ascendante)."""
    connues = {f.name for f in fields(classe)}
    return {k: v for k, v in valeurs.items() if k in connues}
