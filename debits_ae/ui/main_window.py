"""Fenêtre principale de l'application MK_Debits_Air_Eau.

Interface CustomTkinter avec 6 onglets et un bandeau projet :
1. Vidanges (points bas)
2. Ventouse — Dégazage (1ère fonction)
3. Ventouse — Remplissage (2ème fonction)
4. Ventouse — Admission d'air (3ème fonction)
5. Sélection équipement (PAM / SNH)
6. Synthèse, Vérifications & Rapport

Le bandeau projet permet de créer, ouvrir et enregistrer un dossier
`.mkprojet` : les données et les résultats sont partagés par tous les onglets.
"""

from __future__ import annotations

import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from debits_ae.models import Projet
from debits_ae.project_io import charger_projet, sauvegarder_projet
from debits_ae.formulas import formules_a_risque
from debits_ae.import_xlsx import importer_xlsx
from debits_ae.resources import chemin_ressource
from debits_ae.ui.tab_vidanges import TabVidanges
from debits_ae.ui.tab_ventouse_degazage import TabVentouseDegazage
from debits_ae.ui.tab_ventouse_remplissage import TabVentouseRemplissage
from debits_ae.ui.tab_ventouse_admission import TabVentouseAdmission
from debits_ae.ui.tab_equipement import TabEquipement
from debits_ae.ui.tab_verification import TabVerification
from debits_ae.ui.tab_import_tableau import TabImportTableau
from debits_ae.ui.tab_analyse_allouane import TabAnalyseAllouane


class MainWindow(ctk.CTk):
    """Fenêtre principale de l'application."""

    def __init__(self) -> None:
        super().__init__()

        self.title("MK_Debits_Air_Eau — Calcul des débits air et eau")
        self.geometry("1220x820")
        self.minsize(1080, 700)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._appliquer_icone()

        # --- Source de vérité unique ---
        self.projet = Projet()
        self.resultats_partages: dict = {}
        self._chemin_projet: Path | None = None
        self._onglets: list = []

        self._construire_interface()
        self._maj_titre()
        self._rafraichir_synthese()

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _appliquer_icone(self) -> None:
        """Applique l'icône de l'application (barre de titre, barre des tâches)."""
        ico = chemin_ressource("assets", "icon.ico")
        if ico is not None:
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass

        png = chemin_ressource("assets", "icon.png")
        if png is not None:
            try:
                # La référence doit être conservée pour éviter le ramasse-miettes.
                self._icone_tk = tk.PhotoImage(file=str(png))
                self.iconphoto(True, self._icone_tk)
            except Exception:
                pass

    def _construire_interface(self) -> None:
        self._construire_bandeau()
        self._construire_onglets()
        self._construire_pied()

    def _construire_bandeau(self) -> None:
        self.header = ctk.CTkFrame(self, height=104, corner_radius=0)
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)

        # Ligne 1 — titre
        ligne1 = ctk.CTkFrame(self.header, fg_color="transparent")
        ligne1.pack(fill="x", padx=16, pady=(8, 0))

        ctk.CTkLabel(
            ligne1,
            text="MK_Debits_Air_Eau",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4DA3FF",
        ).pack(side="left")

        ctk.CTkLabel(
            ligne1,
            text="Calcul des débits air et eau — Points bas et hauts",
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e",
        ).pack(side="left", padx=(14, 0))

        self.lbl_statut = ctk.CTkLabel(
            ligne1, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#757575"
        )
        self.lbl_statut.pack(side="right")

        # Ligne 2 — projet + actions
        ligne2 = ctk.CTkFrame(self.header, fg_color="transparent")
        ligne2.pack(fill="x", padx=16, pady=(2, 8))

        ctk.CTkLabel(ligne2, text="Projet :", font=ctk.CTkFont(size=12)).pack(side="left")

        self.var_nom = tk.StringVar(value=self.projet.donnees.nom)
        self.var_nom.trace_add("write", self._nom_projet_modifie)
        ctk.CTkEntry(ligne2, textvariable=self.var_nom, width=300, height=28).pack(
            side="left", padx=(6, 14)
        )

        for texte, commande, largeur in [
            ("Nouveau", self._nouveau_projet, 90),
            ("Ouvrir…", self._ouvrir_projet, 90),
            ("Enregistrer", self._enregistrer_projet, 105),
            ("Enregistrer sous…", self._enregistrer_sous, 140),
        ]:
            ctk.CTkButton(
                ligne2,
                text=texte,
                command=commande,
                width=largeur,
                height=28,
                fg_color="#1F3B5C",
                hover_color="#154a7a",
            ).pack(side="left", padx=4)

        ctk.CTkButton(
            ligne2,
            text="Importer XLSX…",
            command=self._importer_xlsx,
            width=115,
            height=28,
            fg_color="#6B4FA1",
            hover_color="#5A3D8F",
        ).pack(side="left", padx=(10, 4))

    def _construire_onglets(self) -> None:
        self.tabview = ctk.CTkTabview(self, width=1080, height=680)
        self.tabview.pack(side="top", fill="both", expand=True, padx=10, pady=(6, 6))

        self.tab_vidanges = TabVidanges(
            self.tabview.add("1 — Vidanges (points bas)"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_degazage = TabVentouseDegazage(
            self.tabview.add("2 — Ventouse — Dégazage"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_remplissage = TabVentouseRemplissage(
            self.tabview.add("3 — Ventouse — Remplissage"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_admission = TabVentouseAdmission(
            self.tabview.add("4 — Ventouse — Admission"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_equipement = TabEquipement(
            self.tabview.add("5 — Sélection équipement"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_verification = TabVerification(
            self.tabview.add("6 — Synthèse & Rapport"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_import_tableau = TabImportTableau(
            self.tabview.add("7 — Import tableaux modèles"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )
        self.tab_analyse_allouane = TabAnalyseAllouane(
            self.tabview.add("8 — Comparaison Allouane / App"),
            self.resultats_partages,
            self.projet,
            self._rafraichir_synthese,
        )

        self._onglets = [
            self.tab_vidanges,
            self.tab_degazage,
            self.tab_remplissage,
            self.tab_admission,
            self.tab_equipement,
            self.tab_verification,
            self.tab_import_tableau,
            self.tab_analyse_allouane,
        ]

    def _construire_pied(self) -> None:
        self.footer = ctk.CTkFrame(self, height=28, corner_radius=0)
        self.footer.pack(side="bottom", fill="x")
        self.footer.pack_propagate(False)

        ctk.CTkLabel(
            self.footer,
            text="Formules conformes à la note « Calcul des débits points bas et hauts.pdf » — "
            "Les statuts SUSPECT / À VÉRIFIER / ILLISIBLE sont signalés dans l'onglet 6.",
            font=ctk.CTkFont(size=10),
            text_color="#9e9e9e",
        ).pack(pady=5)

    # ------------------------------------------------------------------
    # Synthèse / titre
    # ------------------------------------------------------------------
    def _nom_projet_modifie(self, *_args: object) -> None:
        nom = self.var_nom.get().strip() or "Projet sans nom"
        self.projet.donnees.nom = nom
        if hasattr(self, "tab_verification"):
            self.tab_verification.rafraichir_synthese()
        self._maj_titre()

    def _rafraichir_synthese(self) -> None:
        if hasattr(self, "tab_verification"):
            self.tab_verification.rafraichir_synthese()

        alertes = formules_a_risque(self.projet)
        if alertes:
            self.lbl_statut.configure(
                text=f"⚠ {len(alertes)} formule(s) à valider",
                text_color="#EF6C00",
            )
        else:
            etapes = self.projet.etapes()
            faites = sum(1 for fait in etapes.values() if fait)
            self.lbl_statut.configure(
                text=f"{faites}/{len(etapes)} étapes calculées",
                text_color="#2E7D32" if faites else "#757575",
            )

    def _maj_titre(self) -> None:
        nom = self.projet.donnees.nom or "Projet sans nom"
        suffixe = f" — {self._chemin_projet.name}" if self._chemin_projet else ""
        self.title(f"{nom} — MK_Debits_Air_Eau{suffixe}")

    # ------------------------------------------------------------------
    # Gestion du dossier projet
    # ------------------------------------------------------------------
    def _nouveau_projet(self) -> None:
        if not messagebox.askyesno(
            "Nouveau projet",
            "Réinitialiser le dossier courant ? Les résultats non enregistrés seront perdus.",
        ):
            return
        self._charger_dans_interface(Projet())
        self._chemin_projet = None
        self._maj_titre()
        self._rafraichir_synthese()
        messagebox.showinfo("Nouveau projet", "Un nouveau dossier vierge a été créé.")

    def _ouvrir_projet(self) -> None:
        chemin = filedialog.askopenfilename(
            title="Ouvrir un dossier projet",
            filetypes=[("Projet MK_Debits_Air_Eau", "*.mkprojet"), ("JSON", "*.json")],
        )
        if not chemin:
            return
        try:
            projet = charger_projet(chemin)
        except Exception as exc:  # fichier corrompu ou mauvais format
            messagebox.showerror("Ouverture impossible", f"Le fichier n'a pas pu être lu :\n{exc}")
            return

        self._charger_dans_interface(projet)
        self._chemin_projet = Path(chemin)
        self._maj_titre()
        self._rafraichir_synthese()
        messagebox.showinfo(
            "Dossier ouvert",
            f"Dossier chargé :\n{chemin}\n\n{projet.prochaine_etape()}",
        )

    def _enregistrer_projet(self) -> None:
        if self._chemin_projet is None:
            self._enregistrer_sous()
            return
        self._ecrire_projet(self._chemin_projet)

    def _enregistrer_sous(self) -> None:
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", self.projet.donnees.nom).strip("_") or "projet"
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer le dossier projet",
            defaultextension=".mkprojet",
            filetypes=[("Projet MK_Debits_Air_Eau", "*.mkprojet"), ("JSON", "*.json")],
            initialfile=f"{slug}.mkprojet",
        )
        if chemin:
            self._ecrire_projet(Path(chemin))

    def _ecrire_projet(self, chemin: Path) -> None:
        try:
            final = sauvegarder_projet(self.projet, chemin)
        except Exception as exc:
            messagebox.showerror("Enregistrement impossible", f"Le dossier n'a pas pu être écrit :\n{exc}")
            return
        self._chemin_projet = final
        self._maj_titre()
        messagebox.showinfo("Dossier enregistré", f"Dossier sauvegardé :\n{final}")

    # ------------------------------------------------------------------
    # Import d'un fichier de vérification .xlsx externe
    # ------------------------------------------------------------------
    def _importer_xlsx(self) -> None:
        """Ouvre un classeur .xlsx externe, en extrait les données d'entrée,
        les fait recalculer par les formules de l'app et recharge l'interface."""
        chemin = filedialog.askopenfilename(
            title="Importer un fichier de vérification .xlsx",
            filetypes=[("Classeur Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
        )
        if not chemin:
            return

        try:
            resultat = importer_xlsx(chemin)
        except Exception as exc:
            messagebox.showerror(
                "Import impossible",
                f"Le fichier n'a pas pu être lu :\n{exc}",
            )
            return

        if resultat.projet is None:
            messagebox.showerror(
                "Import impossible",
                "Aucune donnée exploitable n'a été trouvée dans le classeur.\n"
                "Vérifiez que les colonnes utilisent des libellés reconnaissables "
                "(ex. « Diamètre conduit », « Longueur tronçon », « Cote ventouse »…).",
            )
            return

        # Construit le message récapitulatif de ce qui a été importé.
        d = resultat.projet.donnees
        lignes = [
            f"Projet : {d.nom}",
            f"Conduite : D = {d.diam_conduit:.3f} m ; L = {d.longueur_troncon:.1f} m ; "
            f"h = {d.hauteur_eau:.2f} m ; pente = {d.pente:.5f} m/m.",
            f"Cotes : ventouse = {d.cote_ventouse:.2f} m ; vidange = {d.cote_vidange:.2f} m.",
            f"Coefficients : K Strickler = {d.coeff_rugosite:g} ; ξ = {d.coeff_singularites:g}.",
        ]
        if resultat.projet.vidange is not None:
            v = resultat.projet.vidange
            lignes.append(
                f"Vidange (F1/F2) : Q = {v.debit_decharge:.4f} m³/s ; "
                f"diamètre = {v.diametre_vidange:.1f} mm."
            )
        if resultat.projet.ventouse is not None:
            v = resultat.projet.ventouse
            lignes.append(
                f"Ventouse : H = {v.hauteur_motrice:.3f} m ; "
                f"v = {v.vitesse_vidange:.3f} m/s ; Qair admission = {v.qair_admission:.4f} m³/s."
            )
        if resultat.avertissements:
            lignes.append("")
            lignes.append("Avertissements :")
            lignes.extend(f"• {a}" for a in resultat.avertissements)

        # Recharge l'interface avec le projet importé (données + résultats recalculés).
        self._charger_dans_interface(resultat.projet)
        self._chemin_projet = None  # pas encore de dossier .mkprojet associé
        self._maj_titre()
        self._rafraichir_synthese()

        messagebox.showinfo(
            "Import XLSX terminé",
            "Les données du fichier externe ont été lues et recalculées "
            "avec les formules de MK_Debits_Air_Eau.\n\n" + "\n".join(lignes),
        )

    def _charger_dans_interface(self, projet: Projet) -> None:
        """Remplace le projet courant et recharge tous les onglets."""
        self.projet = projet
        self.resultats_partages = {}

        # Bloque la trace pendant la mise à jour du champ nom.
        nom = projet.donnees.nom
        if hasattr(self, "var_nom"):
            self.var_nom.set(nom)
        projet.donnees.nom = nom

        for onglet in self._onglets:
            onglet.projet = projet
            onglet.resultats_partages = self.resultats_partages
            onglet.restaurer()

        if hasattr(self, "tab_verification"):
            self.tab_verification.rafraichir_synthese()
