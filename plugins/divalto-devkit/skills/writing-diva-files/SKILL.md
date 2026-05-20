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
- Workflow : verifier un fichier existant
- Workflow : corriger un fichier corrompu
- Scripts disponibles
- References

---

## Regle fondamentale

**TOUS les fichiers texte Divalto sont en ISO-8859-1 + CRLF.** Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF — incompatible. Toujours utiliser les scripts de ce skill pour ecrire ou verifier.

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
| `scripts/write_file.py` | Ecrit du contenu en ISO-8859-1+CRLF | `--path` + `--content` ou `--stdin` | `{path, encoding, line_endings, bytes}` |
| `scripts/verify_encoding.py` | Verifie encodage et fins de ligne | `--path` | `{path, valid, encoding, line_endings, issues[]}` |
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
