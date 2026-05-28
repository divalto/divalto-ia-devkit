# Composant `bitmap_constante` -- image fixe via feuille de style

## Contenu

- Quand utiliser
- Grammaire
- Les 2 niveaux de referencement
- Les 8 valeurs `actionbitmap=`
- Surcharge avancee non exposee AGL
- Anti-patterns

---

## Quand utiliser

`bitmap_constante` est le composant **image FIXE** d'un masque. L'image est definie dans la feuille de style `fstylewpf.dhfi` et referencee via la propriete `wnom=`. Cas typique : icone d'information / d'attention / d'avertissement, icone de bouton, illustration statique.

Distinct du `bitmap_variable` (cf. [composant-bitmap-variable.md](composant-bitmap-variable.md)) qui pointe vers une image dynamique calculee a partir d'un champ DIVA au runtime.

---

## Grammaire

```ini
[bitmap_constante]
[presentation]                          ; obligatoire
position=Y,X
taille=H,L                              ; typique 16,16
id=N
actionbitmap=reduire                    ; optionnel -- defaut absent = "Pas de traitement"
wstyle="STD"                            ; optionnel
noms="<id_logique>"                     ; optionnel (cf. XmeSetAttribut)
[param_bitmapc]                         ; obligatoire
wnom="<nom_feuille_style>"              ; quasi-obligatoire -- reference fstylewpf.dhfi
wnom_couleur="TRANS"                    ; OPTIONNEL -- surcharge couleur (NON expose AGL)
adapterfond=oui                         ; OPTIONNEL -- surcharge fond (NON expose AGL)
[info_bulle]                            ; optionnel (3e sous-section legitime)
texte="Bulle de texte"
```

Sous-sections legitimes : `[presentation]`, `[param_bitmapc]`, et `[info_bulle]` (optionnel).

> **Insight critique** : `actionbitmap=` est dans `[presentation]`, **PAS dans `[param_bitmapc]`** -- traite comme propriete de layout.

---

## Les 2 niveaux de referencement

Le bitmap_constante utilise un systeme a 2 niveaux :

```
[bitmap_constante] dans .dhsf
    |
    | wnom="Sous_menu_preparation"
    v
fstylewpf.dhfi (feuille de style)
    |
    | "Sous_menu_preparation" -> "#sous_menu_preparation" (bitmap interne)
    v                       ou  "logo.png" (fichier externe)
xrtdiva.exe (bitmaps internes) ou fichier image reel
```

**Consequences** :

- Le source `.dhsf` ne contient **JAMAIS** de prefixe `#` (`#aff_compta`, etc.) -- 0 occurrence dans le standard. Le `#` est dans la feuille de style uniquement.
- Le source `.dhsf` reference UNIQUEMENT le nom de la feuille de style (`wnom=`), qui fait le lien vers le fichier reel.

Pour personnaliser un bitmap, surcharger la feuille de style via `fstylewpfu.dhfi` (cf. [surcharge-feuilles-style.md](surcharge-feuilles-style.md)).

---

## Les 8 valeurs `actionbitmap=`

| Libelle AGL | Valeur source | Statut |
|-------------|---------------|--------|
| Pas de traitement | *(absent du source)* | **Defaut implicite** -- dominant |
| Reduire si debordement | `reduire` | Adopte |
| Pleine boite | `remplir` | Adopte (rare en constante, frequent en variable) |
| Pleine largeur | `largeur` | Disponible, non adopte standard |
| Pleine hauteur | `hauteur` | Disponible, non adopte standard |
| Taille maximum | `taillemax` | Adopte (variable uniquement) |
| Mosaique | `mosaique` | Disponible, expose AGL mais quasi-inutilise |
| Centrer | `centrer` | Adopte (variable uniquement) |

**Convention de nommage** : mapping AGL -> source plus court que le libelle AGL (`largeur` au lieu de `pleinelargeur`, `taillemax` au lieu de `taillemaximum`). **Toujours valider empiriquement le mapping**.

---

## Surcharge avancee non exposee AGL

Deux proprietes sont valides syntaxiquement mais **NON exposees dans l'AGL** -- modifiables uniquement par edition source manuelle :

| Propriete | Valeur observee | Effet |
|-----------|-----------------|-------|
| `wnom_couleur` | `TRANS` | Surcharge la couleur du bitmap -- `TRANS` rend le fond transparent (pour superposition sur n'importe quel fond) |
| `adapterfond` | `oui` | Active l'adaptation du fond du bitmap a la couleur du conteneur |

Pattern typique : `wnom="INFOG"` + `wnom_couleur="TRANS"` + `adapterfond=oui` = icone d'information qui s'integre visuellement sur n'importe quel fond.

> Selon la doc Divalto interne : *"Les proprietes faisant partie du sous-arbre ayant pour racine la ligne 'Nom dans la feuille de style' peuvent etre personnalisees : une valeur non personnalisee, affichee en noir, est toujours recherchee dans la feuille de styles ; une valeur personnalisee, affichee en rouge, n'est plus affectee par un changement au niveau de la feuille"*.

---

## Pattern legacy `;N` -- non adopte X.13

Doc CHM mentionne le mecanisme `;N` pour les fichiers multi-icones (`.exe`, `.dll`, `.ico`) :

| Syntaxe | Semantique |
|---------|------------|
| `"xrtdiva.exe"` ou `"xrtdiva.exe;0"` | Premiere icone du fichier |
| `"xrtdiva.exe;3"` | 4e icone (0-based) |
| `"xrtdiva.exe;0;;;1"` | Premiere icone, version 16x16 (petite) |

**0 occurrence dans le standard X.13.** Pattern legacy non adopte (centralisation via feuille de style + limitation client leger HTML + migration historique). Preferer la centralisation via feuille de style.

---

## Anti-patterns

1. **Utiliser le prefixe `#` directement dans `wnom=`** -- le `#` n'a sa place que dans la feuille de style, jamais dans le source `.dhsf`.
2. **Reference directe a un `.exe`/`.dll`/`.ico`** -- pattern legacy non adopte X.13. Passer par la feuille de style.
3. **Utiliser `mosaique` comme `actionbitmap`** -- expose AGL mais 0 occurrence corpus standard. Comportement runtime a verifier avant adoption.
4. **Confondre `bitmap_constante` et `bitmap_variable`** -- constante = image fixe via feuille de style, variable = image dynamique via record DIVA.
5. **Tenter de modifier `wnom_couleur` ou `adapterfond` via l'AGL** -- proprietes non exposees, modifiables uniquement par edition source manuelle.
6. **Mettre `actionbitmap=` dans `[param_bitmapc]`** -- il est dans `[presentation]`.
