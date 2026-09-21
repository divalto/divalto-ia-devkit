# Methodes de modification safe pour fichiers Divalto

## Principe

Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF ; un pipe PowerShell ajoute un BOM ; Python en mode texte convertit les CRLF en LF a la lecture. Les fichiers Divalto, eux, sont en **ISO-8859-1 + CRLF**. Il faut donc TOUJOURS passer par les scripts de ce skill.

---

## La voie sanctionnee -- jamais de script maison

Le hook `protect_encoding.py` bloque Edit/Write sur les fichiers DIVA, **mais il ne bloque PAS les scripts de ce skill**. Le reflexe « le hook m'empeche d'ecrire -> je fais mon propre script Python » est donc FAUX : `patch_file.py` / `write_file.py` sont la voie sanctionnee, non bloquee.

- **Jamais de script ad-hoc** (`bytes.replace`, patch inline, `.new` + `os.replace`) pour editer du DIVA. `patch_file` re-implemente deja, teste, tout ce qu'un script maison refait a la main : ISO-8859-1, CRLF final, backup, controle U+FFFD/verify, ancre, `--expect-content`. Le re-ecrire chaque session = gaspillage + bugs.
- **Jamais Edit/Write**, meme pour une seule ligne ASCII : Edit re-ecrit le fichier ENTIER en UTF-8 -> tous les accents existants ailleurs (commentaires, libelles) passent en U+FFFD.
- **Inserer N lignes a la ligne X** = `patch_file --op insert --line X --position after` (ou `--anchor`). Pas besoin d'un `insert_lines.py` maison.

---

## Les gestes et les scripts

| Geste | Script | Note |
|-------|--------|------|
| **CREER** un fichier (ou le remplacer en entier) | `write_file.py` | si le fichier existe deja : `.bak` auto (cache) + avertissement |
| **MODIFIER** un fichier existant (preserver le reste) | `patch_file.py` | edition chirurgicale : `insert` / `prepend` / `append` / `replace` / `delete` ; `.bak` auto |
| **VERIFIER** apres ecriture | `verify_encoding.py` | encodage + fins de ligne (dont BOM et CRLF final manquant) |
| **CORRIGER** un fichier corrompu (UTF-8 / LF / BOM / pas de CRLF final) | `convert_file.py` | `.bak` auto |

> **Fichiers structures** (`.dhsd`, `.dhsf`, `.dhsi`) : NE PAS les editer ligne-a-ligne avec `patch_file.py` (positions/offsets sensibles) — utiliser les skills dedies : `managing-diva-dictionaries` (.dhsd) et `manipulating-dhsf-screens` (.dhsf, .dhsi masques d'impression). `patch_file.py` les refuse par defaut.

---

## `patch_file.py` — modification chirurgicale (methode recommandee)

```
# Inserer apres une ligne reperee par une ancre
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsp --op insert --anchor "Procedure Init" --position after --content "  ; init"

# Inserer en tete de fichier
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsp --op prepend --content ";>xwinobj      programme"

# Remplacer la ligne contenant une ancre
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsq --op replace --anchor "Const C_MAX" --content "Const C_MAX = 999"

# Supprimer une ligne unique par numero -- --expect-content OBLIGATOIRE (contenu actuel attendu)
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsp --op delete --line 18 --expect-content "  ; ligne a supprimer"

# Supprimer/remplacer une plage (1-based, inclusif) -- --expect-content = le bloc ENTIER attendu
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsp --op delete --line-range 10:12 --expect-content-file bloc_attendu.txt
```

Garde-fous : `--expect N` (l'ancre doit matcher exactement N lignes — defaut 1 — sinon refus, rien ecrit), `--expect-content` / `--expect-content-file` (**OBLIGATOIRE** pour le ciblage par numero `--line`/`--line-range` en replace/delete : le contenu actuel attendu aux lignes visees — s'il a derive depuis la lecture, refus, rien ecrit ; cf. #303), `--regex` (ancre = regex), `--dry-run` (apercu sans ecrire, verifie aussi `--expect-content`), `.bak` auto (`--no-backup` pour s'en passer). CRLF final garanti, re-verification automatique apres ecriture.

> **Ancre > numero.** Le ciblage par numero de ligne est fragile : un numero calcule sur une lecture anterieure peut etre perime (le fichier a change entre-temps -- mon edition precedente, ou le collaborateur dans xwin) et viser la MAUVAISE ligne. `--expect-content` transforme ce risque silencieux en refus explicite, mais l'**ancre** (`--anchor`) reste la voie a preferer : elle se repere par le contenu, pas par une position.

---

## Pieges Windows (causes recurrentes de corruption)

| Piege | Symptome | Parade |
|-------|----------|--------|
| **Edit / Write** de Claude Code | re-ecrit le fichier **entier** en UTF-8+LF -> corrompt tous les accents (meme pour 1 ligne ASCII) | ne jamais les utiliser sur du DIVA ; le hook `protect_encoding.py` les bloque -- mais **PAS** les scripts du skill (= la voie sanctionnee) |
| **Pipe PowerShell** (`Get-Content ... \| py`) | un **BOM** se colle en tete du contenu | preferer **`--content-file`** (lu en utf-8-sig, BOM strippe) ; sinon `verify`/`convert` detectent/retirent le BOM |
| **Python en mode texte** (`open(p)` sans `'b'`) | CRLF convertis en LF a la **lecture** -> remplacements silencieusement rates | toujours lire/ecrire en **binaire** (les scripts du skill le font) |
| **Pas de CRLF final** | **Erreur 135** a la compilation | `write_file`/`patch_file` garantissent le CRLF final ; `convert_file` le rajoute ; `verify` le signale |
| **`.ps1` genere en UTF-8** | PowerShell 5.1 le lit en **ANSI** : un chemin accentue en dur devient introuvable | voir ci-dessous |

---

## Le piege des `.ps1` : ecrits en UTF-8, lus en ANSI

**PowerShell 5.1** -- la version installee par defaut sous Windows -- lit un `.ps1` **sans
BOM** en **ANSI/CP1252**, pas en UTF-8. Or un `.ps1` genere depuis une session Claude est en
UTF-8 sans BOM.

Consequence : un **chemin accentue ecrit en dur** dans le script est corrompu a l'execution.

```powershell
# ecrit en UTF-8 :          $outPath = 'C:\Répertoire accentué\sortie.txt'
# lu par PowerShell 5.1 :   $outPath = 'C:\RÃ©pertoire accentuÃ©\sortie.txt'
```

Le repertoire devient introuvable. **Le reste du script s'execute normalement** : seule
l'operation qui touche au chemin echoue, ce qui rend le diagnostic trompeur -- on cherche
l'erreur dans la logique alors qu'elle est dans l'encodage.

### Les deux parades

| Parade | Quand |
|---|---|
| **Passer le chemin en parametre** depuis l'appelant (`param([string]$OutPath)`) | par defaut : aucun accent ne subsiste dans le fichier |
| **Ecrire le `.ps1` en ISO-8859-1** | quand le litteral accentue est indispensable dans le script |

> **Ce piege n'est pas propre aux fichiers DIVA ni au devkit** : c'est une propriete de
> PowerShell 5.1. Il vaut pour **tout** `.ps1` genere depuis une session -- y compris ceux
> qui n'ont rien a voir avec Divalto. Le retour terrain qui l'a signale generait un script
> SQL, **sans aucun skill charge**.

### A ne pas confondre avec le piege du profil xwin7

`compiling-diva-projects` documente une regle **voisine mais de cause distincte** : le `.ps1`
lance par `xwin7` doit etre en ISO-8859-1 parce que **xwin7 compare le nom de profil en
ISO-8859-1**. La c'est l'**argument transmis** qui casse ; ici c'est **le script relu par
PowerShell** qui casse, meme sans xwin7. Les deux causes sont differentes, le remede se
recoupe -- corriger l'une ne dispense pas de verifier l'autre.

---

## Il n'y a pas de voie de secours

Aucune recette `head`/`tail`/`sed`/`tr` n'est sanctionnee, et cette page n'en donne plus :
elle contredisait la regle « jamais de script maison » ci-dessous, et elle offrait
precisement l'echappatoire qui a produit les corruptions a l'origine de ce skill.

Si un script du skill semble inutilisable, le reflexe n'est **pas** de le contourner :

| Symptome | Voie sanctionnee |
|---|---|
| Le hook bloque mon edition | c'est **Edit/Write** qui est bloque, **pas** les scripts du skill -- les invoquer |
| Mon contenu contient des guillemets / des accents | `--content-file <fichier UTF-8>` (evite le quoting **et** le decodage console) |
| Je dois inserer a un endroit precis | `patch_file.py --op insert --anchor "..."` (ou `--line N --position after`) |
| Je dois remplacer plusieurs points | plusieurs appels `patch_file.py` par **ancre unique**, pas un script qui fait tout |
| Le fichier est structure (`.dhsd`/`.dhsf`/`.dhsi`) | passer par le skill dedie (le refus de `patch_file` nomme lequel) |
| Le fichier est corrompu | `verify_encoding.py` pour le diagnostic, `convert_file.py` pour un mojibake franc |

---

## Ce qu'il ne faut JAMAIS faire

- Edit/Write sur `.dhsp`, `.dhsq`, `.dhsd`, `.dhsf`, `.dhsi`, `.dhpt`, `.dhps` (accents + CRLF)
- **Ecrire un script Python ad-hoc** (`bytes.replace`, `.new` + `os.replace`) pour editer du DIVA -- `patch_file`/`write_file` le font deja, avec garde-fous (le hook bloque Edit/Write, PAS ces scripts)
- Pipe PowerShell direct (BOM) ; ouvrir un fichier ISO-8859-1 comme UTF-8 ; lire/ecrire en mode texte Python
- Reecrire un fichier en entier (`write_file`) quand une modif ciblee (`patch_file`) suffit
- **Restaurer/ecraser un fichier a l'aveugle** sans sauver l'etat courant d'abord : le collaborateur a pu editer en parallele dans xwin. Et le `.bak` est **glissant** -- chaque ecriture l'ecrase, donc il ne contient que l'etat d'avant la **DERNIERE** edition, pas d'avant la premiere : restaurer apres plusieurs patches ne revient pas au point de depart
- **Reutiliser des numeros de ligne** d'une lecture anterieure sans les relire juste avant un `--line`/`--line-range`
- Oublier de verifier apres modification
