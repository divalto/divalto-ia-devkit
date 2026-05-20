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

Le script `validate_dhsd.py` verifie 11 regles (D01-D11, detail dans [reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)) :

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

Deux modes de validation :
- `--blocks` : valide les blocs generes (avant insertion)
- `--path --table` : valide une table dans un .dhsd existant (apres insertion)

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/nature_to_size.py` | Convertit un code Nature en taille octets | `--nature "20"` ou `--stdin` JSON | JSON {nature, size, type, description} |
| `scripts/generate_dhsd_block.py` | Genere les 5 blocs INI | JSON params (stdin ou fichier) | JSON {table, blocks, positions, taille, summary} |
| `scripts/insert_dhsd_blocks.py` | Insere les blocs dans un .dhsd (tri alpha, backup, validation) | `--dhsd` + `--blocks` [+ `--dry-run`] | JSON {success, insertions, validation} |
| `scripts/validate_dhsd.py` | Valide blocs generes ou .dhsd existant | `--blocks` JSON ou `--path` .dhsd + `--table` | JSON {target, valid, errors, warnings, summary} |

---

## References

- **Les 5 zones avec format et exemples** : Voir [reference/dhsd-5-zones.md](reference/dhsd-5-zones.md)
- **Table Nature -> taille** : Voir [reference/nature-types.md](reference/nature-types.md)
- **Anti-patterns D01-D11** : Voir [reference/dhsd-anti-patterns.md](reference/dhsd-anti-patterns.md)
