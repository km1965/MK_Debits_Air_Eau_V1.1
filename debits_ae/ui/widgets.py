"""Widgets réutilisables pour l'interface MK_Debits_Air_Eau.

Fournit des champs de saisie numériques validés, des labels de résultat avec
code couleur (vert OK / rouge alerte) et des boutons d'action stylisés.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk


class LabeledEntry(ctk.CTkFrame):
    """Un label + un champ de saisie numérique avec validation."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        label: str,
        default: str = "0",
        unit: str = "",
        width: int = 140,
        tooltip: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.label_text = label
        self.unit = unit
        self._on_change: Callable[[], None] | None = None

        self.lbl = ctk.CTkLabel(self, text=label, width=120, anchor="w")
        self.lbl.pack(side="left", padx=(0, 8))

        self.var = tk.StringVar(value=str(default))
        self.ent = ctk.CTkEntry(
            self,
            textvariable=self.var,
            width=width,
            justify="right",
        )
        self.ent.pack(side="left", padx=(0, 6))
        self.ent.bind("<KeyRelease>", self._on_key)

        if unit:
            self.lbl_unit = ctk.CTkLabel(self, text=unit, width=34, anchor="w")
            self.lbl_unit.pack(side="left")

        if tooltip:
            self._setup_tooltip(tooltip)

    def _on_key(self, _event: tk.Event) -> None:
        if self._on_change:
            self._on_change()

    def set_on_change(self, callback: Callable[[], None]) -> None:
        self._on_change = callback

    def get_value(self) -> float:
        try:
            return float(self.var.get().replace(",", "."))
        except ValueError:
            return 0.0

    def set_value(self, val: float) -> None:
        self.var.set(f"{val:g}")

    def _setup_tooltip(self, text: str) -> None:
        def _enter(_event: tk.Event) -> None:
            self._tip = tk.Toplevel(self)
            self._tip.wm_overrideredirect(True)
            self._tip.wm_attributes("-topmost", True)
            x = self.winfo_rootx() + 20
            y = self.winfo_rooty() + 20
            self._tip.wm_geometry(f"+{x}+{y}")
            lbl = ctk.CTkLabel(
                self._tip,
                text=text,
                fg_color=("#2b2b2b", "#1a1a1a"),
                text_color="white",
                corner_radius=4,
                padx=6,
                pady=3,
            )
            lbl.pack()

        def _leave(_event: tk.Event) -> None:
            if hasattr(self, "_tip"):
                self._tip.destroy()
                del self._tip

        self.ent.bind("<Enter>", _enter)
        self.ent.bind("<Leave>", _leave)


class ResultLabel(ctk.CTkFrame):
    """Un label de résultat avec valeur, unité et statut coloré."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        label: str,
        unit: str = "",
        width: int = 200,
    ) -> None:
        super().__init__(parent)
        self.lbl_name = ctk.CTkLabel(self, text=label, width=150, anchor="w")
        self.lbl_name.pack(side="left", padx=(0, 8))

        self.lbl_val = ctk.CTkLabel(self, text="—", width=90, anchor="e")
        self.lbl_val.pack(side="left", padx=(0, 6))

        if unit:
            self.lbl_unit = ctk.CTkLabel(self, text=unit, width=40, anchor="w")
            self.lbl_unit.pack(side="left")

        self.lbl_stat = ctk.CTkLabel(self, text="", width=70, anchor="center")
        self.lbl_stat.pack(side="left", padx=(6, 0))

    def set(self, value: float | str, fmt: str = "{:.4f}", statut: str | None = None) -> None:
        if isinstance(value, (int, float)):
            self.lbl_val.configure(text=fmt.format(value))
        else:
            self.lbl_val.configure(text=str(value))

        if statut:
            self.lbl_stat.configure(text=statut)
            couleur = self._couleur_statut(statut)
            self.lbl_stat.configure(text_color=couleur)
        else:
            self.lbl_stat.configure(text="")

    def _couleur_statut(self, statut: str) -> str:
        statut_up = statut.upper()
        if "SUSPECT" in statut_up or "ILLISIBLE" in statut_up:
            return "#C62828"  # rouge
        if "EMPIRIQUE" in statut_up or "À VÉRIFIER" in statut_up:
            return "#EF6C00"  # orange
        if "NON CONFORME" in statut_up:
            return "#C62828"
        if "CONFORME" in statut_up or statut_up == "OK":
            return "#2E7D32"  # vert
        if "COHÉRENT" in statut_up:
            return "#1565C0"  # bleu
        return "#757575"  # gris

    def set_statut(self, statut: str) -> None:
        self.lbl_stat.configure(text=statut)
        self.lbl_stat.configure(text_color=self._couleur_statut(statut))

    def reset(self) -> None:
        """Remet le résultat à l'état « non calculé »."""
        self.lbl_val.configure(text="—")
        self.lbl_stat.configure(text="")


class CalcButton(ctk.CTkButton):
    """Bouton de calcul avec icône et couleur principale."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        text: str = "Calculer",
        command: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            text=text,
            command=command,
            fg_color="#1F3B5C",
            hover_color="#154a7a",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
        )


class ExportButton(ctk.CTkButton):
    """Bouton d'export de rapport."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        text: str = "Exporter rapport",
        command: Callable[[], None] | None = None,
        fmt: str = "docx",
    ) -> None:
        couleur = "#2E7D32" if fmt == "docx" else "#1565C0"
        super().__init__(
            parent,
            text=text,
            command=command,
            fg_color=couleur,
            hover_color="#1b5e20" if fmt == "docx" else "#0d47a1",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
            width=150,
        )


class AlerteFrame(ctk.CTkFrame):
    """Cadre d'alerte affichant un message de vérification de formule."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        message: str,
        niveau: str = "info",  # info, attention, alerte
    ) -> None:
        couleurs = {
            "info": ("#E3F2FD", "#1565C0"),
            "attention": ("#FFF3E0", "#EF6C00"),
            "alerte": ("#FFEBEE", "#C62828"),
        }
        fg, text = couleurs.get(niveau, couleurs["info"])
        super().__init__(parent, fg_color=fg)
        self.lbl = ctk.CTkLabel(
            self,
            text=message,
            text_color=text,
            wraplength=700,
            justify="left",
            font=ctk.CTkFont(size=11),
        )
        self.lbl.pack(padx=10, pady=6, fill="x")
