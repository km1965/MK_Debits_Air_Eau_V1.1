# MK_Debits_Air_Eau — Plan du projet

**Application Python 3.14 — Interface CustomTkinter — Calcul des débits air et eau**  
Conforme à la note : *"Calcul des débits points bas et hauts.pdf"*  
(Note sur l'équipement des points bas et des points hauts de l'adduction BR3_LOT 8)

---

## 1. Contexte et document source

La note technique décrit le dimensionnement des organes de manœuvre et de sécurité d'une conduite d'adduction :

* **Section 2 — Vidanges (points bas)** : chaque point bas est équipé d'un ouvrage de vidange (robinet-vanne sur té) permettant de vider le tronçon correspondant en **2 heures**.
* **Section 3 — Equipement des points hauts** : chaque point haut reçoit une **ventouse automatique** assurant 3 fonctions :
  1. évacuation de l'air lors du remplissage,
  2. dégazage (purge des accumulations d'air) en service,
  3. admission d'air lors des vidanges ou d'une casse franche.
* **Annexe 1** : tableau de dimensionnement des ventouses (données de tranches : cotes, longueurs, pentes, débits d'air calculés, équipements).
* **Annexe 2** : tableau de dimensionnement des vidanges.

---

## 2. Objectif de l'application

Une application de bureau (CustomTkinter) qui permet à un utilisateur de :

1. Calculer le **débit de vidange** et le **diamètre de l'ouvrage de vidange** (points bas).
2. Calculer les **débits d'air** pour les 3 fonctions des ventouses (points hauts).
3. Vérifier la cohérence avec les **coulages des ventouses PAM et clapets SNH** du document.
4. Effectuer les **vérifications de fonctionnement** (vitesse de remplissage, dégazage 2 % Qnom, casse franche).
5. Éditer un **rapport de calcul** faisant apparaître chaque formule avec son statut de vérification (OK / SUSPECT / EMPIRIQUE / À VÉRIFIER / ILLISIBLE).

---

## 3. Analyse et vérification des formules du PDF

L'erreur est humaine : chaque formule extraite du PDF a été vérifiée. Voici le verdict à implémenter dans le module `formulas.py` sous forme de drapeaux.

| # | Formule (tel qu'interprétée du PDF) | Usage | Statut | Commentaire |
|---|---|---|---|---|
| F1 | `Q = K · s · √(2 · g · h)` | Débit déchargé par une vidange | ✅ **OK** | Équation de Torricelli/orifice. Dimensionnellement cohérente (m³/s). K = 0,7 (faibles charges), g = 9,81 m/s². |
| F2 | `d = 13,39 · s · L^0,25 / h^0,5` | Ø vidange (vidange 2 h) | ⚠️ **SUSPECT** | Incohérence dimensionnelle apparente si s en m² et d en mm (m^1,75). Exposants L^0,25 / h^0,5 inhabituels vs une dérivation simple (d ∝ √L / h^0,25). Constante 13,39 non documentée. **À re-dériver ou à valider avec le bureau d'études.** |
| F3 | `a = √( k / ( ρ · (1 + (k/E)·(d/e)) )` | Célérité Allievi (conduite PRV) | ⚠️ **À VÉRIFIER** | ρ = 1000 kg/m³, g = 9,81, E = 20 GPa (PRV), k = 2,07 GPa (eau). Le coeff. d'ancrage ψ de la conduite semble absent (Allievi complet : 1 + (k/E)(d/e)ψ). |
| F4 | `ΔH = a · Qair / (g · S0)` ⇔ `Qair = ΔH · g · S0 / a` | Dégazage (coup de bélier ≤ 10 m) | ✅ **OK** | ΔH = suppression de pression à ne pas dépasser (10 m). S0 = section de la conduite. |
| F5 | `Qair = 195 · s` (si P1 = P2) | Évacuation d'air par orifice | ⚠️ **EMPIRIQUE** | 195 non documenté dans le PDF (vitesse de référence en m/s). À traiter comme une **constante paramétrable** de l'application. |
| F6 | `d1 = d · (ΔH / (19,9 · a))^0,5`, 19,9 = 195/g | Ø orifice de dégazage | ✅ **Cohérent** | Cohérent avec F4 + F5 puisque 195/9,81 ≈ 19,88 ≈ 19,9. |
| F7 | `Qair = 195 · s2 ; Qeau = V · S0 ; d2 = d · (V/195)^0,5` | Remplissage de la conduite | ✅ **OK** | Qair = Qeau. V = vitesse de remplissage (doc : 1 m/s ; vérification page 6 : 0,5 m/s). |
| F8 | `Qeau = (π/4) · K · i^0,5 · d^(8/3)` | Débit d'eau de vidange (Strickler) | ⚠️ **À CONFIRMER** | Le PDF affiche "π/4 5/3" (illisible). K = 70 (rugosité) ici ; K = 104 (PRV) / 100 (fonte) pour la suite. La constante /4^(2,3) du rayon hydraulique semble absorbée dans K ou omise. |
| F9 | `Dénivelée = j · L + v²/(2g)` (pertes singulières k=2) | Bernoulli point haut → point bas | ⚠️ **AMBIGU** | Le texte dit "pertes singulières estimées à v²/2g (k=2)" : contradictoire (k=2 ⇒ 2·v²/2g = v²/g). À clarifier : coeff. de singularité = 1 ou 2 ? |
| F10 | Équation finale Qair (page 5–6) | Débit d'air admission casse franche | ❌ **ILLISIBLE** | Équation probablement matricielle/image, non récupérable par extraction de texte. À **re-dériver** depuis F8 + F9 :<br>`Q = (π/4)·d² · √( H / ( L/(K²·(d/4)^(4/3)) + (1+k_s)/(2g) ) )`. |
| F11 | `H = cote_ventouse − 3 m − cote_vidange` | Hauteur motrice nette (dépression max 3 mce) | ✅ **OK** | Dépression max admise : 3 mce. |

### Anomalies relevées dans le document (à signaler dans l'appli)

1. **Table PAM, DN200, évacuation air** : 14 454 m³/h ≠ 4,165 m³/s (4,165 × 3600 = 14 994 m³/h). Petite incohérence entre les deux colonnes.
2. **Vitesses de remplissage** : la section dimensionnement utilise V = 1 m/s, la vérification page 6 utilise V = 0,5 m/s → à paramétrer.
3. **K variable** : K = 70 (vidange/casse), puis K = 104 (PRV) / 100 (fonte) pour l'admission d'air → choix utilisateur requis.
4. **F2 et F10** ne doivent pas être utilisés sans avis du bureau d'études : l'application affichera une alerte visuelle.

### Cohérences vérifiées (OK dans le doc)

* 5652 m³/h à 0,5 m/s pour une conduite DN2000 : `Q = 0,5 × π/4 × 2² = 1,571 m³/s ≈ 5655 m³/h` ✅
* Dégazage ≈ 2 % du débit nominal : `2 % × 5,3 × 3600 ≈ 382 m³/h ≈ 360 m³/h` ✅
* Conversions m³/h → m³/s des clapets SNH : 9360/3600 = 2,6 ; 16380/3600 = 4,55 ; 28080/3600 = 7,8 ; 46800/3600 = 13 ✅
* Conversion PAM : 3330/3600 = 0,925 ; 8173/3600 = 2,27 ✅

---

## 4. Stack technique

| Couche | Choix | Justification |
|---|---|---|
| Langage | **Python 3.14** (cible), compatible 3.10+ | Version demandée ; code écrit sans fonctionnalités 3.11-only pour rester robuste |
| Interface | **CustomTkinter 6.0.0** | UI moderne, widgets thématiques (sombre/clair), onglets natifs |
| Calculs | Python stdlib uniquement (`math`, `dataclasses`) | Pas de dépendance scientifique lourde ; facilite le déploiement |
| Export | CSV / TXT / rapport texte | Génération de rapport de vérification des formules |
| Tests | `unittest` (stdlib) | Tests unitaires sur chaque formule |

---

## 5. Architecture logicielle

```
MK_Debits_Air_Eau/
├── PLAN_DEBIT_AIR_EAU.md          # Ce document
├── README.md                      # Installation, utilisation, avertissements de vérification
├── requirements.txt               # customtkinter, python-docx, openpyxl, matplotlib, Pillow
├── build_exe.py                   # Build PyInstaller (icône + ressources embarquées)
├── assets/
│   ├── icon.png                   # Icône 1024 × 1024
│   └── icon.ico                   # Icône Windows multi-tailles (16 → 256 px)
├── tools/
│   └── generer_icone.py           # Génération reproductible de l'icône (Pillow)
├── tests/
│   ├── __init__.py
│   ├── test_formules.py
│   └── test_audit.py            # 37 tests de non-régression au total
├── debits_ae/
│   ├── __init__.py
│   ├── audit.py                 # Données d'audit + comparatif note / note corrigée
│   ├── models.py                  # Données projet, résultats, registre des statuts
│   ├── formulas.py                # Moteur de calcul : F1…F11 + alertes + formules à risque
│   ├── project_io.py              # Sauvegarde / chargement `.mkprojet` (JSON)
│   ├── resources.py               # Chemins des ressources (dev et PyInstaller)
│   ├── tables.py                  # Tables PAM et SNH du document
│   ├── charts.py                  # Graphiques matplotlib pour les rapports
│   ├── reporting.py               # Rapports DOCX / XLSX consolidés
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── base_tab.py            # Socle commun des onglets (projet partagé)
│   │   ├── widgets.py             # Champs, résultats, boutons, cadres d'alerte
│   │   ├── main_window.py         # Fenêtre principale + bandeau projet + icône
│   │   ├── tab_vidanges.py        # Onglet 1 — Vidanges (points bas)
│   │   ├── tab_ventouse_degazage.py    # Onglet 2 — Dégazage
│   │   ├── tab_ventouse_remplissage.py # Onglet 3 — Remplissage
│   │   ├── tab_ventouse_admission.py   # Onglet 4 — Admission d'air
│   │   ├── tab_equipement.py      # Onglet 5 — Sélection équipement
│   │   └── tab_verification.py    # Onglet 6 — Synthèse, vérifications, rapport
│   └── main.py                    # Point d'entrée
```

---

## 6. Spécifications fonctionnelles par onglet

### Onglet 1 — Vidanges (points bas)
**Entrées :** longueur de tronçon L (m), diamètre conduit D (m), hauteur moyenne d'eau h (m), coeff. de débit K (défaut 0,7), temps de vidange cible (défaut 7200 s).  
**Sorties :** section s (m²), débit Q (m³/s), diamètre de vidange d (mm) via F2.  
**Alerte :** F2 marqué SUSPECT — résultat à confirmer par le BE.

### Onglet 2 — Ventouse : dégazage (1ère fonction)
**Entrées :** paramètres Allievi (ρ, E, k, d conduit, e épaisseur) → calcul de a (F3) ; ΔH (défaut 10 m) ; section conduite S0.  
**Sorties :** célérité a (m/s), débit d'air admissible Qair (m³/s), Ø orifice de dégazage d1 (mm) via F6.  
**Alertes :** F3 à vérifier ; ΔH ne doit pas dépasser 10 m.

### Onglet 3 — Ventouse : remplissage (2ème fonction)
**Entrées :** vitesse de remplissage V (défaut 1 m/s, paramétrable 0,5), diamètre conduit d.  
**Sorties :** Qeau (m³/s), Qair (m³/s), Ø orifice d2 (mm) via F7.  
**Alerte :** F5 corrigé (constante 195 rejetée ; Saint-Venant 499 / 129).

### Onglet 4 — Ventouse : admission d'air (vidange / casse franche) (3ème fonction)
**Entrées :** K (70 / 104 / 100), pente i (m/m), diamètre conduit d (m), longueur L (m), hauteur motrice H (m) — H = cote_ventouse − 3 − cote_vidange (F11).  
**Sorties :** vitesse v (m/s), débit d'eau Qeau (m³/s), débit d'air Qair = Qeau (m³/s).  
**Alertes :** F9 ambigu (coeff. singularité ξ exposé, ξ = 2 retenu par l'audit) ; F10 re-dérivée selon la formule de l'audit (0,102 + 0,000587·L/D^(4/3) pour K = 104, ξ = 2).

### Onglet 5 — Sélection d'équipement
Comparaison du Qair calculé avec :
* Table PAM (admission air à dépression 3 m ; évacuation air à surpression 1 m) : DN100, DN150, DN200.
* Table SNH (clapets d'entrée d'air) : DN100…DN250.
**Sortie :** préconisation du DN d'équipement (premier DN dont le débit admis ≥ Qair calculé).  
**Alerte :** incohérence relevée dans la table PAM DN200 (14 454 m³/h vs 4,165 m³/s).

### Onglet 6 — Vérifications & rapport
* Vitesse de remplissage maintenue à 0,5 m/s → débit 5652 m³/h pour DN2000.
* Dégazage = 2 % du débit nominal de la conduite.
* Génération d'un rapport texte listant toutes les formules F1…F11 avec leur statut et commentaires.
* Export CSV des résultats de calcul.

---

## 7. Plan de mise en œuvre (phases)

| Phase | Tâches | Livrable |
|---|---|---|
| 1 | Squelette du package, `models.py`, `formulas.py` (F1…F11 + drapeaux) | `debits_ae/` fonctionnel en CLI |
| 2 | `tables.py` (PAM, SNH, exemple Annexe 1) + logique de sélection DN | Sélection d'équipement |
| 3 | Interface CustomTkinter : fenêtre principale + 6 onglets | UI utilisable |
| 4 | Alertes de vérification, rapport texte/CSV, README | Rapport de conformité |
| 5 | Tests unitaires (`unittest`) sur les formules, recette sur données Annexe 1 | Application validée |

---

## 8. Tests et validation

* Tests unitaires sur `formulas.py` : valeurs attendues calculées à la main pour chaque formule.
* Test de recette sur les données de l'Annexe 1 (premières tranches) : vérifier que l'application retrouve les équipements préconisés (ventouse DN200, clapets DN200/DN250, purgeur PSA250).
* Vérification que les alertes s'affichent pour les formules encore non validées : F2 (SUSPECT) et F3 (À VÉRIFIER / empirique). F1, F4, F6, F7, F8, F10, F11 sont OK ou COHÉRENT ; F5 est validé (Saint-Venant 499/129).
* **Nouveau** : tests d'audit (`test_audit.py`) sur le comparatif note initiale / note corrigée (Annexes 1 et 2) et sur la présence du comparatif dans les rapports DOCX/XLSX.

---

## 9. Notes importantes

* **Python 3.14** : à la date du projet, 3.14 est récente / en cours de déploiement. Le code est écrit compatible **Python 3.10+** pour fonctionner immédiatement, y compris sur l'environnement actuel (Python 3.10.11), et restera valide sous 3.14.
* **Responsabilité** : les formules marquées SUSPECT / À VÉRIFIER / ILLISIBLE ne doivent pas être utilisées pour un dimensionnement définitif sans validation par le bureau d'études. L'application affiche ces avertissements à l'écran (F2, F3 restent signalés).
* **Audit BR3_LOT 8** : toutes les corrections de `Audit_et_Correction_Note_BR3_LOT8.docx` sont prises en compte (F2 = 6,69 ; Saint-Venant 499/129 ; Allievi 10^11/E ; K Strickler 104 PRV / 100 fonte ; F10 = 0,000587 avec ξ = 2 ; H borné à 0). Un chapitre « Audit et comparatif note initiale / note corrigée » (section 8 du DOCX, feuilles dédiées du XLSX) recense les 12 corrections, les tableaux recalculés des Annexes 1 et 2 et le comparatif des équipements.
* **Unités** : toutes les entrées en unités SI (m, m³/s, m/s, mce) sauf les diamètres d'équipement affichés en mm.

---

## 10. Architecture V2 — dossier projet partagé (implémentée)

### 10.1 Modèle unique `Projet`

`debits_ae/models.py` expose désormais :

* `DonneesProjet` : identité du dossier + données hydrauliques communes
  (D, L, h, pente, cotes, matériau, k Allievi, e, ΔH, P2, vitesses,
  coefficients de rugosité, paramètres de vérification).
* `Projet` : `donnees`, `vidange`, `ventouse`, `equipements`, `verification`,
  plus les méthodes :
  * `etapes()` — avancement des 6 étapes du workflow ;
  * `prochaine_etape()` — prochaine action recommandée ;
  * `resume_texte()` — synthèse utilisée en en-tête des rapports ;
  * `to_dict()` / `from_dict()` — sérialisation JSON compatible ascendante.

Les 6 onglets lisent et écrivent le **même** objet `Projet` : une valeur
saisie dans un onglet est réutilisée par les autres, et un calcul ne peut
plus écraser les résultats d'une autre fonction de la ventouse (fusion des
trois fonctions dans `Projet.ventouse`).

### 10.2 Sauvegarde / chargement `.mkprojet`

`debits_ae/project_io.py` :

* `sauvegarder_projet(projet, chemin)` — JSON UTF-8, extension `.mkprojet` ;
* `charger_projet(chemin)` — reconstruction typée des dataclasses.

Le bandeau de la fenêtre principale propose : **Nouveau**, **Ouvrir…**,
**Enregistrer**, **Enregistrer sous…**. Au chargement, tous les onglets sont
resynchronisés et les résultats sont réaffichés.

### 10.3 Tableau de bord et workflow guidé

L'onglet 6 « Synthèse & Rapport » affiche :

* l'identité du dossier (référence, site, maître d'ouvrage) ;
* l'état des 6 étapes (● fait / ○ à faire) ;
* la prochaine étape recommandée ;
* un résumé chiffré de chaque résultat ;
* le nombre et la liste des formules à valider.

### 10.4 Export consolidé et verrouillage

Le rapport DOCX/XLSX rassemble les résultats des 6 onglets, les graphiques
et le registre des formules. Avant export, l'application :

1. refuse un rapport vide ;
2. affiche la liste des formules à risque réellement utilisées
   (`formules_a_risque(projet)`) et demande une confirmation explicite.

### 10.5 Statuts alignés sur la note de vérification

Le registre et les rapports ne mentionnent plus « Empirique (195) » :

* F3 (célérité d'Allievi) → **OK** — formule exacte confirmée (Partie 3 de la
  note). L'ambiguïté `k = 10^10/E` vs `10^11/E` est tranchée en faveur de
  `10^11/E` (les valeurs du tableau l'imposent) et signalée dans le
  commentaire de la formule.
* F6 (orifice de dégazage) → **COHÉRENT** — formule dérivée de F4 et F5
  validées (inversion de Saint-Venant), avec réserve documentée sur le cas
  `P2 ≤ P1`.
* F7 (remplissage / orifice d2) → **OK**.
* F10 (admission d'air casse franche) → **COHÉRENT** — formule de l'audit
  (`0,102 + 0,000587·L/D^(4/3)` pour K = 104, ξ = 2). L'ambiguïté ξ = 1 / ξ = 2
  reste exposée dans l'interface et signalée dans le rapport.

### 10.6 Tests de non-régression

`tests/test_formules.py` (16 tests, `unittest`) verrouille les points validés :

* coefficient F2 = 6,693 pour 2 h (et 13,39 pour 30 min) ;
* Saint-Venant : 97,6 / 122,9 / 129,1 m³/s pour s = 1 m² ;
* Allievi : a ≈ 763,1 m/s pour la fonte ductile, équivalence `E → k = 10^11/E` ;
* inversion F6 et fallback `P2 = P1 + ΔH` (diamètre non nul + alerte) ;
* F6 au statut `COHÉRENT` et `formules_a_risque()` limité à F10 ;
* aller-retour JSON `.mkprojet` et rejet d'un fichier invalide.

Commande : `python -m unittest discover -s tests -t .`

### 10.7 Corrections de robustesse

* `qair_degazage(..., gravite=...)` : l'appel erroné `G=` est corrigé.
* `qair_admission_casse(hauteur, longueur, diamètre)` : l'appel à 4 arguments
  est corrigé.
* `diametre_orifice_degazage` : si `P2 ≤ P1`, l'application retient
  `P2 = P1 + ΔH` (pression absolue atteinte pendant la surpression) et
  signale explicitement l'hypothèse, au lieu de retourner un diamètre nul.

### 10.8 Identité visuelle et icône

* `assets/icon.png` (1024 × 1024) et `assets/icon.ico` (16, 24, 32, 48, 64,
  128, 256 px) : goutte d'eau et bulles d'air dans une bride de conduite,
  palette navy / cyan / teal cohérente avec l'interface.
* `tools/generer_icone.py` régénère l'icône de façon reproductible (Pillow),
  sans dépendance à un service externe.
* `debits_ae/resources.py` localise les ressources en développement comme
  dans l'exécutable « onefile » (`sys._MEIPASS`).
* La fenêtre applique l'icône à la barre de titre et à la barre des tâches ;
  `build_exe.py` l'embarque dans l'exécutable via `--icon` et `--add-data`.

## 11. Nouveauté V2 — Import de fichier de vérification .xlsx

Le bouton **« Importer XLSX… »** (bandeau projet, à droite d'« Enregistrer sous… »)
permet d'ouvrir un classeur Excel externe contenant les données d'entrée d'un
dossier de vérification. L'application en extrait les champs (diamètre, longueur,
cotes, pentes, coefficients…), les fait recalculer avec ses propres formules
(F1 → F11), et recharge l'interface avec les résultats. Deux formats de saisie
sont acceptés : paires clé|valeur ou tableau avec en-têtes.

Un fichier exemple est fourni : `Exemple_import_verification.xlsx`.

### Double exécutable

* `dist/MK_Debits_Air_Eau.exe` — version V1 (historique, sans import XLSX).
* `dist/MK_Debits_Air_Eau_V2.exe` — version V2 (avec import XLSX).

Les deux builds sont produits par PyInstaller (`--onefile`, icône embarquée) :
* `build_exe.py` → V1
* `build_exe_v2.py` → V2

Commande : `python -m unittest discover -s tests -t .` (37 tests).
