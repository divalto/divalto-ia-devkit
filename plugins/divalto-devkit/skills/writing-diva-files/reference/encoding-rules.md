# Regles d'encodage par type de fichier Divalto

## Regle universelle

**Tous les fichiers texte Divalto utilisent ISO-8859-1 (ANSI) + CRLF (`\r\n`).**

Verifie le 2026-04-08 sur les sources ERP X.13 standard.

---

## Par extension

| Extension | Encodage | Fins de ligne | Accents | Modifiable avec Edit/Write |
|-----------|----------|---------------|---------|---------------------------|
| `.dhsp` | ISO-8859-1 | CRLF | Oui (commentaires) | Non — utiliser scripts |
| `.dhsq` | ISO-8859-1 | CRLF | Oui (commentaires) | Non — utiliser scripts |
| `.dhsj` | ISO-8859-1 | CRLF | Oui (commentaires) | Non — utiliser scripts |
| `.dhpt` | ISO-8859-1 | CRLF | Oui (profil, libelles) | Non — utiliser scripts |
| `.dhps` | ISO-8859-1 | CRLF | Rarement | Non — utiliser scripts |
| `.dhsd` | ISO-8859-1 | CRLF | Oui (descriptions) | Non — utiliser scripts |
| `.dhsf` | ISO-8859-1 | CRLF | Oui (libelles ecran) | Non — utiliser scripts |
| `.dhsi` | ISO-8859-1 | CRLF | Oui (masque d'impression) | Non — fichier **structure**, skill `manipulating-dhsf-screens` |
| `.dhse` | ISO-8859-1 | CRLF | Oui | Non — utiliser scripts |
| `.dhop` | Binaire | — | — | INTERDIT |
| `.dhoq` | Binaire | — | — | INTERDIT |

> `.dhsd`, `.dhsf`, `.dhsi` sont des fichiers **structures** (positions/offsets) : ne pas les editer ligne-a-ligne ; passer par les skills dedies (`managing-diva-dictionaries`, `manipulating-dhsf-screens`).

---

## Caracteres ISO-8859-1 courants dans les fichiers Divalto

| Caractere | Hex ISO-8859-1 | Description |
|-----------|----------------|-------------|
| e accent aigu | `\xe9` | Tres frequent (developpement, reference, genere) |
| e accent grave | `\xe8` | Frequent (requete, modele) |
| a accent grave | `\xe0` | Courant (deja, la) |
| c cedille | `\xe7` | Courant (francais) |
| u accent grave | `\xf9` | Occasionnel |

---

## Verification

**Voie unique : `verify_encoding.py`.** C'est lui qui porte le verdict, et il controle plus
que l'encodage :

```bash
py .claude/skills/writing-diva-files/scripts/verify_encoding.py --path fichier.dhsp
```

| Controle | Pourquoi |
|---|---|
| Encodage ISO-8859-1 (pas UTF-8) | les accents deviennent illisibles pour le compilateur |
| Fins de ligne CRLF, pas de LF nu | XWin attend du CRLF |
| CRLF final present | son absence provoque l'**Erreur 135** a la compilation |
| Pas de BOM UTF-8 | 3 octets parasites en tete de fichier |
| **Aucune sequence UTF-8 residuelle** | signature d'un **mojibake** (Latin-1 double-encode) : le fichier decode en ISO-8859-1 sans erreur mais le contenu est corrompu |
| **Aucune ligne physique > 251 caracteres** | XWin refuse d'**OUVRIR** le source (pas seulement de le compiler) |

`valid: false` + exit 1 des qu'un controle echoue. Les scripts d'ecriture du skill
(`write_file.py`, `patch_file.py`) appliquent les memes regles **avant** d'ecrire et
re-verifient apres : leur champ `verified` signifie la meme chose que ce `valid`.

> `file --mime-encoding` (outil Unix) est **absent d'un poste Windows/PowerShell nu** et ne
> detecte ni le mojibake residuel, ni la limite des 251 caracteres, ni l'absence de CRLF
> final : il declarerait conformes des fichiers que XWin refuse. Ne pas s'en servir comme
> verdict.

> Pieges Windows recurrents (Edit/Write, pipe PowerShell -> BOM, Python mode texte -> LF, pas de CRLF final -> Erreur 135) : voir [safe-methods.md](safe-methods.md#pieges-windows-causes-recurrentes-de-corruption).
