"""Tests de non-régression des formules MK_Debits_Air_Eau.

Références : Note_Verification_Hydraulique_AEP_Complete.docx
  * Partie 2 : coefficient 6,693 (et non 13,39) pour une vidange en 2 h.
  * Partie 3 : célérité d'Allievi a = 9900 / √(48,3 + k·D/e).
  * Partie 1 : loi de Saint-Venant, tableau de référence (s = 1 m²).

Lancement :
    python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

from debits_ae.formulas import (
    celerite_allievi,
    diametre_orifice_degazage,
    diametre_vidange_2h,
    formules_a_risque,
    pente_strickler,
    qair_admission_casse,
    qair_degazage,
    qair_evacuation_air_saint_venant,
)
from debits_ae.models import (
    DonneesProjet,
    Projet,
    VentouseResult,
    VidangeResult,
    STATUT_COHERENT,
)
from debits_ae.project_io import charger_projet, sauvegarder_projet


class TestVidange(unittest.TestCase):
    def test_coefficient_6693_pour_2h(self):
        # D = 1 m, L = 1 m, h = 1 m : d(mm) = coefficient.
        d_mm, alerte = diametre_vidange_2h(1.0, 1.0, 1.0, temps_vidange_h=2.0)
        self.assertAlmostEqual(d_mm, 6.693, places=3)
        self.assertFalse(alerte)

    def test_coefficient_1339_pour_30min(self):
        # Le 13,39 du PDF correspond à 30 min : il ne doit pas être utilisé par défaut.
        d_mm, _ = diametre_vidange_2h(1.0, 1.0, 1.0, temps_vidange_h=0.5)
        self.assertAlmostEqual(d_mm, 13.386, places=2)

    def test_valeurs_invalides(self):
        d_mm, alerte = diametre_vidange_2h(0.0, 100.0, 1.0)
        self.assertEqual(d_mm, 0.0)
        self.assertTrue(alerte)


class TestSaintVenant(unittest.TestCase):
    """Tableau de référence de la note (section s = 1 m²)."""

    def test_subsonique_2_mce(self):
        q, alerte = qair_evacuation_air_saint_venant(1.0, p2_mce=12.33)
        self.assertAlmostEqual(q, 97.6, delta=0.5)
        self.assertFalse(alerte)

    def test_subsonique_5_mce(self):
        q, _ = qair_evacuation_air_saint_venant(1.0, p2_mce=15.33)
        self.assertAlmostEqual(q, 122.9, delta=0.5)

    def test_sonique_10_mce(self):
        q, _ = qair_evacuation_air_saint_venant(1.0, p2_mce=20.33)
        self.assertAlmostEqual(q, 129.1, delta=0.1)

    def test_sonique_plafonne(self):
        for p2 in (40.33, 90.33):
            q, _ = qair_evacuation_air_saint_venant(1.0, p2_mce=p2)
            self.assertAlmostEqual(q, 129.1, delta=0.1)

    def test_section_nulle(self):
        q, _ = qair_evacuation_air_saint_venant(0.0, p2_mce=15.33)
        self.assertEqual(q, 0.0)


class TestAllievi(unittest.TestCase):
    def test_fonte_ductile(self):
        # k = 0,6 ; D/e = 200 → a ≈ 763,1 m/s
        a, _ = celerite_allievi(k_allievi=0.6, diam_conduit=2.0, epaisseur_conduite=0.010)
        self.assertAlmostEqual(a, 763.1, delta=0.2)

    def test_module_young_impose_10_puissance_11(self):
        # acier E = 2,0e11 Pa doit donner k = 0,5 (et non 0,05).
        a_e, _ = celerite_allievi(diam_conduit=2.0, epaisseur_conduite=0.010,
                                  module_young_e=2.0e11)
        a_k, _ = celerite_allievi(k_allievi=0.5, diam_conduit=2.0, epaisseur_conduite=0.010)
        self.assertAlmostEqual(a_e, a_k, places=6)


class TestOrificeDegazage(unittest.TestCase):
    def test_coherence_avec_a_calculer(self):
        a, _ = celerite_allievi(k_allievi=0.6, diam_conduit=2.0, epaisseur_conduite=0.010)
        s0 = math.pi / 4.0 * 2.0**2
        q, _ = qair_degazage(10.0, gravite=9.81, section_conduite=s0, celerite_a=a)
        d1, _ = diametre_orifice_degazage(2.0, 10.0, a, s0, p2_mce=20.33)
        self.assertGreater(d1, 0.0)
        # En inversant Saint-Venant avec la section circulaire d1, on retrouve Q.
        s1 = math.pi / 4.0 * d1**2
        q_retrouve, _ = qair_evacuation_air_saint_venant(s1, p2_mce=20.33)
        self.assertAlmostEqual(q_retrouve, q, delta=0.02 * q)

    def test_fallback_p2_inferieur_a_p1(self):
        # P2 = P1 : pression motrice nulle → fallback P2 = P1 + ΔH, pas de zéro.
        d1, alerte = diametre_orifice_degazage(
            2.0, 10.0, 763.12, math.pi, p2_mce=10.33
        )
        self.assertGreater(d1, 0.0)
        self.assertTrue(alerte)


class TestAdmissionCasse(unittest.TestCase):
    """F10 re-dérivée : H = j·L + ξ·v²/2g avec j de Strickler (F8)."""

    # Cas de référence du dossier BR3_LOT 8 (onglet Admission)
    H, L, D, K = 10.93, 848.3, 2.0, 104.0

    def test_boucle_bernoulli_strickler(self):
        """La ligne d'énergie de F8 doit redonner exactement la dénivelée pour les deux ξ."""
        for xi in (1.0, 2.0):
            v, q_eau, q_air, alerte = qair_admission_casse(
                self.H, self.L, self.D, self.K, coeff_singularites=xi
            )
            self.assertFalse(alerte)
            self.assertAlmostEqual(q_air, q_eau)
            self.assertAlmostEqual(q_eau, v * math.pi * self.D**2 / 4.0, places=9)
            j = pente_strickler(self.D, self.K, q_eau)
            self.assertAlmostEqual(j * self.L + xi * v**2 / (2 * 9.81), self.H, places=6)

    def test_valeurs_de_reference_audit(self):
        """Valeurs de référence de l'audit pour H=10,93 ; L=848,3 ; D=2,0 ; K=104."""
        # ξ = 1 (équation écrite v²/2g) : v = 6,6307 m/s, Q = 20,831 m³/s
        v1, q1, _, _ = qair_admission_casse(self.H, self.L, self.D, self.K, coeff_singularites=1.0)
        self.assertAlmostEqual(v1, 6.6307, places=4)
        self.assertAlmostEqual(q1, 20.831, places=3)
        # ξ = 2 (mention k = 2, retenue par l'audit) : v = 6,0404 m/s, Q = 18,976 m³/s
        v2, q2, _, _ = qair_admission_casse(self.H, self.L, self.D, self.K, coeff_singularites=2.0)
        self.assertAlmostEqual(v2, 6.0404, places=4)
        self.assertAlmostEqual(q2, 18.976, places=3)

    def test_xi_deux_donne_la_lecture_k2(self):
        # ξ = 2 (v²/g) : lecture « k = 2 » du document, retenue par l'audit.
        v2, q2, _, _ = qair_admission_casse(
            self.H, self.L, self.D, self.K, coeff_singularites=2.0
        )
        self.assertAlmostEqual(v2, 6.0404, places=4)
        self.assertAlmostEqual(q2, 18.976, places=3)
        v1, q1, _, _ = qair_admission_casse(self.H, self.L, self.D, self.K, coeff_singularites=1.0)
        self.assertLess(v2, v1)
        self.assertLess(q2, q1)

    def test_rugosite_influe(self):
        # Fonte (K = 100) plus rugueuse que le PRV (K = 104) → vitesse plus faible.
        v_fonte, _, _, _ = qair_admission_casse(self.H, self.L, self.D, 100.0)
        v_prv, _, _, _ = qair_admission_casse(self.H, self.L, self.D, 104.0)
        self.assertLess(v_fonte, v_prv)

    def test_entrees_invalides(self):
        for args in ((0.0, self.L, self.D), (self.H, 0.0, self.D), (self.H, self.L, 0.0)):
            v, q_eau, q_air, alerte = qair_admission_casse(*args)
            self.assertEqual((v, q_eau, q_air), (0.0, 0.0, 0.0))
            self.assertTrue(alerte)

    def test_pente_strickler_inverse_f8(self):
        from debits_ae.formulas import q_eau_strickler

        q, _ = q_eau_strickler(self.K, 0.0027, self.D)
        j = pente_strickler(self.D, self.K, q)
        q_relu, _ = q_eau_strickler(self.K, j, self.D)
        self.assertAlmostEqual(q_relu, q, places=6)


class TestRegistre(unittest.TestCase):
    def test_f6_coherent(self):
        from debits_ae import verifier_formules

        f6 = next(f for f in verifier_formules() if f.nom.startswith("F6"))
        self.assertEqual(f6.statut, STATUT_COHERENT)

    def test_f10_plus_illisible(self):
        # F10 est re-dérivée : elle n'est plus marquée illisible.
        from debits_ae import verifier_formules

        f10 = next(f for f in verifier_formules() if f.nom.startswith("F10"))
        self.assertEqual(f10.statut, STATUT_COHERENT)
        self.assertIn("0,102", f10.commentaire)  # l'ambiguïté reste documentée

    def test_formules_a_risque_projet_complet(self):
        projet = Projet(
            donnees=DonneesProjet(),
            vidange=VidangeResult(diametre_vidange=352.28),
            ventouse=VentouseResult(
                celerite_a=763.12,
                qair_degazage=0.4039,
                diametre_orifice_degazage=0.0631,
                q_eau_remplissage=3.1416,
                qair_remplissage=3.1416,
                diametre_orifice_remplissage=0.0895,
                qair_admission=18.976,  # valeur F10 corrigée (audit, ξ = 2)
            ),
        )
        noms = [f.nom for f in formules_a_risque(projet)]
        # Toutes les formules utilisées (F1, F2, F3, F4, F6, F7, F8, F10) sont
        # désormais OK ou COHÉRENT : aucune n'est à risque.
        self.assertEqual(len(noms), 0)


class TestProjetIo(unittest.TestCase):
    def test_round_trip_json(self):
        projet = Projet(donnees=DonneesProjet(nom="Dossier test", site="BR3"))
        projet.vidange = VidangeResult(diametre_vidange=352.28)
        projet.ventouse = VentouseResult(
            celerite_a=763.12,
            qair_degazage=0.4039,
            qair_admission=32.55,
        )

        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "dossier.mkprojet")
            final = sauvegarder_projet(projet, chemin)
            self.assertTrue(os.path.exists(final))

            with open(final, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["format"], "MK_Debits_Air_Eau")
            self.assertEqual(data["version"], 2)

            relu = charger_projet(final)

        self.assertEqual(relu.donnees.nom, "Dossier test")
        self.assertEqual(relu.donnees.site, "BR3")
        self.assertAlmostEqual(relu.vidange.diametre_vidange, 352.28)
        self.assertAlmostEqual(relu.ventouse.celerite_a, 763.12)
        self.assertAlmostEqual(relu.ventouse.qair_admission, 32.55)

    def test_fichier_invalide(self):
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "invalide.mkprojet")
            with open(chemin, "w", encoding="utf-8") as fh:
                fh.write("{}")
            with self.assertRaises(ValueError):
                charger_projet(chemin)


if __name__ == "__main__":
    unittest.main()
