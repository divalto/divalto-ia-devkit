# Patterns observes dans le corpus RecordSql

> **Note** : les chiffres ci-dessous proviennent d'une extraction du graphe `diva-mcp` en date du **2026-04-17** (snapshot alors X.12). Depuis le 2026-04-24 le graphe est passe X.13 ; les volumes ont peu evolue (+3-6 % en moyenne, cf `docs/MCP-DIVA-GRAPH.md`). Les pourcentages et conclusions ci-dessous restent significatifs, mais n'ont pas ete re-executes sur X.13.

## Contenu

- Vue d'ensemble
- 1. Complexite des jointures
- 2. Tables les plus sollicitees
- 3. Super-patterns -- signatures de jointure re-utilisees
- 4. Scope et visibilite des declarations (artefact de modelisation -- voir note)
- 5. Distribution par domaine fonctionnel
- 6. Implications pour le generateur `generating-recordsql`
- 7bis. Verification X.13 -- Cases WHERE et types de jointures (prerequis L2)
- 7ter. Verification X.13 des super-patterns -- CONFIRME
- 7. Limitations connues du corpus
- Provenance
- Dictionnaires a privilegier / eviter comme reference de nommage

---


> **Avertissement -- source des donnees**
>
> Ce document est derive d'un **snapshot de la version X.12** de l'ERP Divalto, via le MCP `diva-mcp` (graphe Neo4j, ~11 433 RecordSql indexes). **Il ne reflete PAS l'etat X.13 courant.**
>
> Usage autorise : nourrir la conception du generateur, documenter les patterns de reference, identifier les cas non couverts. **Usage interdit** : servir de base a un controle qualite opposable a un projet X.13, ou a un garde-fou de modification.

---

## Vue d'ensemble

Corpus analyse : 11 433 RecordSql extraits de la base standard ERP X.12.

---

## 1. Complexite des jointures

Distribution du nombre de tables accedees par RecordSql (`ACCESSES_TABLE`) :

| Nombre de tables | Nombre de RecordSql | Part | Lecture |
|---:|---:|---:|---|
| 0 | 3 031 | 26 % | Artefact du modele (relation portee par le Program parent) ou RSQL sans acces direct |
| 1 | 1 588 | 14 % | Mono-table -- le cas le plus frequent parmi les RSQL avec acces |
| 2 | 1 084 | 9,5 % | Jointure legere |
| 3 | 869 | 7,6 % | Jointure legere |
| 4-9 | 3 474 | 30 % | Jointures moyennes |
| 10-20 | 1 119 | 10 % | Jointures lourdes |
| 20+ | 1 168 | 10 % | Vues/rapports complexes, bosses a 26, 30, 46, 53 tables |

**Observation** : 65 % du corpus (hors RSQL sans acces detecte) joint au moins 2 tables. Le pattern mono-table, couvert par le template standard, est minoritaire.

---

## 2. Tables les plus sollicitees

Top 15 des tables accedees par les RecordSql (nombre de RSQL distincts qui les referencent) :

| Rang | Table | Nombre de RSQL | Nature presumee |
|---:|---|---:|---|
| 1 | CLI | 2 665 | Client |
| 2 | FOU | 2 138 | Fournisseur |
| 3 | ART | 1 848 | Article |
| 4 | TIA | 1 604 | Tiers adresse |
| 5 | ETS | 1 524 | Etablissement |
| 6 | C3 | 1 413 | Compte comptable |
| 7 | T007 | 1 098 | Table systeme (lookup) |
| 8 | ENT | 1 062 | Entete de piece |
| 9 | T017 | 1 006 | Table systeme (lookup) |
| 10 | PRO | 998 | Prospect / Produit |
| 11 | VRP | 980 | Representant |
| 12 | T006 | 973 | Table systeme (lookup) |
| 13 | MUSER | 912 | Utilisateur |
| 14 | C4 | 837 | Compte comptable secondaire |
| 15 | T020 | 813 | Table systeme (lookup) |

**Pattern "join des lookups"** : les tables T006, T007, T017, T020 sont des tables de parametrage (libelles, codes) sollicitees par presque tous les domaines. Elles sont systematiquement jointes aux tables metier CLI/FOU/ART pour afficher des libelles lisibles dans les zooms.

---

## 3. Super-patterns -- signatures de jointure re-utilisees

Les signatures de jointure les plus frequentes indiquent des **squelettes de RecordSql quasi-identiques re-utilises dans des dizaines de programmes**.

| Nombre de tables | Nombre de RSQL partageant la signature | Interpretation |
|---:|---:|---|
| 53 | 168 | "Zoom piece exhaustif" (ART, CLI, FOU, ENT, MOUV, MVTL, VRP... + 46 autres) |
| 19 | 146 | "Zoom reglement" (C3/C4/C8, CLI, FOU, TIA, SOC, H8, RGLTJNLDET...) |
| 46 | 136 | Zoom piece alternatif |
| 30 | 108 | Zoom mouvement (ART, MOUV, LOTDET, BF...) |
| 19 | 93 | Zoom relation client (ACTIONREL, RECACTIONDET...) |
| 47 | 91 | Zoom piece avec parametrage etendu |
| 9 | 90 | Zoom evenement (GRTEVT, CA, PAR...) |
| 26 | 83 | Zoom projet affaire (GATCRIT, GATETAP, PRJAP...) |

Ces squelettes a 20+ tables ne sont pas modelises dans les templates actuels mais pesent ensemble > 900 RSQL du corpus.

---

## 4. Scope et visibilite des declarations (artefact de modelisation -- voir note)

Distribution brute des `RecordSql` par scope et mode de declaration dans le graphe :

| scope_type | decla_type | Nombre | Part |
|---|---|---:|---:|
| root | public | 4 684 | 41 % |
| root | local | 2 590 | 23 % |
| procedure | local | 2 084 | 18 % |
| function | local | 1 847 | 16 % |
| root | extern | 218 | 2 % |
| main | local | 4 | < 1 % |
| root | protected | 4 | < 1 % |
| if | local | 2 | < 1 % |

### Verification X.13 (2026-04-17) -- le 34 % est un artefact de modelisation

Un grep sur l'ensemble des fichiers `.dhsp` du standard ERP X.13 pour le motif `<RecordSql Name=` retourne **0 occurrence**. Aucun RecordSql n'est declare inline dans un programme metier ; tous sont dans des fichiers `.dhsq` dedies (291 fichiers, 1 814 declarations recensees dans X.13).

Le "34 % en scope procedure/function" observe dans le graphe correspond donc probablement a une **instanciation multiple** dans la modelisation Neo4j : un meme RecordSql defini dans un `.dhsq` semble reindexe au scope de chaque procedure/fonction qui l'utilise. Ce n'est pas une declaration inline reelle.

**Consequence** : l'angle mort "scope procedure/function non supporte" du generateur est **invalide**. Le skill cible le bon scope (fichier dedie). Cet angle mort est retire des implications (section 6).

---

## 5. Distribution par domaine fonctionnel

| Domaine | Nombre de RSQL | Part |
|---|---:|---:|
| Achat-Vente | 3 074 | 27 % |
| Framework A5 | 922 | 8 % |
| Comptabilite | 726 | 6 % |
| Affaires | 539 | 5 % |
| Reglement | 515 | 5 % |
| Paie | 488 | 4 % |
| Mobilite | 237 | 2 % |
| Processus | 186 | 2 % |
| Gestion Ressources | 172 | 2 % |
| Qualite | 161 | 1 % |
| Controle | 156 | 1 % |
| Point de Vente | 123 | 1 % |
| Relation-Tiers | 107 | 1 % |
| Documentation | 92 | 1 % |

Achat-Vente concentre plus du quart du corpus. Les domaines < 200 RSQL offrent un corpus de reference plus maigre.

---

## 6. Implications pour le generateur `generating-recordsql`

Confrontation du template `recordsql.dhsq.j2` (mono-table, 6 Cases standards) avec le corpus X.12 :

| Angle mort | Volume X.12 impacte | Severite | Verification X.13 |
|---|---:|---|---|
| **Absence de support des jointures** | ~7 400 RSQL (65 % du corpus avec acces) | Haute | **CONFIRME** -- un RSQL reel `EntetePiece` (gtrspce.dhsq) joint visiblement 40+ tables |
| ~~Absence de variantes de scope (procedure/function)~~ | ~~3 931 RSQL (34 %)~~ | ~~Haute~~ | **INVALIDE** -- 0 RSQL inline dans les .dhsp X.13, artefact graphe |
| **Absence de squelettes "zoom exhaustif" nommes** | ~900 RSQL partagent 8 super-signatures | Moyenne | CONFIRME -- gtrspce.dhsq (75 RSQL), gtrstab.dhsq (41), ccrsecr.dhsq (26) etc. en X.13 |
| **Absence d'heuristiques lookup** (T006/T007/T017/T020 jointes avec CLI/FOU/ART) | Pervasif, quantification precise non faite | Moyenne | A verifier X.13 |
| **Cases WHERE specialises non-standards** | Non quantifie dans ce rapport | A mesurer | - |
| **Types de jointure dominants** (INNER/LEFT, patterns ON ...) | Non quantifie dans ce rapport | A mesurer | - |

Les deux dernieres lignes sont des questions ouvertes a trancher avant d'engager une extension du template. La priorite #1 reste **l'absence de support des jointures** -- confirme en X.13 comme angle mort reel.

---

## 7bis. Verification X.13 -- Cases WHERE et types de jointures (prerequis L2)

Donnees extraites directement du filesystem X.13 (291 .dhsq, 1 814 RecordSql) -- ce sont des donnees **courantes**, pas des snapshots X.12.

### Top Cases WHERE / ORDERBY observes

| Case | Occurrences X.13 | Type | Couvert par template |
|---|---:|---|---|
| `PK` | 922 | Canonique cle primaire | OUI |
| `Exists` | 737 | Canonique existence | OUI |
| `ID` | 636 | Canonique ID SQL | OUI (+ `Id` 101 occurrences -- casse inconsistante) |
| `Like_Lib` | 257 | Like sur champ `Lib` | Partiellement (template genere `Like_{ChampLibelle}` -- si `ChampLibelle=Lib` alors OK) |
| `Par_Libelle` | 211 | ORDERBY canonique | OUI |
| `Par_Code` | 185 | ORDERBY canonique | OUI |
| `Equal_Ref` | 162 | Equal sur champ Ref | NON (pas de Cases Equal_* secondaires generes) |
| `Equal_Depo` | 146 | Equal sur Depo | NON |
| `Equal_Tiers` | 137 | Equal sur Tiers | NON |
| `Like_Ref` | 111 | Like sur Ref | NON |
| `Equal_Etb` | 102 | Equal sur Etb | NON |
| `Like_Tiers` | 99 | Like sur Tiers | NON |
| `Equal_ArtInd` | 86 | Equal sur ArtInd | NON |
| `Equal_TiCod` | 80 | Equal sur TiCod | NON |
| `Equal_Dos` | 77 | Equal sur Dos | NON |
| `Equal_Nst` | 68 | Equal sur Nst | NON |
| `Between_Tiers` | 66 | Plage Tiers | NON |
| `AvecJoint` | 63 | Filtre thematique | NON |
| `Between_Ref` | 61 | Plage Ref | NON |
| `Like_Depo` | 58 | Like Depo | NON |
| `Equal_Lieu` | 58 | Equal Lieu | NON |
| `Equal_FullRef` | 56 | Equal compose | NON |
| `Equal_Sref1`/`Equal_Sref2` | 52+52 | Equal cles secondaires | NON (+ variantes `SRef1/SRef2` 46+46) |
| `Equal_Serie` | 45 | Equal Serie | NON |
| `Par_Numero` | 45 | ORDERBY Numero | NON |
| `Art_Like_Fam1/2/3` | 42/42/41 | Pattern Article Famille | NON (metier tres specifique) |
| `Equal_TiersStock` | 40 | Equal tiers stock | NON |
| `Valide` | 39 | Filtre etat | NON |
| `Equal_PiCod` | 39 | Equal Pi Code | NON |

### Implications pour L2

1. **Le template actuel couvre ~2 700 occurrences** des Cases canoniques (PK, Exists, ID, Par_Code, Par_Libelle, Like_{ChampCle}, Like_{ChampLibelle}). Bien.
2. **Le corpus contient massivement des Cases `Equal_<champ>`, `Like_<champ>`, `Between_<champ>` par champ metier**. Un seul champ metier peut avoir 100-200 occurrences repartis dans les RSQL. Piste L2 : **autoriser des Cases supplementaires parametriques par champ** (token `--cases-additionnels` par exemple).
3. **Cases custom metier (`AvecJoint`, `Valide`, `Art_Like_Fam*`)** : trop metier-specifiques pour etre templates generiques. A laisser hors du generateur, documenter comme exemples.
4. **Incoherence casse `ID` vs `Id`** : 636 vs 101. Le template genere `ID` (majuscule) -- forme dominante a 86 %. RAS.
5. **Incoherence `Like_Lib` vs `Like_Libelle`** : 257 vs (non compte). Beaucoup d'entites utilisent le champ `Lib` (nom court), pas `Libelle`. Le skill gere deja ca via `--champ-libelle Lib` (token `ChampLibelle`).

### Types de jointures

Mesure sur les .dhsq X.13 :

| Type de jointure | Occurrences | Fichiers |
|---|---:|---:|
| Jointure **implicite** (FROM + WHERE, style SQL-89) | **Majoritaire** (non quantifie precisement) | La plupart des RSQL multi-tables |
| `LEFT JOIN` (SQL standard) | 161 | 26 fichiers |
| `LeftJoin` (keyword Divalto) | 30 | fichiers X.13 |
| `Join` (keyword Divalto) | 15 | fichiers X.13 |
| `INNER JOIN` (SQL standard) | 11 | 4 fichiers |
| `RIGHT JOIN`, `CROSS JOIN`, `FULL OUTER JOIN`, `NATURAL JOIN` | 0 | 0 |

### Implications pour L2 -- priorisation des types de jointure

1. **Priorite #1 : jointure implicite FROM + WHERE** (style natif DIVA, utilisee par `gtrspce.dhsq`/`EntetePiece` avec 40+ tables). Le template L2 doit savoir declarer N tables dans `<FROM>` et gerer les conditions de jointure dans `<WHERE>`.
2. **Priorite #2 : LEFT JOIN SQL** (161 occurrences X.13). Le template L2 doit optionnellement generer des LEFT JOIN explicites pour les tables jointes avec cardinalite 0..1.
3. **A ignorer** : RIGHT JOIN, CROSS JOIN, FULL OUTER JOIN, NATURAL JOIN -- absents du corpus.
4. **A evaluer separement** : les keywords Divalto `Join` / `LeftJoin` (45 occurrences totales) -- marginaux mais existent, peut-etre a traiter en syntaxe alternative ou a ignorer pour un premier jet de L2.

---

## 7ter. Verification X.13 des super-patterns -- CONFIRME

Analyse sur 1 000 RSQL X.13 parses directement depuis le filesystem (extraction des `<FROM>`, comptage heuristique des tables).

### Correspondance avec les signatures X.12

| Signature X.12 | Presence X.13 | Exemples X.13 |
|---|---|---|
| 53 tables | **OUI** | `LignePDP` (gtrspdp.dhsq) |
| 47 tables | **OUI** (2 RSQL) | `DetCtrlFa` (gtrsctrlfa.dhsq), `MouvementDTrFA` (gtrsdtrfa.dhsq) |
| 46 tables | Absent exact, mais 44/45 presents | 2 RSQL a 44 tables, 2 a 45 tables |
| 30 tables | **OUI** (2 RSQL) | `SumMouvArt` (gtrspce.dhsq), `ActivGPA` (garsgpa_old.dhsq) |
| 26 tables | **OUI** (6 RSQL) | `BasePrepa` (gtrspce.dhsq), `EvtGPA`, `FAGPA` (garsgpa.dhsq) |
| 19 tables | **OUI** (17 RSQL) | `TabMatriceCfg`, `DossierGim`, `AcompteDTr` |

Conclusion : les super-patterns observes en X.12 **existent en X.13** avec des volumes similaires. Le chantier L3 (bibliotheque de squelettes nommes) garde toute sa pertinence.

### Queue extreme observee en X.13

| nb_tables | nb_rsql X.13 |
|---:|---:|
| 100-200 | ~10 RSQL |
| 200-400 | 5 RSQL |
| 400-600 | 1 RSQL (581 tables !) |

La queue extreme en X.13 depasse ce que le graphe X.12 montrait (plafond a 53 tables observe). Le corpus reel est encore plus dense en super-patterns -- probablement des RSQL absolument enormes (type tableau de bord transverse).

### Note methodologique

Le parsing X.13 est heuristique (compte les tokens nom dans `<FROM>`). Il est plus conservateur que le graphe X.12 : ~55 % des RSQL sont parses avec succes (limites : sous-queries, vues imbriquees, syntaxes particulieres non couvertes). Les chiffres ne sont donc **pas directement comparables** aux chiffres X.12, mais la presence/absence des super-patterns est fiable.

---

## 7. Limitations connues du corpus

- **Version** : X.12 (et non X.13). Les patterns stylistiques sont generalement stables entre versions mineures mais certaines entites ou champs peuvent avoir ete ajoutes/supprimes en X.13.
- **3 031 RSQL sans `ACCESSES_TABLE`** : probablement un artefact du modele du graphe (relation portee par le programme parent plutot que par le RSQL). Non investigue dans ce rapport.
- **Pas d'information sur les colonnes selectionnees** : le graphe contient `DbField` (35 870) mais pas de relation directe RSQL -> DbField. Les champs projetes par un RSQL particulier ne sont pas extractibles en l'etat.
- **Pas d'information sur les Cases WHERE reels** : non modelises dans le graphe.

---

## Provenance

- **Source** : MCP `diva-mcp` (Neo4j, snapshot version X.12 de l'ERP Divalto standard).
- **Methode** : requetes Cypher agregatives sur les noeuds `RecordSQL`, `DbTable`, `Program`, relations `ACCESSES_TABLE`, `CONTAINS`.
- **Date d'extraction** : 2026-04-17.

Pour reproduire ou approfondir, se connecter au MCP `diva-mcp` et relancer les agregations presentees dans les sections 1 a 5.

---

## Dictionnaires a privilegier / eviter comme reference de nommage

Une mesure de conformite aux conventions a ete conduite sur 21 dicos
`.dhsd` X.13 (voir CONVENTIONS locales -- conventions dans les
dictionnaires .dhsd).

**Dicos-modeles (>= 95 % PascalCase sur champs)** -- inspirations sures pour
choisir les noms de champs quand on projette un RSQL sur une entite :
- `qufdd.dhsd`, `spfdd.dhsd`, `cofdd.dhsd`, `dofdd.dhsd`, `gmfdd.dhsd`,
  `rtlfdd.dhsd`.

**Dicos a NE PAS utiliser** comme reference :
- `bifdd.dhsd` : 66 % des champs en `MOT_MOT_MOT` (miroir OLAP externe).
- `a5dd.dhsd` tables `MXmlNode`/`MDsql*` : camelCase/lowercase (imports XML).
- `ppfdd.dhsd` : 200 camelCase + 46 lowercase (historique Paie).

**Taxonomie de suffixes typés** : quand un RSQL expose des champs projetes,
preferer les noms qui respectent la taxonomie (`Dh`->DH 98 %, `Fl`->1,0 95 %,
`Dt`->D8 93 %). Voir `docs/CONVENTIONS.md` tableau "Suffixes typés".
