"""Onglet 2 — Ventouse : 1ère fonction — Dégazage (coup de bélier).

Calcule :
- Célérité d'Allievi a (F3 empirique, Tableau 7)
- Débit d'air de dégazage Qair (F4 : ΔH · g · S0 / a)
- Diamètre d'orifice de dégazage d1 (F6 via Saint-Venant)

Le résultat est fusionné dans `Projet.ventouse` sans écraser les autres
fonctions de la ventouse.
"""

from __future__ import annotations

import math

import customtkinter as ctk

from debits_ae.models import VentouseResult, P1_ATMOSPHERIQUE_MCE
from debits_ae import celerite_allievi, qair_degazage
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, ResultLabel, CalcButton, ExportButton, AlerteFrame


class TabVentouseDegazage(OngletProjet):
    """Onglet Ventouse — Dégazage (1ère fonction)."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        # --- Saisie ---
        frame_saisie = ctk.CTkFrame(self)
        frame_saisie.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame_saisie,
            text="Données d'entrée — 1ère fonction : Dégazage (coup de bélier)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_saisie)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        self.ent_diametre = LabeledEntry(
            grille, "Diamètre conduit D", default=f"{d.diam_conduit:g}", unit="m",
            tooltip="Diamètre intérieur de la conduite (m).",
        )
        self.ent_diametre.pack(side="left", padx=6, pady=4)

        self.ent_epaisseur = LabeledEntry(
            grille, "Épaisseur conduit e", default=f"{d.epaisseur_conduite:g}", unit="m",
            tooltip="Épaisseur de paroi de la conduite (m).",
        )
        self.ent_epaisseur.pack(side="left", padx=6, pady=4)

        self.ent_kc = LabeledEntry(
            grille, "Coeff. Allievi k", default=f"{d.coeff_allievi:g}", unit="—",
            tooltip="Coefficient Allievi k par matériau (Tableau 8) : acier 0,5 ; fonte ductile 0,6 ; "
            "béton 3,3-5,0 ; PVC 33,3 ; PEHD 100-125.",
        )
        self.ent_kc.pack(side="left", padx=6, pady=4)

        self.ent_delta_h = LabeledEntry(
            grille, "Suppression ΔH max", default=f"{d.delta_h_max:g}", unit="m",
            tooltip="Suppression de pression à ne pas dépasser (10 m max).",
        )
        self.ent_delta_h.pack(side="left", padx=6, pady=4)

        self.ent_p2 = LabeledEntry(
            grille, "Pression absolue P2", default=f"{d.p2_pression_absolue_mce:g}", unit="mCE",
            tooltip="Pression absolue dans la conduite (mCE). 10,33 mCE = pression atmosphérique. "
            "Si P2 ≤ P1, l'application retient P2 = P1 + ΔH pour le calcul de F6.",
        )
        self.ent_p2.pack(side="left", padx=6, pady=4)

        CalcButton(frame_saisie, text="Calculer dégazage", command=self._calculer).pack(
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

        self.res_celerite = ResultLabel(grille_res, "Célérité d'Allievi a (F3)", unit="m/s")
        self.res_celerite.pack(side="left", padx=6, pady=4)
        self.res_qair_degaz = ResultLabel(grille_res, "Débit air dégazage Qair (F4)", unit="m³/s")
        self.res_qair_degaz.pack(side="left", padx=6, pady=4)
        self.res_delta_h = ResultLabel(grille_res, "Suppression ΔH", unit="m")
        self.res_delta_h.pack(side="left", padx=6, pady=4)
        self.res_d1 = ResultLabel(grille_res, "Orifice dégazage d1 (F6)", unit="mm")
        self.res_d1.pack(side="left", padx=6, pady=4)
        self.res_conforme = ResultLabel(grille_res, "Conformité dégazage", unit="—")
        self.res_conforme.pack(side="left", padx=6, pady=4)

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
        e = self.ent_epaisseur.get_value()
        kc = self.ent_kc.get_value()
        delta_h = self.ent_delta_h.get_value()
        p2 = self.ent_p2.get_value()

        if diam <= 0 or e <= 0 or kc <= 0 or delta_h <= 0 or p2 <= 0:
            self._afficher_alerte(
                "Veuillez saisir des valeurs positives pour tous les champs.", niveau="alerte"
            )
            return

        # 1. Célérité Allievi (F3)
        a, _ = celerite_allievi(k_allievi=kc, diam_conduit=diam, epaisseur_conduite=e)

        # 2. Section conduite
        s0 = math.pi / 4.0 * diam**2

        # 3. Débit d'air dégazage (F4) — corrige l'appel : gravite= et non G=
        q_degaz, alerte_dh = qair_degazage(delta_h, gravite=9.81, section_conduite=s0, celerite_a=a)

        # 4. Diamètre orifice dégazage (F6 via Saint-Venant)
        from debits_ae import diametre_orifice_degazage

        d1, _ = diametre_orifice_degazage(
            diam_conduit=diam,
            delta_h=delta_h,
            celerite_a=a,
            section_conduite=s0,
            p2_mce=p2,
        )

        conforme = bool(delta_h <= 10 and not alerte_dh and d1 > 0)

        # Mise à jour du projet partagé (sans écraser les autres fonctions)
        d = self.projet.donnees
        d.diam_conduit = diam
        d.epaisseur_conduite = e
        d.coeff_allievi = kc
        d.delta_h_max = delta_h
        d.p2_pression_absolue_mce = p2

        v = self.projet.ventouse or VentouseResult()
        v.celerite_a = a
        v.qair_degazage = q_degaz
        v.diametre_orifice_degazage = d1
        v.delta_h = delta_h
        v.degazage_conforme = conforme
        self.projet.ventouse = v
        self.resultats_partages["ventouse"] = v

        self._afficher_resultats(v, p2_effective=p2, p1=P1_ATMOSPHERIQUE_MCE)
        self.notifier()

    def _afficher_resultats(self, v: VentouseResult, p2_effective: float | None = None,
                            p1: float = P1_ATMOSPHERIQUE_MCE) -> None:
        self.res_celerite.set(v.celerite_a, "{:.2f}", "OK")
        self.res_qair_degaz.set(v.qair_degazage, "{:.4f}", "OK")
        self.res_delta_h.set(
            v.delta_h, "{:.2f}", "Conforme" if v.delta_h <= 10 else "NON CONFORME"
        )
        self.res_d1.set(v.diametre_orifice_degazage * 1000, "{:.1f}", "COHÉRENT")
        self.res_conforme.set(
            "Conforme" if v.degazage_conforme else "NON CONFORME",
            "",
            "Conforme" if v.degazage_conforme else "NON CONFORME",
        )

        msg = (
            f"Célérité a = {v.celerite_a:.2f} m/s. Débit d'air de dégazage = "
            f"{v.qair_degazage:.4f} m³/s. Orifice dégazage d1 = "
            f"{v.diametre_orifice_degazage*1000:.1f} mm."
        )
        niveau = "info"
        if v.delta_h > 10:
            msg += "  ATTENTION : ΔH > 10 m."
            niveau = "attention"
        if p2_effective is not None and p2_effective <= p1:
            msg += (
                f"  P2 ≤ P1 : la pression P2 = P1 + ΔH = {p1 + v.delta_h:.2f} mCE "
                "a été retenue pour F6."
            )
            niveau = "attention"
        self._afficher_alerte(msg, niveau=niveau)

    def synchroniser_depuis_projet(self) -> None:
        d = self.projet.donnees
        self.ent_diametre.set_value(d.diam_conduit)
        self.ent_epaisseur.set_value(d.epaisseur_conduite)
        self.ent_kc.set_value(d.coeff_allievi)
        self.ent_delta_h.set_value(d.delta_h_max)
        self.ent_p2.set_value(d.p2_pression_absolue_mce)

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        v = self.projet.ventouse
        if v is not None and (v.celerite_a > 0 or v.qair_degazage > 0):
            self._afficher_resultats(v, self.projet.donnees.p2_pression_absolue_mce)
        else:
            for res in (
                self.res_celerite, self.res_qair_degaz, self.res_delta_h,
                self.res_d1, self.res_conforme,
            ):
                res.reset()

    # ------------------------------------------------------------------
    def _exporter_docx(self) -> None:
        from debits_ae import generer_rapport_docx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_degazage.docx",
        )
        if chemin:
            generer_rapport_docx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Dégazage",
                ventouse=self.projet.ventouse,
                inputs_resume=self.projet.resume_texte(),
            )

    def _exporter_xlsx(self) -> None:
        from debits_ae import generer_rapport_xlsx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_degazage.xlsx",
        )
        if chemin:
            generer_rapport_xlsx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Dégazage",
                ventouse=self.projet.ventouse,
                inputs_resume=self.projet.resume_texte(),
            )
