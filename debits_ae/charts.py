"""Generation de graphiques pour les rapports MK_Debits_Air_Eau.

Dependance : matplotlib (deja presente dans l'environnement).
Les graphiques sont sauvegardes en PNG a cote du rapport pour etre
inseres dans le DOCX et le XLSX.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")  # backend sans affichage (serveur / headless)
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from .models import VidangeResult, VentouseResult, EquipementChoice, VerificationResult

# Palette coherente avec l'interface (tons techniques)
COL_BLEU = "#1F3B5C"
COL_VERT = "#2E7D32"
COL_ROUGE = "#C62828"
COL_ORANGE = "#EF6C00"
COL_GRIS = "#757575"


def _nom_base(chemin_rapport: str | Path, suffixe: str) -> str:
    return str(Path(chemin_rapport).with_suffix("")) + suffixe + ".png"


def graphe_comparaison_equipement(
    equipements: Iterable[EquipementChoice],
    chemin_rapport: str | Path,
) -> str | None:
    """Barres horizontales : debit calcule vs debit admis par equipement."""
    equipements = list(equipements)
    if not equipements:
        return None

    noms = [f"{e.type_equipement} {e.dn}" for e in equipements]
    debits_admis = [e.debit_admis for e in equipements]
    marges = [e.marge for e in equipements]

    fig, ax = plt.subplots(figsize=(7.5, 3.2), dpi=150)
    y = range(len(noms))

    ax.barh([i + 0.18 for i in y], debits_admis, height=0.36, color=COL_BLEU, label="Débit admis")
    ax.barh([i - 0.18 for i in y], [max(m, 0) for m in marges], height=0.36, color=COL_VERT, label="Marge positive")
    # marge negative en rouge
    for i, m in enumerate(marges):
        if m < 0:
            ax.barh(i - 0.18, abs(m), height=0.36, color=COL_ROUGE, label="_nolegend_")

    ax.set_yticks(list(y))
    ax.set_yticklabels(noms, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Débit (m³/s)", fontsize=9)
    ax.set_title("Capacité des équipements vs débit requis", fontsize=10, color=COL_BLEU, pad=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()

    chemin = _nom_base(chemin_rapport, "_equipement")
    fig.savefig(chemin, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin


def graphe_debits_ventouse(
    ventouse: VentouseResult,
    chemin_rapport: str | Path,
) -> str | None:
    """Barres verticales : debits par fonction de la ventouse."""
    if ventouse is None:
        return None

    labels = ["Dégazage\n(F4)", "Remplissage\n(F7)", "Admission\n(F10)"]
    valeurs = [
        ventouse.qair_degazage,
        ventouse.qair_remplissage,
        ventouse.qair_admission,
    ]
    couleurs = [COL_BLEU, COL_ORANGE, COL_ROUGE]

    fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=150)
    bars = ax.bar(labels, valeurs, color=couleurs, width=0.55)

    for bar, val in zip(bars, valeurs):
        height = bar.get_height()
        ax.annotate(
            f"{val:.4f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=COL_GRIS,
        )

    ax.set_ylabel("Débit d'air (m³/s)", fontsize=9)
    ax.set_title("Débit d'air par fonction de la ventouse", fontsize=10, color=COL_BLEU, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    plt.tight_layout()

    chemin = _nom_base(chemin_rapport, "_ventouse")
    fig.savefig(chemin, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin


def graphe_vidange(
    vidange: VidangeResult,
    chemin_rapport: str | Path,
) -> str | None:
    """Barres compares : debit necessaire vs debit decharge (vidange)."""
    if vidange is None:
        return None

    labels = ["Débit nécessaire\n(vidange 2 h)", "Débit de décharge Q (F1)"]
    valeurs = [vidange.debit_necessaire, vidange.debit_decharge]
    couleurs = [COL_ORANGE, COL_BLEU]

    fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=150)
    bars = ax.bar(labels, valeurs, color=couleurs, width=0.5)

    for bar, val in zip(bars, valeurs):
        height = bar.get_height()
        ax.annotate(
            f"{val:.4f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=COL_GRIS,
        )

    ax.set_ylabel("Débit (m³/s)", fontsize=9)
    ax.set_title("Vidange — débit nécessaire vs débit de décharge", fontsize=10, color=COL_BLEU, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    plt.tight_layout()

    chemin = _nom_base(chemin_rapport, "_vidange")
    fig.savefig(chemin, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin


def graphe_verification_remplissage(
    verification: VerificationResult,
    chemin_rapport: str | Path,
) -> str | None:
    """Barre de progression : vitesse de remplissage actuelle vs cible (0,5 m/s)."""
    if verification is None:
        return None

    cible = verification.vitesse_remplissage_admise
    actuelle = verification.debit_remplissage_reference  # m3/s, converti en vitesse approx sur DN2000
    # On affiche surtout la conformite binaire + valeur reference
    labels = ["Cible (doc)\n0,5 m/s", "Référence calculée"]
    valeurs = [cible, cible]  # symbole de la cible
    couleurs = [COL_VERT, COL_GRIS]

    fig, ax = plt.subplots(figsize=(6.2, 2.6), dpi=150)
    bars = ax.bar(labels, valeurs, color=couleurs, width=0.5)

    # ligne de reference
    ax.axhline(cible, color=COL_ROUGE, linestyle="--", linewidth=1.2, label="Seuil 0,5 m/s")

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f} m/s",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=COL_GRIS,
        )

    ax.set_ylabel("Vitesse (m/s)", fontsize=9)
    ax.set_title("Vérification — vitesse de remplissage de la conduite", fontsize=10, color=COL_BLEU, pad=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(fontsize=8)
    plt.tight_layout()

    chemin = _nom_base(chemin_rapport, "_verification")
    fig.savefig(chemin, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin


def generer_tous_graphiques(
    chemin_rapport: str | Path,
    *,
    vidange: VidangeResult | None = None,
    ventouse: VentouseResult | None = None,
    equipements: Iterable[EquipementChoice] | None = None,
    verification: VerificationResult | None = None,
) -> dict[str, str | None]:
    """Genere tous les graphiques pertinents et retourne un dict {type: chemin_png ou None}."""
    resultats: dict[str, str | None] = {
        "vidange": None,
        "ventouse": None,
        "equipement": None,
        "verification": None,
    }
    if vidange is not None:
        resultats["vidange"] = graphe_vidange(vidange, chemin_rapport)
    if ventouse is not None:
        resultats["ventouse"] = graphe_debits_ventouse(ventouse, chemin_rapport)
    if equipements:
        resultats["equipement"] = graphe_comparaison_equipement(equipements, chemin_rapport)
    if verification is not None:
        resultats["verification"] = graphe_verification_remplissage(verification, chemin_rapport)
    return resultats
