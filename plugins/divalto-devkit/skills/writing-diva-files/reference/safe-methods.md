# Methodes de modification safe pour fichiers Divalto

## Principe

Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF ; un pipe PowerShell ajoute un BOM ; Python en mode texte convertit les CRLF en LF a la lecture. Les fichiers Divalto, eux, sont en **ISO-8859-1 + CRLF**. Il faut donc TOUJOURS passer par les scripts de ce skill.

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

# Supprimer une plage de lignes (1-based, inclusif)
py .claude/skills/writing-diva-files/scripts/patch_file.py --path f.dhsp --op delete --line-range 10:12
```

Garde-fous : `--expect N` (l'ancre doit matcher exactement N lignes — defaut 1 — sinon refus, rien ecrit), `--regex` (ancre = regex), `--dry-run` (apercu sans ecrire), `.bak` auto (`--no-backup` pour s'en passer). CRLF final garanti, re-verification automatique apres ecriture.

---

## Pieges Windows (causes recurrentes de corruption)

| Piege | Symptome | Parade |
|-------|----------|--------|
| **Edit / Write** de Claude Code | fichier passe en UTF-8 + LF | ne jamais les utiliser sur du DIVA ; le hook `protect_encoding.py` les bloque |
| **Pipe PowerShell** (`echo ... ` redirige vers `py`) | un **BOM** se colle en tete du contenu | preferer `--content`, ou `--stdin` depuis un fichier UTF-8 sans BOM ; `verify`/`convert` detectent/retirent le BOM |
| **Python en mode texte** (`open(p)` sans `'b'`) | CRLF convertis en LF a la **lecture** -> remplacements silencieusement rates | toujours lire/ecrire en **binaire** (les scripts du skill le font) |
| **Pas de CRLF final** | **Erreur 135** a la compilation | `write_file`/`patch_file` garantissent le CRLF final ; `convert_file` le rajoute ; `verify` le signale |

---

## Fallback Bash (uniquement si les scripts sont indisponibles)

Inserer en preservant l'encodage :
```bash
cp f.dhpt .f.dhpt.bak
{ head -n L .f.dhpt.bak; printf 'contenu\r\n'; tail -n +$((L+1)) .f.dhpt.bak; } > f.dhpt
```
Remplacement simple : `tr -d '\r'` -> `sed` -> re-ajouter `\r` en fin de ligne. Toujours lancer `verify_encoding.py` apres.

---

## Ce qu'il ne faut JAMAIS faire

- Edit/Write sur `.dhsp`, `.dhsq`, `.dhsd`, `.dhsf`, `.dhsi`, `.dhpt`, `.dhps` (accents + CRLF)
- Pipe PowerShell direct (BOM) ; ouvrir un fichier ISO-8859-1 comme UTF-8 ; lire/ecrire en mode texte Python
- Reecrire un fichier en entier (`write_file`) quand une modif ciblee (`patch_file`) suffit
- Oublier de verifier apres modification
