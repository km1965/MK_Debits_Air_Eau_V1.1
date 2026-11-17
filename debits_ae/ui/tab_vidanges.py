"""Onglet 1 — Vidanges (points bas).

Calcule :
- Débit de décharge Q (F1 : Torricelli)
- Diamètre de vidange d (F2 corrigé : 6,69 × D × (L/√h)^0,5 pour 2 h)
- Volume du tronçon et débit nécessaire pour vidange en temps cible

Les données de conduite (D, L, h, K, temps) sont partagées avec les autres
onglets via :class:`~debits_ae.models.Projet`.
"""

from __future__ import annotations

import customtkinter as ctk

from debits_ae.models import VidangeInputs, VidangeResult
from debits_ae import calcul_vidange
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, ResultLabel, CalcButton, ExportButton, AlerteFrame


class TabVidanges(OngletProjet):
    """Onglet Vidanges — Points bas."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        # --- Saisie ---
        frame_saisie = ctk.CTkFrame(self)
        frame_saisie.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame_saisie,
            text="Données d'entrée — Ouvrage de vidange (point bas)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_saisie)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        self.ent_longueur = LabeledEntry(
            grille, "Longueur de tronçon L", default=f"{d.longueur_troncon:g}", unit="m",
            tooltip="Longueur du tronçon de conduite contrôlé par la vidange (m).",
        )
        self.ent_longueur.pack(side="left", padx=6, pady=4)

        self.ent_diametre = LabeledEntry(
            grille, "Diamètre conduit D", default=f"{d.diam_conduit:g}", unit="m",
            tooltip="Diamètre intérieur de la conduite (m).",
        )
        self.ent_diametre.pack(side="left", padx=6, pady=4)

        self.ent_hauteur = LabeledEntry(
            grille, "Hauteur moyenne d'eau h", default=f"{d.hauteur_eau:g}", unit="m",
            tooltip="Hauteur moyenne d'eau dans le tronçon contrôlé par la vidange (m).",
        )
        self.ent_hauteur.pack(side="left", padx=6, pady=4)

        self.ent_coeff = LabeledEntry(
            grille, "Coeff. de débit K", default=f"{d.coeff_debit_vidange:g}", unit="—",
            tooltip="Coefficient de débit pour faibles charges (0,7 par défaut).",
        )
        self.ent_coeff.pack(side="left", padx=6, pady=4)

        self.ent_temps = LabeledEntry(
            grille, "Temps de vidange cible", default=f"{d.temps_vidange_h:g}", unit="h",
            tooltip="Temps de vidange visé pour le tronçon (heures).",
        )
        self.ent_temps.pack(side="left", padx=6, pady=4)

        CalcButton(frame_saisie, text="Calculer vidange", command=self._calculer).pack(
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

        self.res_section = ResultLabel(grille_res, "Section de conduite (π/4·D²)", unit="m²")
        self.res_section.pack(side="left", padx=6, pady=4)
        self.res_debit = ResultLabel(grille_res, "Débit de décharge Q (F1)", unit="m³/s")
        self.res_debit.pack(side="left", padx=6, pady=4)
        self.res_diametre = ResultLabel(grille_res, "Diamètre de vidange d (F2)", unit="mm")
        self.res_diametre.pack(side="left", padx=6, pady=4)
        self.res_section_vid = ResultLabel(grille_res, "Section de vidange associée", unit="m²")
        self.res_section_vid.pack(side="left", padx=6, pady=4)
        self.res_volume = ResultLabel(grille_res, "Volume du tronçon", unit="m³")
        self.res_volume.pack(side="left", padx=6, pady=4)
        self.res_debit_nec = ResultLabel(grille_res, "Débit nécessaire (vidange cible)", unit="m³/s")
        self.res_debit_nec.pack(side="left", padx=6, pady=4)

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
    def _lire_inputs(self) -> VidangeInputs:
        return VidangeInputs(
            longueur_troncon=self.ent_longueur.get_value(),
            diam_conduit=self.ent_diametre.get_value(),
            hauteur_eau=self.ent_hauteur.get_value(),
            coeff_debit=self.ent_coeff.get_value(),
            temps_vidange_cible=self.ent_temps.get_value() * 3600.0,
        )

    def _calculer(self) -> None:
        inputs = self._lire_inputs()
        if inputs.diam_conduit <= 0 or inputs.longueur_troncon <= 0 or inputs.hauteur_eau <= 0:
            self._afficher_alerte(
                "Veuillez saisir des valeurs positives pour L, D et h.", niveau="alerte"
            )
            return

        res = calcul_vidange(inputs)

        # Mise à jour du projet partagé
        d = self.projet.donnees
        d.longueur_troncon = inputs.longueur_troncon
        d.diam_conduit = inputs.diam_conduit
        d.hauteur_eau = inputs.hauteur_eau
        d.coeff_debit_vidange = inputs.coeff_debit
        d.temps_vidange_h = inputs.temps_vidange_cible / 3600.0
        self.projet.vidange = res
        self.resultats_partages["vidange"] = res
        self.resultats_partages["inputs_vidange"] = inputs

        self._afficher_resultats(res, inputs)
        self.notifier()

    def _afficher_resultats(self, res: VidangeResult, inputs: VidangeInputs | None = None) -> None:
        self.res_section.set(res.section, "{:.6f}")
        self.res_debit.set(res.debit_decharge, "{:.4f}", "OK")
        self.res_diametre.set(
            res.diametre_vidange, "{:.2f}", "SUSPECT" if res.formule_f2_alerte else "OK"
        )
        self.res_section_vid.set(res.section_vidange, "{:.6f}")
        self.res_volume.set(res.volume_troncon, "{:.2f}")
        self.res_debit_nec.set(res.debit_necessaire, "{:.4f}")

        if inputs is not None:
            msg = (
                f"Vidange du tronçon de {inputs.longueur_troncon:.0f} m en "
                f"{inputs.temps_vidange_cible/3600:.1f} h : diamètre de vidange "
                f"nécessaire ≈ {res.diametre_vidange:.0f} mm."
            )
        else:
            msg = f"Diamètre de vidange nécessaire ≈ {res.diametre_vidange:.0f} mm."
        self._afficher_alerte(msg, niveau="info")

    def synchroniser_depuis_projet(self) -> None:
        d = self.projet.donnees
        self.ent_longueur.set_value(d.longueur_troncon)
        self.ent_diametre.set_value(d.diam_conduit)
        self.ent_hauteur.set_value(d.hauteur_eau)
        self.ent_coeff.set_value(d.coeff_debit_vidange)
        self.ent_temps.set_value(d.temps_vidange_h)

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        if self.projet.vidange is not None:
            self._afficher_resultats(self.projet.vidange)
        else:
            for res in (
                self.res_section, self.res_debit, self.res_diametre,
                self.res_section_vid, self.res_volume, self.res_debit_nec,
            ):
                res.reset()

    # ------------------------------------------------------------------
    def _exporter_docx(self) -> None:
        from debits_ae import generer_rapport_docx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_vidanges.docx",
        )
        if chemin:
            generer_rapport_docx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Vidanges",
                vidange=self.projet.vidange,
                inputs_resume=self.projet.resume_texte(),
            )

    def _exporter_xlsx(self) -> None:
        from debits_ae import generer_rapport_xlsx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_vidanges.xlsx",
        )
        if chemin:
            generer_rapport_xlsx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Vidanges",
                vidange=self.projet.vidange,
                inputs_resume=self.projet.resume_texte(),
            )
