# Composant `bitmap_variable` -- image dynamique liee a un record DIVA

## Contenu

- Quand utiliser
- Grammaire
- Regle canonique -- le champ DIVA contient le chemin d'acces au fichier
- Pattern multi-dimensions dans `donnee=`
- Les 8 valeurs `actionbitmap=`
- `saisie=non` -- contrainte structurelle
- `[param_bitmapv]` -- sous-section vide a 100%
- Pilotage runtime quasi-nul
- Anti-patterns

---

## Quand utiliser

`bitmap_variable` est le composant **image DYNAMIQUE** d'un masque. L'image affichee est determinee au runtime par la valeur d'un champ DIVA pointe via `donnee=`. Cas typiques :

- Animation / video pilotee par contexte metier (`FicAvi`)
- Image associee a une entite (logo client, photo article, signature)
- Indicateur visuel selon valeur d'un flag (matrice multi-dim)

Distinct du `bitmap_constante` (cf. [composant-bitmap-constante.md](composant-bitmap-constante.md)) qui pointe vers une image fixe via la feuille de style.

> Composant **rare** (~2.4% des masques standard) -- a utiliser quand l'image doit changer selon une valeur metier.

---

## Grammaire

```ini
[bitmap_variable]
[presentation]                        ; obligatoire
position=Y,X
taille=H,L
id=N
actionbitmap=reduire                  ; quasi-obligatoire (96% present)
noms="<id_logique>"                   ; rare (4.8%)
options="<DO_EntityPicture>..."       ; optionnel (pattern entity picture)
[description]                         ; obligatoire
donnee=record,champ,instance          ; scalaire OU avec indices
minmaj=majuscules                     ; boilerplate (100% present)
saisie=non                            ; boilerplate -- voir section "saisie=non"
[param_bitmapv]                       ; obligatoire mais TOUJOURS VIDE (100%)
```

3 sous-sections legitimes : `[presentation]`, `[description]`, `[param_bitmapv]`.

---

## Regle canonique -- le champ DIVA contient le chemin d'acces au fichier

**Pour un bitmap_variable, le champ DIVA cible (`donnee=record,champ,instance`) contient le CHEMIN D'ACCES au fichier image**. Le runtime Ywpf lit ce chemin et charge l'image en consequence.

Champs typiques observes dans le standard :

| Champ | Description dictionnaire | Nature | Usage |
|-------|--------------------------|--------|-------|
| `WinChnC`, `WinChnC2`, `WinChnC3` | "Chemin complet windows" | **Alpha 256** | Path Windows complet (= MAX_PATH) |
| `FicNom` | "Nom fichier" | Alpha | Nom de fichier seul |
| `FicAvi` | "bitmap animation" | Alpha | Fichier video |
| `ImageBqy` | "IMage ou bqy affiche sur le menu" | Alpha | Image ou requete bqy |
| `ChoixRessource` | "Multi-choix des ressources" | Alpha 40*3 | Cle de ressource multi-occurrence |

**Convention** : tous les champs cibles sont de type **Alpha** (texte). Pas de blob, pas d'entier. La valeur est traitee comme chemin a la lecture.

Pour un champ custom, prevoir une Nature Alpha de capacite suffisante (256 octets pour un path Windows complet).

---

## Pattern multi-dimensions dans `donnee=`

Le 4e composant `indice` de `donnee=record,champ,instance,indice` est un mecanisme **transverse** pour tous les composants qui consomment un champ multi-dimensionnel du dictionnaire (`Dimensions: N x M x P x Q` dans le `.dhsd`).

**Syntaxe** : `donnee=record,champ,instance,indice1[,indice2,...,indice4]`. Chaque dimension occupe **son propre slot positionnel** separe par virgule (pas un tuple compose).

Exemple validite : matrice 4 lignes x 3 colonnes sur la table `CatPiece` :

```
donnee=catpiece,actioncod,catpiece,1,1   ; ligne 1, colonne 1
donnee=catpiece,actioncod,catpiece,1,2   ; ligne 1, colonne 2
donnee=catpiece,actioncod,catpiece,4,3   ; ligne 4, colonne 3
```

### Mecanique runtime des indices

Variables Harmony exposees au code DIVA (dans un hook `Champ_<X>_<id>_Ap`) :

```diva
ColumnNo1 = Harmony.Dataind1            ; quel indice 1 a declenche le trigger
ColumnNo2 = Harmony.Dataind2            ; quel indice 2 (idem)

if catpiece.actioncod(ColumnNo1, ColumnNo2) <> ' '
    ; lecture/ecriture du champ multi-dim
endif
```

Un seul handler peut servir N instances visuelles d'un meme champ multi-dim.

**Syntaxe d'acces DIVA** : `record.champ(i,j)` (parentheses + virgule). Distincte de la syntaxe `donnee=` qui est tout-virgules.

---

## Les 8 valeurs `actionbitmap=`

L'AGL expose les **memes 8 valeurs** que pour `bitmap_constante` (cf. [composant-bitmap-constante.md](composant-bitmap-constante.md)). Distribution distincte cependant :

| Libelle AGL | Valeur source | bitmap_variable | bitmap_constante |
|-------------|---------------|-----------------|------------------|
| Pas de traitement | *(absent)* | 3.8% | **65%** |
| Reduire si debordement | `reduire` | **61.5%** | 34% |
| Pleine boite | `remplir` | **26.0%** | 0.6% |
| Pleine largeur | `largeur` | 0% | 0% |
| Pleine hauteur | `hauteur` | 0% | 0% |
| Taille maximum | `taillemax` | 7.7% | 0% |
| Mosaique | `mosaique` | 0% | 0% |
| Centrer | `centrer` | 1.0% | 0% |

**Pattern inverse vs constante** : pour la constante, le defaut implicite domine (image de dimensions connues au design). Pour la variable, on **specifie explicitement** dans 96% des cas car la taille de l'image runtime est inconnue au design -> doit toujours indiquer l'adaptation a la boite.

---

## `saisie=non` -- contrainte structurelle

100% des occurrences declarent `saisie=non`. Trois elements convergent :

1. Jamais absent, jamais `oui` dans le corpus standard
2. L'AGL **n'expose PAS** la propriete "Saisie" dans le panneau du `bitmap_variable`
3. Semantique : on ne "saisit" pas une image, l'image vient toujours du champ pointe par `donnee=`

Conclusion : la ligne `saisie=non` est un **boilerplate** genere automatiquement pour respecter la grammaire de `[description]` (heritee de `champ`), sans valeur semantique modifiable.

> Pattern transverse : 100% d'une valeur dans le corpus != usage observe, peut etre un boilerplate. A surveiller sur d'autres composants.

---

## `[param_bitmapv]` -- sous-section vide a 100%

0 sur 104 blocs `[param_bitmapv]` contient une seule propriete dans le standard X.13. La sous-section est presente obligatoirement (forme syntaxique) mais joue le role d'un placeholder. Reserve d'extension non exploitee dans l'etat actuel du standard.

---

## Pilotage runtime quasi-nul

A la difference du `bitmap_constante` (14% avec `noms=`) et du `cadre` (58%) ou du `champ` (variable selon usage), seuls **4.8%** des `bitmap_variable` ont un `noms=` declare. Et **un seul** est reellement pilote par `XmeSetAttribut` dans le standard : `animation` (utilise dans 4 fichiers, avec un seul attribut `AN_VISIBILITE` -- `AV_CACHE`/`AV_VISIBLE`).

Exemple concret -- `doem000.dhsf` + `dopmfene.dhsp` :

```ini
[bitmap_variable]
[presentation]
noms="animation"
actionbitmap=reduire
[description]
donnee=dowfene,ficavi,dowfene
saisie=non
[param_bitmapv]
```

```diva
if animation = " "
    XmeSetAttribut("animation", An_Visibilite, Av_Cache)
else
    XmeSetAttribut("animation", An_Visibilite, Av_Visible)
endif
```

Le pilotage dynamique se fait essentiellement **via le contenu du champ DIVA** (changer la valeur du champ change l'image affichee), pas via `XmeSetAttribut`. Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md) pour la mecanique generale.

---

## Anti-patterns

1. **Pointer un champ DIVA qui ne contient PAS un chemin** -- bitmap_variable interprete la valeur comme chemin, donc un champ avec une valeur arbitraire (entier, code metier) ne fonctionnera pas.
2. **Champ DIVA de Nature non-Alpha** -- les chemins sont des chaines (256 caracteres typique). Un champ entier ou date est inadapte.
3. **Confondre `bitmap_variable` et `bitmap_constante`** -- variable = chemin dans un champ DIVA, constante = nom dans la feuille de style.
4. **Omettre `actionbitmap=`** -- pour une image de taille inconnue au runtime, definir l'adaptation est crucial (`reduire` ou `remplir` les plus utilises).
5. **Tenter de definir `[param_bitmapv]` avec des proprietes** -- la sous-section est vide a 100% dans le standard.
6. **Modifier `saisie=`** -- propriete boilerplate, non modifiable via AGL.
7. **Confondre la syntaxe `donnee=` (slots) et l'acces DIVA `record.champ(i,j)` (parentheses)** -- deux syntaxes distinctes pour le meme mecanisme multi-dim.
