---
name: binding-zoom-to-field
description: >
  Ajoute un binding "FK par zoom standard" a une entite metier DIVA existante
  (post-creation). Pour chaque FK declaree, enrichit le Module Check (.dhsp)
  avec `Module "Gttmchk<cible>.dhop"` + procedures `Check_<SRC>_Field_<CHAMP>(+_Lib)`,
  puis enrichit le masque (.dhsf) avec `f8=<zoom>`, `table_associee`, `diva_apres`,
  bouton zoom + procedure callback dans `[diva]`. A utiliser pour reproduire le
  workflow RETEX R-003 (ajout post-hoc de binding zoom pays/devise/... sur une
  entite deja creee). Pattern documente dans reference/fk-pattern.md.
---

# binding-zoom-to-field

Skill post-creation pour ajouter des **foreign keys par zoom standard** aux
entites metier existantes. Complete le trio de skills createurs :

- **Creation** : `creating-diva-entity` (FK-04 : CP1bis + --fk aux etapes 3 et 5ter)
- **Generateurs** : `generating-objet-metier --fk` (FK-02) + `manipulating-dhsf-screens/dhsf_add_fk.py` (FK-03)
- **Post-creation** : **ce skill** (FK-05) -- inject les FK dans des fichiers deja existants

## Quand utiliser ce skill

- Le **cas RETEX R-003** : une entite est deja en production (RACECHIEN), on
  souhaite brancher un zoom standard (ex pays 9053) sur un champ existant
  (RacPays) sans regenerer tout le Module Check
- **Evolution d'entite** : ajout d'une FK oubliee lors de la creation initiale
- **Migration** : retrofit de FK sur un corpus d'entites existantes

## Ce que le skill fait

Pour chaque FK declaree (`CHAMP:TARGET[:ZOOM]`) :

### Couche 1 -- Module Check (.dhsp)

Via `scripts/dhsp_add_fk.py` :
- Detecte le `PREFIX_` (GT_/CC_/RT_/...) depuis les appels framework existants
- Detecte le `<DICT>` (GTFDD/CCFDD/...) depuis les declarations `Record` du fichier
- Detecte le `<NomVue>` depuis `Declaration_<NomVue>` ou `RS_<NomVue>`
- Insere `Module "Gttmchk<target>.dhop"` apres le dernier `Module` existant (idempotent)
- Genere `Check_<SRC>_Field_<CHAMP>` + `Check_<SRC>_Field_<CHAMP>_Lib` en fin de fichier (idempotent)
- Exempte C3/C4/C5/C6/C7/C8/C9 (framework CC indirect, pas de Module unique dedie)

### Couche 2 + 3 -- Masque (.dhsf)

Via `manipulating-dhsf-screens/scripts/dhsf_add_fk.py` (FK-03) :
- Enrichit le bloc `[champ]` dont `donnee=...,<champ>,...`
- Injecte `[param_saisie] table_associee=oui`, `[touches] f8=<zoom>`, `[traitements] diva_apres`, `[boutons] "zoom"`
- Ajoute la procedure callback `Champ_<CHAMP>_<id>_Ap` dans `[diva]` (compteur sequentiel global)

## Utilisation

### Reproduire le cas RETEX R-003

```
# Couche 1 : Module Check
py .claude/skills/binding-zoom-to-field/scripts/dhsp_add_fk.py \
    --path "gttmchkracechien.dhsp" \
    --src-table RACECHIEN \
    --fk RacPays:T013:9053

# Couche 2 + 3 : Masque
py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_add_fk.py \
    --path "gtezracechien_sql.dhsf" \
    --src-table RACECHIEN \
    --fk RacPays:T013:9053
```

### FK multiples sur une meme entite

```
py .claude/skills/binding-zoom-to-field/scripts/dhsp_add_fk.py \
    --path "gttmchkxyz.dhsp" \
    --src-table XYZ \
    --fk RacPays:T013:9053 \
    --fk RacDev:T007:9047 \
    --fk RacDepo:T017:9057

py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_add_fk.py \
    --path "gtezxyz_sql.dhsf" \
    --src-table XYZ \
    --fk RacPays:T013:9053 --fk RacDev:T007:9047 --fk RacDepo:T017:9057
```

## Workflow recommande

1. **Verifier l'entite existe** : le `.dhsp` et le `.dhsf` sont presents sur disque
2. **Backup** (manuel ou via copie de travail) avant modification in-place
3. **Appeler `dhsp_add_fk.py`** sur le Module Check
4. **Appeler `dhsf_add_fk.py`** sur le masque
5. **Verifier coherence** :
   - Lint : `linting-diva-code/scripts/lint_diva.py` -- doit retourner 0 warning Z15
   - Compilation : `compiling-diva-projects` -- doit etre 0 erreur
6. **Tester dans l'ERP** : via `testing-erp` (Playwright), verifier que le zoom
   s'ouvre bien depuis le champ avec F8

## Limitations V1

- **Cardinalite 1:1 uniquement**. Composee (N champs -> 1 cible), filtre borne (d/f),
  polymorphique (discriminant dynamique) = chantiers futurs.
- **Pas de validation d'existence du champ dans le dictionnaire**. Si le champ
  n'existe pas dans `.dhsd`, la compilation echouera (erreur de symbole
  explicite, facile a diagnostiquer).
- **Idempotence basique**. Re-executer le script ne duplique pas les imports
  Module ni les procedures Check_*_Field_* (detection par nom). Mais le
  masque `.dhsf` : seules les procedures `[diva]` sont idempotentes (compteur
  sequentiel global), les enrichissements `[champ]` sont append-only et
  peuvent dupliquer des attributs si appeles plusieurs fois sur un meme champ
  (warnings visibles mais verification manuelle recommandee).

## Tests

### Scenario minimal (cas RETEX R-003)

Prerequis : une copie de `gttmchkracechien.dhsp` + `gtezracechien_sql.dhsf` dans
un repertoire de test.

Attendu apres appel :
- `.dhsp` : `Module "Gttmchkt013.dhop"` present, `Check_RACECHIEN_Field_RacPays` et `_Lib` en fin de fichier
- `.dhsf` : `[champ] donnee=...,RacPays,...` enrichi avec `f8=9053`, procedure `Champ_RacPays_<id>_Ap` dans `[diva]`
- Lint : 0 erreur, 0 warning Z15
- Compilation : 0 erreur

## References

- [reference/fk-pattern.md](reference/fk-pattern.md) : pattern 3 couches + cardinalites + mapping cible/module + taxonomie suffixes
- [generating-objet-metier](../generating-objet-metier/SKILL.md) : version creation (FK-02)
- [manipulating-dhsf-screens](../manipulating-dhsf-screens/SKILL.md) : script `dhsf_add_fk.py` partage (FK-03)
- [linting-diva-code](../linting-diva-code/SKILL.md) : regles Z14/Z15 (FK-06) pour verifier l'absence d'orphelins
