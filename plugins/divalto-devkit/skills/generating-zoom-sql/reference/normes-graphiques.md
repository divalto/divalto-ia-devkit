# Normes graphiques -- Fragment reference generating-zoom-sql

> Source canonique : `docs/NORMES-GRAPHIQUES.md` (workspace). Ce fragment extrait la regle minimale de coherence dhsp/dhsf pour le generateur de zoom.

## Perimetre du skill

`generating-zoom-sql` genere le **fichier `.dhsp` du zoom** (27 procedures CRUD). Le **masque associe `.dhsf`** est genere par le skill `manipulating-dhsf-screens`. Les deux fichiers doivent etre coherents.

## Regle de coherence dhsp/dhsf : socle audit -> onglet Identifiants

Si le dictionnaire `.dhsd` de l'entite declare les champs audit standard (`Ce1`, `Note`, `Joint`, `UserCr`, `UserCrDh`, `UserMo`, `UserMoDh`), alors :

1. Le **masque .dhsf** (produit par `manipulating-dhsf-screens`) doit exposer ces champs dans l'onglet Identifiants.
2. L'**ordre canonique des groupboxes** dans l'onglet Identifiants :
   - **Codes enregistrements** en 1er (Y min) -- si `Ce1`/`Note`/`Joint` presents
   - **Creation** + **Derniere modification** en dernier (Y max) -- si socle UserCr/UserMo present
   - Extensions domaine acceptees apres.
3. Le **fichier `.dhsp` zoom** (ce skill) doit inclure les references de procedures aux vues liees (typiquement via les blocs `ZoomAvantInsert`, `ZoomAvantRewrite` qui doivent propager les valeurs audit via `GT_PreUpdate_recordSql(rs, majuser=true)` -- cf. anti-pattern M04).

## Verification post-generation

Apres generation du zoom .dhsp ET du masque .dhsf :

```
py .claude/skills/linting-diva-code/scripts/lint_diva.py --path <masque.dhsf> --rules E16,E17,E18,E19
```

Doit retourner :
- 0 erreur E16 (tous les champs audit presents)
- 0 warning E17 (ordre canonique respecte)
- 0 warning E19 (taille ecran autorisee : 25x120 ou 33x120 typique pour un zoom)

## Voir aussi (dans ce skill)

- `reference/zoom-anti-patterns.md` -- Z01-Z15 avec focus M04 (majuser=true)
- `reference/zoom-procedures.md` -- les 27 procedures cycle CRUD
- Pour les details de placement / styles / formules : voir le skill `manipulating-dhsf-screens` et son fragment `reference/normes-graphiques.md`.
