"""Onglet 7 — Import des tableaux de dimensionnement (ventouses / vidanges).

Permet d'importer un fichier .xlsx calqué sur les modèles déposés à la racine
(*Tableau dimensionnement ventouses.png* et *vidanges.png*).
Les colonnes saisies par l'utilisateur sont lues ; les colonnes calculées
(dénivelée, pentes, débits d'air Q air pour les ventouses ; dénivelée,
diamètres pour les vidanges) sont remplies automatiquement par Python avec les
formules de l'application (F2, F8, F9, F10, F11).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import customtkinter as ctk

from debits_ae.models import DonneesProjet
from debits_ae import (
    importer_tableau,
    exporter_resultat_tableau,
    MODELES_DISPONIBLES,
    verifier_contre_audit,
)
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import CalcButton, ExportButton, AlerteFrame


class TabImportTableau(OngletProjet):
    """Onglet Import des tableaux de dimensionnement."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        ctk.CTkLabel(
            self,
            text="Import des tableaux de dimensionnement (ventouses / vidanges)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            self,
            text="Importez un fichier .xlsx calqué sur les modèles de la racine. "
            "Les colonnes saisies par l'utilisateur sont lues ; les colonnes "
            "calculées (dénivelée, pentes, Q air / diamètres) sont remplies "
            "automatiquement par Python.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#757575",
            wraplength=950,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # --- Choix du modèle ---
        frame_modele = ctk.CTkFrame(self)
        frame_modele.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_modele, text="Modèle de tableau :", width=150
        ).pack(side="left", padx=6, pady=6)
        self.var_modele = tk.StringVar(value="Détection automatique")
        modeles = ["Détection automatique"] + [m.nom for m in MODELES_DISPONIBLES]
        self.combo_modele = ctk.CTkComboBox(
            frame_modele,
            values=modeles,
            variable=self.var_modele,
            width=320,
        )
        self.combo_modele.pack(side="left", padx=6, pady=6)

        ctk.CTkButton(
            frame_modele,
            text="Exemple de fichier",
            command=self._ouvrir_exemple,
            width=130,
        ).pack(side="left", padx=6, pady=6)

        # --- Import ---
        frame_import = ctk.CTkFrame(self)
        frame_import.pack(side="top", fill="x", padx=15, pady=(0, 10))

        CalcButton(
            frame_import,
            text="Importer un fichier .xlsx…",
            command=self._importer,
        ).pack(side="left", padx=10, pady=6)

        ExportButton(
            frame_import,
            text="Exporter le résultat (XLSX)",
            command=self._exporter_resultat,
            fmt="xlsx",
        ).pack(side="left", padx=10, pady=6)

        # --- Aperçu des résultats ---
        frame_apercu = ctk.CTkFrame(self)
        frame_apercu.pack(side="top", fill="both", expand=True, padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_apercu,
            text="Aperçu des lignes importées et calculées :",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.txt_apercu = ctk.CTkTextbox(frame_apercu, height=260)
        self.txt_apercu.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Alerte ---
        self.frame_alerte = AlerteFrame(self, message="", niveau="info")
        self.frame_alerte.pack(side="top", fill="x", padx=15, pady=(0, 10))
        self.frame_alerte.pack_forget()

        self.resultat_import = None
        self.chemin_resultat = None

    # ------------------------------------------------------------------
    def _ouvrir_exemple(self) -> None:
        """Ouvre le fichier exemple associé au modèle sélectionné."""
        nom = self.var_modele.get()
        modele = next((m for m in MODELES_DISPONIBLES if m.nom == nom), None)
        if not modele:
            return
        exemple = Path(modele.fichier_exemple)
        if not exemple.exists():
            # Cherche aussi à la racine du projet
            exemple = Path.cwd() / modele.fichier_exemple
        if exemple.exists():
            import os
            os.startfile(str(exemple))
        else:
            messagebox.showwarning(
                "Exemple introuvable",
                f"Le fichier exemple {modele.fichier_exemple} est introuvable.",
            )

    # ------------------------------------------------------------------
    def _importer(self) -> None:
        chemin = filedialog.askopenfilename(
            title="Importer un tableau de dimensionnement",
            filetypes=[("Classeur Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return

        try:
            modele = self.var_modele.get()
            modele_none = None if modele == "Détection automatique" else modele
            resultat = importer_tableau(
                chemin,
                modele_none,
                self.projet.donnees,
            )
        except Exception as exc:
            messagebox.showerror(
                "Import impossible",
                f"Le fichier n'a pas pu être lu :\n{exc}",
            )
            return

        self.resultat_import = resultat
        self.resultats_partages["tableau_import"] = resultat

        # Vérification contre l'audit
        ecarts = verifier_contre_audit(resultat)
        self.resultats_partages["ecarts_audit"] = ecarts

        if resultat.avertissements:
            self._afficher_alerte(
                "\n".join(f"• {a}" for a in resultat.avertissements),
                niveau="attention",
            )
        else:
            self._masquer_alerte()

        self._afficher_aperçu(resultat)

        msg = (
            f"Import terminé : {resultat.lignes_traitees} ligne(s) traitée(s) "
            f"sur {resultat.lignes_lues} lue(s).\n"
            f"Modèle : {resultat.modele}."
        )
        self._afficher_alerte(msg, niveau="info")

    # ------------------------------------------------------------------
    def _afficher_aperçu(self, resultat: ResultatImportTableau) -> None:
        self.txt_apercu.delete("1.0", "end")
        lignes = [
            f"Modèle : {resultat.modele}",
            f"Lignes lues : {resultat.lignes_lues} | traitées : {resultat.lignes_traitees}",
            "",
        ]

        if "ventouse" in resultat.modele.lower():
            for l in resultat.lignes_ventouse[:20]:
                lignes.append(
                    f"PM {l.pm} | H motrice ≈ {l.qair_amont is not None} | "
                    f"Qair amont = {l.qair_amont:.3f} m3/s | "
                    f"Qair aval = {l.qair_aval:.3f} m3/s | "
                    f"Pente amont = {l.pente_amont:.5f} | "
                    f"Pente aval = {l.pente_aval:.5f}"
                )
        else:
            for l in resultat.lignes_vidange[:20]:
                lignes.append(
                    f"Vidange {l.pm_am} | Dénivelée amont = {l.denivelee_amont:.2f} m | "
                    f"Dénivelée aval = {l.denivelee_aval:.2f} m | "
                    f"Ø t=2h = {l.diametre_t2h:.1f} mm | "
                    f"Ø retenu = {l.diametre_retenu_t2h:.1f} mm"
                )

        if len(resultat.lignes_ventouse) > 20 or len(resultat.lignes_vidange) > 20:
            lignes.append(f"\n... et {max(len(resultat.lignes_ventouse), len(resultat.lignes_vidange)) - 20} ligne(s) supplémentaire(s).")

        # Vérification contre l'audit
        ecarts = verifier_contre_audit(resultat)
        if ecarts:
            lignes.append("")
            lignes.append("=== VÉRIFICATION CONTRE L'AUDIT ===")
            for e in ecarts:
                lignes.append(
                    f"  PM {e.pm} ({e.domaine}) : "
                    f"calculé={e.valeur_calculee}, ref audit={e.valeur_reference}, "
                    f"écart={e.ecart_pct:+.1f}% -> {e.statut}"
                )
        else:
            lignes.append("")
            lignes.append("Aucune référence d'audit trouvée pour ces PM.")

        self.txt_apercu.insert("1.0", "\n".join(lignes))

    # ------------------------------------------------------------------
    def _exporter_resultat(self) -> None:
        if self.resultat_import is None:
            self._afficher_alerte(
                "Aucun résultat à exporter. Importez d'abord un fichier.",
                niveau="alerte",
            )
            return

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Classeur Excel", "*.xlsx")],
            initialfile="tableau_dimensionnement_resultat.xlsx",
        )
        if not chemin:
            return

        try:
            exporter_resultat_tableau(self.resultat_import, chemin)
        except Exception as exc:
            messagebox.showerror(
                "Export impossible",
                f"Le fichier n'a pas pu être écrit :\n{exc}",
            )
            return

        self.chemin_resultat = Path(chemin)
        self._afficher_alerte(
            f"Résultat exporté :\n{chemin}",
            niveau="info",
        )

    # ------------------------------------------------------------------
    def synchroniser_depuis_projet(self) -> None:
        pass

    def restaurer(self) -> None:
        self._masquer_alerte()
        self.txt_apercu.delete("1.0", "end")
        self.resultat_import = None
