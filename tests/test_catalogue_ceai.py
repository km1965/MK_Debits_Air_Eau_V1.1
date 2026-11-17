"""Tests du catalogue CEAI / TRIFON et des configurations d'équipement."""

from __future__ import annotations

import os
import tempfile
import unittest

from docx import Document as DocxDocument
from openpyxl import load_workbook

from debits_ae import (
    CONFIG_AUDIT,
    CONFIG_CEAI,
    CLAPETS_CEAI,
    PURGEURS_SONIQUES_SNH,
    VENTOUSES_TRIFON_CEAI,
    analyser_configurations,
    generer_rapport_docx,
    generer_rapport_xlsx,
)
from debits_ae.models import DonneesProjet


class TestCatalogueCEAI(unittest.TestCase):
    def test_tableaux_complets(self):
        self.assertEqual(len(VENTOUSES_TRIFON_CEAI), 8)
        self.assertEqual(len(CLAPETS_CEAI), 9)
        self.assertEqual(len(PURGEURS_SONIQUES_SNH), 8)

    def test_conversion_m3h_vers_m3s(self):
        self.assertAlmostEqual(VENTOUSES_TRIFON_CEAI[-1].capacite_m3s, 38000 / 3600)
        self.assertAlmostEqual(CLAPETS_CEAI[-1].capacite_m3s, 70600 / 3600)
        self.assertAlmostEqual(PURGEURS_SONIQUES_SNH[-1].capacite_m3s, 144 / 3600)

    def test_configurations_grand_debit(self):
        """Pour Qair = 19 m³/s, les deux configurations couvrent le débit."""
        configs = analyser_configurations(19.0)
        audit, ceai = configs[CONFIG_AUDIT], configs[CONFIG_CEAI]

        self.assertEqual(audit.ventouse.dn, "DN200")
        self.assertEqual(audit.ventouse.nombre, 5)
        self.assertEqual(audit.clapet.dn, "DN250")
        self.assertEqual(audit.clapet.nombre, 2)
        self.assertTrue(audit.couvert)

        self.assertEqual(ceai.ventouse.dn, "DN300")
        self.assertEqual(ceai.ventouse.nombre, 2)
        self.assertEqual(ceai.clapet.dn, "DN500")
        self.assertEqual(ceai.clapet.nombre, 1)
        self.assertTrue(ceai.couvert)

    def test_configurations_tres_grand_debit(self):
        configs = analyser_configurations(32.0)
        self.assertEqual(configs[CONFIG_CEAI].clapet.nombre, 2)
        self.assertEqual(configs[CONFIG_AUDIT].ventouse.nombre, 8)


class TestRapportConfigurationsCEAI(unittest.TestCase):
    def _donnees(self) -> DonneesProjet:
        donnees = DonneesProjet()
        donnees.debit_air_equipement = 19.0
        donnees.diam_conduit = 2.0
        return donnees

    def test_docx_contient_choix_et_purgeur(self):
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "rapport_ceai.docx")
            configuration = {
                "choix": CONFIG_CEAI,
                "configurations": analyser_configurations(19.0),
            }
            generer_rapport_docx(
                chemin,
                projet="Test CEAI",
                donnees=self._donnees(),
                configuration_equipements=configuration,
            )
            doc = DocxDocument(chemin)
            texte = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        texte += "\n" + cell.text
            self.assertIn("★ RETENU — " + CONFIG_CEAI, texte)
            self.assertIn("Purgeurs soniques SNH", texte)
            self.assertIn("DN1500", texte)
            self.assertIn("70600", texte)

    def test_xlsx_contient_feuille_configurations(self):
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "rapport_ceai.xlsx")
            configuration = {
                "choix": CONFIG_CEAI,
                "configurations": analyser_configurations(19.0),
            }
            generer_rapport_xlsx(
                chemin,
                projet="Test CEAI",
                donnees=self._donnees(),
                configuration_equipements=configuration,
            )
            wb = load_workbook(chemin)
            self.assertIn("Configurations Air", wb.sheetnames)
            ws = wb["Configurations Air"]
            valeurs = "\n".join(
                str(c.value) for row in ws.iter_rows() for c in row
                if c.value is not None
            )
            self.assertIn("Configuration retenue : " + CONFIG_CEAI, valeurs)
            self.assertIn("★ RETENU — " + CONFIG_CEAI, valeurs)
            self.assertIn("Purgeurs soniques SNH", valeurs)


if __name__ == "__main__":
    unittest.main()
