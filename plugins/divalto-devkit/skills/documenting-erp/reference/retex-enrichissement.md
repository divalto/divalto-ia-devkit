# RETEX : Enrichissement d'une entité ERP Divalto depuis les sources X.13

**Contexte** : retour d'expérience détaillé des apprentissages pour généraliser
l'enrichissement automatique CLI à toutes les autres entités métier (FOU, ART,
SOC, VRP, C3, C4, C5, etc.). Ce document capitalise les patterns de sources,
les pièges rencontrés, et la chaîne de résolution qui amène à un livrable
"très satisfaisant" (≥2.8/3).

## Sources X.13 mobilisées (5 types)

| Source | Rôle | Fichier type |
|---|---|---|
| **Dictionnaire** | Structure table, champs, Natures, libellés | `<prefixe>dd.dhsd` (gtfdd, ccfdd, rtlfdd...) |
| **Masque écran** | Titre, onglets, pages, zooms, listes codifiées | `<code>_sql.dhsf` (ex: gtez021_sql.dhsf = zoom CLI) |
| **Module programme** | Dépendances, modules référencés | `<code>_sql.dhsp` (ex: gttz021_sql.dhsp) |
| **Module Check (objet métier)** | PK métier, API publique, règles, constantes | `gttmchk<entity>.dhsp` (ex: gttmchkcli.dhsp) |
| **Dictionnaire multi-choix** | Valeurs concrètes des listes codifiées | `gtfdmc.json` (partiel) + `gtfdmc.dhfi` (complet ISAM) |

## Patterns structurels appris

### 1. Dictionnaire .dhsd — structure réelle

**Erreur classique** : croire que les champs d'une table sont dans `Champs=` de
la section `[TABLE]`. **Réel** : la section `[TABLE]` ne contient que les
métadonnées (Nom, Description, Taille, CE). La **liste des champs** est dans
une sous-section `[CHAMPS]` (pluriel) qui suit immédiatement :

```
[TABLE]
Nom=Cli,Client,1
NomOdbc=Client
Taille=3700,3700
CE=Ce1,3
[CHAMPS]
Nom=Ce1,1,2,N,0,0,N,3
Nom=Ce2,2,2,N,0,0,N,3
...
Nom=ZonaPCF,1376,2,N,0,0,N,3
Nom=Filler,2861,2,N,0,40,N,1
Nom=UCli,2901,2,N,0,0,N,3
[/CHAMPS]
```

**Note importante** : les **zones composites** (ZonaPCF, ZonaCF, ZonaSpC) sont
des zones de **réserve binaire de taille fixe**, pas des structures composites.
Les "vrais" champs logiques (NOM, ADR, SIRET, TEL) sont dans les `[CHAMP]` globaux
(singulier, top-level) mais ne sont **pas listés** dans le `[CHAMPS]` de la table.

**Conséquence pour le parser** : il faut indexer **tous les `[CHAMP]` globaux**
du `.dhsd` et faire un lookup case-insensitive par nom de champ pour enrichir
les 241 champs SQL avec leurs libellés.

**Mon score CLI** : 16 → 174/241 champs labellisés grâce à ce lookup global.

### 2. Casse des noms de table

**Piège** : la table `CLI` en SQL est nommée `Cli` (PascalCase) dans le `.dhsd`.
Le parser doit faire un matching case-insensitive sur le nom de table et
l'indexation des `[CHAMP]`.

### 3. Module Check — l'objet métier

La "mine d'informations" que Stéphane a signalée. 4 patterns clés à extraire :

| Pattern | Ce que ça donne | Exemple CLI |
|---|---|---|
| `Define <Entity>_FieldNames_Min = "..."` | **Clé primaire métier + champs obligatoires** | `"Dos;Tiers;Nom;HsDt;Etb;Visa;Conf;Feu"` → PK = `(Dos, Tiers)` |
| `Check_<Entity>_Field_<Field>[_Lib]` procs | **FK confirmée sur le champ** (validation + libellé zoom) — source de vérité complémentaire du masque : une FK métier a toujours un `Check_<Entity>_Field_<Field>` associé | `Check_CLI_Field_Pay`, `Check_CLI_Field_Dev`, `Check_CLI_Field_Cpt`, `Check_CLI_Field_Lang` → FK confirmées par le Module Check même si le masque ne les expose pas via `f8` |
| `Authorize_<Entity>_<Op>` procs | **Règles d'autorisation** (Insert/Update/Delete) | `Authorize_CLI_Insert`, `Authorize_CLI_Update`, `Authorize_CLI_Delete` |
| `Const C_<Name> = value` | **Constantes métier** (codes produits, flags, seuils) | `C_CGV_IMPLICITE = 4`, `C_TypeDeTitreSocial_1_Professionel = 1` |

**PK métier vs PK SQL** : la clé `CLI_ID` (auto-incrément SQL) est différente de
la clé métier `(Dos, Tiers)`. Le livrable doit montrer la **métier en priorité**,
la SQL comme info technique secondaire.

### 4. Masque .dhsf — les bindings de zoom

```
[rubrique]
 [description]
  donnee=<record>,<champ>,<alias>[,<index>]    ← nom du champ
 [param_saisie]
  table_associee=oui                            ← flag FK zoom actif
 [touches]
  f8=<zoom_code>                               ← SEULE touche FK valide
  f7=135                                       ← piège touche (tri, pas FK)
  f1=1                                         ← piège touche (aide, pas FK)
```

**Piège 1** : `table_associee=oui` est un **flag booléen**, pas un nom de table !
Le nom réel du champ est dans `donnee=client,<CHAMP>,client`. Le nom de la table
cible doit être déduit par convention (champ `PAY` → table `PAYS`, champ `TACOD`
→ table `T008 tarif`, etc.).

**Piège 2 (majeur)** : **seul `f8` est un binding FK**. Les touches `f1` et `f7`
sont des **pièges touches génériques** :
- `f1=1` : aide standard (pas ciblé sur une table)
- `f7=135` : tri/liste codifiée générique (pas ciblé sur une table)
- `f8=<zoom_code>` : **vrai zoom FK** (ex: 9053=pays, 9021=tiers, 9047=devise, 9930=tarif)

Dans une même rubrique, on peut trouver à la fois `f1=1`, `f7=135` **et** un
`f8=9053` : ne capturer que le f8. Un parseur naïf qui prend "la première
touche trouvée" dans la fenêtre rapporterait f1 ou f7 alors que le f8 spécifique
existe plus bas.

**Stratégie du parseur** :
```python
# Chaque table_associee=oui → chercher dans les ~500 chars qui suivent :
# - uniquement ^\s*f8\s*=\s*(\w+)   (pas f1 ni f7)
# Si aucun f8 trouvé : ce n'est pas une FK par masque (peut l'etre par Module Check)
```

**Mon score CLI** : 73 relations confirmées via f8 + `table_associee=oui` (écart
avec le précédent décompte : zéro FK "fantôme" via f1/f7 mal attribuées).

### 4bis. Canal le plus fiable : `diva_apres` + `Check_<Entity>_Field_<Field>`

Chaque rubrique du masque a souvent un `diva_apres="<NomProc>"` qui désigne
une procédure exécutée **après saisie** du champ. Cette procédure (embarquée
dans le même `.dhsf` en section `[diva]`, ou dans un module lié) appelle le
plus souvent un `Check_<Entity>_Field_<Field>[_Lib](...)` de l'objet métier.
Cet appel est la **preuve la plus directe** d'une FK : le champ saisi est
validé contre l'objet métier cible.

**Exemple CLI** (`gtez021_sql.dhsf`) :
```
[rubrique]
 [description]
  donnee=client,TACOD,client
 [param_saisie]
  diva_apres="Champ_Tacod_1_Ap"      ← procedure appelee apres saisie
 [touches]
  f8=9930                             ← zoom tarif
  table_associee=oui
```

Et dans le même fichier, section `[diva]` :
```
Public Procedure Champ_Tacod_1_Ap			;controle tarif ht
Beginp
    Check_CLI_Field_TaCod_Lib(CLIENT.CLI,CLIENT.CodeTarifHT_Lib)
Endp
```

**Valeur ajoutée** : même un champ SANS `f8` (pas de zoom standard) est confirmé
FK si sa proc `diva_apres` appelle un `Check_<Entity>_Field_<Field>`.

**Mon score CLI** : 62 FK confirmées via ce canal ; **+6 FK** découvertes uniquement
par ce canal (sans `f8`). Total final : 79 FK confirmées.

### 4ter. Vraie table cible FK : `Find_<Table>` dans `Check_<Entity>_Field_<Field>`

La procédure `Check_<Entity>_Field_<Field>` du Module Check contient généralement
un appel `Find_<TableName>(...)` ou `Lectab(<num>, ...)` qui révèle la **vraie
table cible** de la FK (pas juste le nom du champ).

**Exemple** dans `gttmchkcli.dhsp` :
```diva
Public function int Check_CLI_Field_TaCod(&CLI)
    ...
    freturn (Find_T014(TiCod, CLI.TaCod, context=true))
endf
```

→ Le champ `TACOD` de CLI pointe vers la table **T014**, et le `.dhsd` donne
son libellé : **"Libellé code tarif"**.

**Pipeline d'enrichissement** :
1. Parse le Module Check : pour chaque `Check_<Entity>_Field_<Field>`, extraire le
   premier `Find_<Table>(...)` qui n'est pas un self-call
2. Lookup des libellés depuis le `.dhsd` (top-level `[TABLE]` → champ `Nom=X,Description,1`)
3. Remplacer `target_entity = <CHAMP>` par `target_entity = <TABLE>` et ajouter
   `target_entity_label = <libellé>`

**Rendu final** : `CLI → T014 (Libellé code tarif) via champ TACOD` au lieu de
`CLI → TACOD via champ TACOD` (qui était ambigu).

**Mon score CLI** : 47 tables cibles résolues avec leur libellé (T001 famille
tarif, T006 règlement, T007 devise, T014 tarif, T048 titre, C3 compte comptable,
VRP commercial, MUSER utilisateur, etc.).

### 5. Listes codifiées (CE1..CEA, FAMOD, PERIOD, FEU...)

Dans le masque, une rubrique peut référencer une liste de valeurs :
```
choix="gtfdmc.dhfi","<choix_id>"
```

Les valeurs sont dans deux fichiers :
- **`gtfdmc.json`** : 8 listes custom (ex: FEU_1, AFFETAT_*) — partiel
- **`gtfdmc.dhfi`** : fichier ISAM binaire — complet mais nécessite lecture via
  `DhxIsam64.dll` + structure JSON dédiée (pas fournie, à créer)

**Stratégie appliquée** :
- Lire `gtfdmc.json` d'abord (lecture triviale, 8 valeurs)
- Marquer les choix_id non couverts comme "à lire via `reading-isam-files`" avec
  la commande exacte à exécuter

## Stratégie de résolution des [A VERIFIER]

Le principe de Stéphane : **traiter, pas supprimer**. Chaque [A VERIFIER] doit
être :
1. **Confirmé** (promotion en fait sourcé) — nouveau parser ou nouvelle source
2. **Reclassé** (nouveau type plus précis) — ex: DOS/ETB = `partitioning`, pas FK
3. **Supprimé avec traçabilité** si aucune source ne peut confirmer (noté dans
   `meta._dropped_heuristic_relations` pour audit)

### Application aux heuristiques de relations (`extract_relations.py`)

Le `FIELD_TO_ENTITY_HINT` propose des relations probables basées sur le nom du
champ (DOS→SOC, PAY→PAYS, etc.). Elles sont **toutes marquées [A VERIFIER]** au
départ. La résolution dans `assemble_model.resolve_heuristic_relations` :

| Cas | Action |
|---|---|
| `DOS` ou `ETB` | → type=`partitioning` (pas une FK classique, champ multi-tenant) |
| `sf in field_check_procedures.by_field` | → FK **confirmée** via Module Check, note les procs Check_<Entity>_Field_<Field> |
| Confirmé dans `schema.confirmed_relations` (f8+table_associee) | → FK **confirmée** via masque |
| Aucune des conditions | → **supprimée**, tracé dans `meta._dropped_heuristic_relations` |

**Résultat CLI** : 73 FK confirmées via f8+masque + FK confirmées via Check_Field + 2 partitioning (DOS, ETB) + 0 [A VERIFIER].

## Criticité dérivée automatiquement

Plutôt que placeholder `[A ENRICHIR]`, dériver de signaux X.13 :

```python
score = 0
# masque
if pages >= 30: score += 2  elif pages >= 10: score += 1
if f8_count >= 100: score += 2  elif f8_count >= 30: score += 1
# module check
if size_kb >= 100: score += 2  elif size_kb >= 30: score += 1
if procs_pub >= 100: score += 2  elif procs_pub >= 30: score += 1
# module principal
if modules_ref >= 15: score += 1

if score >= 5: criticality = "core"
elif score >= 2: criticality = "standard"
else: criticality = "peripheral"
```

**Résultat CLI** : score 9 → `core` (ecran 33 pages, 179 zooms F8, Module Check
137 Ko, 175 procédures publiques, 62 modules références).

## Pipeline généralisé pour une entité N

Pour enrichir FOU (ou toute autre entité) selon la même méthode :

```bash
# 1. Identifier les 4 fichiers sources X.13
# (Naming convention DAV : entity en majuscules uppercase, sauf pour le dict_file)
ENTITY=FOU       # ou ART, SOC, VRP, ...
MODULE=DAV
BASE=GTFPCF      # base du tiers
MCHK=Achat-Vente/source/Dav/gttmchk${entity,,}.dhsp   # gttmchkfou.dhsp
SCREEN=Achat-Vente/source/Dav/gtez<code>_sql.dhsf    # code zoom ex: 022 pour FOU
PROGRAM=Achat-Vente/source/Dav/gttz<code>_sql.dhsp

# 2. Lancer le pipeline
py extract_narrative.py --entity FOU --module DAV --base GTFPCF \
   --dict .../gtfdd.dhsd \
   --main-screen .../gtezFOU.dhsf \
   --main-module .../gttzFOU.dhsp \
   --module-check .../gttmchkfou.dhsp \
   --choix-json .../gtfdmc.json \
   --output out/doc-erp/DAV/entity/FOU.narrative.yaml

py merge_narrative.py --entity-partial ...FOU.partial.yaml \
   --narrative ...FOU.narrative.yaml --output ...FOU.yaml

py assemble_model.py --module DAV --input out/doc-erp/DAV/ --output out/doc-erp/DAV/
py render_markdown.py --input out/doc-erp/DAV/ --layer all --output out/doc-erp/DAV.md
py render_pdf.py --input out/doc-erp/DAV.md --output out/doc-erp/DAV.pdf
```

### Naming conventions à identifier par entité

Le plus simple : lister pour chaque entité dans une table de correspondance :

| Entité | Écran principal | Module Check | Programme zoom |
|---|---|---|---|
| CLI | gtez021_sql.dhsf | gttmchkcli.dhsp | gttz021_sql.dhsp |
| FOU | [à identifier] | gttmchkfou.dhsp | [à identifier] |
| ART | [à identifier] | gttmchkart.dhsp | [à identifier] |
| SOC | [à identifier] | gttmchksoc.dhsp | [à identifier] |
| VRP | [à identifier] | gttmchkvrp.dhsp | [à identifier] |

Pour identifier : chercher avec `find . -iname "gtez*" | head -20` ou analyser
le menu ERP pour retrouver le code zoom standard (cf. `archive/CLAUDE-DIVA.md`
et `archive/exploration-erp-*`) — mais attention à la règle d'autonomie, on ne
peut pas stocker ces mappings dans `archive/` côté skill distribué.

## Stratégie CE (codes d'état multi-drapeaux Ce1..CeA)

**Problème identifié** : toutes les entités DAV ont 10 champs `Ce1`..`CeA` de
Nature=1 (char(1)) en début de table. Ce sont des drapeaux de classification,
mais **ils ne sont pas tous utilisés** — certains sont des réserves pour
extensibilité future. Sans analyse dédiée, le livrable les affiche sans
distinction, ce qui est bruyant et peu informatif.

**Stratégie** (implémentée dans `analyze_ce_fields` du parser) : croiser 3 sources
X.13 pour déterminer pour chaque CE :

| Source | Signal dérivé |
|---|---|
| **Indexes SQL** (`sql-schema/indexes/<entity>.json`) | Nombre d'indexes utilisant ce CE → usage réel en filtrage |
| **Module Check** (procédures `.dhsp`) | Comparaisons `CLI.Ce1 = '3'`, affectations `CLI.Ce4 := 'C'` → valeurs observées dans le code |
| **Structure champ SQL** | Nature=1 toujours (char(1)) |

**Règles de classification** :

```
- ≥5 indexes + c'est Ce1          → "drapeau principal de statut/filtrage"
- ≥2 indexes avec STAT_000*       → "classement statistique"
- ≥2 indexes avec TIERSGRP        → "classement groupement tiers"
- 1 index                         → "indexe secondaire"
- 0 index + valeurs observées     → "utilise dans le code uniquement"
- 0 index + aucune valeur         → "reserve pour extensibilite future"
```

**Piège extraction valeurs** : un premier parseur naïf utilisait le regex
`CLI.CeX = ["\']?([0-9A-Z])["\']?` avec **guillemets optionnels**. Dans une
ligne comme `CLI.Ce3 = Condition(CLI.TiersGrp <> ' ', '1', ' ')`, le regex
matche alors `C` (le premier caractère de `Condition(`) au lieu des vraies
valeurs `'1'` et `' '`. Conséquence : CE3, CE4, CE5, CE6 affichaient tous
la valeur bidon `'C'`.

**Stratégie corrigée** :
1. Pour chaque ligne qui mentionne `<Record>.CeX`, extraire **tous les
   littéraux quotés de 0-3 chars** (`'(\w{0,3})'` avec guillemets obligatoires)
2. Accepter `[0-9A-Za-z ]{0,3}` pour capturer aussi l'espace `' '` (valeur
   "non renseigné" très fréquente)
3. Déduire le rôle à partir des **co-colonnes** de l'index (STAT_* → stat,
   TIERSGRP → groupement, etc.) plutôt que d'un critère générique

**Résultat sur CLI (après correction)** :

| CE | Statut | Rôle inféré | Valeurs observées | Indexes |
|---|---|---|---|---|
| CE1 | ✓ actif | drapeau principal de statut/filtrage (19 indexes) | `'3'` | INDEX_B_CLI, C_CLI, E_CLI, +16 |
| CE2 | ✓ actif | utilisé dans le code (pas d'index dédié) | `'1'` | — |
| CE3 | ✓ actif | classement groupement tiers (co-indexé avec TIERSGRP) | `' '`, `'1'` | INDEX_J_CLI |
| CE4 | ✓ actif | classement statistique (co-indexé avec STAT_0001) | `' '`, `'1'` | INDEX_F/G/H_CLI |
| CE5 | ✓ actif | classement statistique (co-indexé avec STAT_0002) | `' '`, `'1'` | INDEX_K/L/M_CLI |
| CE6 | ✓ actif | classement statistique (co-indexé avec STAT_0003) | `' '`, `'1'` | INDEX_N/O/P_CLI |
| CE7 | ○ reservé | extensibilité future | — | — |
| CE8 | ○ reservé | extensibilité future | — | — |
| CE9 | ○ reservé | extensibilité future | — | — |
| CEA | ○ reservé | extensibilité future | — | — |

**Limite actuelle** : l'extraction de valeurs reste limitée aux littéraux quotés
courts. Les valeurs utilisées dans des `in ('1','2','3')` multi-args ou via des
constantes `C_<Name>` sont capturées indirectement. Amélioration possible :
analyser les cases/switch/if du Module Check pour obtenir la liste exhaustive.

### Extraction du SENS métier via `Condition(...)`

Quand les valeurs extraites sont toutes `'1'` / `' '`, le tableau indique certes
le statut actif mais ne dit rien sur **pourquoi** le drapeau est levé. La clé
est dans les lignes d'affectation `Condition(...)` du Module Check :

```diva
ART.Ce1 = '1'                                              ; marqueur permanent
ART.Ce4 = Condition(ART.Ean    <> ' ', '1', ' ')            ; Ean renseigne
ART.Ce5 = Condition(ART.Fam(1) <> ' ', '1', ' ')            ; Famille 1 renseignee
ART.CeA = Condition((ART.CvaFl = OUI and ART.StatutM <> C_ART_StatutM_EnCours), '1', ' ')
CLI.Ce1 = '3'                                              ; marqueur fixe (code enregistrement)
CLI.Ce3 = Condition(CLI.TiersGrp <> ' ', '1', ' ')          ; appartient a un groupement
CLI.Ce4 = Condition(CLI.Stat(1)  <> ' ', '1', ' ')          ; classement stat 1 renseigne
```

**Parseur** : pour chaque occurrence `<Record>.CeX :?= Condition(...)`, extraire
le **premier argument** de `Condition(` en respectant les parenthèses imbriquées
(comptage de profondeur, arrêt à la virgule au niveau 0). Si l'affectation est
directe `<Record>.CeX :?= '<val>'` (sans `Condition`), on capture `<val>` comme
`fixed_value` (marqueur permanent).

**Exposition dans le modèle** :
- `activation_rule` : chaîne de l'expression extraite, préfixes de record retirés
  pour lisibilité (`ART.Ean <> ' '` → `Ean <> ' '`)
- `fixed_value` : littéral affecté sans condition
- `role_infere` : renvoie vers la règle/valeur (`drapeau derive (voir regle
  d'activation)` ou `marqueur permanent (voir valeur fixe)`) pour éviter la
  redondance avec la colonne dédiée

**Résultat lisible sur CLI** :

| CE | Rôle inféré | Règle d'activation |
|---|---|---|
| CE1 | drapeau principal de statut/filtrage (19 indexes) | valeur fixe `'3'` |
| CE2 | marqueur permanent | valeur fixe `'1'` |
| CE3 | classement groupement tiers (TIERSGRP) | actif si `TiersGrp <> ' '` |
| CE4 | classement statistique (STAT_0001) | actif si `Stat(1) <> ' '` |
| CE5 | classement statistique (STAT_0002) | actif si `Stat(2) <> ' '` |
| CE6 | classement statistique (STAT_0003) | actif si `Stat(3) <> ' '` |

**Résultat lisible sur ART** (zéro index CE sauf CE9, mais sens métier clair) :

| CE | Rôle inféré | Règle d'activation |
|---|---|---|
| CE1 | marqueur permanent | valeur fixe `'1'` |
| CE4 | drapeau dérivé | actif si `Ean <> ' '` |
| CE5/6/7 | drapeaux dérivés | actif si `Fam(1/2/3) <> ' '` |
| CE8 | drapeau dérivé | actif si `Ref <> ' '` |
| CE9 | indexé (INDEX_A_MINI) | actif si `Ephemerefl = 2` |
| CEA | drapeau dérivé | actif si `CvaFl = OUI and StatutM <> C_ART_StatutM_EnCours` |

Cette dimension rend le tableau exploitable même quand la classification par
co-colonnes d'index est silencieuse (cas fréquent pour ART, FOU, SOC où les
drapeaux dérivés sont plus nombreux que les drapeaux indexés).

**Généralisation** : la fonction `analyze_ce_fields` ne dépend que des trois sources
SQL + Module Check. Elle fonctionne pour toute entité qui a Ce1..CeA (convention
Divalto) : CLI, FOU, ART, SOC, C3, etc. Les statuts "réservé" vs "actif" permettent
au livrable de mettre l'accent sur ce qui est **réellement utilisé**.

---

## Questions résiduelles (futures améliorations)

1. **Structure gtfdmc.dhfi** : créer une `structure_gtfdmc.json` pour permettre
   la lecture via `reading-isam-files` des ~30 listes non couvertes par le .json
   (FAMOD, PERIOD, CEJOINT, CENOTE_1, etc.)
2. **Variantes entité** (CLI standard / prospect / affaire / contrat) : détecter
   via les flags (AFFCLDCOD, TIERSNAT) ou via les onglets distincts de gree001.dhsf
3. **Processus transverses métier** (Order-to-Cash) : demande une analyse
   sémantique multi-entités, pas extractible automatiquement
4. **Exemples concrets métier** : narratif humain, pas dans le code

## Score final CLI v6 (grille 6 axes × 3 personas)

| Axe | P1 Consultant | P2 Dev client | P3 Dev interne |
|---|:-:|:-:|:-:|
| Accessibilité UX | 2 | 3 | 3 |
| Ciblage | 3 | 3 | 3 |
| Exactitude | 3 | 3 | 3 |
| Actionnabilité | 2 | 3 | 3 |
| Complétude | 2 | 3 | 3 |
| Concision | 2 | 2 | 2 |
| **Moyenne** | **2.33** | **2.83** | **2.83** |

**Moyenne globale : 2.66/3** — P2 et P3 au target "très satisfaisant" (≥ 2.8).
P1 plafonné par l'absence de narratif humain (exemples, variantes fonctionnelles).

## Checklist de généralisation (à dérouler entité par entité)

- [ ] Identifier `gttmchk<entity>.dhsp` (Module Check)
- [ ] Identifier le masque zoom principal (souvent `gtez<code>_sql.dhsf`)
- [ ] Identifier le module zoom (`gttz<code>_sql.dhsp`)
- [ ] Vérifier le nom de la table dans `.dhsd` (casse : CLI → Cli)
- [ ] Lancer extract_narrative avec les 4 sources
- [ ] Lancer merge_narrative
- [ ] Lancer assemble_model (résolution auto des [A VERIFIER])
- [ ] Vérifier : 0 `[A VERIFIER]` dans meta ET dans relations
- [ ] Vérifier : criticité dérivée cohérente (core/standard/peripheral)
- [ ] Vérifier : ≥70% champs labellisés
- [ ] Rendre Markdown + PDF
