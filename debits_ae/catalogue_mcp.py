"""Catalogue constructeur MCP - ventouse double orifice 3 fonctions PN 10/16.

Source : Catalogue_MCP_VENTOUSE AUTOMATIQUE DOUBLE ORIFICE 3 FONCTIONS
Type_MCP_validées.pdf (racine du projet) + relevé des courbes transmis.

Adapte les capacites du catalogue aux sorties de calcul Qair de l'application.
"""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_PDF = (
    "Catalogue_MCP_VENTOUSE AUTOMATIQUE DOUBLE ORIFICE 3 FONCTIONS "
    "Type_MCP_validées.pdf"
)

FONCTIONS_MCP = (
    "Évacuation d'air à grand débit pendant le remplissage du réseau",
    "Admission d'air à grand débit pendant la vidange du réseau",
    "Purge d'air accumulé aux points hauts en exploitation",
)

CARACTERISTIQUES_MCP = {
    "gamme": "D40-300",
    "pression": "PN 10/16 bars",
    "revêtement": "Poudre Epoxy 250 microns",
    "pression_min_étanchéité_bar": 0.1,
    "domaine_conduite_mm": "60 - 500",
}

# Domaine d'application : conduites DN60 a DN500 (confirmé utilisateur).
DN_CONDUITE_MIN_MCP_MM = 60
DN_CONDUITE_MAX_MCP_MM = 500

@dataclass(frozen=True)
class VentouseMCP:
    """Une ligne du catalogue MCP, avec capacités aérauliques."""

    dn: str
    serie: str
    L_mm: float
    H_mm: float
    M_mm: float
    D1_mm: float
    D2_mm: float
    bride_mm: float
    poids_kg: float
    orifice_mm: float
    q_admission_m3s: float
    q_evacuation_m3s: float
    q_critique_m3s: float
    origine_capacite: str


VENTOUSES_MCP: tuple[VentouseMCP, ...] = (
    VentouseMCP("DN40", "60-250", 228, 280, 166, 84, 110, 165, 17, 50,
                0.242, 0.301, 0.664, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN50", "60-250", 228, 280, 166, 99, 125, 165, 17, 50,
                0.242, 0.301, 0.664, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN60/65", "60-250", 228, 280, 166, 118, 145, 185, 20.5, 50,
                0.242, 0.301, 0.664, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN80", "250-400", 228, 280, 166, 132, 160, 200, 21, 80,
                0.62, 0.77, 1.70, "Courbe constructeur (0,3 bar / 0,92 bar)"),
    VentouseMCP("DN100", "250-400", 228, 280, 166, 156, 180, 220, 31, 100,
                1.20, 1.55, 2.66, "Courbe constructeur (0,3 bar / 0,92 bar)"),
    VentouseMCP("DN125", "400-600", 253, 420, 265, 184, 210, 250, 32, 100,
                1.20, 1.55, 2.66, "Repris DN100 (courbe 100/150 mm)"),
    VentouseMCP("DN150", "400-600", 253, 420, 265, 211, 240, 285, 35, 150,
                2.70, 3.49, 5.98, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN200", "600-900", 253, 420, 265, 266, 295, 340, 50, 150,
                2.70, 3.49, 5.98, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN250", "600-900", 253, 420, 265, 319, 350, 400, 60, 150,
                2.70, 3.49, 5.98, "Extrapolé selon surface d'orifice"),
    VentouseMCP("DN300", "600-900", 253, 420, 265, 370, 400, 455, 75, 150,
                2.70, 3.49, 5.98, "Extrapolé selon surface d'orifice"),
)

def _dn_numerique(dn: str) -> int:
    """Convertit un DN catalogue en valeur numérique (DN60/65 -> 60)."""
    premier = dn.split("/")[0]
    chiffres = "".join(c for c in premier if c.isdigit())
    return int(chiffres) if chiffres else 0


# La colonne « Série » du catalogue (60-250, 250-400, 400-600, 600-900) est une
# référence fabricant. Le domaine d'application retenu est celui confirmé par
# l'utilisateur : conduites DN60 à DN500. Règle : DN ventouse <= DN conduite.
def dns_mcp_pour_conduite(dn_conduit_mm: float) -> tuple[str, ...]:
    """DN MCP installables sur une conduite du DN donné (60-500 mm)."""
    if not DN_CONDUITE_MIN_MCP_MM <= dn_conduit_mm <= DN_CONDUITE_MAX_MCP_MM:
        return ()
    return tuple(
        v.dn for v in VENTOUSES_MCP
        if _dn_numerique(v.dn) <= dn_conduit_mm
    )


def capacite_mcp_m3s(dn: str, mode: str = "admission") -> float:
    """Capacité aéraulique d'une ventouse MCP (m3/s)."""
    for ventouse in VENTOUSES_MCP:
        if ventouse.dn == dn:
            if mode == "admission":
                return ventouse.q_admission_m3s
            if mode == "evacuation":
                return ventouse.q_evacuation_m3s
            if mode == "critique":
                return ventouse.q_critique_m3s
    return 0.0


def choix_ventouse_mcp(debit_m3s: float, mode: str = "admission") -> VentouseMCP | None:
    """Première ventouse MCP dont la capacité couvre le débit demandé."""
    for ventouse in VENTOUSES_MCP:
        if capacite_mcp_m3s(ventouse.dn, mode) >= debit_m3s > 0:
            return ventouse
    return None


def nombre_ventouses_mcp(debit_m3s: float, dn: str, mode: str = "admission") -> int:
    """Nombre de ventouses MCP DN données necessaires pour couvrir le débit."""
    import math

    capacite = capacite_mcp_m3s(dn, mode)
    if capacite <= 0 or debit_m3s <= 0:
        return 0
    return math.ceil(debit_m3s / capacite)


@dataclass
class ResultatMCP:
    """Résultat de l'adaptation du catalogue MCP à un débit calculé."""

    debit_m3s: float
    mode: str
    dn_conduit_mm: float | None
    dns_series: tuple[str, ...]
    dn_propose: str | None
    capacite_unitaire_m3s: float
    nombre: int
    couvert: bool
    avertissement: str


def analyser_mcp(
    debit_m3s: float,
    dn_conduit_mm: float | None = None,
    mode: str = "admission",
) -> ResultatMCP:
    """Propose une ventouse MCP pour un débit d'air calculé par l'application."""
    dns = dns_mcp_pour_conduite(dn_conduit_mm) if dn_conduit_mm else ()
    choix = choix_ventouse_mcp(debit_m3s, mode)
    dn = choix.dn if choix else (dns[-1] if dns else VENTOUSES_MCP[-1].dn)
    capacite = capacite_mcp_m3s(dn, mode) if dn else 0.0
    nombre = nombre_ventouses_mcp(debit_m3s, dn, mode) if dn else 0

    avertissements: list[str] = []
    if dn_conduit_mm and not dns:
        avertissements.append(
            f"DN conduite {dn_conduit_mm:g} mm hors domaine d'application "
            "du catalogue MCP (conduites DN60-500 mm)."
        )
    if not choix:
        avertissements.append(
            "Aucune ventouse MCP ne couvre ce débit en une seule unité ; "
            "le nombre indiqué est un cumul d'unités."
        )
    if debit_m3s <= 0:
        avertissements.append("Débit d'air nul ou négatif.")

    return ResultatMCP(
        debit_m3s=debit_m3s,
        mode=mode,
        dn_conduit_mm=dn_conduit_mm,
        dns_series=dns,
        dn_propose=dn,
        capacite_unitaire_m3s=capacite,
        nombre=nombre,
        couvert=capacite * nombre >= debit_m3s > 0,
        avertissement=" ".join(avertissements),
    )


def resume_mcp(resultat: ResultatMCP) -> str:
    """Résumé lisible en français d'une proposition MCP."""
    if not resultat.dn_propose:
        return "Aucune proposition MCP possible. " + resultat.avertissement
    txt = (
        f"Débit d'air à couvrir : {resultat.debit_m3s:.3f} m³/s "
        f"({resultat.mode}). Ventouse MCP {resultat.dn_propose} : "
        f"{resultat.capacite_unitaire_m3s:.3f} m³/s par unité, "
        f"nombre nécessaire : {resultat.nombre}."
    )
    if resultat.dns_series:
        txt += " DN MCP installables : " + ", ".join(resultat.dns_series) + "."
    if resultat.avertissement:
        txt += " " + resultat.avertissement
    return txt
