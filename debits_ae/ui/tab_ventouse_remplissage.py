"""Onglet 3 — Ventouse : 2ème fonction — Remplissage de la conduite.

Calcule :
- Débit eau de remplissage Qeau = V × S0 (F7)
- Débit air évacuation Qair = Qeau (conservation du volume)
- Diamètre orifice d2 (F7 : d · √(V / 499) si P1 = P2)

Le résultat est fusionné dans `Projet.ventouse` sans écraser les autres
fonctions de la ventouse.
"""

from __future__ import annotations

import math

import customtkinter as ctk

from debits_ae.models import VentouseResult
from debits_ae import q_remplissage, diametre_orifice_remplissage
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, ResultLabel, CalcButton, ExportButton, AlerteFrame


class TabVentouseRemplissage(OngletProjet):
    """Onglet Ventouse — Remplissage (2ème fonction)."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        # --- Saisie ---
        frame_saisie = ctk.CTkFrame(self)
        frame_saisie.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame_saisie,
            text="Données d'entrée — 2ème fonction : Remplissage de la conduite",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_saisie)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        self.ent_diametre = LabeledEntry(
            grille, "Diamètre conduit D", default=f"{d.diam_conduit:g}", unit="m",
            tooltip="Diamètre intérieur de la conduite (m).",
        )
        self.ent_diametre.pack(side="left", padx=6, pady=4)

        self.ent_vitesse = LabeledEntry(
            grille, "Vitesse de remplissage V", default=f"{d.vitesse_remplissage:g}", unit="m/s",
            tooltip="Vitesse de remplissage (1 m/s doc ; 0,5 m/s en vérification page 6).",
        )
        self.ent_vitesse.pack(side="left", padx=6, pady=4)

        CalcButton(frame_saisie, text="Calculer remplissage", command=self._calculer).pack(
            anchor="e", padx=10, pady=(0, 10)
        )

        # --- Résultats ---
        frame_res = ctk.CTkFrame(self)
        frame_res.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_res, text="Résultats du calcul", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille_res = ctk.CTkFrame(frame_res)
        grille_res.pack(fill="x", padx=10, pady=(0, 10))

        self.res_section = ResultLabel(grille_res, "Section de conduite S0", unit="m²")
        self.res_section.pack(side="left", padx=6, pady=4)
        self.res_qeau = ResultLabel(grille_res, "Débit eau remplissage Qeau (F7)", unit="m³/s")
        self.res_qeau.pack(side="left", padx=6, pady=4)
        self.res_qair = ResultLabel(grille_res, "Débit air évacuation Qair (F7)", unit="m³/s")
        self.res_qair.pack(side="left", padx=6, pady=4)
        self.res_d2 = ResultLabel(grille_res, "Ø orifice évacuation d2 (F7)", unit="mm")
        self.res_d2.pack(side="left", padx=6, pady=4)

        # --- Alerte ---
        self.frame_alerte = AlerteFrame(self, message="", niveau="info")
        self.frame_alerte.pack(side="top", fill="x", padx=15, pady=(0, 10))
        self.frame_alerte.pack_forget()

        # --- Export ---
        frame_export = ctk.CTkFrame(self)
        frame_export.pack(side="top", fill="x", padx=15, pady=(0, 15))
        ExportButton(
            frame_export, text="Exporter rapport DOCX", command=self._exporter_docx, fmt="docx"
        ).pack(side="left", padx=10, pady=6)
        ExportButton(
            frame_export, text="Exporter rapport XLSX", command=self._exporter_xlsx, fmt="xlsx"
        ).pack(side="left", padx=10, pady=6)

    # ------------------------------------------------------------------
    def _calculer(self) -> None:
        diam = self.ent_diametre.get_value()
        vitesse = self.ent_vitesse.get_value()

        if diam <= 0 or vitesse <= 0:
            self._afficher_alerte("Veuillez saisir des valeurs positives.", niveau="alerte")
            return

        s0 = math.pi / 4.0 * diam**2
        q_eau = q_remplissage(vitesse, s0)
        q_air = q_eau  # conservation du volume lors du remplissage
        d2, _ = diametre_orifice_remplissage(diam, vitesse)

        d = self.projet.donnees
        d.diam_conduit = diam
        d.vitesse_remplissage = vitesse

        v = self.projet.ventouse or VentouseResult()
        v.q_eau_remplissage = q_eau
        v.qair_remplissage = q_air
        v.diametre_orifice_remplissage = d2
        self.projet.ventouse = v
        self.resultats_partages["ventouse"] = v

        self._afficher_resultats(v)
        self.notifier()

    def _afficher_resultats(self, v: VentouseResult) -> None:
        s0 = math.pi / 4.0 * self.projet.donnees.diam_conduit**2
        self.res_section.set(s0, "{:.6f}")
        self.res_qeau.set(v.q_eau_remplissage, "{:.4f}", "OK")
        self.res_qair.set(v.qair_remplissage, "{:.4f}", "OK")
        self.res_d2.set(v.diametre_orifice_remplissage * 1000, "{:.1f}", "OK")

        msg = (
            f"Section conduite S0 = {s0:.4f} m². Débit eau de remplissage = "
            f"{v.q_eau_remplissage:.4f} m³/s. Débit air évacuation = "
            f"{v.qair_remplissage:.4f} m³/s. Ø orifice évacuation d2 = "
            f"{v.diametre_orifice_remplissage*1000:.1f} mm."
        )
        self._afficher_alerte(msg, niveau="info")

    def synchroniser_depuis_projet(self) -> None:
        d = self.projet.donnees
        self.ent_diametre.set_value(d.diam_conduit)
        self.ent_vitesse.set_value(d.vitesse_remplissage)

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        v = self.projet.ventouse
        if v is not None and v.qair_remplissage > 0:
            self._afficher_resultats(v)
        else:
            for res in (self.res_section, self.res_qeau, self.res_qair, self.res_d2):
                res.reset()

    # ------------------------------------------------------------------
    def _exporter_docx(self) -> None:
        from debits_ae import generer_rapport_docx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_remplissage.docx",
        )
        if chemin:
            generer_rapport_docx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Remplissage",
                ventouse=self.projet.ventouse,
                inputs_resume=self.projet.resume_texte(),
            )

    def _exporter_xlsx(self) -> None:
        from debits_ae import generer_rapport_xlsx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_remplissage.xlsx",
        )
        if chemin:
            generer_rapport_xlsx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Remplissage",
                ventouse=self.projet.ventouse,
                inputs_resume=self.projet.resume_texte(),
            )
