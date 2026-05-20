# Cleanup post-compilation [communs]

Étape conditionnelle de l'Etape 12bis du workflow `creating-diva-entity`. À exécuter uniquement si un workaround `[communs]` a été appliqué à l'Etape 13 (sous-projet).

## Contexte

Si l'Etape 13 (sous-projet) a déjà été réalisée avec push temporaire de
`gtfdd.dhsd` / `gtpmficsql.dhsp` en `[fichiers]` (workaround pour recompiler
les communs via `-sousproject`, cf. `compiling-diva-projects` piège [communs]),
ces entrées doivent être nettoyées **après** confirmation de la réussite de la
compilation.

## Commande

```
py .claude/skills/managing-diva-projects/scripts/cleanup_communs_from_subproject.py \
    --path "{REPERTOIRE_TRAVAIL}/{nom_sous_projet}.dhps" \
    --remove gtfdd.dhsd --remove gtpmficsql.dhsp
```

## Comportement du script

- Sauvegarde le .dhps en .bak
- Retire les lignes `fic="<X>"` ciblées de la section `[fichiers]`
- Réécrit en ISO-8859-1 + CRLF
- Retourne `{removed[], kept[], backup}` en JSON

## Pré-requis

La compilation CP6 doit être OK. Si elle est en échec, garder le workaround pour la prochaine itération et reporter le cleanup.

## Checkpoint CP6bis -- Cleanup [communs] (conditionnel)

Saute cette étape si aucun workaround [communs] n'a été appliqué.

Sinon présenter au collaborateur :

- Liste des fichiers retirés du .dhps (vérifier que ce sont bien les workarounds temporaires, pas le code métier)
- Liste des fichiers conservés (devrait inclure les .dhsf/.dhsp métier)
- Chemin du backup .bak (rollback rapide si nécessaire)

Attendre validation avant la synchro SQL.
