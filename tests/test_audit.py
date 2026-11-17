"""Tests des données d'audit et du comparatif « note initiale / note corrigée ».

Vérifie :
- les données des Annexes 1 (points hauts) et 2 (vidanges) de l'audit ;
- les propriétés couvre_note / couvre_corrige ;
- les 4 points hauts sous-équipés dans la note initiale, tous couverts après correction ;
- la présence du comparatif dans les rapports DOCX et XLSX générés.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from docx import Document as DocxDocument
from openpyxl import load_workbook

from debits_ae import audit as audit_data
from debits_ae import generer_rapport_docx, generer_rapport_xlsx
from debits_ae.models import DonneesProjet, Projet, VentouseResult, VidangeResult


class TestComparatifPointsHauts(unittest.TestCase):
    """Annexe 1 corrigée : points hauts."""

    def test_nombre_lignes(self):
        self.assertEqual(len(audit_data.COMPARATIF_POINTS_HAUTS), 10)

    def test_proprietes_couvre(self):
        """Chaque ligne expose couvre_note et couvre_corrige."""
        for ligne in audit_data.COMPARATIF_POINTS_HAUTS:
            self.assertIsInstance(ligne.couvre_note, bool)
            self.assertIsInstance(ligne.couvre_corrige, bool)
            self.assertIsInstance(ligne.verdict_note, str)
            self.assertIsInstance(ligne.verdict_corrige, str)

    def test_quatre_sous_equipes_note_initiale(self):
        """Les 4 points hauts signalés par l'audit sont sous-équipés dans la note."""
        sous_equipes = audit_data.points_hauts_sous_equipes()
        pms = sorted(ligne.pm for ligne in sous_equipes)
        self.assertEqual(
            pms,
            sorted(
                [
                    "51 041,59",
                    "51 801,59",
                    "53 561,59",
                    "57 121,59",
                ]
            ),
        )

    def test_tous_couverts_apres_correction(self):
        """Après correction, tous les points hauts sont couverts par l'audit."""
        non_couverts = audit_data.points_hauts_non_couverts_apres_correction()
        self.assertEqual(len(non_couverts), 0)
        for ligne in audit_data.COMPARATIF_POINTS_HAUTS:
            self.assertTrue(ligne.couvre_corrige)

    def test_combinaisons_reelles(self):
        """Les combinaisons réelles couvrent le débit (ex. 2 PAM DN200 + 1 SNH DN250 = 21,33)."""
        combos = {c.libelle: c.capacite_m3s for c in audit_data.COMBINAISONS_EQUIPEMENTS}
        self.assertAlmostEqual(combos["2 ventouses PAM DN200 + 1 clapet SNH DN250"], 21.33, delta=0.01)
        self.assertAlmostEqual(combos["2 ventouses PAM DN200 + 3 clapets SNH DN250"], 47.33, delta=0.01)
        self.assertAlmostEqual(combos["1 ventouse PAM DN200 + 1 clapet SNH DN250"], 17.17, delta=0.01)
        self.assertAlmostEqual(combos["2 ventouses PAM DN200"], 8.33, delta=0.01)

    def test_resume_points_hauts(self):
        resume = audit_data.resume_points_hauts()
        self.assertEqual(resume["total"], 10)
        self.assertEqual(resume["sous_equipes_note"], 4)
        self.assertEqual(resume["couverts_note"], 6)
        self.assertEqual(resume["non_couverts_apres_correction"], 0)
        self.assertEqual(resume["couverts_apres_correction"], 10)


class TestComparatifVidanges(unittest.TestCase):
    """Annexe 2 corrigée : vidanges."""

    def test_nombre_lignes(self):
        self.assertEqual(len(audit_data.COMPARATIF_VIDANGES), 9)

    def test_cas_critiques(self):
        """PM 52 621,59 et PM 58 721,59 sont les cas critiques de l'audit."""
        sous_dim = [l for l in audit_data.COMPARATIF_VIDANGES if l.statut == "Sous-dimensionné"]
        self.assertEqual([l.pm for l in sous_dim], ["52 621,59"])
        limite = [l for l in audit_data.COMPARATIF_VIDANGES if l.statut == "Limite"]
        self.assertEqual([l.pm for l in limite], ["58 721,59"])

    def test_pm_59_701_59_ecart(self):
        """PM 59 701,59 : d de la note surévalué (442,29 vs 312,7 mm)."""
        ligne = next(l for l in audit_data.COMPARATIF_VIDANGES if l.pm == "59 701,59")
        self.assertAlmostEqual(ligne.diametre_note_mm, 442.29, places=1)
        self.assertAlmostEqual(ligne.diametre_corrige_mm, 312.7, places=1)
        self.assertAlmostEqual(ligne.ecart_mm, 129.6, places=1)

    def test_resume_vidanges(self):
        resume = audit_data.resume_vidanges()
        self.assertEqual(resume["total"], 9)


class TestCorrectionsAudit(unittest.TestCase):
    """Inventaire des corrections de l'audit."""

    def test_toutes_appliquees(self):
        non_appliquees = audit_data.corrections_non_appliquees()
        self.assertEqual(len(non_appliquees), 0)

    def test_corrections_presentes(self):
        codes = {c.code for c in audit_data.CORRECTIONS_AUDIT}
        self.assertIn("C1", codes)  # F2 coefficient 6,69
        self.assertIn("C5", codes)  # F5 Saint-Venant 499/129
        self.assertIn("C10", codes)  # conversion PAM DN200
        self.assertIn("C12", codes)  # 4 points hauts sous-équipés


class TestRapportContientAudit(unittest.TestCase):
    """Le comparatif audit doit apparaître dans les rapports DOCX et XLSX."""

    def _projet_avec_admission(self) -> Projet:
        donnees = DonneesProjet(
            nom="Test audit",
            diam_conduit=2.0,
            longueur_troncon=848.3,
            cote_ventouse=112.98,
            cote_vidange=99.05,
            coeff_rugosite=104.0,
            coeff_singularites=2.0,
        )
        ventouse = VentouseResult(
            hauteur_motrice=10.93,
            vitesse_vidange=6.0404,
            q_eau_vidange=18.976,
            qair_admission=18.976,
            coeff_singularites=2.0,
        )
        projet = Projet(donnees=donnees, ventouse=ventouse)
        projet.vidange = VidangeResult(diametre_vidange=352.28)
        return projet

    def test_docx_contient_comparatif(self):
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "rapport_audit.docx")
            projet = self._projet_avec_admission()
            generer_rapport_docx(
                chemin,
                projet="Test audit",
                vidange=projet.vidange,
                ventouse=projet.ventouse,
                donnees=projet.donnees,
                inputs_resume=projet.resume_texte(),
            )
            doc = DocxDocument(chemin)
            texte = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        texte += "\n" + cell.text
            self.assertIn("Audit et comparatif note initiale / note corrigée", texte)
            self.assertIn("51 041,59", texte)
            self.assertIn("51 801,59", texte)
            self.assertIn("53 561,59", texte)
            self.assertIn("57 121,59", texte)
            self.assertIn("6,69", texte)
            self.assertIn("13,39", texte)
            self.assertIn("14 454", texte)
            self.assertIn("4,015", texte)
            self.assertIn("4,165", texte)
            self.assertIn("381,6", texte)

    def test_xlsx_contient_comparatif(self):
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "rapport_audit.xlsx")
            projet = self._projet_avec_admission()
            generer_rapport_xlsx(
                chemin,
                projet="Test audit",
                vidange=projet.vidange,
                ventouse=projet.ventouse,
                donnees=projet.donnees,
                inputs_resume=projet.resume_texte(),
            )
            wb = load_workbook(chemin)
            self.assertIn("Comparatif Points Hauts", wb.sheetnames)
            self.assertIn("Comparatif Vidanges", wb.sheetnames)
            self.assertIn("Corrections Audit", wb.sheetnames)
            ws = wb["Comparatif Points Hauts"]
            cellules = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
            self.assertTrue(any("51 801,59" in c for c in cellules))
            self.assertTrue(any("57 121,59" in c for c in cellules))


if __name__ == "__main__":
    unittest.main()
