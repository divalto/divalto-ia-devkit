# Quel fichier viser : overlay `*u` ou fichier propre ?

> Une ecriture custom ne doit **jamais** viser un fichier livre par Divalto : elle serait
> **ecrasee** a la prochaine montee de version ou au prochain patch ERP. Mais la bonne
> cible n'est pas la meme partout (#228 / #250).

Une ecriture custom ne doit **jamais** viser un fichier livre par Divalto : elle serait
**ecrasee** a la prochaine montee de version ou au prochain patch ERP. Mais la bonne cible
n'est pas la meme partout -- il y a **deux regles distinctes**, et les confondre donne un
mauvais conseil.

| Fichier standard | Cible d'une ecriture custom | Mecanisme |
|------------------|-----------------------------|-----------|
| `a5f.dhfi` (zooms, visibilite F7) | **`a5fu.dhfi`** | **overlay** : meme structure, entree prioritaire sur le standard, union des deux a la lecture |
| `g3f.dhfi` (choix de menu) | **`g3fu.dhfi`** | **overlay**, idem |
| tout autre fichier standard (ex. un `XXfdmc` de multichoix) | **le fichier PROPRE du partenaire** | **pas d'overlay** : on ne fusionne pas dans le standard, on gere son propre fichier |

L'overlay vit dans l'**arborescence specifique**, pas a cote du standard. Cas reel : un zoom
custom enregistre dans le `a5fu.dhfi` du partenaire, et non dans le `a5f.dhfi` du pack
standard.

`write_isam.py` **avertit** quand la cible porte le nom d'un fichier standard pour lequel un
overlay existe :

```
AVERTISSEMENT: CIBLE STANDARD : 'g3f.dhfi' est le fichier livre par Divalto. Une ecriture
custom doit viser son overlay 'g3fu.dhfi' dans l'arborescence SPECIFIQUE [...]
```

- emis **une seule fois par fichier**, meme sur un lot de 200 entrees ;
- emis aussi en **`--dry-run`** -- c'est precisement le moment ou l'on veut l'entendre ;
- repris dans `avertissements[]` de la sortie JSON ;
- **avertissement, pas refus** : ecrire dans le standard reste possible si c'est
  intentionnel.

> La liste des fichiers a overlay est **explicite et courte** (`a5f`, `g3f`). L'existence
> d'un overlay ne se deduit **pas** du nom d'un fichier : pour les autres fichiers
> standard, la regle est le fichier propre du partenaire.

