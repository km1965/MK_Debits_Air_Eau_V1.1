"""Génère les fichiers exemples d'import pour les tableaux de dimensionnement."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from pathlib import Path

REMPISSAGE = PatternFill("solid", fgColor="1F3B5C")
POLICE = Font(bold=True, color="FFFFFF")
ALIGN_C = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _style_entete(ws, entetes, ligne=1):
    for c, h in enumerate(entetes, start=1):
        cell = ws.cell(row=ligne, column=c, value=h)
        cell.fill = REMPISSAGE
        cell.font = POLICE
        cell.alignment = ALIGN_C


def _largeurs(ws, largeurs):
    for c, w in enumerate(largeurs, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w


# ===========================================================================
# Exemple VENTOUSES (Annexe 1)
# ===========================================================================
wb = Workbook()
ws = wb.active
ws.title = "Ventouses"

entetes = [
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
    # Colonnes calculées par Python (laisser vides ou pré-remplies à 0)
    "Dénivelée tronçon amont (m)",
    "Dénivelée tronçon aval (m)",
    "Pente tronçon amont (m/m)",
    "Pente tronçon aval (m/m)",
    "Débit d'air calculé Qair amont (m3/s)",
    "Débit d'air calculé Qair aval (m3/s)",
    "Qair max (m3/s)",
]
_style_entete(ws, entetes)

# Quelques lignes d'exemple (calculées automatiquement à l'import)
lignes = [
    ["50 529,89", 112.98, "49 681,6", 99.05, "50 741,6", 110.4, 2.0, 848.3, 11.9,
     "2 ventouse DN200 + 1 clapet DN250", 21.33, None, None, None, None, None, None, None],
    ["51 041,59", 111.5, "50 741,6", 110.4, "51 801,59", 105.55, 2.0, 300.0, 760.0,
     "1 purgeur sonique PSA250 + 1 Clapet d'entrée d'air DN250", 13.0, None, None, None, None, None, None, None],
    ["51 801,59", 105.55, "", None, "52 621,6", 100.64, 2.0, "", 820.0,
     "1 ventouse DN200", 4.17, None, None, None, None, None, None, None],
    ["53 561,59", 103.4, "52 621,6", 100.64, "54 041,6", 98.4, 2.0, 940.0, 480.0,
     "1 purgeur sonique PSA250 + 1 Clapet d'entrée d'air DN250", 13.0, None, None, None, None, None, None, None],
    ["57 121,59", 101.8, "56 845,3", 5.6, "58 721,6", 93.8, 1.6, 276.3, 1600.0,
     "1 ventouse DN200 + 3 clapets DN250", 43.17, None, None, None, None, None, None, None],
]
for r, ligne in enumerate(lignes, start=2):
    for c, val in enumerate(ligne, start=1):
        ws.cell(row=r, column=c, value=val)

_largeurs(ws, [16, 14, 16, 14, 16, 14, 12, 16, 16, 34, 18, 16, 16, 16, 16, 18, 18, 14])

out = Path("D:/MK_PROJETS/MK_Debits_Air_Eau/Exemple_import_ventouses.xlsx")
wb.save(out)
print("Créé :", out)

# ===========================================================================
# Exemple VIDANGES (Annexe 2)
# ===========================================================================
wb = Workbook()
ws = wb.active
ws.title = "Vidanges"

entetes = [
    "PM Am",
    "Cprojet Am",
    "PM (ventouse amont)",
    "Cprojet (ventouse amont)",
    "PM (ventouse aval)",
    "Cprojet (ventouse aval)",
    "DN conduite (m)",
    "Longueur tronçon amont (m)",
    "Longueur tronçon aval (m)",
    # Colonnes calculées par Python (laisser vides)
    "Dénivelée tronçon amont (m)",
    "Dénivelée tronçon aval (m)",
    "Diamètre t=1h (mm)",
    "Diamètre t=2h (mm)",
    "Diamètre retenu T=2h (mm)",
    "Diamètre vidange (mm)",
]
_style_entete(ws, entetes)

lignes = [
    ["50 741,59", 110.41, "50 529,89", 112.98, "51 041,59", 111.5, 2.0, 211.70, 300.00, None, None, None, None, None, None],
    ["52 621,59", 100.64, "51 041,59", 111.5, "53 561,59", 103.4, 2.0, 1580.00, 940.00, None, None, None, None, None, None],
    ["54 041,59", 103.4, "53 561,59", 103.4, "54 264,59", 102.0, 2.0, 480.00, 223.00, None, None, None, None, None, None],
    ["54 661,59", 99.3, "54 264,59", 102.0, "54 783,45", 102.4, 2.0, 397.00, 121.90, None, None, None, None, None, None],
    ["58 721,59", 93.8, "57 121,59", 101.8, "58 961,59", 94.5, 2.0, 1600.00, 240.00, None, None, None, None, None, None],
]
for r, ligne in enumerate(lignes, start=2):
    for c, val in enumerate(ligne, start=1):
        ws.cell(row=r, column=c, value=val)

_largeurs(ws, [16, 14, 18, 18, 18, 18, 12, 16, 16, 16, 16, 14, 14, 16, 16])

out = Path("D:/MK_PROJETS/MK_Debits_Air_Eau/Exemple_import_vidanges.xlsx")
wb.save(out)
print("Créé :", out)
