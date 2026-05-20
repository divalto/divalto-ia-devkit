# Table Nature -> Taille en octets

Source : `docs/DICTIONNAIRE-DHSD.md` (section 2).

---

## Natures simples

Pour les natures simples, **Nature = Taille en octets**. Toute valeur entiere est valide.

| Nature | Taille (octets) | Description | Statut |
|--------|-----------------|-------------|--------|
| `1` | 1 | Booleen / char(1) / code enregistrement | Confirme |
| `2` | 2 | Code court | [A VERIFIER] |
| `3` | 3 | Entier court | [A VERIFIER] |
| `4` | 4 | Code reference | Confirme |
| `8` | 8 | Reference longue / dossier | Confirme |
| `10` | 10 | Code alphanumerique (Ce composite) | Confirme |
| `13` | 13 | Code EAN / tiers | Confirme |
| `20` | 20 | Code long (article, tiers, user) | Confirme |
| `25` | 25 | Designation abregee | Confirme |
| `28` | 28 | UserTrace | Confirme |
| `33` | 33 | Reference complete | Confirme |
| `38` | 38 | Texte / adresse | [A VERIFIER] |
| `48` | 48 | Droits d'acces | Confirme |
| `60` | 60 | Email | [A VERIFIER] |
| `80` | 80 | Designation longue | Confirme |
| `255` | 255 | Texte long | [A VERIFIER] |
| `1000` | 1000 | Memo | [A VERIFIER] |
| N | N | Toute valeur entiere | Confirme |

---

## Natures speciales

| Nature | Taille (octets) | Description | Statut |
|--------|-----------------|-------------|--------|
| `D8` | 8 | Date (AAAAMMJJ) | Confirme |
| `H6` | 6 | Heure (HHMMSS) | Confirme |
| `DH` | 14 | Date+Heure | Confirme |

---

## Natures numeriques

Format : `N,M` ou `N,D0`

| Nature | Taille (octets) | Description | Statut |
|--------|-----------------|-------------|--------|
| `N,M` | N | Numerique : N octets total, M decimales | Confirme |
| `N,D0` | N | Numerique signe : N octets total, signe | Confirme |
| `11,0` | 11 | Compteur | [A VERIFIER] |
| `14,0` | 14 | Grand compteur | [A VERIFIER] |

**Exemples :**
- `6,2` = 6 octets, 2 decimales
- `13,D0` = 13 octets, signe
- `10,2` = 10 octets, 2 decimales

---

## Regles de calcul

### Nature simple (entier seul)

```
Taille = Nature
```

### Nature speciale (D8, H6, DH)

```
D8 -> 8 octets
H6 -> 6 octets
DH -> 14 octets
```

### Nature numerique (N,M ou N,D0)

```
Taille = N  (la partie avant la virgule)
```

### Formule de position suivante

```
Position(champ N+1) = Position(champ N) + Taille(Nature du champ N)
```
