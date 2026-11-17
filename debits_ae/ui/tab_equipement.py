"""Onglet 5 — Sélection d'équipement (tables PAM / SNH).

Compare le débit d'air calculé avec les caractéristiques des ventouses
triple fonction PAM et des clapets d'entrée d'air SNH. Le débit peut être
repris automatiquement du calcul le plus défavorable des trois fonctions.
"""

from __future__ import annotations

import customtkinter as ctk

from debits_ae.models import EquipementChoice
from debits_ae import (
    TABLE_PAM,
    TABLE_SNH,
    choix_ventouse_pam,
    choix_clapet_snh,
    VENTOUSES_MCP,
    analyser_mcp,
    resume_mcp,
)
from debits_ae.ui.base_tab import OngletProjet
from debits_ae.ui.widgets import LabeledEntry, CalcButton, ExportButton, AlerteFrame


class TabEquipement(OngletProjet):
    """Onglet Sélection d'équipement."""

    def _construire_interface(self) -> None:
        d = self.projet.donnees

        # --- Saisie ---
        frame_saisie = ctk.CTkFrame(self)
        frame_saisie.pack(side="top", fill="x", padx=15, pady=(15, 10))

        ctk.CTkLabel(
            frame_saisie,
            text="Sélection d'équipement — Comparaison avec les tables PAM / SNH",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille = ctk.CTkFrame(frame_saisie)
        grille.pack(fill="x", padx=10, pady=(0, 10))

        self.ent_debit = LabeledEntry(
            grille, "Débit d'air calculé Qair", default=f"{d.debit_air_equipement:g}", unit="m³/s",
            tooltip="Débit d'air à couvrir par l'équipement (m³/s).",
        )
        self.ent_debit.pack(side="left", padx=6, pady=4)

        ctk.CTkButton(
            grille,
            text="Reprendre le débit calculé",
            width=190,
            command=self._utiliser_debit_calcule,
        ).pack(side="left", padx=6, pady=4)

        CalcButton(frame_saisie, text="Sélectionner équipement", command=self._calculer).pack(
            anchor="e", padx=10, pady=(0, 10)
        )

        # --- Résultat PAM ---
        frame_pam = ctk.CTkFrame(self)
        frame_pam.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_pam,
            text="Ventouse triple fonction PAM (admission air, dépression 3 m)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1F3B5C",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.lbl_pam_resultat = ctk.CTkLabel(
            frame_pam, text="—", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_pam_resultat.pack(anchor="w", padx=10, pady=(0, 5))

        grille_pam = ctk.CTkFrame(frame_pam)
        grille_pam.pack(fill="x", padx=10, pady=(0, 10))
        for equip in TABLE_PAM:
            txt = (
                f"{equip.dn} : admission {equip.debit_admission_depression_3m_m3s} m³/s  |  "
                f"évacuation {equip.debit_evacuation_surpression_1m_m3h} m³/h"
            )
            if equip.dn == "DN200":
                converti = equip.debit_admission_converti_m3s
                txt += (
                    f"  |  conversion exacte {converti:.3f} m³/s "
                    f"(écart tableau {equip.ecart_conversion_m3s:+.3f} m³/s)"
                )
            ctk.CTkLabel(grille_pam, text=txt, anchor="w").pack(anchor="w", padx=10, pady=1)

        # --- Résultat SNH ---
        frame_snh = ctk.CTkFrame(self)
        frame_snh.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_snh,
            text="Clapet d'entrée d'air SNH (dépression 3 m)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1F3B5C",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.lbl_snh_resultat = ctk.CTkLabel(
            frame_snh, text="—", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_snh_resultat.pack(anchor="w", padx=10, pady=(0, 5))

        grille_snh = ctk.CTkFrame(frame_snh)
        grille_snh.pack(fill="x", padx=10, pady=(0, 10))
        for equip in TABLE_SNH:
            txt = f"{equip.dn} : admission {equip.debit_admission_depression_3m_m3s} m³/s"
            ctk.CTkLabel(grille_snh, text=txt, anchor="w").pack(anchor="w", padx=10, pady=1)

        # --- Catalogue MCP ---
        frame_mcp = ctk.CTkFrame(self)
        frame_mcp.pack(side="top", fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            frame_mcp,
            text="Catalogue MCP — ventouse double orifice 3 fonctions PN 10/16",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#6B4FA1",
        ).pack(anchor="w", padx=10, pady=(10, 5))

        grille_mcp = ctk.CTkFrame(frame_mcp)
        grille_mcp.pack(fill="x", padx=10, pady=(0, 4))

        self.ent_dn_conduite = LabeledEntry(
            grille_mcp, "DN conduite", default=f"{d.diam_conduit * 1000:g}", unit="mm",
            tooltip="DN de la conduite — domaine d'application MCP : DN60 à DN500.",
        )
        self.ent_dn_conduite.pack(side="left", padx=6, pady=4)

        self.lbl_mcp_resultat = ctk.CTkLabel(
            frame_mcp, text="—", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_mcp_resultat.pack(anchor="w", padx=10, pady=(0, 4))

        for equip in VENTOUSES_MCP:
            if equip.dn in ("DN80", "DN100", "DN300"):
                txt = (
                    f"{equip.dn} : admission {equip.q_admission_m3s:.2f} m³/s | "
                    f"évacuation {equip.q_evacuation_m3s:.2f} m³/s "
                    f"({equip.origine_capacite})"
                )
                ctk.CTkLabel(grille_mcp, text=txt, anchor="w").pack(
                    anchor="w", padx=10, pady=1
                )
        ctk.CTkLabel(
            frame_mcp,
            text="Capacités à 0,3 bar ; Débit critique DN80 à 0,92 bar : "
                 "1,70 m³/s (source : courbes constructeur).",
            anchor="w", font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=10, pady=(2, 8))

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
    def _debit_calcule(self) -> float:
        v = self.projet.ventouse
        if v is None:
            return 0.0
        return max(v.qair_degazage, v.qair_remplissage, v.qair_admission)

    def _utiliser_debit_calcule(self) -> None:
        debit = self._debit_calcule()
        if debit <= 0:
            self._afficher_alerte(
                "Aucun débit d'air calculé : renseignez d'abord les onglets 2, 3 ou 4.",
                niveau="attention",
            )
            return
        self.ent_debit.set_value(debit)
        self._afficher_alerte(
            f"Débit d'air repris du calcul le plus défavorable : {debit:.4f} m³/s.",
            niveau="info",
        )

    def _calculer(self) -> None:
        debit = self.ent_debit.get_value()

        if debit <= 0:
            self._afficher_alerte(
                "Veuillez saisir un débit d'air positif.", niveau="alerte"
            )
            return

        pam = choix_ventouse_pam(debit, fonction="admission")
        snh = choix_clapet_snh(debit)

        if pam:
            marge = pam.debit_admission_depression_3m_m3s - debit
            self.lbl_pam_resultat.configure(
                text=f"✔ Préconisation : Ventouse PAM {pam.dn} "
                f"(débit admis {pam.debit_admission_depression_3m_m3s} m³/s, "
                f"marge {marge:+.4f} m³/s)",
                text_color="#2E7D32",
            )
        else:
            self.lbl_pam_resultat.configure(
                text="✖ Aucun équipement PAM ne couvre ce débit (max DN200 : 4,165 m³/s).",
                text_color="#C62828",
            )

        if snh:
            marge = snh.debit_admission_depression_3m_m3s - debit
            self.lbl_snh_resultat.configure(
                text=f"✔ Préconisation : Clapet SNH {snh.dn} "
                f"(débit admis {snh.debit_admission_depression_3m_m3s} m³/s, "
                f"marge {marge:+.4f} m³/s)",
                text_color="#2E7D32",
            )
        else:
            self.lbl_snh_resultat.configure(
                text="✖ Aucun clapet SNH ne couvre ce débit (max DN250 : 13 m³/s).",
                text_color="#C62828",
            )

        dn_conduite = self.ent_dn_conduite.get_value() or None
        resultat_mcp = analyser_mcp(debit, dn_conduite, mode="admission")
        resume = resume_mcp(resultat_mcp)
        self.lbl_mcp_resultat.configure(
            text=("✔ " if resultat_mcp.couvert else "⚠ ") + resume,
            text_color="#2E7D32" if resultat_mcp.couvert else "#F57C00",
        )
        self.resultats_partages["catalogue_mcp"] = resultat_mcp

        msg = (
            f"Pour un débit d'air de {debit:.4f} m³/s : "
            f"PAM {pam.dn if pam else '—'}, SNH {snh.dn if snh else '—'}, "
            f"MCP {resultat_mcp.dn_propose or '—'} "
            f"×{resultat_mcp.nombre}."
        )
        self._afficher_alerte(msg, niveau="info")

        equipements: list[EquipementChoice] = []
        if pam:
            equipements.append(
                EquipementChoice(
                    "Ventouse PAM",
                    pam.dn,
                    pam.debit_admission_depression_3m_m3s,
                    pam.debit_admission_depression_3m_m3s - debit,
                    "admission",
                )
            )
        if snh:
            equipements.append(
                EquipementChoice(
                    "Clapet SNH",
                    snh.dn,
                    snh.debit_admission_depression_3m_m3s,
                    snh.debit_admission_depression_3m_m3s - debit,
                    "admission",
                )
            )

        self.projet.donnees.debit_air_equipement = debit
        self.projet.equipements = equipements
        self.resultats_partages["equipements"] = equipements
        self.notifier()

    def synchroniser_depuis_projet(self) -> None:
        debit = self.projet.donnees.debit_air_equipement
        if debit > 0:
            self.ent_debit.set_value(debit)

    def restaurer(self) -> None:
        self.synchroniser_depuis_projet()
        self._masquer_alerte()
        # Réaffiche la préconisation sauvegardée, sans recalcul.
        if self.projet.equipements:
            self._afficher_sauvegarde()
        else:
            self.lbl_pam_resultat.configure(text="—", text_color="#757575")
            self.lbl_snh_resultat.configure(text="—", text_color="#757575")

        resultat_mcp = self.resultats_partages.get("catalogue_mcp")
        if resultat_mcp:
            self.lbl_mcp_resultat.configure(
                text=("✔ " if resultat_mcp.couvert else "⚠ ")
                + resume_mcp(resultat_mcp),
                text_color="#2E7D32" if resultat_mcp.couvert else "#F57C00",
            )
        else:
            self.lbl_mcp_resultat.configure(text="—", text_color="#757575")

    def _afficher_sauvegarde(self) -> None:
        for eq in self.projet.equipements:
            if eq.type_equipement == "Ventouse PAM":
                self.lbl_pam_resultat.configure(
                    text=f"✔ Préconisation enregistrée : Ventouse PAM {eq.dn} "
                    f"(débit admis {eq.debit_admis} m³/s, marge {eq.marge:+.4f} m³/s)",
                    text_color="#2E7D32",
                )
            elif eq.type_equipement == "Clapet SNH":
                self.lbl_snh_resultat.configure(
                    text=f"✔ Préconisation enregistrée : Clapet SNH {eq.dn} "
                    f"(débit admis {eq.debit_admis} m³/s, marge {eq.marge:+.4f} m³/s)",
                    text_color="#2E7D32",
                )

    # ------------------------------------------------------------------
    def _exporter_docx(self) -> None:
        from debits_ae import generer_rapport_docx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile="rapport_equipement.docx",
        )
        if chemin:
            generer_rapport_docx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Sélection équipement",
                ventouse=self.projet.ventouse,
                donnees=self.projet.donnees,
                equipements=self.projet.equipements,
                inputs_resume=self.projet.resume_texte(),
                catalogue_mcp=self.resultats_partages.get("catalogue_mcp"),
            )

    def _exporter_xlsx(self) -> None:
        from debits_ae import generer_rapport_xlsx
        from tkinter import filedialog

        chemin = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="rapport_equipement.xlsx",
        )
        if chemin:
            generer_rapport_xlsx(
                chemin,
                projet=f"{self.projet.donnees.nom} — Sélection équipement",
                ventouse=self.projet.ventouse,
                donnees=self.projet.donnees,
                equipements=self.projet.equipements,
                inputs_resume=self.projet.resume_texte(),
                catalogue_mcp=self.resultats_partages.get("catalogue_mcp"),
            )
