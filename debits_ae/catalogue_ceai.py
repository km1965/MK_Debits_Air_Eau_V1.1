"""Catalogue CEAI / TRIFON et référence SNH - organes d'air pour grands DN.

Source : ``Catalogue des équipements.docx`` (racine du projet), annexe de
vérification. Capacités d'air admis en m³/h à la dépression nominale de 3 mCE
(NF EN 805), converties en m³/s par division par 3600.

Trois familles sont répertoriées :
- TRIFON (CEAI) - ventouse (DN50 a DN300) ;
- CEAI - clapet d'admission d'air (DN80 a DN500) ;
- SNH - purgeur sonique (DN200 a DN1500), rôle de purge continue, référence
  distincte du dimensionnement admission.

Les configurations AUDIT (PAM DN200 + clapets SNH) et CEAI sont comparées
côte à côte ; l'utilisateur choisit celle qui est retenue dans les rapports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .tables import TABLE_PAM, TABLE_SNH

SOURCE_DOCX = "Catalogue des équipements.docx"
ORIGINE_FIRM = "FIRM V1/2025"
PRESSION_REFERENCE = "3 mCE (NF EN 805)"

CONFIG_AUDIT = "PAM DN200 + clapets SNH (audit)"
CONFIG_CEAI = "Trifon CEAI + clapet CEAI"
CONFIGURATIONS: tuple[str, ...] = (CONFIG_AUDIT, CONFIG_CEAI)


@dataclass(frozen=True)
class OrganeAir:
    """Un organe d'air du catalogue, avec sa capacité unitaire."""

    famille: str
    dn: str
    capacite_m3h: float
    retenu: str = "—"
    origine: str = ORIGINE_FIRM

    @property
    def capacite_m3s(self) -> float:
        """Capacité convertie en m³/s."""
        return self.capacite_m3h / 3600.0


# TRIFON (CEAI) — Ventouse. Statut : validé ; origine FIRM V1/2025.
VENTOUSES_TRIFON_CEAI: tuple[OrganeAir, ...] = (
    OrganeAir("Ventouse Trifon CEAI", "DN50", 750),
    OrganeAir("Ventouse Trifon CEAI", "DN65", 1200),
    OrganeAir("Ventouse Trifon CEAI", "DN80", 2100),
    OrganeAir("Ventouse Trifon CEAI", "DN100", 3800),
    OrganeAir("Ventouse Trifon CEAI", "DN150", 8000),
    OrganeAir("Ventouse Trifon CEAI", "DN200", 17000, "---"),
    OrganeAir("Ventouse Trifon CEAI", "DN250", 26000),
    OrganeAir("Ventouse Trifon CEAI", "DN300", 38000, "---"),
)

# CEAI — Clapet d'admission d'air. Statut : validé ; origine FIRM V1/2025.
CLAPETS_CEAI: tuple[OrganeAir, ...] = (
    OrganeAir("Clapet CEAI", "DN80", 1800),
    OrganeAir("Clapet CEAI", "DN100", 2902),
    OrganeAir("Clapet CEAI", "DN150", 6300),
    OrganeAir("Clapet CEAI", "DN200", 11304),
    OrganeAir("Clapet CEAI", "DN250", 17600),
    OrganeAir("Clapet CEAI", "DN300", 26701),
    OrganeAir("Clapet CEAI", "DN350", 34600),
    OrganeAir("Clapet CEAI", "DN400", 47401),
    OrganeAir("Clapet CEAI", "DN500", 70600),
)

# SNH — Purgeur sonique. Référence de purge continue, pas d'admission grand débit.
PURGEURS_SONIQUES_SNH: tuple[OrganeAir, ...] = (
    OrganeAir("Purgeur sonique SNH", "DN200", 9),
    OrganeAir("Purgeur sonique SNH", "DN300", 14),
    OrganeAir("Purgeur sonique SNH", "DN400", 19),
    OrganeAir("Purgeur sonique SNH", "DN500", 27),
    OrganeAir("Purgeur sonique SNH", "DN700", 36),
    OrganeAir("Purgeur sonique SNH", "DN900", 79),
    OrganeAir("Purgeur sonique SNH", "DN1200", 108),
    OrganeAir("Purgeur sonique SNH", "DN1500", 144, "---"),
)


@dataclass(frozen=True)
class PropositionFamille:
    """Proposition dimensionnée pour une famille d'organes."""

    famille: str
    dn: str
    capacite_unitaire_m3s: float
    nombre: int
    debit_m3s: float
    origine: str

    @property
    def capacite_totale_m3s(self) -> float:
        return self.capacite_unitaire_m3s * self.nombre

    @property
    def marge_m3s(self) -> float:
        return self.capacite_totale_m3s - self.debit_m3s

    @property
    def couvert(self) -> bool:
        return self.debit_m3s > 0 and self.capacite_totale_m3s >= self.debit_m3s


def _proposition(
    famille: str,
    dn: str,
    capacite_unitaire_m3s: float,
    debit_m3s: float,
    origine: str,
) -> PropositionFamille:
    """Construit une proposition (capacité unitaire et nombre d'unités)."""
    nombre = (
        math.ceil(debit_m3s / capacite_unitaire_m3s)
        if capacite_unitaire_m3s > 0 and debit_m3s > 0
        else 0
    )
    return PropositionFamille(
        famille, dn, capacite_unitaire_m3s, nombre, debit_m3s, origine
    )


def proposer_organe(
    table: tuple[OrganeAir, ...], debit_m3s: float, famille: str
) -> PropositionFamille:
    """Premier organe couvrant le débit, sinon le plus grand avec cumul d'unités."""
    couvrant = next(
        (o for o in table if debit_m3s > 0 and o.capacite_m3s >= debit_m3s),
        None,
    )
    organe = couvrant or table[-1]
    return _proposition(
        famille, organe.dn, organe.capacite_m3s, debit_m3s, organe.origine
    )


def proposer_clapet_snh(debit_m3s: float) -> PropositionFamille:
    """Proposition issue de la table SNH validée par l'audit (note PDF p. 6)."""
    couvrant = next(
        (
            c for c in TABLE_SNH
            if debit_m3s > 0 and c.debit_admission_depression_3m_m3s is not None
            and c.debit_admission_depression_3m_m3s >= debit_m3s
        ),
        None,
    )
    if couvrant:
        return _proposition(
            "Clapet SNH",
            couvrant.dn,
            couvrant.debit_admission_depression_3m_m3s,
            debit_m3s,
            "Note PDF page 6 (audit)",
        )
    dernier = TABLE_SNH[-1]
    return _proposition(
        "Clapet SNH",
        dernier.dn,
        dernier.debit_admission_depression_3m_m3s or 0.0,
        debit_m3s,
        "Note PDF page 6 (audit)",
    )


def proposer_pam_dn200(debit_m3s: float) -> PropositionFamille:
    """Configuration audit : ventouse PAM DN200 fixée."""
    pam = next(c for c in TABLE_PAM if c.dn == "DN200")
    return _proposition(
        "Ventouse PAM",
        pam.dn,
        pam.debit_admission_depression_3m_m3s or 0.0,
        debit_m3s,
        "Note PDF page 6 (audit) - valeur tableau",
    )


@dataclass(frozen=True)
class ResultatConfiguration:
    """Résultat complet d'une configuration de dimensionnement d'air."""

    nom: str
    debit_m3s: float
    ventouse: PropositionFamille
    clapet: PropositionFamille

    @property
    def couvert(self) -> bool:
        return self.ventouse.couvert and self.clapet.couvert

    @property
    def resume(self) -> str:
        v, c = self.ventouse, self.clapet
        return (
            f"{self.nom} — Qair à couvrir : {self.debit_m3s:.3f} m³/s. "
            f"{v.famille} {v.dn} ×{v.nombre} = {v.capacite_totale_m3s:.3f} m³/s "
            f"(marge {v.marge_m3s:+.3f}) ; "
            f"{c.famille} {c.dn} ×{c.nombre} = {c.capacite_totale_m3s:.3f} m³/s "
            f"(marge {c.marge_m3s:+.3f}). "
            f"Couverture {'OUI' if self.couvert else 'NON'}."
        )


def analyser_configurations(debit_m3s: float) -> dict[str, ResultatConfiguration]:
    """Compare les configurations audit et CEAI pour un débit d'air donné."""
    return {
        CONFIG_AUDIT: ResultatConfiguration(
            CONFIG_AUDIT,
            debit_m3s,
            proposer_pam_dn200(debit_m3s),
            proposer_clapet_snh(debit_m3s),
        ),
        CONFIG_CEAI: ResultatConfiguration(
            CONFIG_CEAI,
            debit_m3s,
            proposer_organe(VENTOUSES_TRIFON_CEAI, debit_m3s, "Ventouse Trifon CEAI"),
            proposer_organe(CLAPETS_CEAI, debit_m3s, "Clapet CEAI"),
        ),
    }


def resume_configuration(resultat: ResultatConfiguration) -> str:
    """Résumé lisible d'une configuration."""
    return resultat.resume


def plus_grand_purgeur_sonique() -> OrganeAir:
    """Purgeur sonique SNH de plus grande capacité (référence de purge)."""
    return PURGEURS_SONIQUES_SNH[-1]
