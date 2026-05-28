# Table Nature -> Taille en octets

Cette table documente les Natures **les plus courantes** observees dans les dictionnaires Divalto. **La taxonomie reelle est plus large** : une inspection ce 2026-05-04 du dictionnaire standard `gtfdd.dhsd` (pack v2026_erpX13_p223a, 6392 blocs `[CHAMP]`) a recense ~280 valeurs `Nature` distinctes -- la presente reference en couvre environ 40 %.

**Action en cas de Nature non documentee** : inspecter le `.dhsd` standard pour trouver un autre champ utilisant la meme Nature, en deduire la taille en octets en croisant avec son offset suivant dans `[CHAMPS]`. **Ne pas deviner** -- un offset cumule incorrect dans une surcharge corrompt les donnees silencieusement (cf. [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md) section "Regle d'offset cumule").

Une RETEX SUGGESTION-DOC peut etre ouverte pour enrichir cette reference au fil des decouvertes terrain (Nature observee + taille validee).

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

La regle s'applique **strictement** :
- Dans le `[CHAMPS]` d'une nouvelle table (cf. [dhsd-5-zones.md](dhsd-5-zones.md) Zone 2)
- Dans le `[CHAMPL]` d'une surcharge, **a partir de l'offset 1 dans le container `U<NomTable>`** (cf. [dhsd-surcharge-pattern.md](dhsd-surcharge-pattern.md))

---

## Familles de Nature observees (couverture estimative)

Inspection ce 2026-05-04 du standard `gtfdd.dhsd` :

| Famille | Doc actuelle | Constat reel | Couverture |
|---------|--------------|--------------|------------|
| Strings simples (`Nature=N`) | ~14 valeurs (1, 2, 4, 8, 10, 13, 20, 25, 28, 33, 38, 48, 60, 80, 255, 1000) | Dizaines d'autres en usage : 16, 30, 32, 35, 40, 45, 49, 50, 64, 70, 75, 79, 87, 100, 150, 200, 250, 256, 300, 400, 500, 600, 800, 1500, 2000, 8189, 8191, 32000... -- regle `taille = N` reste valide | ~40 % |
| Numeriques ASCII (`N,M`) | Regle generique documentee | Couverte | 100 % |
| Numeriques BCD packed (`N,DM`) | Uniquement `D0` mentionne | `D0`, `D2`, `D3` observes (`12,D2` utilise 163 fois) | ~33 % |
| Dates / Heures | `D8`, `DH`, `H6` | `DM` (Date/Mois) observe en plus, taille a confirmer | ~75 % |
| Types techniques mono-lettre | 0 documentees | `L` (Long), `B` (Boolean), `X` (Variant), `OB` (Object) observes | 0 % |
| Types Temps `T7`/`T8`/`T10` | 0 documentees | Observes (`RealTps`, `TpsDureeMaxi`, `BudgetTpsP`) -- format/taille a confirmer | 0 % |
| Tableaux (`Nature=X*N` ou `*N*M`) | 0 documente | Frequent : `Nature=L*50`, `Nature=20*3*4`, `Nature=12,D2*99` -- regle probable `taille_totale = taille_unitaire * N [* M]` | 0 % |

Les sections ci-dessous documentent uniquement les Natures **confirmees**. Les autres familles ci-dessus restent a documenter au fil des decouvertes (RETEX SUGGESTION-DOC).
