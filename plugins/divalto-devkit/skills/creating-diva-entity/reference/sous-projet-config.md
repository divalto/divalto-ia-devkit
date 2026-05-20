# Sous-projet `.dhps` de l'entite -- Etape 13

> Fragment de reference pour l'etape 13 de `creating-diva-entity`. Voir le skill [`managing-diva-projects`](../../managing-diva-projects/SKILL.md) pour la manipulation generique .dhpt/.dhps.

## Creation

Creer `gt_zoom {entite}.dhps` **base sur le modele `gt_zoom article.dhps`** (`Achat-Vente/projet/gt_zoom article.dhps`).

## Structure obligatoire

```
[communs]
incl="gt_base"," "
incl="gt_dictionnaires"," "
incl="gt_recordsql"," "
[fichiers]
fic="{masque}.dhsf"," "
fic="{fichier_mchk}"," "
fic="{fichier_zoom}"," "
[includes]
fic="a5pcbaslic.dhsp"
fic="a5tcchk000.dhsp"
fic="a5tczoom.dhsp"
fic="a5tcficsql.dhsp"
fic="gtpc000.dhsp"
fic="gttc000.dhsp"
fic="gttcdav000.dhsp"
fic="gttcficsql.dhsp"
fic="zdiva.dhsp"
```

## Regles critiques

- Les `[communs]` `gt_base`, `gt_dictionnaires`, `gt_recordsql` sont **indispensables**. Sans eux, le compilateur ne trouve pas les modules framework (gtpmficsql.dhop, etc.).
- L'include `gttcficsql.dhsp` est necessaire pour que `Declaration_{NomVue}` soit disponible.

## Integration

Ajouter dans `divalto.dhpt` puis compiler en incremental ERP.

## Checkpoint CP7 -- Sous-projet

Presenter au collaborateur :
- Le fichier .dhps cree : nom, contenu des sections `[communs]`, `[fichiers]`, `[includes]`
- L'ajout dans `divalto.dhpt` (section `[sousprojets]`)
- Les dependances (`gt_base`, `gt_dictionnaires`, `gt_recordsql`) et pourquoi elles sont necessaires

Attendre validation avant la synchro SQL.
