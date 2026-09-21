---
name: managing-diva-dictionaries
description: >
  Ajoute une table complete dans un dictionnaire Divalto (.dhsd) en generant les 5 zones
  obligatoires : [CHAMP] (declaration des champs), [TABLE] (structure avec positions calculees),
  [BASE] (fichier physique), [INDEX] (index avec positions cumulees), et [INDEXL] (mapping).
  Inclut le socle audit canonique (Ce1, Dos, UserCr, UserMo, UserCrDh, UserMoDh, Filler, U-field),
  le calcul automatique des positions sans trou, la taxonomie de suffixes typés (Dt->D8, Dh->DH,
  Fl->1,0...) via suggest_nature.py, et la validation de coherence DICT01-DICT16.
  Preserve l'encodage ISO-8859-1+CRLF. A utiliser pour declarer une nouvelle table metier
  dans le dictionnaire avant de generer le code, ou pour modifier la Nature d'un champ
  existant avec recalcul automatique des positions (tables + index) lors d'un alignement
  de version / migration (modify_field_nature.py). Compare deux versions d'un .dhsd
  (Service Pack, montee de version) : quelles tables ont change de Taille=, donc quel
  specifique recompiler.
---

# Managing DIVA Dictionaries

## Contenu

- Utilisation rapide
- Workflow complet
- Validation
- Ajouter un champ a une table existante
- Options pour une table specifique integrateur
- Changement de version : quelles tables obligent a recompiler
- Scripts disponibles
- References

---

## Utilisation rapide

```
echo '{
  "table": "MonEntite",
  "description": "Ma table metier",
  "ce_value": "A",
  "base": "GtfMonEntite",
  "base_prefix": "Gtf",
  "dict_name": "gtfdd",
  "creator": "<login_diva>",
  "u_field_size": 0,
  "filler_size": 0,
  "fields": [
    {"name": "MonCode", "nature": "20", "description": "Code entite"},
    {"name": "MonLib", "nature": "80", "description": "Libelle"}
  ],
  "indexes": [
    {"name": "Index_A", "description": "Index primaire", "unique": false,
     "fields": ["Dos", "MonCode"]}
  ]
}' | py .claude/skills/managing-diva-dictionaries/scripts/generate_dhsd_block.py \
    --stdin --user <login_diva> --output blocs.json
```

---

## Workflow complet

### 1. Preparer les parametres

Determiner :
- **table** : nom de la table DIVA (PascalCase, ex: `MonEntite`)
- **ce_value** : valeur CE unique dans la base (1-9, A-Z) -- verifier dans le .dhsd cible
- **base** : nom de la base physique = `{PrefixeDict}{NomBase}` (ex: `GtfMonEntite`)
- **dict_name** : dictionnaire cible (ex: `gtfdd`)
- **fields** : liste des champs metier avec nom + Nature (voir `reference/nature-types.md`)
- **indexes** : au minimum `Index_A` avec `Dos` + champ(s) cle

Les champs du socle audit canonique sont ajoutes automatiquement : `Ce1`, `Dos`, `UserCr`, `UserMo`, `UserCrDh`, `UserMoDh`. Le champ historique `UserTrace` (Nature=28) n'est plus ajoute : 0 occurrence dans le corpus X.13 (2026-04-17).

**Proposer une Nature ET une FK pour un champ metier** : utiliser `suggest_nature.py`
qui applique (a) la taxonomie de suffixes DIVA (Dt->D8 93 %, Dh->DH 98 %, Fl->1,0 95 %, etc.)
et (b) la taxonomie "foreign key par zoom standard" (Pay->T013/9053 100 %, Dev->T007/9047 93 %,
Depo->T017/9057 97 %, Cpt->C3 97 %, ...) :

```
py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py --name CdeDt
# -> {"nature": "D8", "confidence": 0.93, "rule": "suffix:Dt", "fk_target": null}

py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py --name RacPays
# -> {"nature": null, "fk_target": {"target": "T013", "zoom_num": 9053,
#      "module_dhop": "Gttmchkt013.dhop", "find_fn": "Find_T013",
#      "get_lib_fn": "Get_T013_Lib", "confidence": 1.0, "kind": "t-table"}}

py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py --name RacCod
# -> fk_target=null + fk_note="Code generique -- multiples cibles possibles. DEMANDER le contexte."
```

Utilisation :
- Si `fk_target` est non null avec `confidence >= 0.90`, proposer automatiquement au CP3 de `creating-diva-entity`
- Si `fk_note` est present (suffixe ambigu : Cod, Lib, Ref, ...), demander le contexte au collaborateur
- Si les deux sont nuls, pas de FK deduite (champ metier simple)

Voir :
- [reference/taxonomie-suffixes.md](reference/taxonomie-suffixes.md) pour la matrice Nature complete
- Le skill [`binding-zoom-to-field`](../binding-zoom-to-field/SKILL.md) et son `reference/fk-pattern.md` pour le pattern FK 3 couches + taxonomie suffixes predicteurs

### 2. Generer les 5 blocs

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_dhsd_block.py \
    --stdin --user <login_diva> --output blocs.json < params.json
```

Le script calcule automatiquement les positions, la taille totale, et les positions cumulees dans les index.

### 3. Valider les blocs generes

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --blocks blocs.json
```

### 4. Inserer dans le .dhsd

```
py .claude/skills/managing-diva-dictionaries/scripts/insert_dhsd_blocks.py \
    --dhsd "chemin/dictionnaire.dhsd" --blocks blocs.json
```

Le script insere automatiquement les 5 blocs au bon endroit (tri alphabetique) :
- Blocs `[CHAMP]` : position alphabetique (champs globaux existants skippes avec rapport)
- Bloc `[TABLE]` : position alphabetique parmi les [TABLE]
- Bloc `[BASE]` : position alphabetique parmi les [BASE] -- ou, si la base existe
  deja, rattachement de la table a son `[TABLES]` via `--attach-to-base` (voir la section
  `Options pour une table specifique integrateur`)
- Blocs `[INDEX]` : groupes par base, position alphabetique
- Lignes `[INDEXL]` : avant `[/INDEXL]`

Options : `--dry-run` (previsualiser sans ecrire), `--no-backup` (pas de .bak).
Detection automatique des doublons (table, base → erreur ; champ global → skip).
Validation post-insertion automatique via `validate_dhsd.py`.

#### Comportement sur champs globaux existants

Le script lit la section `[CHAMP]` globale du dictionnaire cible et utilise
la **Nature reelle** des champs deja declares (ex: `Lib` Nature=40). Un
parametre utilisateur divergent (ex: Nature=80) declenche un warning dans
`nature_warnings` mais **ne remplace PAS** la declaration globale -- le
champ est utilise tel qu'il existe dans le dictionnaire.

**Consequence pratique** : avant de definir un bloc table avec un champ
global, verifier sa Nature dans la section `[CHAMP]` globale du dictionnaire
cible. Si vous utilisez `Lib` (40 octets), definissez le bloc avec cette
taille, pas avec une nature/taille differente -- sinon les positions
calculees seront fausses.

Reference code : `insert_dhsd_blocks.py:342-359`.

### 5. Valider le .dhsd modifie

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --path "chemin/dictionnaire.dhsd" --table MonEntite
```

---

## Validation

Le skill porte **seize regles**, `DICT01`-`DICT16`, mais elles ne sont pas toutes
verifiees au meme endroit -- et le savoir evite d'attendre seize verdicts de la
meme commande (detail dans
[reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)) :

- **douze** sont emises par `validate_dhsd.py` : `DICT01`-`DICT09` et
  `DICT14`-`DICT16` ;
- **deux** sont des garde-fous de GENERATION portes par `generate_dhsd_block.py`
  (`DICT12`, `DICT13`) : elles arretent la generation, elles n'apparaissent dans
  aucune sortie du validateur ;
- **deux** ne sont pas codees dans ce skill (`DICT10`, `DICT11`) -- le linter les
  implemente sous `D10` et `D11`, lancer `lint_diva.py` sur le `.dhsd` les couvre.

| Regle | Severite | Quoi |
|-------|----------|------|
| DICT01 | error | Champs qui se chevauchent (positions) |
| DICT02 | error | Trous entre les champs (positions) |
| DICT03 | error | U-field absent |
| DICT04 | error | Champ sans declaration [CHAMP] |
| DICT05 | error | Encodage pas ISO-8859-1 |
| DICT06 | error | Fins de ligne pas CRLF |
| DICT07 | error | [/CHAMPS] manquant |
| DICT08 | error | [/TABLES] manquant |
| DICT09 | error | [/INDEX] manquant |
| DICT10 | *non implementee* | CE incoherent dans l'index -- le linter la porte sous `D10` |
| DICT11 | *non implementee* | Prefixe base incorrect -- le linter la porte sous `D11` |
| DICT12 | error | `ce_value` invalide avec discriminator Ce1 (pre-generation) |
| DICT13 | error | Lettre cle d'index non alphanumerique 1 char (pre-generation) |
| DICT14 | error (avec `--dhsd-standard`) | Metadonnees [BASEU]/[TABLEU] divergentes du standard |
| DICT15 | error (avec `--dhsd-standard`) | [CHAMPR] sur table sans U-container standard |
| DICT16 | error (avec `--dhsd-standard`) | [CHAMP] surcharge redeclare un champ standard avec attributs differents (option C interdite) |

Trois modes de validation :
- `--blocks` : valide les blocs generes (avant insertion)
- `--path --table` : valide une table dans un .dhsd existant (apres insertion)
- `--path --dhsd-standard <chemin_standard>` : valide une surcharge contre son .dhsd standard (DICT14/DICT15/DICT16)

**Option `--migration`** : sur une table **legacy en cours d'alignement**
(migration de version), l'absence de U-field (DICT03) est un etat **preexistant**, pas
une regression. `--migration` fait passer **DICT03 en `warning`** au lieu d'`error`, pour
que le vrai signal d'une modification de positions (DICT01 chevauchement / DICT02 trou) ne
soit pas noye. Mesure terrain : 45 % des tables standard X.13 et 67 % des tables
specifiques n'ont pas de U-field -> sans ce mode, DICT03 sature le rapport. `modify_field_nature.py`
valide automatiquement en mode migration.

---

## Ajouter un champ a une table existante (#199 / #167)

Cas distinct de la creation d'une table complete et de la surcharge d'une table
standard : ajouter **un** champ a une table qui existe deja dans **votre** dictionnaire.

Trois points decident du travail, detailles dans
[reference/ajout-champ-table-existante.md](reference/ajout-champ-table-existante.md) :

1. **Les 5 lignes obligatoires** du bloc `[CHAMP]` -- `Version`, `Nom`, `Gel`, `Nature`, `Flags` (359/359 sur un dictionnaire reel). `DateM` et `NomOdbc` sont
   **facultatifs** -- ne pas inventer de `DateM`.
2. **Ou placer le champ** : en **fin** de table rien ne se decale ; **au milieu**, tous
   les champs en aval se decalent dans la table **et** dans chaque index.
3. **Faut-il synchroniser SQL ?** Le critere est le **rattachement a une `[BASE]`** (le
   nom de la table figure-t-il dans un `[TABLES]` ?), **pas** la presence de `NomOdbc`.
   Une structure de travail en memoire n'a besoin d'aucune synchro -- 25 % des tables
   mesurees sont dans ce cas.

> Pour un champ sur une table **du standard**, ce n'est pas cette page : passer par la
> surcharge (voir « Ajouter un champ a une table standard via `generate_surcharge_field.py` »).

---

## Options pour une table specifique integrateur (#207 / #245)

Les valeurs par defaut du generateur suivent la convention d'une table dont
**l'integrateur est proprietaire**, pas celle d'une table du standard.

| Option | Defaut | Effet |
|--------|--------|-------|
| `--user <login_diva>` | **aucun -- obligatoire** | Login DIVA estampille dans chaque ligne `Version=`. Le script **refuse** sans. |
| `--u-field-size N` | **`0`** | `0` = **pas de container U**. En ajouter un (`--u-field-size 500`) n'est pas faux, c'est un choix explicite. |
| `--no-audit` | absent | Retire `UserCr`, `UserMo`, `UserCrDh`, `UserMoDh`. |

`Ce1` est **toujours** genere : une table peut exister sans discriminateur (cf.
[reference/dhsd-5-zones.md](reference/dhsd-5-zones.md), « Table sans discriminateur »),
mais en prevoir un fait partie des bonnes pratiques -- il n'y a donc **pas** d'option pour
s'en passer a la generation.

### `--user` : pourquoi obligatoire

Le login DIVA du developpeur (ex. `xyz_dev222`) **ne se devine pas** -- ce n'est pas le
login Windows. Avant, toutes les lignes `Version=` portaient `"Claude"` : la tracabilite
des modifications du dictionnaire etait rompue. Le script voisin
`generate_surcharge_field.py` exigeait deja `--user` ; les deux sont desormais coherents.

Deux garde-fous, pour la raison meme qui a motive la demande :

- une **virgule** est refusee (elle casserait la ligne `Version=`, a champs separes par des
  virgules) ;
- au-dela de **20 caracteres**, le script **refuse** au lieu de tronquer en silence -- une
  troncature muette detruirait la tracabilite recherchee.

Le login peut aussi venir de la cle `creator` du JSON ; l'option CLI est prioritaire.

### Container U absent : consequence sur `DICT03`

`DICT03` (container U absent) est une **erreur** par defaut. Une absence **declaree** la fait
passer en **warning**, sans quoi le generateur produirait des blocs refuses par son propre
validateur :

- **blocs generes** : rien a faire, le JSON porte `summary.u_field = null` et
  `validate_dhsd.py --blocks` le lit ;
- **fichier existant** : `validate_dhsd.py --path ... --table ... --no-u-field`.

`--no-u-field` est distinct de `--migration` : le premier dit « conçue ainsi, c'est
assume », le second « etat preexistant subi sur une table legacy ». Une absence **non
declaree** reste une erreur -- l'assouplissement est cible, pas global. Detail :
[reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md), DICT03.

### Base deja existante : rattacher, pas recreer

Si la base est deja declaree dans le dictionnaire, l'insertion echoue sur
`Base 'X' existe deja`. La table se rattache alors a la base existante :

```
py .claude/skills/managing-diva-dictionaries/scripts/insert_dhsd_blocks.py \
    --dhsd "chemin/dictionnaire.dhsd" --blocks blocs.json --attach-to-base GtfTrace
```

Aucun bloc `[BASE]` n'est cree ; une ligne `Nom=<table>,0` est inseree au **rang
alphabetique** dans le `[TABLES]` de la base cible. Ce cas n'a rien d'exotique : sur un
dictionnaire specifique reel, **10 bases sur 24** portent plusieurs tables.

> **Ne pas se contenter d'omettre le bloc `[BASE]`.** C'est la ligne dans `[TABLES]` qui
> attache la table a son fichier physique : sans elle, la table est **orpheline**.

Le nom passe a `--attach-to-base` doit etre celui que referencent les blocs generes
(`CLE=` des index et lignes `[INDEXL]`). Sinon le script **refuse sans rien ecrire** --
autrement la table serait rattachee a une base et ses index pointeraient vers une autre.
Meme refus, fichier inchange, si la base est introuvable ou la table deja rattachee.

---

## Changement de version : quelles tables obligent a recompiler (#110)

Quand l'integrateur recoit une nouvelle version ou un Service Pack, la question operationnelle
est : **quelles tables ont change de taille ?** Car un objet compile **memorise la taille**
des tables qu'il utilise ; un specifique compile contre l'ancien dictionnaire leve a
l'execution `enregistrement deja alloue avec la taille X par le module Y`.

```
py .claude/skills/managing-diva-dictionaries/scripts/compare_dhsd_versions.py --from "ancien/gtfdd.dhsd" --to "nouveau/gtfdd.dhsd" --format text
```

Le critere est la **`Taille=`** du bloc `[TABLE]`, **jamais le nombre de champs** -- qui se
trompe dans les deux sens (mesures dans
[reference/dhsd-diff-downgrade.md](reference/dhsd-diff-downgrade.md)).

| Sortie | Contenu |
|--------|---------|
| `incompatibles` | tables dont la `Taille=` a change -> **recompiler le specifique qui les utilise** (obligatoire) |
| `compatibles_champs_ajoutes` | champs ajoutes **a taille constante** (le standard a consomme son `Filler`) -> rien a faire |
| `containers_u_modifies` | capacite d'une zone `U<NomTable>` modifiee -> une **reduction** est anormale, a remonter a Divalto |
| `tables_ajoutees` / `tables_supprimees` | apparitions / disparitions |

**Codes retour** : `0` aucun changement de taille, `1` au moins un (utilisable en garde-fou
de script), `2` erreur. `--only-incompatible` reduit la sortie au perimetre a recompiler ;
`--format json` pour un traitement automatise.

> **Ce que l'integrateur ne peut pas faire** : corriger un dictionnaire standard. Les sources
> du standard sont protegees (pas de recompilation possible) et l'objet compile porte deja la
> taille. Face a une anomalie du standard -- y compris une zone `U` reduite -- la seule action
> est de la **remonter a Divalto**.

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/nature_to_size.py` | Convertit un code Nature en taille octets | `--nature "20"` ou `--stdin` JSON | JSON {nature, size, type, description} |
| `scripts/generate_dhsd_block.py` | Genere les 5 blocs INI (nouvelle table) | JSON params (stdin ou fichier) + `--user` **obligatoire** [+ `--u-field-size` `--no-audit`] | JSON {table, blocks, positions, taille, summary{creator, u_field, audit_fields}} |
| `scripts/generate_surcharge_field.py` | Ajoute un champ a une table standard via surcharge (mode `--output` creation ou `--append-to` ajout) | `--dhsd-standard --table --field-name --nature --label --user [--prefix]` | JSON {status, file, mode, field, nature, size_bytes, container, container_capacity, offset_in_container, capacity_remaining, table_metadata_source, bases_metadata_source, filetime_le} |
| `scripts/insert_dhsd_blocks.py` | Insere les blocs dans un .dhsd (tri alpha, backup, validation) | `--dhsd` + `--blocks` [+ `--attach-to-base` `--dry-run`] | JSON {success, insertions, validation} |
| `scripts/modify_field_nature.py` | **Modifie la Nature d'un champ existant** + re-propage les positions (tables + index) | `--path` + `--field` + `--new-nature` [+ `--filler-policy` `--dry-run`] | JSON {field, delta, tables[], indexes[], warnings[], validation[]} |
| `scripts/compare_dhsd_versions.py` | **Compare deux versions d'un `.dhsd`** : quelles tables ont change de `Taille=` (= a recompiler) | `--from` + `--to` [+ `--only-incompatible` `--format json|text`] | JSON {resume, incompatibles[], compatibles_champs_ajoutes[], containers_u_modifies[], tables_ajoutees[], tables_supprimees[], action} -- exit 1 si une taille a change |
| `scripts/validate_dhsd.py` | Valide blocs generes ou .dhsd existant | `--blocks` JSON ou `--path` .dhsd + `--table` [+ `--migration` `--no-u-field`] | JSON {target, valid, errors, warnings, summary} |

---

## Surcharge dictionnaire

Le skill couvre aussi la **surcharge** d'un dictionnaire standard (ajout de champs custom sur des tables existantes via `<dict>u.dhsd`). Deux references dediees :

- [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md) -- pattern complet (structure `[CHAMP]/[CHAMPR]/[CHAMPL]/[TABLEU]/[BASEU]`, regle d'offset cumule dans le U-container, metadonnees recopiees du standard, options A/B/C)
- [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md) -- pattern d'ajout d'index custom en surcharge (les 6 ecarts marketplace, filtered indexes via `Ce<N>` calcules mchk, 3 types d'index principal/conditionnel/avec identifiant)

### Ajouter un champ a une table standard via `generate_surcharge_field.py`

Operation deterministe une fois `(table, champ, Nature)` connus. Le script `generate_surcharge_field.py` automatise le pattern complet (parse metadonnees standard pour DICT14, verif U-container et capacite DICT15, calcul offset cumule, FILETIME courant, ecriture ISO-8859-1+CRLF). Deux modes mutuellement exclusifs :

**Mode `--output` -- creation d'une nouvelle surcharge :**

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_surcharge_field.py \
    --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/gtfdd.dhsd" \
    --table T143 \
    --field-name speTrajetKmMax \
    --nature 5,0 \
    --label "Plafond km deplacement" \
    --user rootSPE \
    --prefix spe \
    --output "{CHEMIN_SPECIFIQUE}/fichiers/gtfddu.dhsd"
```

**Mode `--append-to` -- ajout dans une surcharge existante :**

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_surcharge_field.py \
    --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/gtfdd.dhsd" \
    --table T143 \
    --field-name speTrajetKmMin \
    --nature 5,0 \
    --label "Plancher km deplacement" \
    --user rootSPE \
    --prefix spe \
    --append-to "{CHEMIN_SPECIFIQUE}/fichiers/gtfddu.dhsd"
```

Le script calcule automatiquement l'**offset cumule** en re-parsant la surcharge existante (`--append-to`) ou demarre a 1 (`--output`). Il genere `[BASEU]` pour **chaque** base concernee (cas multi-bases : `c3` ancre simultanement sur `CcfJCA` + `Ccfm`).

**Argument `--prefix` (optionnel)** : garde-fou anti-typo uniquement. Il **n'existe aucune regle universelle** pour identifier un champ specifique depuis son nom -- selon les postes integrateur, le prefixe peut etre 1/2/3 caracteres, n'importe quelle casse, ou totalement absent (PascalCase pur identique au standard). Si `--prefix` est fourni, le script verifie juste que `field_name.startswith(prefix)`. Sans `--prefix`, n'importe quel nom est accepte. **Consequence linter** : DICT12 (PascalCase) reste un warning informatif structurel -- faux positifs frequents sur les surcharges avec prefixe poste.

**Limitations v1** : champs tableau (`Nature=20*3`), multi-table composite (un meme champ ancre sur `U-A` et `U-B` simultanement), index custom en surcharge -- non couverts par le script. Pour ces cas, voir [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md) et [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md) (rédaction manuelle).

**Validation post-ecriture** -- enchainer avec `validate_dhsd.py --dhsd-standard` :

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --path "<dict>u.dhsd" --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/{dict_name}.dhsd"
```

Verifie DICT14 (metadonnees divergentes), DICT15 (table sans U-container), DICT16 (option C interdite). Necessite l'acces au `.dhsd` standard de l'ERP livre (`{CHEMIN_ERP_STANDARD}/dictionnaires/`).

---

## Modifier la Nature d'un champ existant

Changer la Nature d'un champ **deja declare** (ex. alignement de version : `Dos` 3->8,
`Lib` 40->50) decale les positions de **tous les champs suivants** dans **chaque**
`[TABLE]/[CHAMPS]` et **chaque** `[INDEX]/[CHAMPS]` qui l'utilisent. Le script
`modify_field_nature.py` automatise ce recalcul (la modification de Nature est
**globale** -- une seule declaration `[CHAMP]` -- donc la re-propagation couvre
**toutes** les tables/index, jamais un sous-ensemble).

```
py .claude/skills/managing-diva-dictionaries/scripts/modify_field_nature.py \
    --path "chemin/dictionnaire.dhsd" --field Lib --new-nature 50
```

Le script : (1) lit la Nature actuelle du `[CHAMP]` global -> `delta` ; (2) met a jour
la ligne `Nature=` ; (3) decale les positions en aval dans chaque table et index ;
(4) reecrit en ISO-8859-1+CRLF (+ `.bak`) ; (5) valide chaque table touchee via
`validate_dhsd` en **mode migration**.

**Politique Filler** (`--filler-policy`) :

| Valeur | Effet sur la table | Quand |
|--------|--------------------|-------|
| `shift` **(defaut)** | tout decale, `Taille` grandit de `delta`, Filler inchange | migration / creation / **table sans Filler** / on accepte que le record grandisse (= comportement standard Divalto) |
| `cannibalize` | zone champ->Filler decalee, **Filler reduit de `delta`**, champs apres le Filler figes, `Taille` **constante** | preserver la taille du record **sans reconstruire le fichier** (donnees en prod, downgrade) -- **erreur explicite si `Filler < delta` ou absent** |

> **`cannibalize` s'applique a VOTRE dictionnaire, jamais a un dictionnaire standard.** Le `Filler` d'une table standard est la **reserve de Divalto**, qu'il consomme lui-meme a chaque version (262 tables mesurees) : y prendre des octets, c'est se placer sur le chemin de ses futurs champs, **a taille de table constante** -- donc sans qu'aucun controle de compatibilite ne le detecte. Sur une table standard, la seule zone utilisable est le container `U<NomTable>` (cf. [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md), section « `Filler` vs container `U` »). Et de toute facon un dictionnaire standard **ne se modifie pas** : on le surcharge.

**Limites v1 (signalees, non traitees)** :
- couche relationnelle `[CHAMPL]` (records logiques RecordSQL) **non re-propagee** ->
  le script emet un **warning** si le champ y figure (cf. [reference/dhsd-diff-downgrade.md](reference/dhsd-diff-downgrade.md), regle des 3 couches) ;
- champs **tableau** (Nature avec `*`) et **multi-table composite** -> **refuses**
  (rediger a la main, cf. [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md)).

Toujours relire le `validation[]` du JSON avant de compiler : une violation `DICT01`
(chevauchement) ou `DICT02` (trou) signale un recalcul casse.

---

## References

- **Les 5 zones avec format et exemples** : Voir [reference/dhsd-5-zones.md](reference/dhsd-5-zones.md) (Zone 4 documente les 3 types d'index et les filtered indexes Divalto)
- **Surcharge -- pattern complet** : Voir [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md)
- **Surcharge -- index custom** : Voir [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md)
- **Table Nature -> taille** : Voir [reference/nature-types.md](reference/nature-types.md) (couverture ~40 % des Nature reelles du standard -- inviter a enrichir)
- **Ajouter un champ a une table existante** : Voir [reference/ajout-champ-table-existante.md](reference/ajout-champ-table-existante.md) (5 lignes obligatoires du `[CHAMP]`, placement, decision de synchro SQL)
- **Anti-patterns DICT01-DICT16** : Voir [reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)
- **Diff de dictionnaire & arbitrage downgrade (3 couches, 3 voies)** : Voir [reference/dhsd-diff-downgrade.md](reference/dhsd-diff-downgrade.md) (compatibilite binaire **outillee** par `compare_dhsd_versions.py` ; arbitrage 3-voies methodologique)
