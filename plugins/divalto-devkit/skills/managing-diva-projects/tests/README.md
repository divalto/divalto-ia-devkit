# Tests du skill managing-diva-projects

Suites executables, **sans poste Divalto** : chaque cas fabrique un `.dhpt` ou `.dhps`
minimal en ISO-8859-1 + CRLF dans un repertoire temporaire, lance
`scripts/validate_project.py` dessus et compare le verdict et les codes de regles.

```
py .claude/skills/managing-diva-projects/tests/run_all.py
```

A lancer apres **toute** modification de `scripts/validate_project.py`.

---

## test_entete_et_conventions.py

### 1. PROJ04 / PROJ05 etaient structurellement inatteignables

Le type du fichier etait deduit de `detect_file_type(lines)`, c'est-a-dire **de
l'en-tete que ces deux regles sont censees valider**. `validate_dhps` (qui porte PROJ04)
n'etait donc appele que si l'en-tete etait **deja** un en-tete de `.dhps`, ou son test
`header.startswith("xwin-projet")` ne peut jamais etre vrai. Idem pour PROJ05 dans
`validate_dhpt`. Un melange en-tete/extension etait **invisible par construction**.

Mesure du comportement d'avant : un `.dhps` portant `xwin-projet` repondait
`valid: true`, se declarait `type: dhpt`, et sortait en **exit 0**. Un fichier `.txt`
etait valide de la meme facon, sur la seule foi de son en-tete.

Le type vient desormais de l'**extension** (`type_attendu()`), et `detect_file_type()`
ne sert plus qu'a savoir ce que l'en-tete **annonce**, pour que PROJ04/PROJ05 puissent
comparer les deux. La sortie JSON porte les deux champs : `type` (extension) et
`type_annonce_par_entete`.

| Groupe de cas | Ce qui est verifie |
|---------------|--------------------|
| **Matrice en-tete x extension** | Les 8 croisements. **UN seul code par extension** : `PROJ04` pour le `.dhps`, `PROJ05` pour le `.dhpt` -- les deux formes de surcharge (`xwin-s-projet`, `xwin-s-sprojet`) sont acceptees a leur place et refusees ailleurs. |
| **Verdict et sortie** | Un melange n'est plus `valid: true` ; `type` suit l'extension ; le type annonce par l'en-tete est rapporte a part ; exit 1 quand le fichier est invalide. |
| **En-tete non reconnu** | Devient un constat **structure** dans le JSON (PROJ04/PROJ05 selon l'extension) au lieu d'un `exit 1` sans aucune sortie exploitable. |
| **Extension non geree** | `exit 2` (erreur interne) au lieu d'un verdict silencieux sur un fichier qui n'est ni `.dhpt` ni `.dhps`. |

### 2. PROJ09 etait une `error` « obligatoire »

`zdiva.dhsp` dans `[includes]` est une **convention**, pas une obligation : le standard
X.13 livre ne le fait **jamais** (0 / 2304 `.dhps`) alors qu'un specifique partenaire
mesure le fait a 80-98 %. En `error` et active par defaut, la regle rendait
`valid: false` sur **100 % des sous-projets du standard** -- que l'on valide couramment
comme **modele de reference**. Mesure avant/apres sur 2735 fichiers projet reels :
**2349 constats -> 0**, et ils reviennent a l'identique sous `--with-rules PROJ09`.

| Cas | Ce qui est verifie |
|-----|--------------------|
| Par defaut | PROJ09 muette, et le fichier reste **valide** (ce n'est pas un defaut) |
| `--with-rules PROJ09` | L'absence est signalee, **sans** rendre le fichier invalide (severite `info`) |
| `--with-rules PROJ09` + `zdiva.dhsp` present | Muet : la detection legitime est preservee |
| `--with-rules` **AJOUTE** | PROJ04 remonte toujours en meme temps que PROJ09 -- l'option n'est pas un filtre |
| Code deja actif passe a `--with-rules` | Ignore avec un avertissement, sans plantage |

> **`--with-rules` (ici) n'est pas `--rules` (linting-diva-code).** Le `--rules` du
> linter **filtre** : il n'execute que les regles nommees. Le `--with-rules` de ce
> validateur **ajoute** au jeu normal -- un validateur structurel prive de ses controles
> de structure n'aurait aucun sens. Deux sens differents, deux noms differents : une
> fausse symetrie sur le meme nom d'option serait pire que deux noms distincts.

---

## Verification de discrimination

Jouee contre la version anterieure de `validate_project.py`, la suite tombe sur
**16 cas** sur 22 -- les 6 autres sont les gardes de non-regression (les croisements
corrects, qui doivent rester muets dans les deux versions).

---

## Convention

- Les fichiers de test sont ecrits en **ISO-8859-1 + CRLF** (comme de vrais fichiers
  projet), jamais en UTF-8 : le validateur controle l'encodage (PROJ01/PROJ02), un fichier de
  test mal encode ferait remonter de faux constats.
- Les cas lisent la sortie **JSON** de `validate_project.py` et son **code de sortie**
  (0 valide / 1 invalide / 2 erreur interne) -- tester le verdict sans le code de sortie
  laisserait passer une regression sur l'un des deux.
- Aucun chemin absolu : tout se passe dans un `tempfile.mkdtemp()` nettoye en `finally`.
