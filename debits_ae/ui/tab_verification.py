"""Onglet 6 — Synthèse, Vérifications & Rapport.

Affiche :
- Le tableau de bord du projet (identité, avancement, alertes de formules)
- Le registre de vérification des formules (F1 → F11) avec statuts
- Les vérifications de fonctionnement (page 6 du PDF)
- La génération du rapport consolidé (.docx et .xlsx)

Le rapport est verrouillé par un avertissement explicite lorsqu'une formule
utilisée est marquée SUSPECT / EMPIRIQUE / À VÉRIFIER / ILLISIBLE.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from debits_ae.models import VerificationResult
from debits_ae import (
    verifier_formules,
    generer_rapport_docx,
    generer_rapport_xlsx,
    formules_a_risque,
)
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, ResultLabel, CalcButton, ExportButton, AlerteFrame


class TabVerification(OngletProjet):
    """Onglet Synthèse, Vérifications & Rapport."""

    def _construire_interface(self) -> None:
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)

        self._construire_synthese()
        self._construire_registre()
        self._construire_verifications()
        self._construire_rapport()

        self.rafraichir_synthese()

    # ------------------------------------------------------------------
    # Tableau de bord
    # ------------------------------------------------------------------
    def _construire_synthese(self) -> None:
        frame = ctk.CTkFrame(self.scroll)
        frame.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame,
            text="Tableau de bord du projet",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Identité
        grille_id = ctk.CTkFrame(frame)
        grille_id.pack(fill="x", padx=10, pady=(0, 6))

        self.ent_ref = LabeledEntry(
            grille_id, "Référence dossier", default=self.projet.donnees.reference, unit="",
            width=170,
        )
        self.ent_ref.pack(side="left", padx=6, pady=4)

        self.ent_site = LabeledEntry(
            grille_id, "Site / ouvrage", default=self.projet.donnees.site, unit="", width=170
        )
        self.ent_site.pack(side="left", padx=6, pady=4)

        self.ent_mo = LabeledEntry(
            grille_id, "Maître d'ouvrage", default=self.projet.donnees.maitre_ouvrage,
            unit="", width=170,
        )
        self.ent_mo.pack(side="left", padx=6, pady=4)

        ctk.CTkButton(
            grille_id, text="Appliquer l'identité", width=150, command=self._appliquer_identite
        ).pack(side="left", padx=6, pady=4)

        # Avancement
        grille_etapes = ctk.CTkFrame(frame)
        grille_etapes.pack(fill="x", padx=10, pady=(0, 6))

        self._lbl_etapes: dict[str, ctk.CTkLabel] = {}
        for nom in self.projet.etapes():
            lbl = ctk.CTkLabel(grille_etapes, text="", anchor="w", font=ctk.CTkFont(size=12))
            lbl.pack(side="left", padx=8, pady=4)
            self._lbl_etapes[nom] = lbl

        self.lbl_prochaine = ctk.CTkLabel(
            frame, text="", anchor="w", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1565C0",
        )
        self.lbl_prochaine.pack(anchor="w", padx=20, pady=(0, 4))

        self.lbl_detail = ctk.CTkLabel(
            frame, text="", anchor="w", justify="left", font=ctk.CTkFont(size=11),
            wraplength=900,
        )
        self.lbl_detail.pack(anchor="w", padx=20, pady=(0, 4))

        self.lbl_alertes = ctk.CTkLabel(
            frame, text="", anchor="w", justify="left", font=ctk.CTkFont(size=11),
            wraplength=900,
        )
        self.lbl_alertes.pack(anchor="w", padx=20, pady=(0, 10))

    def _appliquer_identite(self) -> None:
        d = self.projet.donnees
        d.reference = self.ent_ref.var.get().strip()
        d.site = self.ent_site.var.get().strip()
        d.maitre_ouvrage = self.ent_mo.var.get().strip()
        self.rafraichir_synthese()
        self.notifier()
        self._afficher_alerte("Identité du projet mise à jour.", niveau="info")

    def rafraichir_synthese(self) -> None:
        """Met à jour le tableau de bord (appelé par la fenêtre principale)."""
        etapes = self.projet.etapes()
        for nom, lbl in self._lbl_etapes.items():
            fait = etapes[nom]
            lbl.configure(
                text=("● " if fait else "○ ") + nom,
                text_color="#2E7D32" if fait else "#757575",
            )

        self.lbl_prochaine.configure(text=self.projet.prochaine_etape())
        self.lbl_detail.configure(text=self._texte_detail())

        alertes = formules_a_risque(self.projet)
        if alertes:
            details = " ; ".join(f"{f.nom} [{f.statut}]" for f in alertes)
            self.lbl_alertes.configure(
                text=f"⚠ {len(alertes)} formule(s) utilisée(s) à valider avant dimensionnement définitif : "
                f"{details}",
                text_color="#C62828",
            )
        else:
            self.lbl_alertes.configure(
                text="✔ Aucune formule à risque parmi les résultats calculés.",
                text_color="#2E7D32",
            )

    def _texte_detail(self) -> str:
        p = self.projet
        lignes: list[str] = []
        if p.vidange is not None:
            lignes.append(
                f"Vidange : d = {p.vidange.diametre_vidange:.1f} mm ; "
                f"Q décharge = {p.vidange.debit_decharge:.4f} m³/s."
            )
        v = p.ventouse
        if v is not None:
            if v.qair_degazage > 0 or v.celerite_a > 0:
                lignes.append(
                    f"Dégazage : a = {v.celerite_a:.1f} m/s ; Qair = {v.qair_degazage:.4f} m³/s ; "
                    f"d1 = {v.diametre_orifice_degazage*1000:.1f} mm."
                )
            if v.qair_remplissage > 0:
                lignes.append(
                    f"Remplissage : Qair = {v.qair_remplissage:.4f} m³/s ; "
                    f"d2 = {v.diametre_orifice_remplissage*1000:.1f} mm."
                )
            if v.qair_admission > 0:
                lignes.append(
                    f"Admission : H = {v.hauteur_motrice:.2f} m ; "
                    f"Qair = {v.qair_admission:.4f} m³/s."
                )
        if p.equipements:
            eqs = " + ".join(f"{e.type_equipement} {e.dn}" for e in p.equipements)
            lignes.append(f"Équipement : {eqs}.")
        if p.verification is not None:
            etat = "conforme" if p.verification.tous_conformes else "NON conforme"
            lignes.append(f"Vérifications page 6 : {etat}.")
        return "\n".join(lignes) if lignes else "Aucun résultat calculé pour le moment."

    # ------------------------------------------------------------------
    # Registre des formules
    # ------------------------------------------------------------------
    def _construire_registre(self) -> None:
        frame_formules = ctk.CTkFrame(self.scroll)
        frame_formules.pack(side="top", fill="both", expand=True, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_formules,
            text="Registre de vérification des formules (extrait du PDF)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            frame_formules,
            text="Les formules marquées SUSPECT / EMPIRIQUE / À VÉRIFIER / ILLISIBLE ne doivent pas "
            "servir à un dimensionnement définitif sans validation du bureau d'études.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#EF6C00",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 8))

        cols = ("formule", "statut", "commentaire")
        self.tree = ttk.Treeview(frame_formules, columns=cols, show="headings", height=9)
        self.tree.heading("formule", text="Formule")
        self.tree.heading("statut", text="Statut")
        self.tree.heading("commentaire", text="Commentaire")
        self.tree.column("formule", width=260)
        self.tree.column("statut", width=130)
        self.tree.column("commentaire", width=650)

        scrollbar = ttk.Scrollbar(frame_formules, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        scrollbar.pack(side="right", fill="y", pady=(0, 10))

        self.tree.tag_configure("OK", foreground="#2E7D32")
        self.tree.tag_configure("SUSPECT", foreground="#C62828")
        self.tree.tag_configure("EMPIRIQUE", foreground="#EF6C00")
        self.tree.tag_configure("À VÉRIFIER", foreground="#EF6C00")
        self.tree.tag_configure("ILLISIBLE", foreground="#C62828")
        self.tree.tag_configure("COHÉRENT", foreground="#1565C0")

        for f in verifier_formules():
            self.tree.insert("", "end", values=(f.nom, f.statut, f.commentaire), tags=(f.statut,))

    # ------------------------------------------------------------------
    # Vérifications page 6
    # ------------------------------------------------------------------
    def _construire_verifications(self) -> None:
        frame_verif = ctk.CTkFrame(self.scroll)
        frame_verif.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_verif,
            text="Vérifications de fonctionnement (page 6 du PDF)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille_verif = ctk.CTkFrame(frame_verif)
        grille_verif.pack(fill="x", padx=10, pady=(0, 10))

        d = self.projet.donnees
        self.ent_vitesse = LabeledEntry(
            grille_verif, "Vitesse remplissage admise",
            default=f"{d.vitesse_remplissage_admise:g}", unit="m/s",
            tooltip="Vitesse de remplissage à maintenir (0,5 m/s selon page 6 du PDF).",
        )
        self.ent_vitesse.pack(side="left", padx=6, pady=4)

        self.ent_qnominal = LabeledEntry(
            grille_verif, "Débit nominal conduite", default=f"{d.debit_nominal:g}", unit="m³/s",
            tooltip="Débit nominal de la conduite pour le calcul du dégazage (2 %).",
        )
        self.ent_qnominal.pack(side="left", padx=6, pady=4)

        self.ent_degazage_pct = LabeledEntry(
            grille_verif, "Dégazage ≈ % Qnominal", default=f"{d.degazage_pct_qnom:g}", unit="%",
            tooltip="Pourcentage du débit nominal correspondant au dégazage (2 % selon page 6).",
        )
        self.ent_degazage_pct.pack(side="left", padx=6, pady=4)

        CalcButton(frame_verif, text="Vérifier conformité", command=self._verifier).pack(
            anchor="e", padx=10, pady=(0, 10)
        )

        grille_res = ctk.CTkFrame(frame_verif)
        grille_res.pack(fill="x", padx=10, pady=(0, 10))

        self.res_debit_ref = ResultLabel(grille_res, "Débit de remplissage référence", unit="m³/h")
        self.res_debit_ref.pack(side="left", padx=6, pady=4)
        self.res_degazage = ResultLabel(grille_res, "Débit dégazage vérification", unit="m³/h")
        self.res_degazage.pack(side="left", padx=6, pady=4)
        self.res_global = ResultLabel(grille_res, "Résultat global", unit="—")
        self.res_global.pack(side="left", padx=6, pady=4)

        self.frame_alerte = AlerteFrame(frame_verif, message="", niveau="info")
        self.frame_alerte.pack(side="top", fill="x", padx=10, pady=(0, 10))
        self.frame_alerte.pack_forget()

    def _verifier(self) -> None:
        vitesse = self.ent_vitesse.get_value()
        qnominal = self.ent_qnominal.get_value()
        pct = self.ent_degazage_pct.get_value()

        if qnominal <= 0:
            self._afficher_alerte("Le débit nominal doit être positif.", niveau="alerte")
            return

        # Débit de remplissage référence pour DN2000 à 0,5 m/s
        import math

        s_dn2000 = math.pi / 4.0 * 2.0**2
        debit_ref = vitesse * s_dn2000  # m3/s
        debit_ref_m3h = debit_ref * 3600.0
        debit_degazage = pct / 100.0 * qnominal * 3600.0  # m3/h

        tous_conformes = True
        messages: list[str] = []
        if abs(vitesse - 0.5) > 0.01:
            messages.append(
                f"Vitesse de remplissage {vitesse} m/s ≠ 0,5 m/s recommandé."
            )
            tous_conformes = False

        result = VerificationResult(
            vitesse_remplissage_admise=vitesse,
            debit_remplissage_reference=debit_ref,
            debit_remplissage_reference_m3h=debit_ref_m3h,
            degazage_pourcentage_qnom=pct,
            debit_degazage_verification=debit_degazage,
            debit_nominal=qnominal,
            tous_conformes=tous_conformes,
            messages=messages,
        )

        d = self.projet.donnees
        d.vitesse_remplissage_admise = vitesse
        d.debit_nominal = qnominal
        d.degazage_pct_qnom = pct
        self.projet.verification = result
        self.resultats_partages["verification"] = result

        self._afficher_verification(result)
        self.rafraichir_synthese()
        self.notifier()

    def _afficher_verification(self, result: VerificationResult) -> None:
        self.res_debit_ref.set(result.debit_remplissage_reference_m3h, "{:.0f}")
        self.res_degazage.set(result.debit_degazage_verification, "{:.0f}")
        self.res_global.set(
            "Conforme" if result.tous_conformes else "NON CONFORME",
            "",
            "Conforme" if result.tous_conformes else "NON CONFORME",
        )
        msg = (
            f"Vérification : débit remplissage ≈ {result.debit_remplissage_reference_m3h:.0f} m³/h "
            "(référence 5652 m³/h pour DN2000 à 0,5 m/s). "
            f"Dégazage ≈ {result.debit_degazage_verification:.0f} m³/h "
            f"({result.degazage_pourcentage_qnom:g}% de {result.debit_nominal:g} m³/s)."
        )
        self._afficher_alerte(msg, niveau="info" if result.tous_conformes else "attention")

    # ------------------------------------------------------------------
    # Rapport consolidé
    # ------------------------------------------------------------------
    def _construire_rapport(self) -> None:
        frame_rapport = ctk.CTkFrame(self.scroll)
        frame_rapport.pack(side="top", fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            frame_rapport,
            text="Rapport consolidé du projet",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            frame_rapport,
            text="Le rapport rassemble les résultats de tous les onglets, les graphiques et le "
            "registre des formules. Un avertissement est affiché si une formule à risque est utilisée.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#757575",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        grille_rapport = ctk.CTkFrame(frame_rapport)
        grille_rapport.pack(fill="x", padx=10, pady=(0, 10))

        ExportButton(
            grille_rapport, text="Rapport complet DOCX", command=self._exporter_docx, fmt="docx"
        ).pack(side="left", padx=10, pady=6)
        ExportButton(
            grille_rapport, text="Rapport complet XLSX", command=self._exporter_xlsx, fmt="xlsx"
        ).pack(side="left", padx=10, pady=6)

    def _confirmer_export(self) -> bool:
        if not any(self.projet.etapes().values()):
            messagebox.showwarning(
                "Rapport vide",
                "Aucun résultat n'est disponible. Calculez au moins une étape avant d'exporter.",
            )
            return False

        alertes = formules_a_risque(self.projet)
        if alertes:
            details = "\n".join(f"• {f.nom} — {f.statut}" for f in alertes)
            return messagebox.askyesno(
                "Export — formules à valider",
                "Les formules suivantes sont utilisées mais ne sont pas validées :\n\n"
                f"{details}\n\n"
                "Le rapport les signalera explicitement. Voulez-vous l'exporter quand même ?",
            )
        return True

    def _exporter_docx(self) -> None:
        if not self._confirmer_export():
            return
        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_complet.docx",
        )
        if not chemin:
            return
        generer_rapport_docx(
            chemin,
            projet=f"{self.projet.donnees.nom} — Rapport complet",
            vidange=self.projet.vidange,
            ventouse=self.projet.ventouse,
            equipements=self.projet.equipements,
            verification=self.projet.verification,
            donnees=self.projet.donnees,
            inputs_resume=self.projet.resume_texte(),
            tableau_import=self.resultats_partages.get("tableau_import"),
            catalogue_mcp=self.resultats_partages.get("catalogue_mcp"),
            configuration_equipements=self.resultats_partages.get(
                "configuration_equipements"
            ),
        )
        messagebox.showinfo("Rapport généré", f"Rapport DOCX enregistré :\n{chemin}")

    def _exporter_xlsx(self) -> None:
        if not self._confirmer_export():
            return
        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_complet.xlsx",
        )
        if not chemin:
            return
        generer_rapport_xlsx(
            chemin,
            projet=f"{self.projet.donnees.nom} — Rapport complet",
            vidange=self.projet.vidange,
            ventouse=self.projet.ventouse,
            equipements=self.projet.equipements,
            verification=self.projet.verification,
            donnees=self.projet.donnees,
            inputs_resume=self.projet.resume_texte(),
            tableau_import=self.resultats_partages.get("tableau_import"),
            catalogue_mcp=self.resultats_partages.get("catalogue_mcp"),
            configuration_equipements=self.resultats_partages.get(
                "configuration_equipements"
            ),
        )
        messagebox.showinfo("Rapport généré", f"Rapport XLSX enregistré :\n{chemin}")

    # ------------------------------------------------------------------
    def synchroniser_depuis_projet(self) -> None:
        d = self.projet.donnees
        self.ent_ref.var.set(d.reference)
        self.ent_site.var.set(d.site)
        self.ent_mo.var.set(d.maitre_ouvrage)
        self.ent_vitesse.set_value(d.vitesse_remplissage_admise)
        self.ent_qnominal.set_value(d.debit_nominal)
        self.ent_degazage_pct.set_value(d.degazage_pct_qnom)

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        if self.projet.verification is not None:
            self._afficher_verification(self.projet.verification)
        else:
            for res in (self.res_debit_ref, self.res_degazage, self.res_global):
                res.reset()
        self.rafraichir_synthese()
