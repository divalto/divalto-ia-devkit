# Methodes de modification safe pour fichiers Divalto

## Principe

Les outils Edit et Write de Claude Code ecrivent en UTF-8 + LF. Les fichiers Divalto sont en ISO-8859-1 + CRLF. Il faut donc soit utiliser les scripts du skill, soit passer par Bash avec les methodes ci-dessous.

---

## Methode recommandee : scripts du skill

Toujours preferer les scripts `write_file.py`, `verify_encoding.py`, `convert_file.py` qui gerent automatiquement l'encodage et les fins de ligne.

---

## Methode Bash : modification par insertion (head/tail)

Preserve l'encodage et les fins de ligne du fichier original. Ideal pour inserer des lignes dans un fichier existant.

```bash
cp fichier.dhpt fichier.dhpt.bak
{ head -n LIGNE fichier.dhpt.bak; printf 'contenu\r\n'; tail -n +$((LIGNE+1)) fichier.dhpt.bak; } > fichier.dhpt
rm fichier.dhpt.bak
```

---

## Methode Bash : modification par sed

Pour des remplacements simples dans un fichier existant. Convertir LF temporairement, modifier, reconvertir.

```bash
tr -d '\r' < fichier.dhsf > /tmp/fix.tmp
sed -i 's/ancien/nouveau/' /tmp/fix.tmp
sed 's/$/\r/' /tmp/fix.tmp > fichier.dhsf
rm /tmp/fix.tmp
```

---

## Methode Bash : conversion post-Edit/Write

Si un fichier a ete ecrit avec Edit/Write (UTF-8 + LF) et doit devenir ISO-8859-1 + CRLF :

```bash
# 1. Convertir encodage
iconv -f UTF-8 -t ISO-8859-1 fichier.dhsp > /tmp/conv.tmp

# 2. Convertir fins de ligne
sed 's/$/\r/' /tmp/conv.tmp > fichier.dhsp
rm /tmp/conv.tmp
```

---

## Resume par situation

| Situation | Methode |
|-----------|---------|
| Creer un nouveau fichier Divalto | `write_file.py` |
| Modifier un fichier existant (remplacement) | `write_file.py` ou sed (Bash) |
| Inserer des lignes dans un fichier existant | head/tail (Bash) |
| Corriger un fichier corrompu (UTF-8/LF) | `convert_file.py` |
| Verifier un fichier apres modification | `verify_encoding.py` |
| Fichier ASCII pur sans accents | Edit/Write possibles + `sed 's/$/\r/'` apres |

---

## Ce qu'il ne faut JAMAIS faire

- Utiliser Edit/Write sur .dhpt, .dhps, .dhsd, .dhsf (toujours des accents)
- Ouvrir un fichier ISO-8859-1 comme UTF-8 (les octets > 0x7F deviennent invalides)
- Melanger LF et CRLF dans un meme fichier
- Oublier de verifier apres modification
