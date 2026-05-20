# Patterns observes dans le corpus Module Check (mchk)

> **Note** : les chiffres ci-dessous proviennent d'une extraction du graphe `diva-mcp` en date du **2026-04-17** (snapshot alors X.12). Depuis le 2026-04-24 le graphe est passe X.13 ; les volumes ont peu evolue (+3-6 % en moyenne, cf `docs/MCP-DIVA-GRAPH.md`). Les pourcentages et conclusions ci-dessous restent significatifs, mais n'ont pas ete re-executes sur X.13.

## Contenu

- Vue d'ensemble
- 1. Taux de presence des 22 fonctions canoniques du pattern STRUCT
- 2. Distribution du nombre total de fonctions par mchk
- 3. Architecture mixte Function / Procedure / DObj
- 4. Implications pour le generateur `generating-objet-metier`
- 5. Limitations connues de cette analyse
- Provenance
- Dictionnaires a privilegier / eviter comme reference de nommage

---


> **Avertissement -- source des donnees**
>
> Ce document est derive d'un **snapshot de la version X.12** de l'ERP Divalto, via le MCP `diva-mcp` (graphe Neo4j). Les patterns stylistiques (conventions de nommage, structure des fonctions) sont generalement stables entre versions mineures X.12 et X.13.
>
> Usage autorise : valider l'alignement du generateur, documenter les patterns recurrents, identifier les fonctions "quasi-obligatoires" absentes du template. **Usage interdit** : servir de base a un controle qualite opposable a un projet X.13 sans re-verification, ou a un garde-fou de modification.

---

## Vue d'ensemble

- **Population identifiee** : 1 244 programmes Module Check reperes par la convention `contient "mchk"` dans le nom.
- **Distribution par domaine** : Achat-Vente domine (578, 46 %), suivi de Framework A5 (133), Paie (104), Comptabilite (74), Affaires (71).

| Domaine | Nombre de mchk |
|---|---:|
| Achat-Vente | 578 |
| Framework A5 | 133 |
| Paie | 104 |
| Comptabilite | 74 |
| Affaires | 71 |
| Reglement | 63 |
| Controle | 53 |
| Gestion Ressources | 34 |
| Qualite | 27 |
| Relation-Tiers | 25 |
| Point de Vente | 25 |
| Processus | 24 |
| Documentation | 23 |
| Mobilite | 10 |

---

## 1. Taux de presence des 22 fonctions canoniques du pattern STRUCT

Presence mesuree sur les 1 244 mchk, en unifiant la typologie graphe `Function` + `Procedure` + `DObj` (le template mixe les trois).

| Fonction canonique | Presence | Taux |
|---|---:|---:|
| `init_module` | 1 239 | 99,6 % |
| `get_*_reservation` | 1 222 | 98,2 % |
| `initialize_*_preinsert` | 1 222 | 98,2 % |
| `get_*_key` | 1 221 | 98,2 % |
| `initialize_*_postinsert` | 1 221 | 98,2 % |
| `initialize_*_preupdate` | 1 221 | 98,2 % |
| `initialize_*_postupdate` | 1 221 | 98,2 % |
| `authorize_*_insert` | 1 221 | 98,2 % |
| `authorize_*_update` | 1 221 | 98,2 % |
| `initialize_*_postdelete` | 1 220 | 98,1 % |
| `authorize_*_delete` | 1 220 | 98,1 % |
| `initialize_*_predelete` | 1 203 | 96,7 % |
| `initialize_*_new` | 1 182 | 95,0 % |
| `initialize_*_postfetch` | 1 181 | 94,9 % |
| `initialize_*_duplication` | 1 180 | 94,9 % |
| `get_*_record` | 1 179 | 94,8 % |
| `get_*_fieldnames_min` | 1 177 | 94,6 % |
| `get_*_fieldnames_all` | 1 177 | 94,6 % |
| `get_*_chkdata` | 1 175 | 94,5 % |
| `get_*_fieldproperties` | 1 174 | 94,4 % |
| `check_*_fieldcod` | 1 172 | 94,2 % |
| `check_*_key` | 1 170 | 94,0 % |
| `get_*_lib` | **575** | **46,2 %** |

### Observations

- **21 fonctions sur 22 ont un taux de presence > 94 %** -- le template genere des noms qui correspondent massivement au standard X.12.
- **`get_*_lib` est l'exception** : seulement 46 % de presence. Logique -- cette fonction n'a de sens que pour une entite ayant un champ "Libelle". Dans le template actuel, elle est conditionnelle (`{% if has_libelle %}`), coherent avec l'observation.
- **Aucun ecart critique de nommage detecte** (contrairement au skill `generating-zoom-sql` ou une procedure etait nommee differemment de la convention majoritaire).

---

## 2. Distribution du nombre total de fonctions par mchk

Nombre total de `Function` declarees dans chaque mchk (hors procedures et DObj) :

| Plage nb fonctions | Nombre de mchk | Lecture |
|---|---:|---|
| < 20 | 52 | mchk tres simplifies (delegation d'un autre mchk ?) |
| 20-32 | 56 | mchk reduits |
| 33-37 | 33 | mchk minimaux |
| **38-45** | **694** | **mediane du corpus -- pattern canonique enrichi** |
| 46-55 | 217 | mchk enrichis (3-10 fonctions custom) |
| 56-80 | 85 | mchk metier lourds |
| 81-273 | 31 | cas exceptionnels (mchk de tres grosses entites) |

**Mediane autour de 42-45 fonctions**. C'est plus eleve que les "22 obligatoires" et les "~52 du pattern complet" -- signe que la plupart des mchk respectent bien le pattern etendu et ajoutent typiquement quelques fonctions custom.

Un mchk "strict" a ~38-40 fonctions. Les mchk "enrichis" en ont 45+. Les mchk exceptionnels (>80 fonctions) concernent les entites avec beaucoup de metier (probablement : ENT pour les pieces, ART pour les articles).

---

## 3. Architecture mixte Function / Procedure / DObj

**Point important pour l'analyse ulterieure** : le corpus X.12 modelise les objets d'un mchk sous trois typologies dans le graphe :
- `Function` : fonctions avec retour typé (ex: `Check_{TABLE}` qui retourne `int`)
- `Procedure` : procedures sans retour (ex: `Get_{TABLE}_FieldProperties`, `Initialize_*_PreInsert`)
- `DObj` : objets declaratifs (ex: `Init_Module` qui peut etre declaree comme DObj selon sa structure)

Une analyse Cypher qui ne filtre que sur `Function` **ratera les procedures et DObj** -- conduisant a des faux "0 % de presence" comme observe lors de la premiere passe sur ce corpus.

Le validateur `validate_mchk.py` travaille sur le **texte brut du fichier** via regex, il n'est donc pas sensible a cette distinction. Pour les analyses de graphe, toujours utiliser l'union des trois types.

---

## 4. Implications pour le generateur `generating-objet-metier`

| Angle | Severite | Action |
|---|---|---|
| **Template bien aligne avec le corpus** (22 fonctions canoniques a > 94 %, pas d'ecart de nommage) | Aucune | RAS |
| **`get_*_lib` conditionnelle sur `has_libelle`** | Aucune | Comportement actuel correct (46 % de presence dans le corpus = entites avec libelle) |
| **Extensions hors 22 canoniques non quantifiees** (~30 autres fonctions canoniques du pattern complet : Seek, Find, Exists, Load, Cache, Reservation, ...) | Faible | A mesurer dans une passe dediee pour validation exhaustive |
| **Extensions custom par entite** (fonctions metier specifiques) | Faible | Documenter comme extensions optionnelles plutot que generees automatiquement |
| **Median nb_fn = 42-45** | Informatif | Indicateur de taille attendue pour un mchk valide (benchmark de coherence) |

**Conclusion principale** : contrairement au skill `generating-zoom-sql` ou une anomalie de nommage a ete detectee et corrigee, **le generateur de Module Check est correctement aligne sur le standard X.12**. Aucune correction du template n'est proposee a l'issue de cette passe.

---

## 5. Limitations connues de cette analyse

- **Version** : X.12 (et non X.13). Les conventions de nommage des mchk sont tres stables, mais une verification X.13 reste possible si necessaire.
- **Pattern etendu non mesure** : le skill genere ~52 fonctions (pattern complet du mchk) dont seulement 22 sont testees ici. Les ~30 autres (Seek, Find, Exists, Load, Cache, Reservation, etc.) n'ont pas ete mesurees car chacune est declinee par entite avec un nom unique -- mesure plus couteuse qui demande une extraction par prefixe.
- **Extensions custom** : les fonctions metier specifiques (hors pattern) n'ont pas ete listees. Le seuil d'interet (> 30 programmes) n'a produit aucun candidat, ce qui suggere que les extensions custom sont tres variables d'une entite a l'autre.
- **Normalisation en minuscules** : les noms d'objets du graphe sont en minuscules. Le mapping vers la forme originale (CamelCase) est implicite.

---

## Provenance

- **Source** : MCP `diva-mcp` (Neo4j, snapshot version X.12 de l'ERP Divalto standard).
- **Population** : 1 244 programmes "mchk" identifies par `toLower(name) CONTAINS 'mchk'`.
- **Methode** : agregations Cypher sur les noeuds `Program`, `Function`, `Procedure`, `DObj`, relation `CONTAINS`, proprietes `name`, `domain`.
- **Date d'extraction** : 2026-04-17.

Pour reproduire ou approfondir, se connecter au MCP `diva-mcp` et relancer les agregations presentees dans les sections 1 a 3.

---

## Dictionnaires a privilegier / eviter comme reference de nommage

Une mesure de conformite aux conventions a ete conduite sur 21 dicos
`.dhsd` X.13 (voir CONVENTIONS locales -- conventions dans les
dictionnaires .dhsd).

**Dicos-modeles (>= 95 % PascalCase sur champs)** -- inspirations sures :
- `qufdd.dhsd` (Qualite), `spfdd.dhsd` (Processus), `cofdd.dhsd` (Controle),
  `dofdd.dhsd` (Documentaire), `gmfdd.dhsd` (GRM), `rtlfdd.dhsd` (Retail).

**Dicos a NE PAS utiliser** comme reference de nommage :
- `bifdd.dhsd` : 66 % des champs en `MOT_MOT_MOT` (miroir OLAP externe).
- `a5dd.dhsd` tables `MXmlNode`/`MDsql*` : camelCase/lowercase (imports XML).
- `ppfdd.dhsd` : 200 camelCase + 46 lowercase (historique Paie).
- `mofdd.dhsd`, `rcftredd.dhsd` : bases en ALLCAPS atypiques.

**Socle canonique des tables metier** : toute table `<metier>` doit inclure
`Ce1`+`Dos`+`UserCr`+`UserMo`+`UserCrDh`+`UserMoDh` (~88 % couverture X.12).
`UserTrace` a **retirer** (0 occurrence corpus).

**Suffixes typés sur les noms de champ** (correlation nom -> Nature) :
voir `docs/CONVENTIONS.md` tableau "Suffixes typés sur les noms de champ".
Extraits : `Dh`->DH (98 %), `Fl`->1,0 (95 %), `Dt`->D8 (93 %), `Qte`->12,D2 (72 %),
`Mt`->16,D0 (65 %). Piege : `Tb` = tableau repete (Nature `X*N`), **pas** cle de table.
