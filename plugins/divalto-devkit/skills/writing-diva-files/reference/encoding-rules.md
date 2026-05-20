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
| `.dhop` | Binaire | — | — | INTERDIT |
| `.dhoq` | Binaire | — | — | INTERDIT |

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

```bash
# Encodage
file --mime-encoding fichier.dhsp
# Attendu : iso-8859-1, us-ascii, ou unknown-8bit
# ERREUR si : utf-8

# Fins de ligne
file fichier.dhsp
# Attendu : "CRLF line terminators"
```
