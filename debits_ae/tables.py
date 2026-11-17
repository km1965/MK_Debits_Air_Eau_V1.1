"""Tables de référence du document PDF (page 6 de la note).

Contient les caractéristiques réelles des ventouses triple fonction type PAM
et des clapets d'entrée d'air type SNH. Ces valeurs unitaires servent à
construire les combinaisons d'équipements (voir :mod:`debits_ae.audit`).

ATTENTION — incohérence relevée dans la table PAM (DN200) :
14 454 m³/h ≠ 4,165 m³/s (4,165 × 3600 = 14 994 m³/h). La valeur imprimée
4,165 m³/s est conservée pour rester fidèle au tableau constructeur, mais la
conversion exacte 14 454 / 3600 = 4,015 m³/s est exposée par la propriété
``debit_admission_converti_m3s``. L'écart doit être signalé, pas masqué.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CaracteristiqueEquipement:
    dn: str
    debit_admission_depression_3m_m3h: float | None = None
    debit_admission_depression_3m_m3s: float | None = None
    debit_evacuation_surpression_1m_m3h: float | None = None
    debit_evacuation_surpression_1m_m3s: float | None = None

    @property
    def debit_admission_converti_m3s(self) -> float | None:
        """Conversion exacte du débit m³/h en m³/s (révèle l'écart du tableau)."""
        if self.debit_admission_depression_3m_m3h is None:
            return None
        return self.debit_admission_depression_3m_m3h / 3600.0

    @property
    def ecart_conversion_m3s(self) -> float | None:
        """Écart entre la valeur imprimée et la conversion exacte (m³/s)."""
        converti = self.debit_admission_converti_m3s
        if converti is None or self.debit_admission_depression_3m_m3s is None:
            return None
        return self.debit_admission_depression_3m_m3s - converti


# ---------------------------------------------------------------------------
# Table PAM - Ventouses triple fonction (page 6 du PDF)
# Colonnes : DN | Débit admission air (dépression 3 m) m3/h (m3/s) |
#            Débit évacuation air (surpression 1 m) m3/h
# ---------------------------------------------------------------------------
TABLE_PAM: list[CaracteristiqueEquipement] = [
    CaracteristiqueEquipement(
        dn="DN100",
        debit_admission_depression_3m_m3h=3330,
        debit_admission_depression_3m_m3s=0.925,
        debit_evacuation_surpression_1m_m3h=1298,
        debit_evacuation_surpression_1m_m3s=None,
    ),
    CaracteristiqueEquipement(
        dn="DN150",
        debit_admission_depression_3m_m3h=8173,
        debit_admission_depression_3m_m3s=2.27,
        debit_evacuation_surpression_1m_m3h=3338,
        debit_evacuation_surpression_1m_m3s=None,
    ),
    CaracteristiqueEquipement(
        dn="DN200",
        debit_admission_depression_3m_m3h=14454,
        debit_admission_depression_3m_m3s=4.165,
        debit_evacuation_surpression_1m_m3h=5300,
        debit_evacuation_surpression_1m_m3s=None,
    ),
]

# Incohérence notee : 14 454 m3/h != 4,165 m3/s (4,165 × 3600 = 14 994 m3/h)

# ---------------------------------------------------------------------------
# Table SNH - Clapots d'entree d'air (page 6 du PDF)
# Colonnes : DN clapet | m3/h | m3/s
# ---------------------------------------------------------------------------
TABLE_SNH: list[CaracteristiqueEquipement] = [
    CaracteristiqueEquipement(dn="DN100", debit_admission_depression_3m_m3h=9360, debit_admission_depression_3m_m3s=2.6),
    CaracteristiqueEquipement(dn="DN150", debit_admission_depression_3m_m3h=16380, debit_admission_depression_3m_m3s=4.55),
    CaracteristiqueEquipement(dn="DN200", debit_admission_depression_3m_m3h=28080, debit_admission_depression_3m_m3s=7.8),
    CaracteristiqueEquipement(dn="DN250", debit_admission_depression_3m_m3h=46800, debit_admission_depression_3m_m3s=13.0),
]


# ---------------------------------------------------------------------------
# Aide à la sélection
# ---------------------------------------------------------------------------
def _debit_m3s(car: CaracteristiqueEquipement, fonction: str) -> float | None:
    if fonction == "admission":
        return car.debit_admission_depression_3m_m3s
    if fonction == "evacuation":
        return car.debit_evacuation_surpression_1m_m3s
    return None


def choix_ventouse_pam(
    debit_calcule_m3s: float, fonction: str = "admission"
) -> CaracteristiqueEquipement | None:
    """Retourne la premiere ventouse PAM dont le débit admis couvre le débit calculé."""
    for car in TABLE_PAM:
        debit = _debit_m3s(car, fonction)
        if debit is not None and debit >= debit_calcule_m3s:
            return car
    return None


def choix_clapet_snh(
    debit_calcule_m3s: float,
) -> CaracteristiqueEquipement | None:
    """Retourne le premier clapet SNH dont le débit d'admission couvre le débit calculé."""
    for car in TABLE_SNH:
        if car.debit_admission_depression_3m_m3s is not None and car.debit_admission_depression_3m_m3s >= debit_calcule_m3s:
            return car
    return None


# ---------------------------------------------------------------------------
# Données de l'Annexe 1
# ---------------------------------------------------------------------------
# L'ancien extrait indicatif ``EXEMPLE_ANNEXE_1`` a été supprimé : ses valeurs
# étaient fausses (colonnes Qair max / débit admis inversées, capacité 19,8 au
# lieu de 21,33 m³/s). La référence unique et corrigée est désormais
# ``debits_ae.audit.COMPARATIF_POINTS_HAUTS``.
