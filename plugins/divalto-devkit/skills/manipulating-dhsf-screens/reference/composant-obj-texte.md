# Composant `obj_texte` -- libelle statique

## Contenu

- Quand utiliser
- Grammaire
- Sous-sections detaillees
- Position et taille
- Anti-patterns
- Datapoints valides empiriquement

---

## Quand utiliser

`obj_texte` est le composant **libelle statique** d'un masque -- un texte fixe affiche a une position donnee, sans interaction utilisateur. Usage typique : libelle accompagnant un champ de saisie, titre de section, indication contextuelle.

Distinct du `champ` (cf. [composant-champ.md](composant-champ.md)) qui est lie a une donnee record DIVA et editable.

> **Note** : la balise INI `[obj_texte]` est aussi utilisee pour un **bouton textuel** quand un sous-bloc `[param_bouton]` est present. Ce n'est pas le meme composant -- voir le futur composant `bouton` (non couvert ici).

---

## Grammaire

```ini
[obj_texte]
[presentation]
position=Y,X                ; obligatoire -- en orteils
taille=H,L                  ; obligatoire -- en orteils
id=N                        ; obligatoire (>= 1000001 en surcharge)
wstyle="STD"                ; obligatoire -- ref fstylewpf.dhfi
[texte]
texte="Mon libelle"         ; obligatoire -- ATTENTION : l'attribut est 'texte=', pas 'nom='
[info_bulle]                ; optionnel
texte="Tooltip au survol"
```

Sous-sections obligatoires : `[presentation]` + `[texte]`. Sous-section optionnelle : `[info_bulle]`.

---

## Sous-sections detaillees

### `[presentation]`

| Propriete | Obligatoire | Valeur |
|-----------|-------------|--------|
| `position=Y,X` | Oui | Coordonnees en orteils (Y vertical, X horizontal) |
| `taille=H,L` | Oui | Hauteur et longueur en orteils |
| `id=N` | Oui | Identifiant unique dans le masque. **>= 1000001 en surcharge** (cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md)). Incrementer `[masque].dernier_id` apres ajout. |
| `wstyle="<X>"` | Oui | Reference vers une clef de `fstylewpf.dhfi`. Valeur dominante pour libelle simple : `"STD"`. Variantes : `"STD_AFF"`, `"STD_GRAS"`. Voir [surcharge-feuilles-style.md](surcharge-feuilles-style.md) pour les styles disponibles. |
| `cadrage=<X>` | Non | Alignement du **texte dans la boite** : `gauche` / `centre` / `droite`. **Ne deplace pas le composant** -- pour positionner le composant, modifier `position.X`. |
| `noms="<X>"` | Non | Identifiant logique pour `XmeSetAttribut` (visibilite dynamique, etc.). Voir [xmesetattribut-dynamique.md](xmesetattribut-dynamique.md). |
| `attache_x=oui` / `attache_lgx=oui` | Non | Comportement de redimensionnement horizontal (ancrage droite / largeur variable). Mutuellement exclusifs. Idem `attache_y` / `attache_lgy` pour vertical. |

### `[texte]`

| Propriete | Obligatoire | Valeur |
|-----------|-------------|--------|
| `texte="<X>"` | Oui | Texte affiche. **L'attribut s'appelle bien `texte=`** (pas `nom=`). Echappement special : `_` simple est elimine par Ywpf (heritage Windows non implemente Harmony), `__` produit un `_` litteral. |

### `[info_bulle]`

| Propriete | Obligatoire | Valeur |
|-----------|-------------|--------|
| `texte="<X>"` | Oui | Texte du tooltip au survol souris. Pas besoin de `noms=` ni de `[aide_page]` -- `[info_bulle].texte=` seul suffit. |

---

## Position et taille

Coefficients de conversion entre coordonnees orteils et nb_lig/nb_col de la page (a valider auprès de Stephane Castelain pour le coefficient exact) :

```
~ 1 ligne (nb_lig) = 8 a 9 orteils en Y
~ 1 colonne (nb_col) = 4 orteils en X
```

Une page `nb_lig=N, nb_col=M` couvre donc ~`(N*9) x (M*4)` orteils. La regle n'est pas strictement encadree -- des composants peuvent depasser ces bornes (extension automatique probable).

Pour un centrage vertical visuel approximatif : `Y = (nb_lig * 9) / 2 - taille_H / 2 + offset_correction`. Offset empirique observe : +3 a +5 orteils.

Voir [normes-graphiques.md](normes-graphiques.md) pour les regles canoniques d'ergonomie (X=5 bord gauche, Y=8/26 selon onglet, formule libelle-champ accole).

---

## Anti-patterns

1. **`nom=` au lieu de `texte=`** dans `[texte]` -- l'attribut est `texte=`. `nom=` est utilise dans d'autres sous-sections (ex: `[param_onglet_page]`).
2. **`id < 1000001` dans une surcharge** -- collision potentielle avec un id standard. Pour modifier un libelle standard, editer en place le bloc existant (cf. [dhsf-overwrite-pattern.md](dhsf-overwrite-pattern.md) "Modifier un composant standard").
3. **Oublier d'incrementer `[masque].dernier_id`** apres ajout d'un composant custom.
4. **Inventer un `wstyle`** non present dans `fstylewpf.dhfi` ni dans le `fstylewpfu.dhfi` du projet de surcharge (cf. [surcharge-feuilles-style.md](surcharge-feuilles-style.md)).
5. **Confondre `cadrage` et `position.x`** -- `cadrage` aligne le texte dans la boite du composant ; pour positionner le composant a gauche/centre/droite de la page, modifier `position.x`.
6. **Utiliser un wstyle `TABLEAU_*` sur un libelle simple** -- ces styles sont concus pour les composants tabulaires (lignes pointees, entetes de colonne) et donnent un rendu inadapte (fond colore, faible contraste). Rester sur `"STD"` (88% des libelles standards) ou `"STD_AFF"` / `"STD_GRAS"`.
7. **Confondre `obj_texte` (libelle) et `obj_texte + [param_bouton]` (bouton textuel)** -- meme balise INI, semantique differente.

---

## Datapoints valides empiriquement

Tests `gtez047_sqlu.dhsf` page 12, session 2026-05-06 (compile OK 0 erreur, 6 masques) :

| Test | Resultat |
|------|----------|
| Insertion `obj_texte` `id=1000001` + incrementation `dernier_id` -> 1000001 | Composant insere, masque compile, libelle visible au runtime |
| `cadrage=gauche` (etait `centre`) | Le **texte** s'aligne a gauche dans la boite. La **boite reste centree** dans la page. Confirme : `cadrage` aligne le texte dans le composant, pas le composant dans la page. |
| `wstyle="TABLEAU_AFF_POINTE_12"` (etait `"STD"`) | Fond orange/saumon, texte clair, faible contraste. Style destine aux lignes pointees d'un tableau, inadapte pour un libelle classique. |
| Ajout `[info_bulle]` avec `texte="Tooltip de test"` | Tooltip s'affiche au survol souris. Pas besoin de `noms=` ni de `[aide_page]`. |

---

## Exemple complet

Libelle simple "Code devise" a position 80,5 sur un masque de surcharge :

```ini
[obj_texte]
[presentation]
position=80,5
taille=9,40
id=1000001
wstyle="STD"
[texte]
texte="Code devise"
[info_bulle]
texte="Code ISO 4217 sur 3 caracteres"
```

Apres l'ajout, mettre a jour `[masque].dernier_id=1000001` (si c'etait < 1000001 avant) ou `[masque].dernier_id=<valeur+1>` (si on continue une numerotation existante).
