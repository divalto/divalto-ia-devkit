# Taxonomie des suffixes typés DIVA

## Contenu

- Principe
- Table des suffixes et Natures associees
- Decision du suffixe depuis la description semantique

## Principe

Quand le collaborateur decrit un champ metier, l'orchestrateur propose un nom
PascalCase avec le suffixe adapte au type semantique. Le suffixe determine la
Nature (type DIVA).

## Table des suffixes

| Description semantique | Suffixe propose | Nature DIVA |
|------------------------|-----------------|-------------|
| "date X" | `X<contexte>Dt` | `D8` |
| "timestamp X" | `X<contexte>Dh` | `DH` |
| "heure X" | `X<contexte>He` | `H6` |
| "flag / booleen X" | `X<contexte>Fl` ou `X<contexte>Flg` | `1,0` |
| "type / classification X" | `X<contexte>Typ` | `1,0` ou `2,0` |
| "montant X" | `X<contexte>Mt` | `16,D0` |
| "quantite X" | `X<contexte>Qte` | `12,D2` |
| "nombre / compteur X" | `X<contexte>Nb` | `N,0` (entier court) |
| "code X" | `X<contexte>Cod` | a demander (1/4/5/8/20 octets) |
| "numero X" | `X<contexte>No` | a demander |
| "libelle X" | `X<contexte>Lib` | a demander (20/40/80/155) |
| "reference X" | `X<contexte>Ref` | Nature 25/33/49 selon longueur |

## Decision du suffixe

1. Lire la description semantique du collaborateur.
2. Mapper au suffixe type dans la table ci-dessus.
3. Si Nature determinee : proposer directement.
4. Si Nature "a demander" : poser la question au collaborateur avec les options
   courantes (longueur pour Cod/No/Lib/Ref).

## Lien avec suggest_nature.py

Pour les suffixes non-ambigus, `suggest_nature.py` deduit automatiquement la Nature.
Appel :

```
py .claude/skills/managing-diva-dictionaries/scripts/suggest_nature.py --name "{nom_champ}"
```

Retourne `{ "nature": "...", "confidence": 0.xx, "rule": "...", "alternatives": [...] }`.

Regle de decision sur la confidence :
- `>= 0.85` -> proposer la Nature directement
- `0.5 <= x < 0.85` -> proposer + alternatives, demander confirmation
- `< 0.5` -> demander explicitement la Nature au collaborateur
