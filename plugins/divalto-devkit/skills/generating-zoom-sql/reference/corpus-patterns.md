# Patterns observes dans le corpus Zoom SQL

> **Note** : les chiffres ci-dessous proviennent d'une extraction du graphe `diva-mcp` en date du **2026-04-17** (snapshot alors X.12). Depuis le 2026-04-24 le graphe est passe X.13 ; les volumes ont peu evolue (+3-6 % en moyenne, cf `docs/MCP-DIVA-GRAPH.md`). Les pourcentages et conclusions ci-dessous restent significatifs, mais n'ont pas ete re-executes sur X.13.

## Contenu

- Vue d'ensemble
- 1. Taux de presence des 27 procedures canoniques
- 2. Procedures "hors 27 canoniques" les plus frequentes
- 3. Ecart critique : nommage de `Construire_Condition(_)Selection` — RESOLU
- 4. Distribution du nombre de procedures par zoom
- 5. Taille des procedures canoniques -- zooms avec code metier vs stubs
- 6. Implications pour le generateur `generating-zoom-sql`
- 7. Limitations connues du corpus
- Provenance
- Dictionnaires a privilegier / eviter comme reference de nommage

---


> **Avertissement -- source des donnees**
>
> Ce document est derive d'un **snapshot de la version X.12** de l'ERP Divalto, via le MCP `diva-mcp` (graphe Neo4j). Le template actuel du skill cite comme source `rttzfamrglt_sql.dhsp` **version X.13**. Les ecarts observes entre le corpus X.12 et le template X.13 peuvent donc refleter une evolution volontaire entre versions -- a investiguer avant toute conclusion.
>
> Usage autorise : nourrir la conception du generateur, documenter les patterns recurrents, identifier les procedures "presque-canoniques" absentes du template. **Usage interdit** : servir de base a un controle qualite opposable a un projet X.13, ou a un garde-fou de modification.

---

## Vue d'ensemble

- **Population identifiee** : 1 091 programmes Zoom SQL reperes via la convention `.{3}z.*_sql` (4e lettre = `z`, suffixe `_sql`).
- **Distribution par domaine** : Achat-Vente domine nettement (528 zooms, 48 % du total).

| Domaine | Nombre de Zoom SQL |
|---|---:|
| Achat-Vente | 528 |
| Paie | 97 |
| Framework A5 | 93 |
| Reglement | 71 |
| Comptabilite | 65 |
| Affaires | 62 |
| Controle | 29 |
| Gestion Ressources | 25 |
| Qualite | 24 |
| Documentation | 23 |
| Point de Vente | 23 |
| Processus | 23 |
| Relation-Tiers | 18 |
| Mobilite | 10 |

---

## 1. Taux de presence des 27 procedures canoniques

Presence des 27 procedures declarees obligatoires par le skill, mesuree sur les 1 091 Zoom SQL du corpus :

| Procedure | Presence | Taux |
|---|---:|---:|
| zoomdebut | 1 091 | 100 % |
| zoomaprescle | 1 091 | 100 % |
| zoomarret | 1 090 | 99,9 % |
| zoomvalidation | 1 086 | 99,5 % |
| zoomavantinput | 1 084 | 99,4 % |
| zoomconsult | 1 082 | 99,2 % |
| zoomapresread | 1 078 | 98,8 % |
| zoomcreation | 1 047 | 96,0 % |
| zoommodification | 1 045 | 95,8 % |
| zoomsuppression | 1 045 | 95,8 % |
| zoomavantconsult | 1 014 | 93,0 % |
| zoomavantdelete | 995 | 91,2 % |
| zoomfin | 993 | 91,0 % |
| zoomabandon | 992 | 90,9 % |
| zoomduplication | 989 | 90,7 % |
| zoomavantrewrite | 980 | 89,8 % |
| zoomavantwrite | 974 | 89,3 % |
| zoommodificationres | 941 | 86,3 % |
| zoomapresmodification | 930 | 85,2 % |
| zoomcreationres | 929 | 85,2 % |
| zoomaprescreation | 923 | 84,6 % |
| zoomapressuppression | 915 | 83,9 % |
| zoomsuppressionres | 865 | 79,3 % |
| zoomfiltreavantvaleur | 494 | 45,3 % |
| zoomfiltreapresvaleur | 494 | 45,3 % |
| construire_conditionselection | 19 | **1,7 %** |
| zoomapresclecreation (forme normalisee) | 918 | 84,1 % |

### Observations

- **19 procedures sont presentes dans > 80 % des zooms X.12** -- le squelette "CRUD de base" est tres stable.
- **Les 2 procedures de filtre** (`zoomfiltreavantvaleur`, `zoomfiltreapresvaleur`) ne sont presentes que dans 45 % des zooms. A traiter comme optionnelles dans le template ?
- **`construire_conditionselection` n'est presente que dans 19 zooms X.12** (1,7 %). La forme **`construire_condition_selection`** (avec underscore central, voir section 2) est la forme dominante. Ecart a investiguer.

---

## 2. Procedures "hors 27 canoniques" les plus frequentes

Top 25 des procedures non incluses dans la liste des 27 officielles mais frequemment presentes dans les Zoom SQL X.12 :

| Procedure | Nombre de programmes | Taux | Interpretation possible |
|---|---:|---:|---|
| **construire_condition_selection** | 1 048 | **96,1 %** | Forme canonique reelle (voir ecart section 3) |
| zoomapresclecreation | 918 | 84,1 % | Variante du nom `zoomapresCleCreation` |
| **zoomentetetableau** | 689 | **63,2 %** | Procedure quasi-canonique non listee |
| **zoomapresreadliste** | 496 | **45,5 %** | Procedure quasi-canonique non listee |
| maj_menu_boutons | 438 | 40,1 % | Pattern "mise a jour dynamique des boutons" |
| maj_note | 170 | 15,6 % | Gestion de notes attachees a l'enregistrement |
| traiter_selection | 156 | 14,3 % | Action sur la selection multi-ligne |
| envoyer_selections | 144 | 13,2 % | Envoi vers un autre module |
| titre_afficher | 141 | 12,9 % | Mise a jour du titre dynamique |
| requete_initialiser | 140 | 12,8 % | Initialisation avancee d'une requete |
| libelle_rechercher | 130 | 11,9 % | Recherche par libelle |
| envoyer_courant | 120 | 11,0 % | Envoi de l'enregistrement courant |
| indicateur_positionner | 110 | 10,1 % | Positionnement d'indicateur |
| zoomdebutliste | 107 | 9,8 % | Init specifique en mode liste |
| zoomapresdetail | 102 | 9,3 % | Apres detail d'une ligne |
| initialiser_requete | 101 | 9,3 % | Doublon semantique avec `requete_initialiser` |
| menu_boutons_maj | 101 | 9,3 % | Doublon semantique avec `maj_menu_boutons` |
| rechercher_libelle | 65 | 6,0 % | Doublon semantique avec `libelle_rechercher` |
| determiner_tri_interrogation | 52 | 4,8 % | Selection d'un ordre de tri |
| zoomavantdetail | 52 | 4,8 % | Avant detail d'une ligne |
| zoomfinliste | 51 | 4,7 % | Nettoyage en mode liste |
| zoomavantblocfin | 50 | 4,6 % | Avant bloc fin |
| zoomapresblocfin | 50 | 4,6 % | Apres bloc fin |
| majtitre | 46 | 4,2 % | Doublon semantique avec `titre_afficher` |
| regler_affichage | 45 | 4,1 % | Reglage d'affichage |

### Observations

- **`construire_condition_selection` (forme avec underscore) presente dans 96 % du corpus** : c'est la forme canonique reelle en X.12, pas celle du skill (section 3).
- **Deux procedures "presque-canoniques" absentes des 27 officielles** : `zoomentetetableau` (63 %) et `zoomapresreadliste` (45 %). Elles concernent manifestement la gestion du mode liste/tableau du zoom. Leur integration dans le template pourrait etre envisagee.
- **Doublons semantiques** : plusieurs paires designent apparemment la meme operation sous des conventions de nommage differentes, ex. `maj_menu_boutons` (438) vs `menu_boutons_maj` (101), ou `requete_initialiser` (140) vs `initialiser_requete` (101), ou `libelle_rechercher` (130) vs `rechercher_libelle` (65), ou `titre_afficher` (141) vs `majtitre` (46). A trancher : quelle forme le generateur devrait-il privilegier ?

---

## 3. Ecart critique : nommage de `Construire_Condition(_)Selection` — RESOLU

Le template **avant correction** (`scripts/templates/zoom_sql.dhsp.j2`, ligne 37) generait une procedure nommee `Construire_ConditionSelection` (sans underscore central). Or les deux corpus X.12 et X.13 utilisent massivement la forme avec underscore.

**Verification X.12 (graphe Neo4j, 1 091 zoom SQL)** :

| Forme | Presence X.12 |
|---|---:|
| `Construire_ConditionSelection` (sans underscore central) | 19 programmes (1,7 %) |
| `Construire_Condition_Selection` (avec underscore central) | 1 048 programmes (96,1 %) |

**Verification X.13 (filesystem standard ERP, 1 117 zoom SQL)** :

| Forme | Presence X.13 |
|---|---:|
| `Construire_ConditionSelection` (sans underscore central) | 19 programmes (1,7 %) -- dont `rttzfamrglt_sql.dhsp`, le fichier qui avait servi de source au skill |
| `Construire_Condition_Selection` (avec underscore central) | 1 074 programmes (96,2 %) |

**Conclusion** : la forme avec underscore est la convention canonique dans les deux versions. Le fichier source utilise pour concevoir le skill (`rttzfamrglt_sql.dhsp`) etait une **anomalie dans l'ensemble X.13**. Pas d'evolution de convention entre X.12 et X.13.

**Correction appliquee** (2026-04-17) :
- `scripts/templates/zoom_sql.dhsp.j2` : 3 occurrences corrigees (declaration + 2 appels).
- `scripts/validate_zoom.py` : entree `MANDATORY_PROCEDURES` corrigee.
- `reference/zoom-procedures.md` : table des 27 procedures mise a jour.

---

## 4. Distribution du nombre de procedures par zoom

Nombre total de procedures contenues dans chaque programme Zoom SQL (canoniques + custom) :

| Nombre de procedures | Nombre de programmes | Lecture |
|---:|---:|---|
| 20-25 | 127 | Zooms simplifies (moins de hooks implementes) |
| 26-28 | 345 | Zooms "canoniques propres" (proches du squelette des 27) |
| 29-33 | 427 | Zooms avec quelques extensions metier |
| 34-38 | 107 | Zooms "enrichis" (3-11 procedures custom) |
| 39-67 | ~30 | Zooms avec logique metier importante |

**Mediane** autour de 27-30 procedures.

Un zoom SQL "strict" (exactement 27 procedures, les canoniques uniquement) existe dans 129 programmes. Les autres ajoutent typiquement 1 a 11 procedures custom (manipulation de menu, envoi inter-modules, gestion de notes, requetes specifiques).

---

## 5. Taille des procedures canoniques -- zooms avec code metier vs stubs

Statistiques de `lines_length` sur un echantillon de 10 procedures canoniques :

| Procedure | Nombre d'observations | Min | Median | Moyenne | Max |
|---|---:|---:|---:|---:|---:|
| zoomdebut | 1 091 | 8 | 30 | 35,5 | 511 |
| construire_conditionselection (forme rare) | 19 | 20 | 37 | 37,0 | 76 |
| zoomavantwrite | 974 | 3 | 12 | 15,1 | 107 |
| zoomcreation | 1 047 | 3 | 12 | 13,9 | 120 |
| zoomavantrewrite | 980 | 3 | 11 | 13,1 | 151 |
| zoomsuppression | 1 045 | 3 | 8 | 9,2 | 72 |
| zoommodification | 1 045 | 3 | 8 | 8,9 | 42 |
| zoomapresread | 1 078 | 3 | 6 | 8,6 | 112 |
| zoomaprescreation | 923 | 3 | 7 | 7,5 | 132 |
| zoomavantdelete | 995 | 3 | 6 | 6,8 | 70 |

### Observations

- **`zoomdebut` est la plus volumineuse** (mediane 30 lignes, max 511 !) -- elle concentre l'initialisation, les appels `Init_Zoom`, `Load_Gtfdos`, `TitreFixe`, et eventuellement des pre-traitements complexes.
- **Les procedures "de validation metier"** (`zoomavantwrite`, `zoomcreation`, `zoomavantrewrite`) ont une mediane de 11-12 lignes -- contiennent typiquement `Check + PreInsert/PreUpdate`.
- **Les procedures "de post-traitement"** (`zoommodification`, `zoomsuppression`, `zoomapresread`) ont une mediane de 6-8 lignes -- plus courtes.
- **Les queues extremes** (max 100+ lignes) indiquent des zooms tres metier, candidats a une factorisation ou a de la documentation ciblee.

---

## 6. Implications pour le generateur `generating-zoom-sql`

| Angle a etudier | Severite | Action possible |
|---|---|---|
| ~~Forme `Construire_Condition_Selection` vs `Construire_ConditionSelection`~~ | **RESOLU (2026-04-17)** | X.13 confirme 96,2 % avec underscore, template corrige |
| **Procedures "presque-canoniques" absentes** (`zoomentetetableau` 63 %, `zoomapresreadliste` 45 %) | Moyenne | Envisager un mode template "avec liste/tableau" |
| **`zoomfiltreavantvaleur` / `zoomfiltreapresvaleur` optionnelles** (45 %) | Faible | Les rendre conditionnelles dans le template |
| **Procedures custom recurrentes** (`maj_menu_boutons` 40 %, `maj_note` 16 %, `traiter_selection` 14 %) | Faible | Documenter comme extensions optionnelles plutot que generees |
| **Doublons semantiques de nommage** (ex: `maj_menu_boutons` vs `menu_boutons_maj`) | Faible | Enrichir `docs/CONVENTIONS.md` pour trancher la forme privilegiee |

---

## 7. Limitations connues du corpus

- **Version** : X.12 (et non X.13). Certains patterns et conventions peuvent avoir evolue entre versions mineures (voir section 3).
- **Pas d'info sur le masque `.dhsf` associe** : le graphe ne relie pas directement le Zoom SQL `.dhsp` a son masque `.dhsf`. Impossible de croiser les patterns de procedures avec la structure d'ecran.
- **`body` des procedures disponible mais non exploite ici** : le graphe contient le code source complet de chaque procedure (`Procedure.body`). Des analyses plus fines sont possibles (detection de hooks implementes vs stubs vides, extraction des appels framework recurrents, etc.) -- non realisees dans ce rapport.
- **Normalisation en minuscules** : les noms d'objets du graphe sont en minuscules. Le mapping vers la forme originale (CamelCase) est implicite ; attention en cas d'exploitation automatique.

---

## Provenance

- **Source** : MCP `diva-mcp` (Neo4j, snapshot version X.12 de l'ERP Divalto standard).
- **Population** : 1 091 programmes Zoom SQL identifies par le pattern `.{3}z.*_sql`.
- **Methode** : requetes Cypher agregatives sur les noeuds `Program`, `Procedure`, relation `CONTAINS`, proprietes `name`, `lines_length`, `domain`.
- **Date d'extraction** : 2026-04-17.

Pour reproduire ou approfondir, se connecter au MCP `diva-mcp` et relancer les agregations presentees dans les sections 1 a 5.

---

## Dictionnaires a privilegier / eviter comme reference de nommage

Une mesure de conformite aux conventions a ete conduite sur 21 dicos
`.dhsd` X.13 (voir CONVENTIONS locales -- conventions dans les
dictionnaires .dhsd).

**Dicos-modeles (>= 95 % PascalCase sur champs)** -- a privilegier quand le zoom
projette des champs ou utilise des noms de table de reference :
- `qufdd.dhsd`, `spfdd.dhsd`, `cofdd.dhsd`, `dofdd.dhsd`, `gmfdd.dhsd`,
  `rtlfdd.dhsd`.

**Dicos a NE PAS utiliser** comme reference :
- `bifdd.dhsd` : 66 % des champs en `MOT_MOT_MOT` (miroir OLAP externe).
- `a5dd.dhsd` tables `MXmlNode`/`MDsql*` : camelCase/lowercase (imports XML).
- `ppfdd.dhsd` : 200 camelCase + 46 lowercase (historique Paie).

**Taxonomie de suffixes typés** (nom -> Nature) : voir `docs/CONVENTIONS.md`
tableau "Suffixes typés sur les noms de champ". Pertinent pour nommer les
colonnes du tableau dans le zoom : `Dt` date, `Dh` datetime, `Fl` flag,
`Mt` montant, `Qte` quantite.
