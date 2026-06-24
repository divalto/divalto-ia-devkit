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

**TOUS les fichiers texte Divalto sont en ISO-8859-1 + CRLF.** Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF — incompatible. Toujours utiliser les scripts de ce skill pour ecrire ou verifier.

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

Opérations (`--op`) : `insert` (par `--anchor` ou `--line N` + `--position before|after`), `prepend`, `append`, `replace` (`--anchor` ou `--line-range A:B`), `delete`.

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
| `scripts/write_file.py` | Crée / réécrit un fichier en ISO-8859-1+CRLF (`.bak` auto + avertissement si écrasement) | `--path` + `--content` ou `--stdin` [+ `--no-backup`] | `{path, encoding, line_endings, bytes, backup, warning}` |
| `scripts/patch_file.py` | **Modifie** un fichier existant (chirurgical : insert/prepend/append/replace/delete), `.bak` caché, refuse les fichiers structurés | `--path --op ...` [`--anchor`/`--line`/`--line-range` `--expect` `--dry-run`] | `{path, op, matched, lines_before, lines_after, changed, backup, verified}` |
| `scripts/verify_encoding.py` | Verifie encodage et fins de ligne (dont BOM et CRLF final manquant) | `--path` | `{path, valid, encoding, line_endings, issues[]}` |
| `scripts/convert_file.py` | Convertit vers ISO-8859-1+CRLF | `--path` [+ `--no-backup`] | `{path, backup, converted, verified}` |
| `scripts/add_zoom_constant.py` | Ajoute une constante de zoom dans a5tczoom.dhsp | `--file` `--instance` `--num` `--comment` [+ `--dry-run`] | `{success, constant_name, constant_line, line_number, already_exists}` |

Tous les scripts : `py .claude/skills/writing-diva-files/scripts/<script>.py --help`

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
