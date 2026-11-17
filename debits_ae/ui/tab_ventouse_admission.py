"""Onglet 4 — Ventouse : 3ème fonction — Admission d'air (vidange / casse franche).

Calcule :
- Hauteur motrice H (F11 : cote_ventouse − 3 − cote_vidange)
- Vitesse de vidange v, débit eau Qeau, débit air Qair (F10)

F10 n'est plus la formule illisible du PDF : elle est re-dérivée depuis
« Dénivelée = j·L + ξ·v²/2g » (page 5) avec la ligne d'énergie j de
Strickler (F8), soit :
    v = √[ H / ( ξ/(2g) + L / (K²·(π/4)^(4/3)·D^(4/3)) ) ]
    Qair = Qeau = v · πD²/4
Le sélecteur « pertes singulières » permet de comparer les deux lectures du
document (v²/2g écrit, ou « k = 2 » ⇒ v²/g).

Le résultat est fusionné dans `Projet.ventouse` sans écraser les autres
fonctions de la ventouse.
"""

from __future__ import annotations

import customtkinter as ctk

from debits_ae.models import VentouseResult
from debits_ae import qair_admission_casse, hauteur_motriere
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, ResultLabel, CalcButton, ExportButton, AlerteFrame

# Libellés du sélecteur de pertes singulières (ξ en multiples de v²/2g)
XI_V2_SUR_2G = "v²/2g  (ξ = 1)"
XI_V2_SUR_G = "v²/g  (k = 2)"


def _libelle_xi(xi: float) -> str:
    return XI_V2_SUR_G if xi >= 1.5 else XI_V2_SUR_2G


class TabVentouseAdmission(OngletProjet):
    """Onglet Ventouse — Admission d'air (3ème fonction)."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        # --- Saisie ---
        frame_saisie = ctk.CTkFrame(self)
        frame_saisie.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame_saisie,
            text="Données d'entrée — 3ème fonction : Admission d'air (vidange / casse franche)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_saisie)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        self.ent_k = LabeledEntry(
            grille, "Coeff. rugosité K", default=f"{d.coeff_rugosite:g}", unit="m^(1/3)/s",
            tooltip="104 pour PRV ; 100 pour la fonte.",
        )
        self.ent_k.pack(side="left", padx=6, pady=4)

        self.ent_pente = LabeledEntry(
            grille, "Pente i", default=f"{d.pente:g}", unit="m/m",
            tooltip="Pente du tronçon (m/m).",
        )
        self.ent_pente.pack(side="left", padx=6, pady=4)

        self.ent_diametre = LabeledEntry(
            grille, "Diamètre conduit D", default=f"{d.diam_conduit:g}", unit="m",
            tooltip="Diamètre intérieur de la conduite (m).",
        )
        self.ent_diametre.pack(side="left", padx=6, pady=4)

        self.ent_longueur = LabeledEntry(
            grille, "Longueur de tronçon L", default=f"{d.longueur_troncon:g}", unit="m",
            tooltip="Longueur du tronçon de conduite (m).",
        )
        self.ent_longueur.pack(side="left", padx=6, pady=4)

        self.ent_cote_v = LabeledEntry(
            grille, "Cote ventouse", default=f"{d.cote_ventouse:g}", unit="m",
            tooltip="Cote projet de la ventouse (m).",
        )
        self.ent_cote_v.pack(side="left", padx=6, pady=4)

        self.ent_cote_d = LabeledEntry(
            grille, "Cote vidange", default=f"{d.cote_vidange:g}", unit="m",
            tooltip="Cote projet de la vidange (m).",
        )
        self.ent_cote_d.pack(side="left", padx=6, pady=4)

        # Choix de la perte singulière : ambiguïté du PDF (v²/2g écrit, « k = 2 »)
        frame_xi = ctk.CTkFrame(frame_saisie, fg_color="transparent")
        frame_xi.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(frame_xi, text="Pertes singulières ξ :").pack(side="left", padx=(6, 8))
        self.seg_xi = ctk.CTkSegmentedButton(
            frame_xi, values=[XI_V2_SUR_2G, XI_V2_SUR_G]
        )
        self.seg_xi.set(_libelle_xi(d.coeff_singularites))
        self.seg_xi.pack(side="left")
        ctk.CTkLabel(
            frame_xi,
            text="1 = équation écrite du PDF ; 2 = mention « k = 2 » "
            "(la constante 0,102 de la formule imprimée vaut 1/g).",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#90A4AE",
            wraplength=520,
            justify="left",
        ).pack(side="left", padx=12)

        CalcButton(frame_saisie, text="Calculer admission", command=self._calculer).pack(
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

        self.res_h = ResultLabel(grille_res, "Hauteur motrice H (F11)", unit="m")
        self.res_h.pack(side="left", padx=6, pady=4)
        self.res_v = ResultLabel(grille_res, "Vitesse de vidange v", unit="m/s")
        self.res_v.pack(side="left", padx=6, pady=4)
        self.res_qeau = ResultLabel(grille_res, "Débit eau vidange Qeau", unit="m³/s")
        self.res_qeau.pack(side="left", padx=6, pady=4)
        self.res_qair = ResultLabel(grille_res, "Débit air admission Qair (F10)", unit="m³/s")
        self.res_qair.pack(side="left", padx=6, pady=4)

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
        k = self.ent_k.get_value()
        pente = self.ent_pente.get_value()
        diam = self.ent_diametre.get_value()
        longueur = self.ent_longueur.get_value()
        cote_v = self.ent_cote_v.get_value()
        cote_d = self.ent_cote_d.get_value()
        xi = 2.0 if self.seg_xi.get() == XI_V2_SUR_G else 1.0

        if diam <= 0 or longueur <= 0:
            self._afficher_alerte(
                "Veuillez saisir des valeurs positives pour D et L.", niveau="alerte"
            )
            return

        h = hauteur_motriere(cote_v, cote_d)
        # F10 — Bernoulli (H = j·L + ξ·v²/2g) résolu avec j de Strickler (F8)
        v, q_eau, q_air, _ = qair_admission_casse(
            h,
            longueur,
            diam,
            coeff_rugosite=k,
            coeff_singularites=xi,
        )

        d = self.projet.donnees
        d.coeff_rugosite = k
        d.pente = pente
        d.diam_conduit = diam
        d.longueur_troncon = longueur
        d.cote_ventouse = cote_v
        d.cote_vidange = cote_d
        d.coeff_singularites = xi

        vent = self.projet.ventouse or VentouseResult()
        vent.hauteur_motrice = h
        vent.vitesse_vidange = v
        vent.q_eau_vidange = q_eau
        vent.qair_admission = q_air
        vent.coeff_singularites = xi
        self.projet.ventouse = vent
        self.resultats_partages["ventouse"] = vent

        self._afficher_resultats(vent, h)
        self.notifier()

    def _afficher_resultats(self, vent: VentouseResult, h: float | None = None) -> None:
        h = vent.hauteur_motrice if h is None else h
        xi = vent.coeff_singularites
        self.res_h.set(h, "{:.3f}", "OK")
        self.res_v.set(vent.vitesse_vidange, "{:.3f}", "COHÉRENT")
        self.res_qeau.set(vent.q_eau_vidange, "{:.4f}", "COHÉRENT")
        self.res_qair.set(vent.qair_admission, "{:.4f}", "COHÉRENT")

        xi_txt = "v²/g (k = 2)" if xi >= 1.5 else "v²/2g"
        msg = (
            f"Hauteur motrice H = {h:.3f} m. Pertes singulières retenues : "
            f"ξ·v²/2g avec ξ = {xi:g} ({xi_txt}). Vitesse de vidange v = "
            f"{vent.vitesse_vidange:.3f} m/s. Débit eau de vidange Qeau = "
            f"{vent.q_eau_vidange:.4f} m³/s. Débit d'air à admettre Qair = "
            f"{vent.qair_admission:.4f} m³/s (Qair = Qeau). Formule F10 "
            f"re-dérivée depuis Bernoulli + Strickler (F8) : plus de formule "
            f"illisible ; reste à confirmer la valeur de ξ par le bureau d'études."
        )
        self._afficher_alerte(msg, niveau="info")

    def synchroniser_depuis_projet(self) -> None:
        d = self.projet.donnees
        self.ent_k.set_value(d.coeff_rugosite)
        self.ent_pente.set_value(d.pente)
        self.ent_diametre.set_value(d.diam_conduit)
        self.ent_longueur.set_value(d.longueur_troncon)
        self.ent_cote_v.set_value(d.cote_ventouse)
        self.ent_cote_d.set_value(d.cote_vidange)
        self.seg_xi.set(_libelle_xi(d.coeff_singularites))

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        v = self.projet.ventouse
        if v is not None and v.qair_admission > 0:
            self._afficher_resultats(v)
        else:
            for res in (self.res_h, self.res_v, self.res_qeau, self.res_qair):
                res.reset()

    # ------------------------------------------------------------------
    def _exporter_docx(self) -> None:
        from debits_ae import generer_rapport_docx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_admission.docx",
        )
        if chemin:
            generer_rapport_docx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Admission air",
                ventouse=self.projet.ventouse,
                donnees=self.projet.donnees,
                inputs_resume=self.projet.resume_texte(),
            )

    def _exporter_xlsx(self) -> None:
        from debits_ae import generer_rapport_xlsx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_admission.xlsx",
        )
        if chemin:
            generer_rapport_xlsx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Admission air",
                ventouse=self.projet.ventouse,
                donnees=self.projet.donnees,
                inputs_resume=self.projet.resume_texte(),
            )
