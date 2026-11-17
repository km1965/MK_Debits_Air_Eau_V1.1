"""Script de build PyInstaller pour MK_Debits_Air_Eau — VERSION V2.

Génère un exécutable Windows autonome : MK_Debits_Air_Eau_V2.exe
avec l'icône de l'application et la fonction d'import XLSX.

L'exécutable V1 (MK_Debits_Air_Eau.exe) est conservé intact.
"""

import os
import PyInstaller.__main__

BASE = os.path.dirname(os.path.abspath(__file__))
SEP = ";"  # séparateur Windows pour --add-data

# Fichiers de données à embarquer à la racine de l'exécutable
DATAS_RACINE = [
    "Calcul des debits points bas et  hauts.pdf",
    "Note_Verification_195 et 13.39 Hydraulique_AEP compléte.docx",
    "Verification_Evacuation_Air_AEP.docx",
    "Note_Verification_Hydraulique_AEP_Complete.docx",
    "PLAN_DEBIT_AIR_EAU.md",
    "requirements.txt",
    "README.md",
    "Exemple_import_verification.xlsx",
    "Exemple_import_ventouses.xlsx",
    "Exemple_import_vidanges.xlsx",
    "Catalogue_MCP_VENTOUSE AUTOMATIQUE DOUBLE ORIFICE 3 FONCTIONS Type_MCP_validées.pdf",
]

# Ressources graphiques embarquées dans un sous-dossier « assets »
DATAS_ASSETS = [
    "assets/icon.ico",
    "assets/icon.png",
    "assets/catalogue_mcp_courbe_grand_orifice.png",
    "assets/catalogue_mcp_courbe_petit_orifice.png",
]

add_data_args = []
for name in DATAS_RACINE:
    src = os.path.join(BASE, name)
    if os.path.exists(src):
        add_data_args.append(f"--add-data={src}{SEP}.")
    else:
        print(f"[ATTENTION] Fichier introuvable, ignoré : {name}")

for name in DATAS_ASSETS:
    src = os.path.join(BASE, name)
    if os.path.exists(src):
        add_data_args.append(f"--add-data={src}{SEP}assets")
    else:
        print(f"[ATTENTION] Ressource introuvable, ignorée : {name}")

# Icône Windows embarquée dans l'exécutable
chemin_ico = os.path.join(BASE, "assets", "icon.ico")
args_icone = [f"--icon={chemin_ico}"] if os.path.exists(chemin_ico) else []
if not args_icone:
    print("[ATTENTION] Icône absente : assets/icon.ico")

entry_point = os.path.join(BASE, "debits_ae", "main.py")

PyInstaller.__main__.run([
    entry_point,
    "--name=MK_Debits_Air_Eau_V2",
    "--windowed",          # pas de console
    "--onefile",           # un seul exécutable
    "--clean",
    *args_icone,
    *add_data_args,
])
