# Bibliotheque de squelettes RSQL (G-022)

Squelettes pre-configures reproduisant les 8 super-signatures X.12 identifiees dans
`corpus-patterns.md` (section 3). Ces 8 signatures concentrent >900 RSQL du corpus X.12
et sont confirmees en X.13 (section 7ter).

## Format

Chaque squelette est un JSON contenant `joined_tables` et `additional_cases` pre-remplis,
avec des conditions de jointure canoniques ERP. Le token `{MAIN}` est un placeholder pour
le nom de la table principale (TableSQL), substitue au moment du merge.

## Utilisation

```bash
py generate_rsql.py \
    --params --domaine Reglements --entite DtrFa --table RCMDTRFA \
    --champ-cle NumDtr --description "Detail reglement fournisseur" \
    --skeleton zoom-reglement-19 \
    --output output/rcmrsdtrfa.dhsq
```

Le flag `--skeleton <nom>` charge le skeleton, remplace `{MAIN}` par la `table_sql`
principale, puis fusionne avec les tokens calcules par `compute_names()`.

## Squelettes disponibles (8/8 super-patterns X.12)

| Fichier | Pattern | Jointures | Cible X.12 | RSQL X.12 |
|---------|---------|-----------|------------|-----------|
| `zoom-piece-53.skel.json` | Zoom piece exhaustif (ART, CLI, FOU, ENT, DEPO, VRP, DEV, T007) | 8 | 53 tables | 168 |
| `zoom-piece-47.skel.json` | Zoom piece avec parametrage etendu (CTRL, MOUV, ART, CLI, FOU, TIA, T006, T007) | 8 | 47 tables | 91 |
| `zoom-piece-46.skel.json` | Zoom piece alternatif (ART, CLI, FOU, ENT, DEV, TVA, T007) | 7 | 46 tables | 136 |
| `zoom-mouvement-30.skel.json` | Zoom mouvement stock (ART, DEPO, LOTDET, BF, T006, T007, U) | 7 | 30 tables | 108 |
| `zoom-projet-affaire-26.skel.json` | Zoom projet affaire (GAPROJ, GATCRIT, GATETAP, PRJAP, CLI, T006, T007) | 7 | 26 tables | 83 |
| `zoom-reglement-19.skel.json` | Zoom reglement (CLI, FOU, TIA, C3, C8) | 5 | 19 tables | 146 |
| `zoom-relation-client-19.skel.json` | Zoom relation client CRM (CLI, TIA, VRP, MUSER, ACTIONREL, T006, T007) | 7 | 19 tables | 93 |
| `zoom-evenement-9.skel.json` | Zoom evenement (GRTEVT, CA, PAR, T007) | 4 | 9 tables | 90 |

**Total RSQL X.12 couverts par ces patterns** : > 900 (8 super-signatures identifiees dans `corpus-patterns.md` section 3).

**Note sur "cible vs jointures"** : chaque squelette contient le noyau semantique des jointures canoniques (5-8), pas la liste exhaustive de la cible (9-53). Le pattern complet X.13 inclut souvent des lookups repetitifs T006/T007/T017/T020 ou des tables de specialisation par entite -- ajouter localement si necessaire.

## Limites connues

- Les squelettes pilotes contiennent un **sous-ensemble representatif** des jointures, pas
  la liste exhaustive. Pour reproduire un RSQL X.13 complet a 53 tables, extraire depuis
  le fichier source correspondant (cf. section `_source_x13` de chaque skeleton).
- Les conditions de jointure utilisent les noms de colonnes canoniques ERP (CliCod, Ticod,
  etc.). Si l'entite principale utilise des noms differents, editer le skeleton localement
  avant appel.
- Le `{MAIN}` placeholder est substitue au moment du merge, mais **seulement** dans les
  champs `join_condition` des jointures. Pour d'autres usages, editer les tokens manuellement.

## Ajouter un squelette

1. Identifier un RSQL X.13 representatif du pattern (cf. `corpus-patterns.md`).
2. Extraire les sections `<FROM>` et `<WHERE>` du fichier source.
3. Traduire chaque table jointe en entree `joined_tables` avec le bon `join_type`.
4. Remplacer la table principale par `{MAIN}` dans les conditions.
5. Sauvegarder en JSON dans ce repertoire avec le nom `<pattern>-<nbtables>.skel.json`.
6. Tester avec `py generate_rsql.py --skeleton <nom> --params ...`.
