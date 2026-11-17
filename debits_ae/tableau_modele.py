"""Modèles de tableaux d'import pour les tableaux de dimensionnement.

Deux modèles sont proposés, calqués sur les images déposées à la racine :

* ``Tableau dimensionnement ventouses.png`` (Annexe 1) — colonnes calculées
  par Python : dénivelée des tronçons, pentes, débits d'air calculés (Q air)
  via F10/F11. Les autres colonnes (cotes, diamètres, longueurs, équipement,
  débit admis) sont renseignées par l'utilisateur.

* ``Tableau dimensionnement vidanges.png`` (Annexe 2) — colonnes calculées
  par Python : dénivelée des tronçons, diamètres de vidange (F2, coeff 6,69
  pour 2 h). Les autres colonnes (cotes, longueurs, DN conduite) sont
  renseignées par l'utilisateur.

Les hypothèses (nature du fluide, matériaux, épaisseurs, K Strickler, ξ…)
sont portées par les données partagées du projet (:class:`debits_ae.models.DonneesProjet`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Colonnes du tableau VENTOUSES (Annexe 1)
# ---------------------------------------------------------------------------
# Les colonnes "calculees" sont remplies automatiquement par Python.
# Les colonnes "saisies" doivent être remplies par l'utilisateur.

COLONNES_VENTOUSE_SAIES: list[str] = [
    "PM",
    "Cote projet (ventouse)",
    "PM Am",
    "Cote projet (amont)",
    "PM aval",
    "Cote projet (aval)",
    "DN conduite (m)",
    "Longueur tronçon amont (m)",
    "Longueur tronçon aval (m)",
    "Equipement du point haut",
    "Débit d'air admis équipé (m3/s)",
]

COLONNES_VENTOUSE_CALCULEES: list[str] = [
    "Dénivelée tronçon amont (m)",
    "Dénivelée tronçon aval (m)",
    "Pente tronçon amont (m/m)",
    "Pente tronçon aval (m/m)",
    "Débit d'air calculé Qair amont (m3/s)",
    "Débit d'air calculé Qair aval (m3/s)",
    "Qair max (m3/s)",
]

COLONNES_VENTOUSE_TOUTES: list[str] = (
    COLONNES_VENTOUSE_SAIES + COLONNES_VENTOUSE_CALCULEES
)


@dataclass
class LigneVentouse:
    """Une ligne du tableau de dimensionnement des ventouses."""

    pm: str = ""
    cote_projet: float | None = None
    pm_am: str = ""
    cote_amont: float | None = None
    pm_aval: str = ""
    cote_aval: float | None = None
    dn_conduite: float | None = None
    longueur_amont: float | None = None
    longueur_aval: float | None = None

    # Colonnes calculées
    denivelee_amont: float | None = None
    denivelee_aval: float | None = None
    pente_amont: float | None = None
    pente_aval: float | None = None
    qair_amont: float | None = None
    qair_aval: float | None = None
    qair_max: float | None = None

    # Colonnes saisies par l'utilisateur
    equipement: str = ""
    debit_admis_equipe: float | None = None

    def calculer(
        self,
        cote_ventouse: float | None,
        cote_vidange: float | None,
        longueur_troncon: float,
        diametre_conduit: float,
        coeff_rugosite: float,
        coeff_singularites: float,
        gravite: float = 9.81,
    ) -> None:
        """Calcule les colonnes automatiques avec les formules de l'app."""
        from debits_ae import hauteur_motriere, qair_admission_casse

        # --- Dénivelées (différence de cotes entre extrémités du tronçon) ---
        # Tronçon amont : entre Vidange Amont et Ventouse
        if self.cote_amont is not None and self.cote_projet is not None:
            self.denivelee_amont = abs(self.cote_amont - self.cote_projet)
        else:
            self.denivelee_amont = 0.0
        # Tronçon aval : entre Ventouse et Vidange Aval
        if self.cote_projet is not None and self.cote_aval is not None:
            self.denivelee_aval = abs(self.cote_projet - self.cote_aval)
        else:
            self.denivelee_aval = 0.0

        # --- Pentes = dénivelée / longueur ---
        if self.denivelee_amont is not None and self.longueur_amont:
            self.pente_amont = self.denivelee_amont / self.longueur_amont
        else:
            self.pente_amont = 0.0
        if self.denivelee_aval is not None and self.longueur_aval:
            self.pente_aval = self.denivelee_aval / self.longueur_aval
        else:
            self.pente_aval = 0.0

        # --- Débit d'air calculé Qair (F10 + F11) ---
        # H = max(0 ; cote_ventouse − 3 − cote_vidange)
        if cote_ventouse is not None and cote_vidange is not None:
            h = hauteur_motriere(cote_ventouse, cote_vidange)
        else:
            h = 0.0

        if h > 0 and self.longueur_amont and diametre_conduit and diametre_conduit > 0:
            v, q, _, _ = qair_admission_casse(
                hauteur_motrice=h,
                longueur_troncon=self.longueur_amont,
                diametre_conduit=diametre_conduit,
                coeff_rugosite=coeff_rugosite,
                coeff_singularites=coeff_singularites,
            )
            self.qair_amont = q
        else:
            self.qair_amont = 0.0

        if h > 0 and self.longueur_aval and diametre_conduit and diametre_conduit > 0:
            v, q, _, _ = qair_admission_casse(
                hauteur_motrice=h,
                longueur_troncon=self.longueur_aval,
                diametre_conduit=diametre_conduit,
                coeff_rugosite=coeff_rugosite,
                coeff_singularites=coeff_singularites,
            )
            self.qair_aval = q
        else:
            self.qair_aval = 0.0

        self.qair_max = max(self.qair_amont or 0.0, self.qair_aval or 0.0)


# ---------------------------------------------------------------------------
# Colonnes du tableau VIDANGES (Annexe 2)
# ---------------------------------------------------------------------------
COLONNES_VIDANGE_SAIES: list[str] = [
    "PM Am",
    "Cprojet Am",
    "PM (ventouse amont)",
    "Cprojet (ventouse amont)",
    "PM (ventouse aval)",
    "Cprojet (ventouse aval)",
    "DN conduite (m)",
    "Longueur tronçon amont (m)",
    "Longueur tronçon aval (m)",
]

COLONNES_VIDANGE_CALCULEES: list[str] = [
    "Dénivelée tronçon amont (m)",
    "Dénivelée tronçon aval (m)",
    "Diamètre t=1h (mm)",
    "Diamètre t=2h (mm)",
    "Diamètre retenu T=2h (mm)",
    "Diamètre vidange (mm)",
]

COLONNES_VIDANGE_TOUTES: list[str] = (
    COLONNES_VIDANGE_SAIES + COLONNES_VIDANGE_CALCULEES
)


@dataclass
class LigneVidange:
    """Une ligne du tableau de dimensionnement des vidanges."""

    pm_am: str = ""
    cprojet_am: float | None = None
    pm_ventouse_am: str = ""
    cprojet_ventouse_am: float | None = None
    pm_ventouse_av: str = ""
    cprojet_ventouse_av: float | None = None
    dn_conduite: float | None = None
    longueur_amont: float | None = None
    longueur_aval: float | None = None

    # Colonnes calculées
    denivelee_amont: float | None = None
    denivelee_aval: float | None = None
    diametre_t1h: float | None = None
    diametre_t2h: float | None = None
    diametre_retenu_t2h: float | None = None
    diametre_vidange: float | None = None

    def calculer(
        self,
        coeff_debit: float = 0.7,
        temps_vidange_h: float = 2.0,
        diametre_conduit: float = 2.0,
        gravite: float = 9.81,
    ) -> None:
        """Calcule les colonnes automatiques avec les formules de l'app (F2)."""
        from debits_ae import diametre_vidange_2h

        # --- Dénivelées ---
        # Tronçon amont : entre Vidange et Ventouse Amont
        if self.cprojet_am is not None and self.cprojet_ventouse_am is not None:
            self.denivelee_amont = abs(self.cprojet_am - self.cprojet_ventouse_am)
        else:
            self.denivelee_amont = 0.0
        # Tronçon aval : entre Ventouse Amont et Ventouse Aval
        if self.cprojet_ventouse_am is not None and self.cprojet_ventouse_av is not None:
            self.denivelee_aval = abs(self.cprojet_ventouse_am - self.cprojet_ventouse_av)
        else:
            self.denivelee_aval = 0.0

        # --- Diamètres via F2 (coeff 6,69 pour 2 h) ---
        if (
            self.dn_conduite
            and self.longueur_amont
            and self.dn_conduite > 0
        ):
            # On utilise la longueur totale (amont + aval) comme dans l'audit
            longueur_totale = (self.longueur_amont or 0) + (self.longueur_aval or 0)
            # hauteur_moyenne : on prend une valeur par défaut si non renseignée
            hauteur_moyenne = 1.5  # m, hypothèse utilisateur
            d_mm, _ = diametre_vidange_2h(
                diam_conduit_m=self.dn_conduite,
                longueur_troncon=longueur_totale,
                hauteur_eau=hauteur_moyenne,
                temps_vidange_h=temps_vidange_h,
                coeff_debit=coeff_debit,
                gravite=gravite,
            )
            self.diametre_t2h = d_mm
            self.diametre_retenu_t2h = d_mm  # DN normalisé à ajuster par l'utilisateur
            self.diametre_vidange = d_mm


# ---------------------------------------------------------------------------
# Ensemble des modèles
# ---------------------------------------------------------------------------
@dataclass
class ModeleTableau:
    """Description d'un modèle de tableau importable."""

    nom: str
    fichier_exemple: str
    colonnes_saisies: list[str]
    colonnes_calculees: list[str]
    toutes_colonnes: list[str]


MODELES_DISPONIBLES: list[ModeleTableau] = [
    ModeleTableau(
        nom="Dimensionnement des ventouses (Annexe 1)",
        fichier_exemple="Exemple_import_ventouses.xlsx",
        colonnes_saisies=COLONNES_VENTOUSE_SAIES,
        colonnes_calculees=COLONNES_VENTOUSE_CALCULEES,
        toutes_colonnes=COLONNES_VENTOUSE_TOUTES,
    ),
    ModeleTableau(
        nom="Dimensionnement des vidanges (Annexe 2)",
        fichier_exemple="Exemple_import_vidanges.xlsx",
        colonnes_saisies=COLONNES_VIDANGE_SAIES,
        colonnes_calculees=COLONNES_VIDANGE_CALCULEES,
        toutes_colonnes=COLONNES_VIDANGE_TOUTES,
    ),
]
