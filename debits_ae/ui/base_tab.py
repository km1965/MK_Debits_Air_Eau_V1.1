"""Socle commun des onglets : projet partagé, notifications et alertes.

Chaque onglet hérite de :class:`OngletProjet` afin de :
* partager le même objet :class:`~debits_ae.models.Projet` (source de vérité) ;
* signaler à la fenêtre principale qu'un calcul a été effectué ;
* afficher les messages d'alerte de façon homogène.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from debits_ae.models import Projet


class OngletProjet(ctk.CTkFrame):
    """Base des 6 onglets de l'application."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        resultats_partages: dict | None = None,
        projet: Projet | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.resultats_partages = resultats_partages if resultats_partages is not None else {}
        self.projet = projet if projet is not None else Projet()
        self._on_change = on_change
        self._construire_interface()

    def _construire_interface(self) -> None:
        """À surcharger : construit les widgets de l'onglet."""

    # ------------------------------------------------------------------
    def notifier(self) -> None:
        """Prévient la fenêtre principale (rafraîchissement du tableau de bord)."""
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception:
                # Le tableau de bord ne doit jamais faire échouer un calcul.
                pass

    # ------------------------------------------------------------------
    def _afficher_alerte(self, message: str, niveau: str = "info") -> None:
        """Affiche un message coloré dans le cadre d'alerte de l'onglet."""
        couleurs = {
            "info": ("#E3F2FD", "#1565C0"),
            "attention": ("#FFF3E0", "#EF6C00"),
            "alerte": ("#FFEBEE", "#C62828"),
        }
        fg, text = couleurs.get(niveau, couleurs["info"])
        self.frame_alerte.configure(fg_color=fg)
        self.frame_alerte.lbl.configure(text=message, text_color=text)
        self.frame_alerte.pack(side="top", fill="x", padx=15, pady=(0, 10))

    def _masquer_alerte(self) -> None:
        if hasattr(self, "frame_alerte"):
            self.frame_alerte.pack_forget()

    # ------------------------------------------------------------------
    # À surcharger dans les onglets
    # ------------------------------------------------------------------
    def synchroniser_depuis_projet(self) -> None:
        """Recopie les données partagées du projet dans les champs de l'onglet."""

    def restaurer(self) -> None:
        """Recharge les champs puis réaffiche/recalcule les résultats si possible."""
        self.synchroniser_depuis_projet()
