"""Moteur de calcul des formules de la note "Calcul des débits points bas et hauts".

Formules intégrées selon les corrections fournies :

* Célérité :     a = 9900 / √( 48,3 + k · D / e ) — Allievi (Tableau 7)
                     (D, e en même unité ; k par matériau, voir Tableau 8)
                     ou forme exacte a = 1 / √[ ρ · (1/K_eau + D/(E·e)) ]
* Strickler :    Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5
                     (forme Manning-Strickler en conduite pleine, R = D/4,
                     cohérente avec le coefficient 0,000587 de F10)
* Admission air : Qair = Qeau = (π/4)·D² · √( H / [ ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ] )
                     soit, pour K = 104 et ξ = 2 :
                     Qair = (π·D²/4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ]
                     (formule de l'audit et du PDF page 5)

Chaque fonction expose le résultat ET un drapeau de vérification (`statut`)
reflétant la confiance dans la formule.

ATTENTION : les formules fournies par l'utilisateur et celles marquées
SUSPECT / EMPIRIQUE / À VÉRIFIER / ILLISIBLE ne doivent pas servir à un
dimensionnement définitif sans validation du bureau d'études.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import (
    G,
    RHO_EAU,
    K_VIDANGE_DEFAUT,
    TEMPS_VIDANGE_CIBLE_DEFAUT,
    K_ALLIEVI_DEFAUT,
    K_STRICKLER_PRC_DEFAUT,
    P1_ATMOSPHERIQUE_MCE,
    SEUIL_SONIQUE_P2_MCE,
    STATUT_OK,
    STATUT_SUSPECT,
    STATUT_EMPIRIQUE,
    STATUT_A_VERIFIER,
    STATUT_ILLISIBLE,
    STATUT_COHERENT,
)

# ---------------------------------------------------------------------------
# Constante empirique du PDF (loi d'evacuation d'air, F5 - ANCIENNE, A REJETER)
# 195 n'est pas documentee dans le PDF. Forme erronée selon Saint-Venant.
# ---------------------------------------------------------------------------
CONSTANTE_EVACUATION_AIR_ANCIENNE: float = 195.0  # m/s (vitesse de reference, formule erronée)

# Facteurs de la formule pratique simplifiée Saint-Venant (subsonique)
# Qair ≈ 499 × s × (P1/P2)^0,714 × √[1 - (P1/P2)^0,286]
COEFF_SV_SUBSONIQUE: float = 499.0
EXPOSE_DETENTE: float = 0.714  # 1/gamma avec gamma = 1,4
EXPOSE_MOTEUR: float = 0.286  # (gamma-1)/gamma

# Cas B : écoulement sonique/bloqué (P2 >= 19,55 mCE)
# Qair ≈ 129 × s
COEFF_SV_SONIQUE: float = 129.0

# Coefficient de Strickler en conduite pleine (rayon hydraulique R = D/4).
# Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5 = 0,3117 · K · D^(8/3) · i^0,5
COEFF_STRICKLER_CONDUITE_PLEINE: float = (math.pi / 4.0) * (1.0 / 4.0) ** (2.0 / 3.0)

# Coefficient de F10 : j = (4^(4/3) / K²) · v² / D^(4/3).
# Pour K = 104 : 4^(4/3)/104² = 0,00058706, soit le 0,000587 de l'audit.
COEFF_F10_SINGULARITES: float = 4.0 ** (4.0 / 3.0)


@dataclass
class FormuleVerifiee:
    """Description d'une formule avec son statut de verification."""

    nom: str
    statut: str
    commentaire: str
    formule_latex: str = ""
    formule_clair: str = ""


# ---------------------------------------------------------------------------
# Registre des formules (affiche dans l'onglet "Verifications")
# ---------------------------------------------------------------------------
FORMULES_REGISTRE: list[FormuleVerifiee] = [
    FormuleVerifiee(
        nom="F1 - Débit de vidange (Torricelli)",
        statut=STATUT_OK,
        commentaire="Q = K · s · √(2·g·h). Dimensionnellement cohérente (m3/s). "
        "K = 0,7 (faibles charges), g = 9,81 m/s2.",
        formule_latex="Q = K \\, s \\, \\sqrt{2 g h}",
        formule_clair="Q = K · s · √(2·g·h)",
    ),
    FormuleVerifiee(
        nom="F2 - Diametre de vidange (vidange en 2 h)",
        statut=STATUT_OK,
        commentaire="Formule corrigée (Note de Verification Hydraulique AEP) : "
        "d(mm) = 6,69 × D × (L / √hmoy)^0,5 pour t = 2 h, K = 0,7. "
        "Le coefficient 13,39 du PDF correspond à une vidange en 30 min "
        "(13,39 = 2 × 6,69) et surdimensionnerait la vanne de vidange.",
        formule_latex="d_{mm} = \\frac{1000}{\\sqrt{K \\, t \\, \\sqrt{2g}}} \\, D \\, (L / \\sqrt{h})^{0,5}",
        formule_clair="d(mm) = 6,69 × D × (L / √h)^0,5 pour une vidange en 2 h",
    ),
    FormuleVerifiee(
        nom="F3 - Celerite d'Allievi (Tableau 7)",
        statut=STATUT_OK,
        commentaire="Formule exacte d'Allievi confirmée par la Note de Vérification "
        "Hydraulique AEP (Partie 3) : a = 9900 / √( 48,3 + k·D/e ), avec D et e "
        "dans la même unité. Coefficients k du même tableau : acier 0,5 ; fonte "
        "ductile 0,6 ; béton 3,3-5,0 ; PVC 33,3 ; PEHD 100-125. "
        "AMBIGUÏTÉ LEVÉE : le tableau écrit « k = 10^10 / E », mais ses propres "
        "valeurs (acier E = 2,0×10^11 Pa → k = 0,5) imposent k = 10^11 / E ; "
        "c'est ce facteur 10^11 qui est retenu dans l'application. "
        "Contrôle indépendant : la forme exacte a = 1/√[ρ·(1/K_eau + D/(E·e))] "
        "est également implémentée (F3 exacte) et donne a ≈ 548 m/s pour "
        "DN 2000, e = 35 mm, E = 20 GPa.",
        formule_latex="a = 9900 / \\sqrt{ 48,3 + k \\, D / e } \\quad ; \\quad k = 10^{11}/E",
        formule_clair="a = 9900 / √(48,3 + k · D / e) ; k = 10^11 / E",
    ),
    FormuleVerifiee(
        nom="F4 - Débit d'air dégazage (coup de bélier)",
        statut=STATUT_OK,
        commentaire="Qair = ΔH · g · S0 / a, équivalent à ΔH = a · Qair / (g · S0). "
        "ΔH = suppression de pression à ne pas dépasser (10 m).",
        formule_latex="Q_{air} = \\frac{\\Delta H \\, g \\, S_0}{a}",
        formule_clair="Qair = ΔH · g · S0 / a",
    ),
    FormuleVerifiee(
        nom="F5 - Loi d'evacuation d'air par orifice (Saint-Venant)",
        statut=STATUT_OK,
        commentaire="Formule exacte issue de la loi de Saint-Venant (doc Verification_Evacuation_Air_AEP.docx). "
        "Cas A (subsonique, P2 < 19,55 mCE) : Qair = 499 · s · (P1/P2)^0,714 · √[1 - (P1/P2)^0,286]. "
        "Cas B (sonique/bloqué, P2 ≥ 19,55 mCE) : Qair = 129 · s. "
        "L'ancienne formule '195 × (P1/P2)^0,714 × s' est physiquement fausse (réjettée).",
        formule_latex="Q_{air} = \\begin{cases} 499 \\, s \\, (P_1/P_2)^{0,714} \\sqrt{1-(P_1/P_2)^{0,286}} & \\text{si } P_2 < 19,55 \\\\ 129 \\, s & \\text{si } P_2 \\ge 19,55 \\end{cases}",
        formule_clair="Qair = 499 · s · (P1/P2)^0,714 · √[1 − (P1/P2)^0,286] si P2 < 19,55 ; Qair = 129 · s si P2 ≥ 19,55",
    ),
    FormuleVerifiee(
        nom="F6 - Diametre orifice de degazage",
        statut=STATUT_COHERENT,
        commentaire="Formule dérivée, non indépendante : d1 est obtenu en inversant la loi de "
        "Saint-Venant (F5, validée) pour la section s, avec le débit de dégazage Qair de F4 "
        "(validée), puis d1 = 2·√(s/π). Le résultat est donc COHÉRENT dès lors que F4 et F5 "
        "le sont. Réserve : si P2 ≤ P1, l'application retient P2 = P1 + ΔH et le signale ; "
        "ce cas doit être confirmé au BE. L'ancienne relation d1 = d·√(ΔH/(19,9·a)) était "
        "basée sur la formule erronée 195 et a été abandonnée.",
        formule_latex="s = Q_{air} / [499 \\, (P_1/P_2)^{0,714} \\sqrt{1-(P_1/P_2)^{0,286}}] \\quad ; \\quad d_1 = 2\\sqrt{s/\\pi}",
        formule_clair="s = Qair / [499 · (P1/P2)^0,714 · √(1 − (P1/P2)^0,286)] ; d1 = 2 · √(s/π)",
    ),
    FormuleVerifiee(
        nom="F7 - Remplissage de la conduite",
        statut=STATUT_OK,
        commentaire="Qair = Qeau = V · S0 (conservation du volume lors du remplissage). "
        "d2 = d · √(V / 499) si P1 = P2 (dépression nulle). V = vitesse de remplissage "
        "(1 m/s doc ; 0,5 m/s en vérification page 6).",
        formule_latex="Q_{air} = Q_{eau} = V \\, S_0 \\quad ; \\quad d2 = d \\, \\sqrt{V / 499}",
        formule_clair="Qair = Qeau = V · S0 ; d2 = d · √(V / 499) si P1 = P2",
    ),
    FormuleVerifiee(
        nom="F8 - Débit d'eau vidangé (Strickler)",
        statut=STATUT_COHERENT,
        commentaire="Forme Manning-Strickler en conduite pleine, rayon hydraulique R = D/4 : "
        "Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5, soit Qeau = 0,3117 · K · D^(8/3) · i^0,5. "
        "Le PDF écrivait (π/4)^(5/3), incohérent avec sa propre formule F10 et avec R = D/4 "
        "(écart d'un facteur 2,145). La forme retenue redonne exactement le coefficient "
        "0,000587 de F10 pour K = 104. K = 104 (PRV) ou 100 (fonte).",
        formule_latex="Q_{eau} = K \\, (\\pi/4) \\, (1/4)^{2/3} \\, D^{8/3} \\, i^{0,5}",
        formule_clair="Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5 = 0,3117 · K · D^(8/3) · i^0,5",
    ),
    FormuleVerifiee(
        nom="F9 - Bernoulli point haut → point bas",
        statut=STATUT_COHERENT,
        commentaire="Dénivelée = j · L + ξ·v²/(2g). L'audit retient ξ = 2 "
        "(mention « k = 2 », constante 0,102 = 1/g). Le choix ξ = 1 / ξ = 2 "
        "reste exposé dans l'interface pour lever toute ambiguïté.",
        formule_latex="H = j \\, L + \\xi \\, v^2/(2g)",
        formule_clair="H = j · L + ξ · v²/(2g) ; ξ = 2 selon l'audit",
    ),
    FormuleVerifiee(
        nom="F10 - Débit d'air admission (casse franche)",
        statut=STATUT_COHERENT,
        commentaire="Formule de l'audit (et du PDF page 5) : Qair = (π·D²/4) · "
        "√[ H / (0,102 + 0,000587 · L / D^(4/3)) ] pour K = 104 et ξ = 2. "
        "Forme générale : v = √[ H / ( ξ/(2g) + 4^(4/3)·L / (K²·D^(4/3)) ) ] et "
        "Qair = Qeau = v·πD²/4. Le coefficient 0,000587 vaut exactement 4^(4/3)/104² ; "
        "0,102 = 1/g. ξ = 1 (v²/2g, équation écrite) ou 2 (mention « k=2 ») : "
        "l'audit retient ξ = 2. Choix à confirmer par le bureau d'études.",
        formule_latex="Q_{air} = \\frac{\\pi D^2}{4} \\sqrt{ \\frac{H}{\\frac{\\xi}{2g} + \\frac{4^{4/3} L}{K^2 D^{4/3}}} }",
        formule_clair="Qair = Qeau = v · π·D²/4 ; v = √[ H / ( ξ/(2g) + 4^(4/3)·L/(K²·D^(4/3)) ) ] ; pour K = 104 et ξ = 2 : Qair = (π·D²/4) · √[ H / (0,102 + 0,000587·L/D^(4/3)) ]",
    ),
    FormuleVerifiee(
        nom="F11 - Hauteur motrice nette (dépression max 3 mce)",
        statut=STATUT_OK,
        commentaire="H = max(0 ; cote_ventouse − 3 m − cote_vidange). Dépression max "
        "admise : 3 mce. La borne à 0 évite une hauteur négative lorsqu'il n'y a "
        "pas assez de chute (audit, Annexe 1 corrigée).",
        formule_latex="H = \\max(0 ; z_{ventouse} - 3 - z_{vidange})",
        formule_clair="H = max(0 ; cote_ventouse − 3 − cote_vidange)",
    ),
]


# ===========================================================================
# CALCULS
# ===========================================================================


def debit_vidange(
    coeff_debit: float = K_VIDANGE_DEFAUT,
    section_vidange: float = 0.0,
    hauteur_eau: float = 0.0,
    gravite: float = G,
) -> float:
    """F1 — Débit déchargé par une vidange : Q = K · s · √(2·g·h)."""
    if section_vidange < 0 or hauteur_eau < 0:
        return 0.0
    return coeff_debit * section_vidange * math.sqrt(2.0 * gravite * hauteur_eau)


def section_ronde(diametre_m: float) -> float:
    """Section d'un cercle de diamètre donné (m) -> m2."""
    if diametre_m <= 0:
        return 0.0
    return math.pi / 4.0 * diametre_m**2


def diametre_vidange_2h(
    diam_conduit_m: float = 0.0,  # D en mètres
    longueur_troncon: float = 0.0,  # L en mètres
    hauteur_eau: float = 0.0,  # hmoy en mètres
    temps_vidange_h: float = 2.0,  # temps de vidange cible en heures
    coeff_debit: float = K_VIDANGE_DEFAUT,  # K = 0,7
    gravite: float = G,
) -> tuple[float, bool]:
    """F2 — Diamètre de vidange (mm) pour vidange du tronçon en t heures.

    Formule corrigée (voir Note de Vérification Hydraulique AEP) :
        d(mm) = [ 1000 / √(K · t · √(2·g)) ] × D × (L / √hmoy)^0,5

    Avec t en secondes. Pour t = 2 h (7200 s), K = 0,7, g = 9,81 :
        coeff = 1000 / √(0,7 × 7200 × √19,62) = 6,69

    L'ancienne formule du PDF utilisait 13,39, ce qui correspond à une
    vidange en 30 minutes (t = 1800 s), pas 2 heures. 13,39 = 2 × 6,69.

    Retourne (diametre_mm, alerte).
    """
    alerte = False
    if diam_conduit_m <= 0 or longueur_troncon <= 0 or hauteur_eau <= 0:
        return 0.0, True

    temps_s = temps_vidange_h * 3600.0
    coeff = 1000.0 / math.sqrt(
        coeff_debit * temps_s * math.sqrt(2.0 * gravite)
    )
    d_mm = coeff * diam_conduit_m * (longueur_troncon / math.sqrt(hauteur_eau)) ** 0.5
    return d_mm, alerte


def diametre_vidange_2h_derive(
    diam_conduit: float,
    longueur_troncon: float,
    hauteur_eau: float,
    coeff_debit: float = K_VIDANGE_DEFAUT,
    gravite: float = G,
    temps_vidange: float = TEMPS_VIDANGE_CIBLE_DEFAUT,
) -> float:
    """F2 re-déduite physiquement (à titre indicatif, non utilisée par défaut).

    Dérivation : Q = Volume / temps = (π/4 D² L) / t
                 Q = K · s_orifice · √(2 g h), s_orifice = π/4 d²
    ⇒ d = D · √( L / (t · K · √(2 g h)) )
    """
    if diam_conduit <= 0 or longueur_troncon <= 0 or hauteur_eau <= 0:
        return 0.0
    return diam_conduit * math.sqrt(
        longueur_troncon / (temps_vidange * coeff_debit * math.sqrt(2.0 * gravite * hauteur_eau))
    )


def celerite_allievi(
    k_allievi: float = K_ALLIEVI_DEFAUT,  # Coefficient Allievi k par matériau
    diam_conduit: float = 0.0,  # D (m ou mm, meme unite que e)
    epaisseur_conduite: float = 0.0,  # e (m ou mm, meme unite que D)
    module_young_e: float = 0.0,  # Module d'Young E (Pa), si saisi : k = 10^11 / E
) -> tuple[float, bool]:
    """F3 — Célérité d'Allievi (Tableau 7 du document de vérification).

    a = 9900 / √( 48,3 + k · D / e )

    Avec :
      - a en m/s
      - D et e en même unité (m ou mm, seul le rapport D/e compte)
      - k = coefficient d'Allievi par matériau (Tableau 8) :
          Acier 0,5 ; Fonte ductile 0,6 ; Béton 3,3-5,0 ; PVC 33,3 ; PEHD 100-125
      - Si module_young_e est renseigne (Pa) : k = 10^11 / E

    ATTENTION : formule empirique. A valider avec le bureau d'etudes.
    Retourne (celerite_m_s, alerte). Alerte systematique.
    """
    alerte = True  # empirique, a verifier (Allievi / Tableau 7)
    if module_young_e and module_young_e > 0:
        k_allievi = 1.0e11 / module_young_e

    if k_allievi <= 0 or diam_conduit <= 0 or epaisseur_conduite <= 0:
        return 0.0, alerte

    return 9900.0 / math.sqrt(48.3 + (k_allievi * diam_conduit / epaisseur_conduite)), alerte


def celerite_allievi_exacte(
    diam_conduit: float,
    epaisseur_conduite: float,
    module_young_conduite: float = 20.0e9,  # E conduite (Pa) : PRV = 20 GPa
    module_compressibilite_eau: float = 2.07e9,  # K_eau (Pa)
    masse_volumique: float = RHO_EAU,
) -> tuple[float, bool]:
    """F3 exacte — Célérité d'Allievi (audit, Partie 2.2).

    a = 1 / √[ ρ · ( 1/K_eau + D/(E·e) ) ]

    Avec ρ = 1 000 kg/m³, K_eau = 2,07 GPa, E = 20 GPa (PRV). Pour DN 2000
    et e = 35 mm, on retrouve a ≈ 548 m/s. Cette forme sert de contrôle de
    la formule empirique F3 (9900 / √(48,3 + k·D/e)).

    Retourne (celerite_m_s, alerte). L'alerte signale une entrée invalide.
    """
    if (
        diam_conduit <= 0
        or epaisseur_conduite <= 0
        or module_young_conduite <= 0
        or module_compressibilite_eau <= 0
        or masse_volumique <= 0
    ):
        return 0.0, True

    inverse_module = 1.0 / module_compressibilite_eau + diam_conduit / (
        module_young_conduite * epaisseur_conduite
    )
    return 1.0 / math.sqrt(masse_volumique * inverse_module), False


def qair_degazage(
    delta_h: float,
    gravite: float = G,
    section_conduite: float = 0.0,
    celerite_a: float = 0.0,
) -> tuple[float, bool]:
    """F4 — Débit d'air de dégazage : Qair = ΔH · g · S0 / a.

    Retourne (qair_m3_s, alerte). Alerte si ΔH > 10 m.
    """
    alerte = delta_h > 10.0
    if celerite_a <= 0 or section_conduite <= 0:
        return 0.0, alerte
    return delta_h * gravite * section_conduite / celerite_a, alerte


def q_remplissage(
    vitesse: float = 1.0,
    section_conduite: float = 0.0,
) -> float:
    """F7 — Débit d'eau de remplissage : Qeau = V · S0."""
    if vitesse < 0 or section_conduite < 0:
        return 0.0
    return vitesse * section_conduite


def qair_evacuation_air_saint_venant(
    section_orifice: float,
    p2_mce: float,
    p1_mce: float = P1_ATMOSPHERIQUE_MCE,
) -> tuple[float, bool]:
    """F5 — Débit d'air évacué par un orifice (Loi de Saint-Venant).

    Cas A : Écoulement subsonique (P2 < 19,55 mCE, pression relative < 9,2 mCE)
        Qair = 499 × s × (P1/P2)^0,714 × √[1 - (P1/P2)^0,286]

    Cas B : Écoulement sonique / bloqué (P2 ≥ 19,55 mCE)
        Qair = 129 × s

    L'ancienne formule '195 × (P1/P2)^0,714 × s' est physiquement fausse (réjettée).

    Retourne (qair_m3_s, alerte).
    """
    alerte = False  # Formule physique validée (Saint-Venant)
    if section_orifice < 0 or p2_mce <= 0:
        return 0.0, True

    ratio = p1_mce / p2_mce

    if p2_mce >= SEUIL_SONIQUE_P2_MCE:
        # Cas B : blocage sonique, débit constant
        return COEFF_SV_SONIQUE * section_orifice, alerte
    else:
        # Cas A : subsonique, avec terme moteur sous racine carrée
        terme_racine = 1.0 - (ratio ** EXPOSE_MOTEUR)
        if terme_racine < 0:
            terme_racine = 0.0
        return (
            COEFF_SV_SUBSONIQUE
            * section_orifice
            * (ratio ** EXPOSE_DETENTE)
            * math.sqrt(terme_racine)
        ), alerte


def diametre_orifice_degazage(
    diam_conduit: float,
    delta_h: float,
    celerite_a: float,
    section_conduite: float,
    p2_mce: float = P1_ATMOSPHERIQUE_MCE,
    p1_mce: float = P1_ATMOSPHERIQUE_MCE,
) -> tuple[float, bool]:
    """F6 — Diamètre de l'orifice de dégazage.

    Résout la formule Saint-Venant pour la section s nécessaire,
    puis en déduit le diamètre d1 = 2·√(s/π).

    Qair_degazage = ΔH · g · S0 / a (F4)
    s = Qair_degazage / [499 × (P1/P2)^0,714 × √(1 - (P1/P2)^0,286)]

    Retourne (d1_m, alerte).
    """
    alerte = True  # À valider avec le BE (dépend de la nouvelle formule SV)
    if celerite_a <= 0 or diam_conduit <= 0 or section_conduite <= 0 or p1_mce <= 0:
        return 0.0, alerte

    # Cas dégénéré P2 <= P1 : aucune pression motrice, donc aucun orifice fini
    # ne peut évacuer le débit de dégazage. On prend la pression absolue
    # atteinte pendant la surpression : P2 = P1 + ΔH (mCE), ce qui rend le
    # calcul exploitable et physiquement cohérent. Le statut reste à vérifier.
    if p2_mce <= p1_mce:
        p2_mce = p1_mce + max(delta_h, 0.0)
        alerte = True
    if p2_mce <= 0:
        return 0.0, alerte

    # Débit de dégazage requis (F4)
    q_degaz, _ = qair_degazage(delta_h, G, section_conduite, celerite_a)
    if q_degaz <= 0:
        return 0.0, alerte

    # Section nécessaire selon Saint-Venant
    ratio = p1_mce / p2_mce
    if p2_mce >= SEUIL_SONIQUE_P2_MCE:
        coeff_denom = COEFF_SV_SONIQUE
    else:
        terme_racine = 1.0 - (ratio ** EXPOSE_MOTEUR)
        if terme_racine < 0:
            terme_racine = 0.0
        coeff_denom = COEFF_SV_SUBSONIQUE * (ratio ** EXPOSE_DETENTE) * math.sqrt(terme_racine)

    if coeff_denom <= 0:
        return 0.0, alerte

    s_necessaire = q_degaz / coeff_denom  # m2
    d1 = 2.0 * math.sqrt(s_necessaire / math.pi)  # m
    return d1, alerte


def diametre_orifice_remplissage(
    diam_conduit: float,
    vitesse: float = 1.0,
) -> tuple[float, bool]:
    """F7 — Diamètre de l'orifice d'évacuation d'air au remplissage.

    Lors du remplissage, Qair = Qeau = V · S0 (conservation du volume).
    Si P1 = P2 (dépression nulle), la section équivalente d'après Saint-Venant
    donnerait : d2 = d · √(V / 499).

    Retourne (d2_m, alerte).
    """
    alerte = False  # Conservation de volume, physiquement correct
    if diam_conduit <= 0 or vitesse <= 0:
        return 0.0, True
    return diam_conduit * math.sqrt(vitesse / COEFF_SV_SUBSONIQUE), alerte


def q_eau_strickler(
    coeff_rugosite: float,
    pente: float,
    diam_conduit: float,
) -> tuple[float, bool]:
    """F8 — Débit d'eau vidangé par Strickler (conduite pleine, R = D/4).

    Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5
         = 0,3117 · K · D^(8/3) · i^0,5

    Cette forme est cohérente avec le coefficient 0,000587 de F10.
    K : coefficient de rugosité (m^(1/3)/s), défaut 104 (PRV) ; 100 pour la fonte.
    Retourne (qeau_m3_s, alerte).
    """
    alerte = False
    if coeff_rugosite <= 0 or pente <= 0 or diam_conduit <= 0:
        return 0.0, True
    return (
        COEFF_STRICKLER_CONDUITE_PLEINE
        * coeff_rugosite
        * (pente**0.5)
        * (diam_conduit ** (8.0 / 3.0))
    ), alerte


def pente_strickler(
    diam_conduit: float,
    coeff_rugosite: float,
    q_eau: float,
) -> float:
    """Ligne d'énergie j (m/m) de Strickler — inverse exact de F8.

    j = Q² / [ (0,3117 · K)² · D^(16/3) ]
    """
    if diam_conduit <= 0 or coeff_rugosite <= 0 or q_eau <= 0:
        return 0.0
    denominateur = (
        COEFF_STRICKLER_CONDUITE_PLEINE**2
        * coeff_rugosite**2
        * diam_conduit ** (16.0 / 3.0)
    )
    return q_eau**2 / denominateur


def qair_admission_casse(
    hauteur_motrice: float,
    longueur_troncon: float,
    diametre_conduit: float,  # D en m
    coeff_rugosite: float = K_STRICKLER_PRC_DEFAUT,  # K Strickler : 104 PRV / 100 fonte
    coeff_singularites: float = 2.0,  # ξ (1 = v²/2g ; 2 = v²/g, mention « k=2 »)
    gravite: float = G,
) -> tuple[float, float, float, bool]:
    """F10 — Débit d'air d'admission en casse franche (formule de l'audit).

    Chaîne du PDF (page 5), « 3ème fonction : entrée d'air lors des vidanges
    ou casse franche » :

        Dénivelée  H = j · L + ξ · v² / (2 g)
        j (Strickler, F8, R = D/4)  ⇒  j = 4^(4/3) · v² / (K² · D^(4/3))
        Qair = Qeau = v · π D² / 4

    En reportant j :

        H = v² · [ ξ/(2g) + 4^(4/3) · L / (K² · D^(4/3)) ]
    ⇒   v = √( H / [ ξ/(2g) + 4^(4/3) · L / (K² · D^(4/3)) ] )

    Pour K = 104 et ξ = 2, le dénominateur devient
    0,102 + 0,000587 · L / D^(4/3), exactement la formule de l'audit.

    ξ = 1 traduit l'équation écrite « v²/2g ». ξ = 2 traduit la mention
    « pertes singulières estimées à v²/2g (k = 2) » : la constante 0,102 de
    l'équation imprimée vaut 1/g, et l'audit retient ξ = 2.

    Retourne (vitesse_v, q_eau, q_air, alerte) ; l'alerte signale une entrée
    invalide, pas la formule.
    """
    alerte = False
    if (
        hauteur_motrice <= 0
        or longueur_troncon <= 0
        or diametre_conduit <= 0
        or coeff_rugosite <= 0
    ):
        return 0.0, 0.0, 0.0, True

    xi = max(coeff_singularites, 0.0)
    # Coefficient de v² dans la ligne d'énergie j (cf. F8, R = D/4)
    coeff_j = COEFF_F10_SINGULARITES / coeff_rugosite**2
    denominateur = xi / (2.0 * gravite) + (
        coeff_j * longueur_troncon / diametre_conduit ** (4.0 / 3.0)
    )
    if denominateur <= 0:
        return 0.0, 0.0, 0.0, True

    v = math.sqrt(hauteur_motrice / denominateur)
    section = math.pi / 4.0 * diametre_conduit**2
    q = section * v
    return v, q, q, alerte


def hauteur_motriere(
    cote_ventouse: float,
    cote_vidange: float,
    depression_max: float = 3.0,
) -> float:
    """F11 — Hauteur motrice nette : H = max(0 ; cote_ventouse − dépression − cote_vidange).

    La borne à 0 évite une hauteur négative lorsqu'il n'y a pas assez de chute
    entre la ventouse et la vidange (audit, Annexe 1 corrigée). Une hauteur
    nulle signifie « pas d'admission d'air par casse franche » : le débit est
    alors nul, ce que ``qair_admission_casse`` signale par son drapeau.
    """
    return max(0.0, cote_ventouse - depression_max - cote_vidange)


# ===========================================================================
# ORCHESTRATEURS (appelés par l'UI)
# ===========================================================================


def calcul_vidange(inputs) -> "VidangeResult":
    from .models import VidangeResult

    s_conduite = section_ronde(inputs.diam_conduit)
    q_debit = debit_vidange(
        coeff_debit=inputs.coeff_debit,
        section_vidange=s_conduite,
        hauteur_eau=inputs.hauteur_eau,
    )
    d_mm, alerte_f2 = diametre_vidange_2h(
        diam_conduit_m=inputs.diam_conduit,
        longueur_troncon=inputs.longueur_troncon,
        hauteur_eau=inputs.hauteur_eau,
        temps_vidange_h=inputs.temps_vidange_cible / 3600.0,
        coeff_debit=inputs.coeff_debit,
    )
    volume = s_conduite * inputs.longueur_troncon
    q_necessaire = volume / inputs.temps_vidange_cible if inputs.temps_vidange_cible > 0 else 0.0

    return VidangeResult(
        section=s_conduite,
        debit_decharge=q_debit,
        diametre_vidange=d_mm,
        section_vidange=section_ronde(d_mm / 1000.0) if d_mm > 0 else 0.0,
        volume_troncon=volume,
        debit_necessaire=q_necessaire,
        formule_f2_alerte=alerte_f2,
    )


def calcul_ventouse(inputs) -> "VentouseResult":
    from .models import VentouseResult

    res = VentouseResult()

    # Section conduite
    if inputs.section_conduite is not None and inputs.section_conduite > 0:
        s0 = inputs.section_conduite
    elif inputs.diam_conduit > 0:
        s0 = section_ronde(inputs.diam_conduit)
    else:
        s0 = 0.0

    # --- 1ère fonction : dégazage ---
    if inputs.celerite_a is not None and inputs.celerite_a > 0:
        a = inputs.celerite_a
    elif inputs.diam_conduit > 0 and inputs.epaisseur_conduite > 0:
        a, _ = celerite_allievi(
            k_allievi=inputs.k_allievi,
            diam_conduit=inputs.diam_conduit,
            epaisseur_conduite=inputs.epaisseur_conduite,
            module_young_e=inputs.module_young_e,
        )
    else:
        a = 0.0
    res.celerite_a = a

    if a > 0 and s0 > 0:
        q_degaz, alerte_dh = qair_degazage(
            delta_h=inputs.delta_h_max,
            gravite=G,
            section_conduite=s0,
            celerite_a=a,
        )
        res.qair_degazage = q_degaz
        res.delta_h = inputs.delta_h_max
        res.degazage_conforme = inputs.delta_h_max <= 10.0 and not alerte_dh
        d1, _ = diametre_orifice_degazage(
            diam_conduit=inputs.diam_conduit,
            delta_h=inputs.delta_h_max,
            celerite_a=a,
            section_conduite=s0,
            p2_mce=inputs.p2_pression_absolue_mce,
        )
        res.diametre_orifice_degazage = d1
    else:
        res.degazage_conforme = False

    # --- 2ème fonction : remplissage ---
    if s0 > 0:
        res.q_eau_remplissage = q_remplissage(
            vitesse=inputs.vitesse_remplissage, section_conduite=s0
        )
        # Conservation du volume : Qair_remplissage = Qeau_remplissage
        res.qair_remplissage = res.q_eau_remplissage
        d2, _ = diametre_orifice_remplissage(
            diam_conduit=inputs.diam_conduit,
            vitesse=inputs.vitesse_remplissage,
        )
        res.diametre_orifice_remplissage = d2
    else:
        res.qair_remplissage = 0.0

    # --- 3ème fonction : admission casse franche ---
    h = (
        inputs.hauteur_motrice
        if inputs.hauteur_motrice is not None
        else hauteur_motriere(inputs.cote_ventouse, inputs.cote_vidange)
    )
    res.hauteur_motrice = h
    res.coeff_singularites = inputs.coeff_singularites
    if h > 0 and inputs.longueur_troncon > 0 and inputs.diam_conduit > 0:
        v, q_eau, q_air, _ = qair_admission_casse(
            hauteur_motrice=h,
            longueur_troncon=inputs.longueur_troncon,
            diametre_conduit=inputs.diam_conduit,
            coeff_rugosite=inputs.coeff_rugosite,
            coeff_singularites=inputs.coeff_singularites,
        )
        res.vitesse_vidange = v
        res.q_eau_vidange = q_eau
        res.qair_admission = q_air

    return res


def verifier_formules() -> list[FormuleVerifiee]:
    """Retourne le registre des formules avec leurs statuts."""
    return list(FORMULES_REGISTRE)


def _code_formule(nom: str) -> str:
    """Extrait le code « F1 », « F2 »… du libellé d'une formule."""
    return nom.split(" ", 1)[0]


def formules_utilisees(projet) -> list[FormuleVerifiee]:
    """Formules réellement mobilisées par les résultats présents dans le projet."""
    codes: set[str] = set()

    if projet.vidange is not None:
        codes.update({"F1", "F2"})

    v = projet.ventouse
    if v is not None:
        if v.celerite_a > 0:
            codes.add("F3")
        if v.qair_degazage > 0:
            codes.update({"F4", "F6"})
        if v.q_eau_remplissage > 0 or v.qair_remplissage > 0:
            codes.add("F7")
        if v.qair_admission > 0:
            # F10 résout l'équation de Bernoulli (F9) avec la ligne d'énergie
            # de Strickler (F8) : les trois formules sont mobilisées.
            codes.update({"F8", "F10"})

    if projet.verification is not None:
        codes.add("F7")

    return [f for f in FORMULES_REGISTRE if _code_formule(f.nom) in codes]


def formules_a_risque(projet) -> list[FormuleVerifiee]:
    """Sous-ensemble des formules utilisées dont le statut exige une validation."""
    from .models import STATUTS_A_RISQUE

    return [f for f in formules_utilisees(projet) if f.statut in STATUTS_A_RISQUE]
