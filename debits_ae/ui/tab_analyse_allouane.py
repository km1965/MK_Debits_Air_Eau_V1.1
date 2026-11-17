"""Onglet 8 — Analyse comparative Allouane vs méthode de l'app.

Permet d'importer un rapport Allouane (ex. rapport_allouane_BR3_TR2.docx),
d'extraire les données du tronçon, de les recalculer avec la formule F10 de
l'application (Bernoulli + Strickler, audit BR3_LOT8) et de comparer les
résultats avec la référence Allouane.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from debits_ae import (
    DONNEES_ALLOUANE,
    DonneesAllouane,
    recalculer_tous_tronçons,
    comparer_allouane_vs_app,
    generer_rapport_texte,
    generer_rapport_allouane_docx,
    importer_docx,
    _FORMULES_REFERENCES,
)
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import CalcButton, AlerteFrame, ExportButton


class TabAnalyseAllouane(OngletProjet):
    """Onglet Analyse comparative Allouane / App."""

    def _construire_interface(self) -> None:
        ctk.CTkLabel(
            self,
            text="Analyse comparative : Méthode ALLOUANE vs Méthode de l'app (F10)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            self,
            text="Recalcule un tronçon de casse franche étudié par la méthode "
            "A. ALLOUANE 2026 avec la formule F10 de l'application "
            "(Bernoulli + Strickler, ξ = 2, K = 104 PRV), puis compare les "
            "résultats avec la référence approuvée.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#757575",
            wraplength=950,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # --- Données du tronçon ---
        frame_donnees = ctk.CTkFrame(self)
        frame_donnees.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_donnees,
            text="Données du tronçon (éditables)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1F3B5C",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_donnees)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        # Ligne d'import DOCX
        ligne_import = ctk.CTkFrame(grille, fg_color="transparent")
        ligne_import.pack(fill="x", padx=0, pady=4)

        CalcButton(
            ligne_import,
            text="Importer DOCX…",
            command=self._importer_docx,
        ).pack(side="left", padx=6, pady=4)

        self.lbl_docx = ctk.CTkLabel(
            ligne_import, text="Aucun fichier DOCX importé", text_color="#757575"
        )
        self.lbl_docx.pack(side="left", padx=10, pady=4)

        self.ent_dh_brut = self._ajoute_champ(
            grille, "ΔH brut (Ve − Vi1) [m]",
            f"{DONNEES_ALLOUANE.delta_h_brut:g}", "m",
        )
        self.ent_l1 = self._ajoute_champ(
            grille, "Longueur L1 (Vi1 → Ve) [m]",
            f"{DONNEES_ALLOUANE.longueur_l1:g}", "m",
        )
        self.ent_dh_av = self._ajoute_champ(
            grille, "ΔH brut aval (Ve − Vi2) [m]",
            f"{DONNEES_ALLOUANE.altitude_ve - DONNEES_ALLOUANE.altitude_vi2:g}", "m",
        )
        self.ent_l2 = self._ajoute_champ(
            grille, "Longueur L2 (Ve → Vi2) [m]",
            f"{DONNEES_ALLOUANE.longueur_l2:g}", "m",
        )
        self.ent_diam = self._ajoute_champ(
            grille, "Diamètre intérieur D [m]",
            f"{DONNEES_ALLOUANE.diametre_interieur:g}", "m",
        )
        self.ent_k = self._ajoute_champ(
            grille, "Rugosité K Strickler",
            "104", "m^(1/3)/s (104 PRV / 100 fonte)",
        )
        self.ent_xi = self._ajoute_champ(
            grille, "Pertes singulières ξ",
            "2", "2 = k=2 (audit), 1 = équation écrite",
        )
        self.ent_dep = self._ajoute_champ(
            grille, "Dépression admissible [m]",
            f"{DONNEES_ALLOUANE.depression_admissible:g}", "mCE",
        )

        self.dernier_resultat = None

        # --- Référence Allouane ---
        frame_ref = ctk.CTkFrame(self)
        frame_ref.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_ref,
            text="Référence Allouane (résultats approuvés)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1F3B5C",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille_ref = ctk.CTkFrame(frame_ref)
        grille_ref.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_q_all_am = ctk.CTkLabel(
            grille_ref, text="—", font=ctk.CTkFont(size=11)
        )
        self.lbl_q_all_av = ctk.CTkLabel(
            grille_ref, text="—", font=ctk.CTkFont(size=11)
        )
        self.lbl_q_all_max = ctk.CTkLabel(
            grille_ref, text="—", font=ctk.CTkFont(size=11)
        )

        ctk.CTkLabel(
            grille_ref, text="Q Allouane amont (m³/h) :", anchor="w"
        ).grid(row=0, column=0, padx=6, pady=2, sticky="w")
        self.lbl_q_all_am.grid(row=0, column=1, padx=6, pady=2, sticky="w")
        ctk.CTkLabel(
            grille_ref, text="Q Allouane aval (m³/h) :", anchor="w"
        ).grid(row=1, column=0, padx=6, pady=2, sticky="w")
        self.lbl_q_all_av.grid(row=1, column=1, padx=6, pady=2, sticky="w")
        ctk.CTkLabel(
            grille_ref, text="Q_Ve max (m³/h) :", anchor="w"
        ).grid(row=2, column=0, padx=6, pady=2, sticky="w")
        self.lbl_q_all_max.grid(row=2, column=1, padx=6, pady=2, sticky="w")

        self.lbl_q_all_am.configure(
            text=f"{DONNEES_ALLOUANE.q_allouane_amont:,.1f}"
        )
        self.lbl_q_all_av.configure(
            text=f"{DONNEES_ALLOUANE.q_allouane_aval:,.1f}"
        )
        self.lbl_q_all_max.configure(
            text=f"{DONNEES_ALLOUANE.q_allouane_max:,.1f}"
        )

        # --- Bouton calcul ---
        frame_calc = ctk.CTkFrame(self)
        frame_calc.pack(side="top", fill="x", padx=15, pady=(0, 10))

        CalcButton(
            frame_calc,
            text="Recalculer (F10) et comparer",
            command=self._calculer,
        ).pack(side="left", padx=10, pady=6)

        ExportButton(
            frame_calc,
            text="Exporter résultats détaillés (XLSX)",
            command=self._exporter_resultats_detailles,
            fmt="xlsx",
        ).pack(side="left", padx=10, pady=6)

        ExportButton(
            frame_calc,
            text="Exporter rapport DOCX",
            command=self._exporter_rapport_docx,
            fmt="docx",
        ).pack(side="left", padx=10, pady=6)

        # --- Résultats ---
        frame_res = ctk.CTkFrame(self)
        frame_res.pack(side="top", fill="both", expand=True, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_res,
            text="Résultats du recalcul et comparaison",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1F3B5C",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.txt_res = ctk.CTkTextbox(frame_res, height=300)
        self.txt_res.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Alerte ---
        self.frame_alerte = AlerteFrame(self, message="", niveau="info")
        self.frame_alerte.pack(side="top", fill="x", padx=15, pady=(0, 10))
        self.frame_alerte.pack_forget()

        self.dernier_resultat = None

        self.docx_source = None

        self.donnees_imp = None

    # ------------------------------------------------------------------
    def _ajoute_champ(
        self,
        parent: ctk.CTkFrame,
        label: str,
        default: str,
        unite: str = "",
    ) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="top", fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label + " :", width=340, anchor="w").pack(
            side="left", padx=6
        )
        ent = ctk.CTkEntry(frame, width=120)
        ent.insert(0, default)
        ent.pack(side="left", padx=6)
        if unite:
            ctk.CTkLabel(frame, text=unite, width=60, anchor="w").pack(
                side="left", padx=6
            )
        return ent

    # ------------------------------------------------------------------
    def _calculer(self) -> None:
        try:
            dh_brut = float(self.ent_dh_brut.get().replace(",", "."))
            l1 = float(self.ent_l1.get().replace(",", "."))
            dh_av = float(self.ent_dh_av.get().replace(",", "."))
            l2 = float(self.ent_l2.get().replace(",", "."))
            diam = float(self.ent_diam.get().replace(",", "."))
            k = float(self.ent_k.get().replace(",", "."))
            xi = float(self.ent_xi.get().replace(",", "."))
            dep = float(self.ent_dep.get().replace(",", "."))
        except ValueError:
            messagebox.showerror(
                "Saisie invalide",
                "Veuillez saisir des valeurs numériques valides dans tous les champs.",
            )
            return

        from debits_ae import DonneesAllouane

        donnees = DonneesAllouane(
            delta_h_brut=dh_brut,
            longueur_l1=l1,
            diametre_interieur=diam,
            depression_admissible=dep,
        )
        # On adapte : l'altitude aval et L2 sont calculées depuis dh_av
        # On crée un objet sur mesure pour le recalcul
        from debits_ae.analyse_allouane import recalculer_tronçon

        amont = recalculer_tronçon(
            nom="Tronçon amont (Vi1 → Ve)",
            h_brut=dh_brut,
            longueur=l1,
            diametre=diam,
            coeff_rugosite=k,
            xi=xi,
            depression_admissible=dep,
        )
        aval = recalculer_tronçon(
            nom="Tronçon aval (Ve → Vi2)",
            h_brut=dh_av,
            longueur=l2,
            diametre=diam,
            coeff_rugosite=k,
            xi=xi,
            depression_admissible=dep,
        )

        # Comparaison avec la référence Allouane (document importé ou défaut)
        donnees_ref = self.donnees_imp if self.donnees_imp else DONNEES_ALLOUANE
        comparaisons = comparer_allouane_vs_app(amont, aval, donnees_ref)

        # Affichage
        lignes: list[str] = []
        lignes.append("RÉCALCUL F10 (méthode de l'application)")
        lignes.append("=" * 70)
        lignes.append("")
        for r in (amont, aval):
            lignes.append(f"{r.nom} :")
            lignes.append(f"  H motrice net  = {r.h_motrice:.2f} m")
            lignes.append(f"  Longueur       = {r.longueur:.2f} m")
            lignes.append(f"  Vitesse v      = {r.vitesse:.3f} m/s")
            lignes.append(f"  Débit Qair     = {r.debit_m3h:,.1f} m³/h ({r.debit_m3s:.3f} m³/s)")
            lignes.append("")
        lignes.append("-" * 70)
        lignes.append("COMPARAISON AVEC LA RÉFÉRENCE ALLOUANE")
        lignes.append("-" * 70)
        for c in comparaisons:
            lignes.append(f"{c.nom} :")
            lignes.append(f"  Allouane : {c.q_allouane_m3h:,.1f} m³/h")
            lignes.append(f"  App      : {c.q_app_m3h:,.1f} m³/h")
            lignes.append(f"  Écart    : {c.ecart_abs_m3h:+,.1f} m³/h ({c.ecart_pct:+.1f} %)")
            lignes.append(f"  Statut   : {c.statut}")
            lignes.append("")
        q_besoin = max(amont.debit_m3h, aval.debit_m3h)
        capa = donnees_ref.capa_installee_totale
        fs = capa / q_besoin if q_besoin > 0 else 0.0
        lignes.append("-" * 70)
        lignes.append("VÉRIFICATION ÉQUIPEMENTS (besoin recalculé par l'app)")
        lignes.append("-" * 70)
        lignes.append(f"  Besoin réel (max)           = {q_besoin:,.1f} m³/h")
        lignes.append(f"  Capacité installée          = {capa:,.0f} m³/h")
        lignes.append(f"  Fs (app)                    = {fs:.2f}")
        lignes.append(f"  Verdict                     = {'COUVERT' if fs >= 1.0 else 'SOUS-DIMENSIONNÉ'}")
        lignes.append("")

        self.txt_res.delete("1.0", "end")
        self.txt_res.insert("1.0", "\n".join(lignes))

        self.dernier_resultat = {
            "amont": amont,
            "aval": aval,
            "comparaisons": comparaisons,
        }

        msg = (
            f"Recalcul terminé : amont {amont.debit_m3h:,.0f} m³/h, "
            f"aval {aval.debit_m3h:,.0f} m³/h."
        )
        self._afficher_alerte(msg, niveau="info")

    # ------------------------------------------------------------------
    def _importer_docx(self) -> None:
        """Importe un document .docx (type rapport Allouane) et remplit les champs."""
        chemin = filedialog.askopenfilename(
            title="Importer un rapport .docx (étude de casse franche)",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return

        try:
            resultat = importer_docx(chemin, self.projet.donnees)
        except Exception as exc:
            messagebox.showerror(
                "Import DOCX impossible",
                f"Le document n'a pas pu être lu :\n{exc}",
            )
            return

        if resultat.avertissements:
            self._afficher_alerte(
                "\n".join(f"• {a}" for a in resultat.avertissements),
                niveau="attention",
            )

        # Remplit TOUS les champs depuis les données extraites
        d = resultat.donnees or self.projet.donnees

        def _set_entry(entry: ctk.CTkEntry, valeur) -> None:
            """Met à jour un champ de saisie (efface puis insère)."""
            if valeur is None:
                return
            try:
                v = float(valeur)
            except (TypeError, ValueError):
                return
            entry.delete(0, "end")
            entry.insert(0, f"{v:g}")

        # Lecture directe des valeurs brutes du document (contournement si mapping incomplet)
        db = resultat.donnees_brutes

        # Delta H brut amont : depuis les données brutes ou calculé depuis les altitudes
        dh_amont = None
        for cle in ("delta_h_brut", "dh_q_allouane_amont", "delta h brut"):
            if cle in db and db[cle] is not None:
                dh_amont = db[cle]
                break
        if dh_amont is None and d.altitude_ve and d.altitude_vi1:
            dh_amont = d.altitude_ve - d.altitude_vi1

        # Delta H brut aval
        dh_aval = None
        for cle in ("dh_q_allouane_aval",):
            if cle in db and db[cle] is not None:
                dh_aval = db[cle]
                break
        if dh_aval is None and d.altitude_ve and d.altitude_vi2:
            dh_aval = d.altitude_ve - d.altitude_vi2

        # Longueurs L1 et L2 depuis les données brutes
        l1 = None
        for cle in ("longueur_troncon", "distance l1 vi1 ve", "l_q_allouane_amont"):
            if cle in db and db[cle] is not None:
                l1 = db[cle]
                break

        l2 = None
        for cle in ("longueur_troncon_2", "distance l2 ve vi2", "l_q_allouane_aval"):
            if cle in db and db[cle] is not None:
                l2 = db[cle]
                break

        _set_entry(self.ent_diam, d.diam_conduit if d.diam_conduit and d.diam_conduit > 0 else None)
        _set_entry(self.ent_l1, l1 if l1 is not None else None)
        _set_entry(self.ent_l2, l2 if l2 is not None else None)
        _set_entry(self.ent_dh_brut, dh_amont if dh_amont is not None else None)
        _set_entry(self.ent_dh_av, dh_aval if dh_aval is not None else None)
        if d.delta_h_max and d.delta_h_max > 0:
            _set_entry(self.ent_dep, d.delta_h_max)

        nom_fichier = Path(chemin).name
        self.lbl_docx.configure(text=nom_fichier, text_color="#1E6B1E")
        self.docx_source = chemin

        # Réinitialiser le dernier résultat et les références Allouane
        self.dernier_resultat = None
        self.txt_res.delete("1.0", "end")

        # Construire un objet DonneesAllouane à jour depuis le document importé,
        # afin que la comparaison utilise les vraies valeurs de ce document.
        q_all_am = db.get("q_allouane_amont")
        q_all_av = db.get("q_allouane_aval")
        q_all_max = max(q_all_am, q_all_av) if q_all_am and q_all_av else DONNEES_ALLOUANE.q_allouane_max
        donnees_imp = DonneesAllouane(
            diametre_interieur=d.diam_conduit if d.diam_conduit and d.diam_conduit > 0 else DONNEES_ALLOUANE.diametre_interieur,
            longueur_l1=l1 if l1 is not None else DONNEES_ALLOUANE.longueur_l1,
            delta_h_brut=dh_amont if dh_amont is not None else DONNEES_ALLOUANE.delta_h_brut,
            depression_admissible=d.delta_h_max if d.delta_h_max and d.delta_h_max > 0 else DONNEES_ALLOUANE.depression_admissible,
            q_allouane_amont=q_all_am if q_all_am else DONNEES_ALLOUANE.q_allouane_amont,
            q_allouane_aval=q_all_av if q_all_av else DONNEES_ALLOUANE.q_allouane_aval,
            q_allouane_max=q_all_max,
        )

        # Stocker pour réutilisation dans _calculer (comparaison avec ce document)
        self.donnees_imp = donnees_imp

        # Mettre à jour les labels de référence avec les vraies valeurs du document
        self.lbl_q_all_am.configure(
            text=f"{donnees_imp.q_allouane_amont:,.1f}"
        )
        self.lbl_q_all_av.configure(
            text=f"{donnees_imp.q_allouane_aval:,.1f}"
        )
        self.lbl_q_all_max.configure(
            text=f"{donnees_imp.q_allouane_max:,.1f}"
        )

        self._afficher_alerte(
            f"Document importé : {nom_fichier}\n"
            f"Données extraites : {len(resultat.donnees_brutes)} paramètre(s).\n"
            f"Références Allouane mises à jour pour ce document.",
            niveau="info",
        )

        return donnees_imp

    # ------------------------------------------------------------------
    def _exporter_resultats_detailles(self) -> None:
        """Exporte les résultats détaillés du dernier recalcul vers XLSX."""
        if self.dernier_resultat is None:
            self._afficher_alerte(
                "Aucun résultat à exporter. Calculez d'abord avec le bouton "
                "« Recalculer (F10) et comparer ».",
                niveau="alerte",
            )
            return

        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="resultats_allouane_comparatif.xlsx",
        )
        if not chemin:
            return

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.utils import get_column_letter

            amont, aval = self.dernier_resultat["amont"], self.dernier_resultat["aval"]
            comparaisons = self.dernier_resultat["comparaisons"]

            wb = Workbook()

            # Feuille 1 : Résumé comparatif
            ws1 = wb.active
            ws1.title = "Comparatif Allouane vs App"
            ws1["A1"] = "Comparatif : Méthode ALLOUANE vs Méthode de l'app (F10)"
            ws1["A1"].font = Font(bold=True, size=12, color="1F3B5C")

            entetes = [
                "Tronçon",
                "Q Allouane (m³/h)",
                "Q App (m³/h)",
                "Écart absolu (m³/h)",
                "Écart (%)",
                "Statut",
            ]
            for c, h in enumerate(entetes, start=1):
                cell = ws1.cell(row=3, column=c, value=h)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F3B5C")
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for r, c in enumerate(comparaisons, start=4):
                valeurs = [
                    c.nom,
                    c.q_allouane_m3h,
                    c.q_app_m3h,
                    c.ecart_abs_m3h,
                    c.ecart_pct,
                    c.statut,
                ]
                for c2, val in enumerate(valeurs, start=1):
                    cell = ws1.cell(row=r, column=c2, value=val)
                    cell.alignment = Alignment(horizontal="center", vertical="center")

            for c, w in enumerate([40, 20, 20, 22, 18, 20], start=1):
                ws1.column_dimensions[get_column_letter(c)].width = w

            # Feuille 2 : Détails des calculs F10
            ws2 = wb.create_sheet("Détails F10")
            ws2["A1"] = "Détails des calculs F10 (méthode de l'application)"
            ws2["A1"].font = Font(bold=True, size=12, color="1F3B5C")

            entetes2 = [
                "Tronçon",
                "H motrice net (m)",
                "Longueur (m)",
                "Diamètre (m)",
                "K Strickler",
                "ξ",
                "Vitesse v (m/s)",
                "Débit Qair (m³/s)",
                "Débit Qair (m³/h)",
            ]
            for c, h in enumerate(entetes2, start=1):
                cell = ws2.cell(row=3, column=c, value=h)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F3B5C")
                cell.alignment = Alignment(horizontal="center", vertical="center")

            lignes = [
                [
                    amont.nom,
                    amont.h_motrice,
                    amont.longueur,
                    amont.diametre,
                    amont.coeff_rugosite,
                    amont.xi,
                    amont.vitesse,
                    amont.debit_m3s,
                    amont.debit_m3h,
                ],
                [
                    aval.nom,
                    aval.h_motrice,
                    aval.longueur,
                    aval.diametre,
                    aval.coeff_rugosite,
                    aval.xi,
                    aval.vitesse,
                    aval.debit_m3s,
                    aval.debit_m3h,
                ],
            ]
            for r, ligne in enumerate(lignes, start=4):
                for c2, val in enumerate(ligne, start=1):
                    cell = ws2.cell(row=r, column=c2, value=val)
                    cell.alignment = Alignment(horizontal="center", vertical="center")

            for c, w in enumerate([40, 16, 14, 14, 14, 10, 16, 18, 18], start=1):
                ws2.column_dimensions[get_column_letter(c)].width = w

            # Feuille 3 : Formules de calcul — origines et références
            ws3 = wb.create_sheet("Formules et références")
            ws3["A1"] = "Formules de calcul — Origines et références"
            ws3["A1"].font = Font(bold=True, size=12, color="1F3B5C")

            entetes3 = [
                "Formule",
                "Origine",
                "Référence",
                "Équation (clair)",
                "Forme générale",
                "Commentaires",
            ]
            for c, h in enumerate(entetes3, start=1):
                cell = ws3.cell(row=3, column=c, value=h)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F3B5C")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for r, f in enumerate(_FORMULES_REFERENCES, start=4):
                valeurs = [
                    f["nom"],
                    f["origine"],
                    f["reference"],
                    f["formule_clair"],
                    f["formule_generale"],
                    f["commentaires"],
                ]
                for c2, val in enumerate(valeurs, start=1):
                    cell = ws3.cell(row=r, column=c2, value=val)
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
                    cell.font = Font(size=9)

            for c, w in enumerate([34, 30, 30, 52, 42, 52], start=1):
                ws3.column_dimensions[get_column_letter(c)].width = w

            wb.save(str(chemin))

        except Exception as exc:
            messagebox.showerror(
                "Export impossible",
                f"Le fichier n'a pas pu être écrit :\n{exc}",
            )
            return

        self._afficher_alerte(
            f"Résultats détaillés exportés :\n{chemin}",
            niveau="info",
        )

    # ------------------------------------------------------------------
    def _exporter_rapport_docx(self) -> None:
        """Exporte un rapport DOCX détaillé de l'analyse Allouane vs App."""
        if self.dernier_resultat is None:
            self._afficher_alerte(
                "Aucun résultat à exporter. Calculez d'abord avec le bouton "
                "« Recalculer (F10) et comparer ».",
                niveau="alerte",
            )
            return

        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_allouane_comparatif.docx",
        )
        if not chemin:
            return

        try:
            amont = self.dernier_resultat["amont"]
            aval = self.dernier_resultat["aval"]
            comparaisons = self.dernier_resultat["comparaisons"]

            donnees_ref = self.donnees_imp if self.donnees_imp else DONNEES_ALLOUANE
            generer_rapport_allouane_docx(
                chemin,
                donnees=donnees_ref,
                amont=amont,
                aval=aval,
                comparaisons=comparaisons,
            )

        except Exception as exc:
            messagebox.showerror(
                "Export DOCX impossible",
                f"Le rapport n'a pas pu être généré :\n{exc}",
            )
            return

        self._afficher_alerte(
            f"Rapport DOCX généré :\n{chemin}",
            niveau="info",
        )

    # ------------------------------------------------------------------
    def synchroniser_depuis_projet(self) -> None:
        pass

    def restaurer(self) -> None:
        self._masquer_alerte()
        self.txt_res.delete("1.0", "end")
        self.dernier_resultat = None
        self.donnees_imp = None
        self.docx_source = None
        self.lbl_docx.configure(text="Aucun fichier DOCX importé", text_color="#757575")
        self.lbl_q_all_am.configure(text=f"{DONNEES_ALLOUANE.q_allouane_amont:,.1f}")
        self.lbl_q_all_av.configure(text=f"{DONNEES_ALLOUANE.q_allouane_aval:,.1f}")
        self.lbl_q_all_max.configure(text=f"{DONNEES_ALLOUANE.q_allouane_max:,.1f}")

        # Réinitialiser tous les champs de saisie aux valeurs par défaut
        self.ent_dh_brut.delete(0, "end")
        self.ent_dh_brut.insert(0, f"{DONNEES_ALLOUANE.delta_h_brut:g}")
        self.ent_l1.delete(0, "end")
        self.ent_l1.insert(0, f"{DONNEES_ALLOUANE.longueur_l1:g}")
        self.ent_dh_av.delete(0, "end")
        self.ent_dh_av.insert(0, f"{DONNEES_ALLOUANE.altitude_ve - DONNEES_ALLOUANE.altitude_vi2:g}")
        self.ent_l2.delete(0, "end")
        self.ent_l2.insert(0, f"{DONNEES_ALLOUANE.longueur_l2:g}")
        self.ent_diam.delete(0, "end")
        self.ent_diam.insert(0, f"{DONNEES_ALLOUANE.diametre_interieur:g}")
        self.ent_k.delete(0, "end")
        self.ent_k.insert(0, f"{DONNEES_ALLOUANE.rugosite_k:g}" if False else "104")
        self.ent_xi.delete(0, "end")
        self.ent_xi.insert(0, "2")
        self.ent_dep.delete(0, "end")
        self.ent_dep.insert(0, f"{DONNEES_ALLOUANE.depression_admissible:g}")
