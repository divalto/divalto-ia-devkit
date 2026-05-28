# Composant `cadre` -- element graphique decoratif

## Contenu

- Quand utiliser
- Grammaire
- Les 19 valeurs `nature=`
- `nature=vide` defaut implicite
- `epaisseur=0` -- trait invisible
- Couleurs canoniques
- Comportement runtime -- tri auto par surface
- Distinction `cadre` vs `groupbox`
- Anti-patterns

---

## Quand utiliser

`cadre` est le composant **graphique decoratif pur** d'un masque -- trait simple, rectangle, ellipse ou oblique. Polyvalent et sans titre, distinct du `groupbox` (cf. [composant-groupbox.md](composant-groupbox.md)) qui regroupe logiquement avec un titre nomme.

Cas typiques :

- Separateur visuel (trait horizontal ou vertical)
- Encadrement decoratif (rectangle plein ou vide)
- Forme non-rectangulaire (ellipse, oblique)
- Placeholder runtime pilote (cadre invisible avec `noms=` pour `XmeSetAttribut`)

---

## Grammaire

```ini
[cadre]
[presentation]                              ; obligatoire
position=Y,X                                ; coin haut-gauche
taille=H,L                                  ; H=1 ou L=1 pour traits
id=N                                        ; >= 1000001 en surcharge
[param_cadre]                               ; obligatoire
nature=horizontal                           ; optionnel -- 19 valeurs (absent = "vide")
epaisseur=2                                 ; 0=trait invisible / 2-3=visible
arrondi=4                                   ; pour les natures `_arrondi`
wnom_couleurcadre="TRAIT_SIMPLE_NOIR"       ; quasi-obligatoire (couleur du trait)
wnom_couleurfond="STD"                      ; quasi-obligatoire (couleur du fond)
[info_bulle]                                ; optionnel -- 3e sous-section legitime
texte="Bulle de texte"
```

3 sous-sections legitimes : `[presentation]`, `[param_cadre]`, et `[info_bulle]` (optionnel, rare).

---

## Les 19 valeurs `nature=`

| Libelle AGL | Valeur source | Adoption X.13 |
|-------------|---------------|---------------|
| Vide | *(absent dans le source)* OU `vide` | Dominant -- defaut implicite |
| Trait horizontal haut | `horizontal` (sans suffixe = haut par defaut) | Adopte |
| Trait vertical gauche | `vertical` (sans suffixe = gauche par defaut) | Adopte |
| Trait horizontal bas | `horizontal_b` | Adopte |
| Trait vertical droit | `vertical_d` | Adopte |
| Trait horizontal haut interieur | `horizontal_h_i` | Adopte (impression) |
| Trait vertical gauche interieur | `vertical_g_i` | Adopte (impression) |
| Trait horizontal bas interieur | `horizontal_b_i` | Adopte (impression, rare) |
| Cadre plein | `plein` | Adopte |
| Cadre plein + arrondi | `plein_arrondi` | Adopte |
| Cadre vide + arrondi | `vide_arrondi` | Adopte |
| Trait vertical droit interieur | `vertical_d_i` | Disponible, non adopte X.13 |
| Ellipse pleine | `plein_ellipse` | Disponible, non adopte X.13 |
| Ellipse vide | `vide_ellipse` | Disponible, non adopte X.13 |
| Trait oblique `\` | `diag_bas` | Disponible, non adopte X.13 |
| Trait oblique `/` | `diag_haut` | Disponible, non adopte X.13 |
| Rectangle interieur horizontal | `rectangle_int_h` | Disponible, non adopte X.13 |
| Rectangle interieur vertical | `rectangle_int_v` | Disponible, non adopte X.13 |
| Rectangle interieur | `rectangle_int` | Disponible, non adopte X.13 |

**Convention de nommage** : mapping AGL -> source plus court que le libelle AGL (`largeur` au lieu de `pleinelargeur`, `diag_bas` au lieu de `oblique_descendant`, etc.). **Toujours valider empiriquement** le mapping AGL <-> source pour les enumerations.

### Convention des suffixes `_b/_d/_g/_h/_i`

| Suffixe | Sens | Comportement |
|---------|------|--------------|
| (aucun) | Direction par defaut | `horizontal` = haut, `vertical` = gauche |
| `_b` | bas | `horizontal_b` |
| `_d` | droit | `vertical_d` |
| `_g` | gauche EXPLICITE | uniquement avec `_i` (`vertical_g_i`) -- redondant seul |
| `_h` | haut EXPLICITE | uniquement avec `_i` (`horizontal_h_i`) -- redondant seul |
| `_i` | interieur | Pour masques d'impression -- evite dedoublement aux intersections (pixel-perfect) |

---

## `nature=vide` defaut implicite

**Piege** : si `nature=` est absent du source, l'AGL affiche `Nature: Vide`. Un cadre sans `nature=` est un **rectangle vide** par defaut (pas plein).

Pour un rectangle plein, **declarer explicitement** `nature=plein`.

---

## `epaisseur=0` -- trait invisible

`epaisseur=0` rend le cadre **invisible a l'ecran** (confirme empiriquement). Combinaisons typiques :

| Combinaison | Effet visuel | Cas d'usage |
|-------------|--------------|-------------|
| `vide` (defaut) + `epaisseur=0` + `couleurfond=TRANS` + `noms="..."` | **Cadre 100% invisible** | Placeholder runtime XmeSetAttribut |
| `vide` (defaut) + `epaisseur=2` ou `3` | Cadre vide avec bordure visible | Cadre decoratif classique |
| `plein` + `epaisseur=0` | Rectangle plein sans bordure | Zone coloree sans contour |
| `plein` + `epaisseur=2-3` | Rectangle plein avec bordure | Cadre plein classique |

Valeur `0` est **deliberement fonctionnelle** (pas un defaut Ywpf), souvent pour creer un placeholder invisible cible par code DIVA.

---

## Couleurs canoniques

| Couleur | RGB | Usage |
|---------|-----|-------|
| `TRAIT_SIMPLE_NOIR` | (0,0,0) noir | Couleur trait dominante (83% des cadres) |
| `TRAIT_SIMPLE_GRIS` | (198,198,198) gris | Variante grise |
| **`TRAIT_SIMPLE`** | **(255,255,255) BLANC** | **Nommage trompeur** -- usage typique : couleur de FOND blanc, ou separateur conditionnel discret (avec `noms=` pour pilotage runtime) |
| `STD` | varie | Couleur standard (44% des `wnom_couleurfond`) |
| `TRANS` | transparent | Cadre/corps transparent (42% des `wnom_couleurfond`) |
| `BLANC` | (255,255,255) | Fond blanc explicite |

**Le nom `TRAIT_SIMPLE` est paradoxal car la valeur est BLANCHE.** Heritage historique probable : couleur neutre standard utilisee surtout comme couleur de FOND. Les variants explicites `_NOIR` et `_GRIS` ont ete ajoutes apres pour les traits.

**Convention pratique** :

| Besoin | Valeur recommandee |
|--------|---------------------|
| Couleur de trait NOIR (dominant) | `TRAIT_SIMPLE_NOIR` |
| Couleur de trait gris | `TRAIT_SIMPLE_GRIS` |
| Couleur de FOND blanc | `TRAIT_SIMPLE` ou `BLANC` (RGB equivalents) |
| Trait blanc pour separateur conditionnel runtime | `TRAIT_SIMPLE` avec `noms=` pour pilotage `XmeSetAttribut` |

---

## Comportement runtime -- tri auto par surface

**Specifique aux cadres pleins** (`nature=plein*`) : Ywpf trie automatiquement les cadres pleins **par surface decroissante** au runtime. En cas de chevauchement, c'est toujours le plus petit qui est affiche par-dessus les plus grands.

Permet d'empiler des cadres pleins de tailles differentes (effet visuel "carte") **sans gerer manuellement l'ordre du source**.

> **Distinct du `groupbox`** : groupbox suit strictement l'ordre du source (z-order = ordre source). Cadre plein est trie auto.

---

## Distinction `cadre` vs `groupbox`

| Critere | `groupbox` | `cadre` |
|---------|------------|---------|
| Titre dans un en-tete | Oui (`texte=` obligatoire) | Non |
| Fonction semantique | Regroupement **logique** nomme | Element **graphique** pur |
| Surbrillance auto au focus enfant | Oui (cadre complet + chaine hierarchique) | Aucune (statique) |
| Polyvalence visuelle | 1 forme (rectangle avec en-tete) | 19 formes |
| Couleurs | `couleur_fond` unique | `wnom_couleurcadre` + `wnom_couleurfond` (2 distinctes) |
| Z-order au runtime | Ordre du source | **Trie auto** par surface (pleins) |

**Regle de choix** :

- **`groupbox`** si grouper logiquement avec un titre nomme (semantique + surbrillance focus utile)
- **`cadre`** si decorer visuellement -- separateur, encadrement, forme non-rectangulaire, placeholder runtime

---

## Pilotage dynamique

~58% des cadres ont un `noms=` declare (plus eleve que groupbox a 16%). Usages typiques :

- **Placeholder invisible** : cadre `epaisseur=0 + couleurfond=TRANS + noms="..."` pour marquer une zone ciblable runtime (ex: `sfkpositionleft`)
- **Separateur conditionnel** : cadre `couleurcadre=TRAIT_SIMPLE (blanc) + noms="..."` qui change de couleur visible au runtime selon le contexte metier (ex: `etbc3`)
- **Visibilite dynamique** : `noms="..."` pile entre `AV_VISIBLE` / `AV_CACHE` selon regles metier

Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md) pour la mecanique runtime.

---

## Anti-patterns

1. **Utiliser `TRAIT_SIMPLE` (blanc) comme couleur de trait sans pilotage runtime** -- trait quasi-invisible sur fond clair. Preferer `TRAIT_SIMPLE_NOIR`.
2. **`epaisseur=0` sans intention** -- trait invisible (souvent involontaire). Utiliser `epaisseur=2` ou `3` pour un trait visible.
3. **Cadre sans `nature=` pour un rectangle plein** -- defaut implicite est `vide`, pas `plein`. Declarer explicitement `nature=plein`.
4. **Confondre `cadre` et `groupbox`** -- groupbox = avec titre nomme, cadre = sans titre. Choisir selon la semantique.
5. **Utiliser une valeur `nature=` non adoptee X.13** (ellipses, obliques, rectangles interieurs) -- techniquement disponible mais 0 occurrence standard. Verifier le besoin metier.
6. **Ne pas declarer `wnom_couleurcadre` / `wnom_couleurfond`** -- valeurs quasi-obligatoires en pratique (99%+ des cadres les declarent).
