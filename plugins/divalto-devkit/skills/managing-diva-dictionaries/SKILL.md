---
name: managing-diva-dictionaries
description: >
  Ajoute une table complete dans un dictionnaire Divalto (.dhsd) en generant les 5 zones
  obligatoires : [CHAMP] (declaration des champs), [TABLE] (structure avec positions calculees),
  [BASE] (fichier physique), [INDEX] (index avec positions cumulees), et [INDEXL] (mapping).
  Inclut le socle audit canonique (Ce1, Dos, UserCr, UserMo, UserCrDh, UserMoDh, Filler, U-field),
  le calcul automatique des positions sans trou, la taxonomie de suffixes typés (Dt->D8, Dh->DH,
  Fl->1,0...) via suggest_nature.py, et la validation de coherence D01-D14.
  Preserve l'encodage ISO-8859-1+CRLF. A utiliser pour declarer une nouvelle table metier
  dans le dictionnaire avant de generer le code.
---

# Managing DIVA Dictionaries

## Contenu

- Utilisation rapide
- Workflow complet
- Validation
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
  "u_field_size": 500,
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
    --stdin --output blocs.json
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

Les champs du socle audit canonique sont ajoutes automatiquement : `Ce1`, `Dos`, `UserCr`, `UserMo`, `UserCrDh`, `UserMoDh`. Le champ historique `UserTrace` (Nature=28) n'est plus ajoute : 0 occurrence dans le corpus X.13 (batch 16, 2026-04-17).

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
- Si `fk_target` est non null avec `confidence >= 0.90`, proposer automatiquement au CP-3 de `creating-diva-entity`
- Si `fk_note` est present (suffixe ambigu : Cod, Lib, Ref, ...), demander le contexte au collaborateur
- Si les deux sont nuls, pas de FK deduite (champ metier simple)

Voir :
- [reference/taxonomie-suffixes.md](reference/taxonomie-suffixes.md) pour la matrice Nature complete
- Le skill [`binding-zoom-to-field`](../binding-zoom-to-field/SKILL.md) et son `reference/fk-pattern.md` pour le pattern FK 3 couches + taxonomie suffixes predicteurs

### 2. Generer les 5 blocs

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_dhsd_block.py \
    --stdin --output blocs.json < params.json
```

Le script calcule automatiquement les positions, la taille totale, et les positions cumulees dans les index.

### 3. Valider les blocs generes

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --blocks blocs.json
```

**Check SVN pre-modification** (optionnel) : avant de modifier un dictionnaire .dhsd existant, verifier les modifs locales non committees et l'activite recente pour detecter un refactor en cours.

```bash
py .claude/skills/managing-diva-dictionaries/scripts/check_svn_recent.py     --path "{DHSD_PATH}" --limit 5 --days 30
```

Si `warning != null` ou `local_changes.has_changes=true`, signaler au collaborateur avant de poursuivre. Degradation gracieuse si SVN indispo. Voir [reference/svn-policy.md](reference/svn-policy.md).

### 4. Inserer dans le .dhsd

```
py .claude/skills/managing-diva-dictionaries/scripts/insert_dhsd_blocks.py \
    --dhsd "chemin/dictionnaire.dhsd" --blocks blocs.json
```

Le script insere automatiquement les 5 blocs au bon endroit (tri alphabetique) :
- Blocs `[CHAMP]` : position alphabetique (champs globaux existants skippes avec rapport)
- Bloc `[TABLE]` : position alphabetique parmi les [TABLE]
- Bloc `[BASE]` : position alphabetique parmi les [BASE]
- Blocs `[INDEX]` : groupes par base, position alphabetique
- Lignes `[INDEXL]` : avant `[/INDEXL]`

Options : `--dry-run` (previsualiser sans ecrire), `--no-backup` (pas de .bak).
Detection automatique des doublons (table, base → erreur ; champ global → skip).
Validation post-insertion automatique via `validate_dhsd.py`.

#### Comportement sur champs globaux existants (R-008)

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

Le script `validate_dhsd.py` verifie 16 regles (D01-D16, detail dans [reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)) :

| Regle | Severite | Quoi |
|-------|----------|------|
| D01 | error | Champs qui se chevauchent (positions) |
| D02 | error | Trous entre les champs (positions) |
| D03 | error | U-field absent |
| D04 | error | Champ sans declaration [CHAMP] |
| D05 | error | Encodage pas ISO-8859-1 |
| D06 | error | Fins de ligne pas CRLF |
| D07 | error | [/CHAMPS] manquant |
| D08 | error | [/TABLES] manquant |
| D09 | error | [/INDEX] manquant |
| D10 | error | CE incoherent dans l'index |
| D11 | warning | Prefixe base incorrect |
| D12 | error | `ce_value` invalide avec discriminator Ce1 (pre-generation) |
| D13 | error | Lettre cle d'index non alphanumerique 1 char (pre-generation) |
| D14 | error (avec `--dhsd-standard`) | Metadonnees [BASEU]/[TABLEU] divergentes du standard |
| D15 | error (avec `--dhsd-standard`) | [CHAMPR] sur table sans U-container standard |
| D16 | error (avec `--dhsd-standard`) | [CHAMP] surcharge redeclare un champ standard avec attributs differents (option C interdite) |

Trois modes de validation :
- `--blocks` : valide les blocs generes (avant insertion)
- `--path --table` : valide une table dans un .dhsd existant (apres insertion)
- `--path --dhsd-standard <chemin_standard>` : valide une surcharge contre son .dhsd standard (D14/D15/D16)

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/nature_to_size.py` | Convertit un code Nature en taille octets | `--nature "20"` ou `--stdin` JSON | JSON {nature, size, type, description} |
| `scripts/generate_dhsd_block.py` | Genere les 5 blocs INI (nouvelle table) | JSON params (stdin ou fichier) | JSON {table, blocks, positions, taille, summary} |
| `scripts/generate_surcharge_field.py` | Ajoute un champ a une table standard via surcharge (mode `--output` creation ou `--append-to` ajout) | `--dhsd-standard --table --field-name --nature --label --user [--prefix]` | JSON {status, file, mode, field, nature, size_bytes, container, container_capacity, offset_in_container, capacity_remaining, table_metadata_source, bases_metadata_source, filetime_le} |
| `scripts/insert_dhsd_blocks.py` | Insere les blocs dans un .dhsd (tri alpha, backup, validation) | `--dhsd` + `--blocks` [+ `--dry-run`] | JSON {success, insertions, validation} |
| `scripts/validate_dhsd.py` | Valide blocs generes ou .dhsd existant | `--blocks` JSON ou `--path` .dhsd + `--table` | JSON {target, valid, errors, warnings, summary} |

---

## Surcharge dictionnaire

Le skill couvre aussi la **surcharge** d'un dictionnaire standard (ajout de champs custom sur des tables existantes via `<dict>u.dhsd`). Deux references dediees :

- [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md) -- pattern complet (structure `[CHAMP]/[CHAMPR]/[CHAMPL]/[TABLEU]/[BASEU]`, regle d'offset cumule dans le U-container, metadonnees recopiees du standard, options A/B/C)
- [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md) -- pattern d'ajout d'index custom en surcharge (les 6 ecarts marketplace, filtered indexes via `Ce<N>` calcules mchk, 3 types d'index principal/conditionnel/avec identifiant)

### Ajouter un champ a une table standard via `generate_surcharge_field.py`

Operation deterministe une fois `(table, champ, Nature)` connus. Le script `generate_surcharge_field.py` automatise le pattern complet (parse metadonnees standard pour D14, verif U-container et capacite D15, calcul offset cumule, FILETIME courant, ecriture ISO-8859-1+CRLF). Deux modes mutuellement exclusifs :

**Mode `--output` -- creation d'une nouvelle surcharge :**

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_surcharge_field.py \
    --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/gtfdd.dhsd" \
    --table T143 \
    --field-name dgsTrajetKmMax \
    --nature 5,0 \
    --label "Plafond km deplacement" \
    --user rootDGS \
    --prefix dgs \
    --output "{CHEMIN_SPECIFIQUE}/fichiers/gtfddu.dhsd"
```

**Mode `--append-to` -- ajout dans une surcharge existante :**

```
py .claude/skills/managing-diva-dictionaries/scripts/generate_surcharge_field.py \
    --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/gtfdd.dhsd" \
    --table T143 \
    --field-name dgsTrajetKmMin \
    --nature 5,0 \
    --label "Plancher km deplacement" \
    --user rootDGS \
    --prefix dgs \
    --append-to "{CHEMIN_SPECIFIQUE}/fichiers/gtfddu.dhsd"
```

Le script calcule automatiquement l'**offset cumule** en re-parsant la surcharge existante (`--append-to`) ou demarre a 1 (`--output`). Il genere `[BASEU]` pour **chaque** base concernee (cas multi-bases : `c3` ancre simultanement sur `CcfJCA` + `Ccfm`).

**Argument `--prefix` (optionnel)** : garde-fou anti-typo uniquement. Il **n'existe aucune regle universelle** pour identifier un champ specifique depuis son nom -- selon les postes integrateur, le prefixe peut etre 1/2/3 caracteres, n'importe quelle casse, ou totalement absent (PascalCase pur identique au standard). Si `--prefix` est fourni, le script verifie juste que `field_name.startswith(prefix)`. Sans `--prefix`, n'importe quel nom est accepte. **Consequence linter** : D12 (PascalCase) reste un warning informatif structurel -- faux positifs frequents sur les surcharges avec prefixe poste.

**Limitations v1** : champs tableau (`Nature=20*3`), multi-table composite (un meme champ ancre sur `U-A` et `U-B` simultanement), index custom en surcharge -- non couverts par le script. Pour ces cas, voir [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md) et [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md) (rédaction manuelle).

**Validation post-ecriture** -- enchainer avec `validate_dhsd.py --dhsd-standard` :

```
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --path "<dict>u.dhsd" --dhsd-standard "{CHEMIN_ERP_STANDARD}/dictionnaires/{dict_name}.dhsd"
```

Verifie D14 (metadonnees divergentes), D15 (table sans U-container), D16 (option C interdite). Necessite l'acces au `.dhsd` standard de l'ERP livre (`{CHEMIN_ERP_STANDARD}/dictionnaires/`).

---

## References

- **Les 5 zones avec format et exemples** : Voir [reference/dhsd-5-zones.md](reference/dhsd-5-zones.md) (Zone 4 documente les 3 types d'index et les filtered indexes Divalto)
- **Surcharge -- pattern complet** : Voir [reference/dhsd-surcharge-pattern.md](reference/dhsd-surcharge-pattern.md)
- **Surcharge -- index custom** : Voir [reference/dhsd-surcharge-indexes.md](reference/dhsd-surcharge-indexes.md)
- **Table Nature -> taille** : Voir [reference/nature-types.md](reference/nature-types.md) (couverture ~40 % des Nature reelles du standard -- inviter a enrichir)
- **Anti-patterns D01-D16** : Voir [reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)
