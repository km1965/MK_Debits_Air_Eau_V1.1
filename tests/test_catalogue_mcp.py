"""Tests du catalogue MCP adapte aux debits d'air calcules."""

from __future__ import annotations

import unittest

from debits_ae import (
    VENTOUSES_MCP,
    analyser_mcp,
    capacite_mcp_m3s,
    choix_ventouse_mcp,
    dns_mcp_pour_conduite,
    nombre_ventouses_mcp,
    resume_mcp,
)


class TestCatalogueMCP(unittest.TestCase):
    def test_donnees_courbes_constructeur(self):
        """Les valeurs relevees sur les courbes sont exactes."""
        self.assertAlmostEqual(capacite_mcp_m3s("DN80", "admission"), 0.62)
        self.assertAlmostEqual(capacite_mcp_m3s("DN80", "evacuation"), 0.77)
        self.assertAlmostEqual(capacite_mcp_m3s("DN100", "admission"), 1.20)
        self.assertAlmostEqual(capacite_mcp_m3s("DN100", "evacuation"), 1.55)
        self.assertAlmostEqual(capacite_mcp_m3s("DN80", "critique"), 1.70)

    def test_domaine_conduite(self):
        """Domaine d'application : conduites DN60 a DN500."""
        self.assertEqual(len(dns_mcp_pour_conduite(300)), 10)
        self.assertEqual(dns_mcp_pour_conduite(100), ("DN40", "DN50", "DN60/65", "DN80", "DN100"))
        self.assertEqual(dns_mcp_pour_conduite(800), ())
        self.assertEqual(dns_mcp_pour_conduite(2000), ())

    def test_choix_et_nombre(self):
        self.assertEqual(choix_ventouse_mcp(0.5).dn, "DN80")
        self.assertEqual(choix_ventouse_mcp(1.0).dn, "DN100")
        self.assertEqual(nombre_ventouses_mcp(2.5, "DN100"), 3)

    def test_analyse_hors_gamme(self):
        """Hors gamme, le plus grand DN est propose avec un cumul d'unites."""
        resultat = analyser_mcp(19.0, 2000.0, "admission")
        self.assertEqual(resultat.dn_propose, "DN300")
        self.assertEqual(resultat.nombre, 8)
        self.assertTrue(resultat.couvert)
        self.assertIn("hors domaine", resultat.avertissement)
        self.assertIn("DN300", resume_mcp(resultat))

    def test_table_complete(self):
        self.assertEqual(len(VENTOUSES_MCP), 10)
        for ventouse in VENTOUSES_MCP:
            self.assertGreater(ventouse.q_admission_m3s, 0)
            self.assertGreater(ventouse.q_evacuation_m3s, 0)
            self.assertGreater(ventouse.q_critique_m3s, ventouse.q_evacuation_m3s)


if __name__ == "__main__":
    unittest.main()
