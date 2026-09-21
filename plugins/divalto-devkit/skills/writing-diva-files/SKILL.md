---
name: writing-diva-files
description: >
  Ecrit et modifie les fichiers texte Divalto (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps)
  en garantissant l'encodage ISO-8859-1 et les fins de ligne CRLF. Detecte et corrige les
  fichiers corrompus (UTF-8, LF). A utiliser des qu'un fichier Divalto doit etre cree ou modifie.
---

# Writing DIVA Files

## Contenu

- Regle fondamentale
- Workflow : ecrire un fichier Divalto
- Workflow : modifier un fichier existant (patch chirurgical)
- Workflow : verifier un fichier existant
- Workflow : corriger un fichier corrompu
- Scripts disponibles
- References

---

## Regle fondamentale

**TOUS les fichiers texte Divalto sont en ISO-8859-1 + CRLF.** Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF — incompatible. Toujours utiliser les scripts de ce skill pour ecrire ou verifier — **jamais l'outil Edit/Write, ni un script Python maison** (`bytes.replace`, patch ad-hoc) : le hook `protect_encoding` bloque Edit/Write, mais **pas** les scripts du skill (voie sanctionnée, non bloquée).

Deux gestes distincts : **créer / remplacer en entier** → `write_file.py` ; **modifier en place** (préserver le reste) → `patch_file.py`. Pièges Windows fréquents (pipe PowerShell → BOM, Python mode texte → LF à la lecture, pas de CRLF final → **Erreur 135**) : voir [reference/safe-methods.md](reference/safe-methods.md).

---

## Workflow : ecrire un fichier Divalto

1. Preparer le contenu en memoire (texte brut)
2. Ecrire avec le script :
   ```
   py .claude/skills/writing-diva-files/scripts/write_file.py --path "chemin/fichier.dhsp" --content "contenu"
   ```
   Ou depuis stdin pour du contenu long :
   ```
   echo "contenu" | py .claude/skills/writing-diva-files/scripts/write_file.py --path "chemin/fichier.dhsp" --stdin
   ```
   **Sous PowerShell**, préférer `--content-file` (contenu écrit dans un fichier UTF-8 temporaire) : évite le quoting PowerShell (guillemets absorbés), le décodage console (accents corrompus) **et** le saut de ligne final que `Get-Content -Raw` ajoute sur `--stdin`. `patch_file.py` accepte aussi `--content-file`. Un BOM de tête éventuel est strippé (`utf-8-sig`) sur `--content-file` comme sur `--stdin` ; un caractère non encodable en ISO-8859-1 (tiret cadratin, guillemet typographique…) fait **échouer proprement sans jamais tronquer la cible**.
3. **Verifier immediatement** :
   ```
   py .claude/skills/writing-diva-files/scripts/verify_encoding.py --path "chemin/fichier.dhsp"
   ```
4. Si echec : examiner les issues, corriger, re-verifier

---

## Workflow : modifier un fichier existant (patch chirurgical)

Pour **modifier** un fichier existant sans le réécrire en entier (préserver tout le reste) :

```
py .claude/skills/writing-diva-files/scripts/patch_file.py \
    --path "chemin/fichier.dhsp" --op insert --anchor "Procedure Init" --position after --content "  ; init"
```

Opérations (`--op`) : `insert` (par `--anchor` ou `--line N` + `--position before|after`), `prepend`, `append`, `replace` (`--anchor`, ou `--line N` / `--line-range A:B`), `delete` (idem). **En `replace`/`delete`, le ciblage par numéro (`--line`/`--line-range`) exige `--expect-content` / `--expect-content-file`** (le contenu actuel attendu aux lignes visées) : si le fichier a dérivé depuis la lecture (ma propre édition antérieure, ou le collaborateur dans xwin en parallèle), **refus, rien écrit** — garde-fou anti-numéro-périmé (#303). L'ancre reste la voie sûre par défaut (elle se vérifie par son texte). **Hors de cette portée** — `insert`, ou un ciblage par `--anchor` — l'option n'aurait aucun effet : `patch_file` la **refuse** explicitement plutôt que de l'ignorer en silence (une option acceptée mais inopérante fait croire à une protection inexistante). `insert` n'est volontairement pas gardé : son risque est la position, pas le contenu écrasé.

Garde-fous : `--expect N` (l'ancre doit matcher exactement N lignes — défaut 1 — sinon **refus, rien écrit**), `--regex`, `--dry-run` (aperçu), `.bak` auto (caché sous Windows). CRLF final garanti + re-vérification automatique.

> **Fichiers structurés** : `patch_file.py` **refuse** `.dhsd` / `.dhsf` / `.dhsi` (positions/offsets sensibles) → passer par `managing-diva-dictionaries` (.dhsd) ou `manipulating-dhsf-screens` (.dhsf/.dhsi). Override explicite : `--force-structured`.

---

## Workflow : verifier un fichier existant

```
py .claude/skills/writing-diva-files/scripts/verify_encoding.py --path "chemin/fichier.dhsp"
```

Sortie JSON : `{path, valid, encoding, line_endings, issues[]}`

- `valid: true` → fichier conforme
- `valid: false` → voir `issues[]` pour les problemes detectes

---

## Workflow : corriger un fichier corrompu

Si verify_encoding detecte des problemes (UTF-8, LF, mixte) :

```
py .claude/skills/writing-diva-files/scripts/convert_file.py --path "chemin/fichier.dhsp"
```

Le script :
1. Detecte l'encodage actuel (UTF-8 ou ISO-8859-1)
2. Convertit en ISO-8859-1 si necessaire
3. Convertit les fins de ligne en CRLF
4. Cree un backup `.bak` avant modification
5. Verifie le resultat

Sortie JSON : `{path, backup, original_encoding, original_line_endings, converted, verified}`

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/write_file.py` | Crée / réécrit un fichier en ISO-8859-1+CRLF (`.bak` auto + avertissement si écrasement) | `--path` + `--content` / `--content-file` / `--stdin` [+ `--no-backup`] | `{path, encoding, line_endings, bytes, backup, warning}` |
| `scripts/patch_file.py` | **Modifie** un fichier existant (chirurgical : insert/prepend/append/replace/delete), `.bak` caché, refuse les fichiers structurés | `--path --op ...` [`--anchor`/`--line`/`--line-range` `--content`/`--content-file`/`--stdin` `--expect` `--expect-content`(`-file`) `--dry-run`] | `{path, op, matched, lines_before, lines_after, changed, backup, verified}` |
| `scripts/verify_encoding.py` | Verifie encodage et fins de ligne (dont BOM, CRLF final manquant et ligne physique > 251 caractères que XWin refuse d'ouvrir) | `--path` | `{path, valid, encoding, line_endings, issues[]}` |
| `scripts/convert_file.py` | Convertit vers ISO-8859-1+CRLF (mojibake **franc**). Sur un mojibake **mêlé** à du Latin-1 valide : ne convertit pas, `verified:false` + `hint` (réparation chirurgicale requise) | `--path` [+ `--no-backup`] | `{path, backup, converted, verified, issues[], hint}` |
| `scripts/add_zoom_constant.py` | Ajoute une constante de zoom dans a5tczoom.dhsp (`.bak` avant écriture, CRLF final garanti) | `--file` `--instance` `--num` `--comment` [+ `--dry-run`] | `{success, constant_name, constant_line, line_number, already_exists, backup}` |

Tous les scripts : `py .claude/skills/writing-diva-files/scripts/<script>.py --help`

**Tests** — les garde-fous de ce skill (anti-perte, anti-corruption) ont une suite
exécutable, sans poste Divalto :

```
py .claude/skills/writing-diva-files/tests/run_all.py
```

À lancer après toute modification d'un script. Détail : [tests/README.md](tests/README.md).

> **`verified` = `valid`.** Le champ `verified` de `write_file` / `patch_file` / `convert_file`
> applique **les mêmes** contrôles que le `valid` de `verify_encoding.py` (ISO-8859-1, CRLF,
> CRLF final, BOM, mojibake résiduel, ligne > 251). Il ne peut plus certifier un fichier que
> le vérificateur du skill déclare corrompu — et le **code de sortie suit le verdict**.

> **Le contenu à écrire est validé AVANT de toucher la cible.** Un caractère hors Latin-1 ou
> une séquence de mojibake dans le contenu injecté ⇒ **refus, fichier intact** (jamais une
> cible tronquée à 0 octet). Et si le `.bak` ne peut pas être créé, `write_file` et
> `patch_file` **refusent d'écrire** plutôt que d'écraser sans filet — sauf `--no-backup`,
> qui assume le risque explicitement.

---

## Workflow : ajouter une constante de zoom

Apres avoir enregistre un zoom dans A5F.dhfi (via writing-isam-files), declarer la constante :

```
py .claude/skills/writing-diva-files/scripts/add_zoom_constant.py \
    --file "{CHEMIN_SOURCE}/a5tczoom.dhsp" \
    --instance "MaEntite" --num "9400" --comment "Ma nouvelle entite"
```

Le script insere la ligne `Const C_ZOOM_MaEntite_9400 = 9400 ;Ma nouvelle entite` avant le bloc de regles en fin de fichier. Verifie les doublons (nom et numero). Supporte `--dry-run`.

---

## References

- **Regles d'encodage par type** : Voir [reference/encoding-rules.md](reference/encoding-rules.md)
- **Methodes de modification safe** : Voir [reference/safe-methods.md](reference/safe-methods.md)
