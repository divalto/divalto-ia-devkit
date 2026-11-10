# Heuristiques de reflow multi-breakpoints

> Cette page explique **comment raisonner** pour dériver un placement `responsive` à chaque palier depuis un onglet en positionnement absolu. Les valeurs de grille, les paliers et les règles de validation sont dans [`fluid-contract.md`](./fluid-contract.md) — on les cite ici, on ne les recopie pas.

## 1. Reconstruire la disposition absolue

Avant de reflow quoi que ce soit, il faut relire la géométrie `position` de chaque contrôle comme une grille, au design tel qu'il a été dessiné :

- **Largeur de colonne au design** : `colWidth = deviceWidth / 12` (`deviceWidth` = la largeur du tab/display où l'onglet a été conçu).
- **Span au design** : `col ≈ round(width / colWidth)`.
- **Colonne de gauche au design** : `≈ round(left / colWidth)`.

Regrouper ensuite les contrôles en **lignes** par chevauchement vertical : trier par `top` puis `left`, puis démarrer une nouvelle ligne dès qu'un contrôle ne chevauche plus verticalement la ligne courante. Cette reconstruction donne la disposition « source » — colonnes et lignes — à partir de laquelle tout le reflow se dérive.

## 2. Breakpoint d'ancrage

L'ancre n'est **jamais supposée** : elle se lit sur l'onglet lui-même.

```
ancre = resolveActiveBreakpoint(deviceWidth)
```

où `deviceWidth` est la largeur du display/tab conçu (paliers et seuils : voir [`fluid-contract.md`](./fluid-contract.md#breakpoints)). La disposition reconstruite à l'étape 1 est la plus fidèle **à ce palier précis** — c'est là que le design « tel que dessiné » doit être placé, quel que soit le nom du palier obtenu (`xs`, `sm`, `md` ou `lg`).

## 3. Reflow vers l'extérieur depuis l'ancre

Une fois l'ancre connue, le travail consiste à reflow dans les deux sens à partir d'elle — jamais à repartir de zéro à chaque palier :

- **Palier plus étroit que l'ancre → collapse.** Élargir les `col` vers `12`, empiler les contrôles. Le wrap naturel de la grille (une ligne qui se remplit passe à la suivante) suffit dans la plupart des cas ; réserver `newRow` aux coupures qu'il faut forcer *avant* qu'une ligne soit pleine.
- **Palier plus large que l'ancre → expand.** Mettre davantage de contrôles côte à côte (réduire les `col`), les écarter avec `offset`, ou préserver l'arrangement proportionnel de l'ancre si l'espace disponible ne justifie pas plus de densité.

Cela donne deux profils de design, symétriques :

- **Design phone-first (ancre `xs`)** : `xs` ≈ le design tel quel ; le travail utile est l'**expansion** vers `sm`/`md`/`lg`.
- **Design desktop-first (ancre `lg`)** : `lg` ≈ le design tel quel ; le **collapse** vers `md`/`sm`/`xs` fait le gros du travail.

Dans les deux cas, la direction du reflow (« vers l'extérieur ») ne change pas — seul le point de départ change. Ne jamais halluciner un sens de reflow fixe : toujours partir de l'ancre calculée à l'étape 2.

## 4. Grille proportionnelle

La grille compte 12 colonnes à toute largeur, donc un même `col` représente toujours la même fraction de largeur quel que soit le palier : `col:6` = demi-largeur à `xs` comme à `lg`. Le reflow change `col`, `offset` et `newRow` en fonction de la **classe de largeur** (le palier), jamais en fonction des pixels — le rendu en pixels est automatique une fois la classe posée.

## 5. Cascade mobile-first du stockage

Écrire `xs` comme base — la disposition la plus resserrée — puis n'ajouter `sm`/`md`/`lg` que pour les champs qui **changent** réellement à ce palier. Un champ non redéfini cascade depuis le palier inférieur (voir la cascade dans [`fluid-contract.md`](./fluid-contract.md#breakpoints)). Cette règle de stockage est indépendante de l'ancre : que le design soit phone-first ou desktop-first, le JSON `responsive` reste toujours écrit `xs` → `lg`, jamais dans le sens inverse.

## 6. Flow plutôt qu'explicite

Préférer `col`/`offset`/`newRow` : ils se réordonnent naturellement quand un contrôle voisin change de taille ou de visibilité. Réserver le placement explicite (`colStart`/`row`) aux cas où une cellule fixe est réellement indispensable — par exemple un élément qui doit toujours occuper un point précis de la grille indépendamment de ses voisins. C'est l'exception, pas le mode par défaut.

## 7. Raisonner par groupes sémantiques

Ne pas traiter chaque contrôle isolément : reconnaître les unités fonctionnelles de l'écran et les faire reflow ensemble.

- **Label + champ** : un `Label` suivi de son `TextBox`/`ComboBox`/`DateTimePicker` reflow comme une paire (empilés à l'étroit, côte à côte quand la largeur le permet).
- **Barres de boutons** : un groupe de `Button` alignés horizontalement reste groupé ; il se resserre ou se réétale, mais ne se dissout pas en morceaux dispersés sur la ligne.
- **Sections / blocs de formulaire** : un ensemble de champs qui forment une section logique (ex. adresse, coordonnées) reflow comme un bloc — même nombre de colonnes par ligne à l'intérieur du bloc à un palier donné, plutôt qu'un mapping contrôle par contrôle sans cohérence visuelle.

C'est cet avantage — voir la structure plutôt que la géométrie brute — qui distingue un reflow réfléchi d'un mapping mécanique, surtout sur les écrans denses à plusieurs sections.
