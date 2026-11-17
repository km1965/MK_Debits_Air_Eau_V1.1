# MK_Debits_Air_Eau

**Calcul des débits air et eau — Points bas et points hauts**  
Application CustomTkinter (Python 3.10+) conforme à la note *"Calcul des débits points bas et hauts.pdf"* (adduction BR3_LOT 8) et corrigée selon `Audit_et_Correction_Note_BR3_LOT8.docx`.

Génère des rapports `.docx` et `.xlsx` et peut être empaqueté en `.exe` Windows avec icône.

---

## 1. Installation

### Prérequis
* Python 3.10+ (testé sous 3.10.11 et 3.14.7)
* Dépendances : `customtkinter`, `python-docx`, `openpyxl`, `matplotlib`

```powershell
pip install -r requirements.txt
```

### Lancement en développement

```powershell
# Encodage UTF-8 recommandé sur la console Windows (cp1252 par défaut)
set PYTHONIOENCODING=utf-8
python -m debits_ae
# ou
python debits_ae/main.py
```

### Nouveauté V2 — Import d'un fichier de vérification .xlsx

Le bouton **« Importer XLSX… »** (bandeau projet, à droite d'« Enregistrer sous… ») permet d'ouvrir un
classeur Excel externe contenant les données d'entrée d'un dossier de vérification. L'application en
extrait les champs (diamètre, longueur, cotes, pentes, coefficients…), les fait recalculer avec ses
propres formules (F1 → F11), et recharge l'interface avec les résultats. Vous pouvez ensuite exporter
un rapport DOCX/XLSX corrigé.

Un fichier exemple est fourni : `Exemple_import_verification.xlsx` (deux formats acceptés :
paires clé|valeur ou tableau avec en-têtes).
```

### Build de l'exécutable Windows (avec icône)

```powershell
python build_exe.py
```

L'exécutable est produit dans `dist/` (`MK_Debits_Air_Eau.exe`).

---

## 2. Utilisation

L'interface comporte 6 onglets :

1. **Vidanges (points bas)** — F1 (débit de décharge Torricelli), F2 (diamètre de vidange, coefficient 6,69 pour 2 h).
2. **Ventouse : dégazage** — F3 (célérité d'Allievi), F4 (débit d'air), F6 (Ø orifice).
3. **Ventouse : remplissage** — F7 (débit eau/air, Ø orifice d2).
4. **Ventouse : admission d'air** — F11 (hauteur motrice H), F10 (débit d'air admission, casse franche).
5. **Sélection d'équipement** — comparaison avec les tables PAM et SNH réelles (page 6 de la note).
6. **Vérifications & rapport** — vitesse de remplissage (0,5 m/s), dégazage (2 % du débit nominal), génération des rapports DOCX/XLSX, registre des formules.

---

## 3. Formules (écrites en clair, pas de LaTeX)

Toutes les formules sont rédigées en français lisible dans les rapports et dans l'onglet "Vérifications" :

* **F1** — Débit de vidange : Q = K · s · √(2 · g · h), K = 0,7.
* **F2** — Diamètre de vidange (2 h) : d(mm) = 6,69 × D × (L / √h)^0,5.
    * L'ancien coefficient 13,39 correspond à 30 minutes, pas à 2 heures (erreur corrigée par l'audit).
* **F3** — Célérité d'Allievi : a = 9900 / √(48,3 + k · D / e), avec k = 10^11 / E.
    * Forme exacte de contrôle : a = 1 / √[ ρ · ( 1/K_eau + D/(E·e) ) ] (≈ 548 m/s pour DN 2000, PRV).
* **F4** — Débit d'air dégazage : Qair = ΔH · g · S0 / a.
* **F5** — Évacuation d'air (Saint-Venant) :
    * Sous 19,55 mCE : Qair = 499 · s · (P1/P2)^0,714 · √[1 − (P1/P2)^0,286].
    * Au-dessus (sonique) : Qair = 129 · s.
    * L'ancienne constante 195 est physiquement fausse et rejetée.
* **F6** — Ø orifice de dégazage : inversion de F5 puis d1 = 2 · √(s / π).
* **F7** — Remplissage : Qeau = Qair = V · S0 (V = 0,5 m/s en vérification).
* **F8** — Débit d'eau / ligne d'énergie (Strickler, conduite pleine, R = D/4) :
    * Qeau = K · (π/4) · (1/4)^(2/3) · D^(8/3) · i^0,5 = 0,3117 · K · D^(8/3) · i^0,5.
    * K = 104 (PRV) ou 100 (fonte).
* **F9** — Bernoulli : H = j · L + ξ · v² / (2 g). ξ = 1 (équation écrite) ou ξ = 2 (mention « k = 2 », retenu par l'audit).
* **F10** — Débit d'air admission (casse franche, formule de l'audit) :
    * Qair = (π · D² / 4) · √[ H / ( ξ/(2g) + 4^(4/3) · L / (K² · D^(4/3)) ) ].
    * Pour K = 104 et ξ = 2 : Qair = (π · D² / 4) · √[ H / (0,102 + 0,000587 · L / D^(4/3)) ], avec 0,102 = 1/g.
    * Valeurs de référence (H = 10,93 m ; L = 848,3 m ; D = 2,0 m ; K = 104) :
        * ξ = 1 : v = 6,6307 m/s, Q = 20,831 m³/s.
        * ξ = 2 : v = 6,0404 m/s, Q = 18,976 m³/s.
* **F11** — Hauteur motrice : H = max(0 ; cote_ventouse − 3 − cote_vidange).

---

## 4. Corrections de l'audit prises en charge

Toutes les corrections de `Audit_et_Correction_Note_BR3_LOT8.docx` sont appliquées :

| # | Domaine | Constat de l'audit | Correction appliquée |
|---|---------|-------------------|----------------------|
| C1 | Vidanges F2 | Coefficient 13,39 (en fait 30 min) | 6,69 pour 2 h |
| C2 | Vidanges Annexe 2 | Coeff. 9,47, longueurs additionnées, hauteur biaisée | 6,69 + hauteur moyenne pondérée |
| C3 | Vidanges DN | Uniformisation DN 400 mm | DN exact par point bas (150 à 500 mm) |
| C4 | Ventouse F3 Allievi | Formule erronée (racine, g, d·E·e) | a = 1/√[ρ·(1/K_eau + D/(E·e))], k = 10^11/E |
| C5 | Ventouse F5 Saint-Venant | Qair = 195 × … (terme moteur manquant) | 499 / 129, constante 195 rejetée |
| C6 | Ventouse d1/d | Vitesse air 195 m/s absurde | Inversion de F5 puis d1 = 2·√(s/π) |
| C7 | Remplissage | V = 1 m/s vs 0,5 m/s | 0,5 m/s retenu (5 655 m³/h DN 2000) |
| C8 | Équipement | Une seule PAM DN200 insuffisante (5 300 < 5 655 m³/h) | 2 ventouses DN200 (ou DN200 + clapet DN150) |
| C9 | Dégazage | 2 % × 5,3 × 3600 = 360 m³/h | 381,6 m³/h (5,3 m³/s, pas 5,0) |
| C10 | Conversion PAM DN200 | « 14 454 (4,165 m³/s) » faux | 14 454 m³/h = 4,015 m³/s ; écart signalé, pas masqué |
| C11 | Points hauts F11 | H appliqué sur 4 lignes seulement | H = max(0 ; cote − 3 − cote) partout |
| C12 | Points hauts équipement | 4 points hauts sous-équipés | Équipements corrigés couvrant tous les débits |

Le rapport généré inclut une section « Audit et comparatif note initiale / note corrigée » (DOCX section 8 ; XLSX feuilles *Comparatif Points Hauts*, *Comparatif Vidanges*, *Corrections Audit*) avec :
* les 10 lignes corrigées de l'Annexe 1 (points hauts) ;
* les 9 lignes corrigées de l'Annexe 2 (vidanges) ;
* les combinaisons d'équipements réelles (aucune référence « PAM 800 » ou « SNH 800 » n'existe dans la note) ;
* le signalement de l'écart de conversion PAM DN200 (4,015 vs 4,165 m³/s).

---

## 5. Rapports

### DOCX (sections)
1. Synthèse des entrées
2. Vidanges — Points bas
3. Ventouse — Points hauts (3 fonctions)
4. Sélection d'équipement
5. Récapitulatif équipements admission d'air (F10) — ξ = 1 et ξ = 2, tables PAM/SNH réelles, combinaisons
6. Vérifications de fonctionnement (page 6 du PDF)
7. Registre de vérification des formules (F1 → F11)
8. Audit et comparatif note initiale / note corrigée (tableaux larges en paysage)

### XLSX (feuilles)
*Synthèse, Vidanges, Ventouse, Equipements, Equipements Admission, Verifications, Graphiques, Formules, Comparatif Points Hauts, Comparatif Vidanges, Corrections Audit*.

---

## 6. Tests

```powershell
set PYTHONIOENCODING=utf-8
python -m unittest discover -s tests -t .
```

* `test_formules.py` — non-régression des formules (F1…F11).
* `test_audit.py` — données d'audit, comparatifs, présence dans les rapports DOCX/XLSX.

37 tests au total (état actuel).

---

## 7. Avertissements importants

* Certaines formules restent marquées **SUSPECT** (F2) ou **À VÉRIFIER / empirique** (F3, Allievi). Elles ne doivent pas servir à un dimensionnement définitif sans validation du bureau d'études.
* L'écart de conversion PAM DN200 (14 454 m³/h vs 4,165 m³/s) est affiché, pas masqué ; il doit être tranché avec le fournisseur avant toute commande.
* Le choix ξ = 1 / ξ = 2 dans F10 reste à confirmer par le bureau d'études (l'audit retient ξ = 2).
* L'audit calcule le PM 57 121,59 avec la cote aval 5,6 m (probable coquille pour 95,6 m) : la valeur 43,96 m³/s est reprise telle quelle, avec réserve.

---

## 8. Fichiers du projet

```
MK_Debits_Air_Eau/
├── README.md                      # Ce document
├── PLAN_DEBIT_AIR_EAU.md          # Plan détaillé du projet
├── requirements.txt               # Dépendances Python
├── build_exe.py                   # Build PyInstaller (.exe + icône)
├── Audit_et_Correction_Note_BR3_LOT8.docx   # Source des corrections
├── Calcul des debits points bas et  hauts.pdf # Note d'origine (Annexes 1 et 2)
├── assets/                        # Icône de l'application
├── debits_ae/                     # Package Python (modèle, formules, UI, rapports, audit)
├── tests/                         # Tests unitaires (unittest)
└── dist/                          # Exécutable Windows produit par le build
```

---

*Application générée avec soin pour mon ami. Tous les calculs et rapports sont en français. Bonne utilisation, frère.* 🛠️
