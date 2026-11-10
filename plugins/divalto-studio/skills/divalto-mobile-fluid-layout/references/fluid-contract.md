# Contrat du layout fluide (source de vérité)

> Toutes les valeurs de cette page sont recopiées telles quelles depuis `src/mobile/designer/responsiveMapping.ts`. En cas de doute, c'est ce fichier source qui fait foi — pas cette référence.

## Sommaire

- Grille & constantes
- Breakpoints
- Champs `ResponsiveAt`
- Contrôles masqués
- `height: fill`
- `height: stretch`
- Règles de validation
- Forme de stockage

## Grille & constantes

Le layout fluide repose sur une grille de **12 colonnes** (`FLUID_COLUMNS = 12`).

- Gouttière : `FLUID_GUTTER = 16` (px), sur les deux axes
- Marges de l'onglet : `FLUID_TAB_PADDING = 16` (px) en haut et en bas ; sur les côtés 16 sous une largeur de 600, 48 à partir de 600
- Marges d'une Card : 24 sur les côtés, 20 en haut et en bas ; sa grille n'a pas de marge propre. Une Card bord à bord (une `Maps` seule) ne garde que 1 (son filet)
- Les lignes prennent la hauteur de leur contenu, sans hauteur minimale ; une cellule n'est pas étirée à la hauteur de sa ligne (voir `stretch`)
- Le breakpoint de l'onglet se calcule sur la largeur − 2 × 16, jamais sur les marges de 48

## Breakpoints

Quatre paliers, mobile-first (Material 3 window size classes : compact / medium / expanded), définis dans `DEFAULT_BREAKPOINTS` :

| nom | largeur min (px) |
| --- | ----------------- |
| xs  | 0                  |
| sm  | 600                |
| md  | 905                |
| lg  | 1240               |

Cascade mobile-first : une valeur définie à un palier s'applique à ce palier ET aux plus larges, jusqu'à ce qu'un palier plus large la redéfinisse. Le palier actif d'une largeur = le plus grand palier dont `min ≤ largeur`.

## Champs `ResponsiveAt`

| champ       | type / plage                                | rôle                                          |
| ----------- | -------------------------------------------- | ---------------------------------------------- |
| `col`       | 1..12                                         | nombre de colonnes occupées                    |
| `offset`    | 0..11                                         | colonnes vides avant le contrôle               |
| `newRow`    | booléen                                       | force un saut de ligne avant le contrôle       |
| `hidden`    | booléen                                       | masque le contrôle à ce palier                 |
| `align`     | `'start' \| 'center' \| 'end' \| 'stretch'`   | alignement **horizontal** dans la cellule ; hors `stretch`, le contrôle se réduit à sa largeur intrinsèque (une image n'en a pas — utiliser `width`) |
| `colStart`  | 1..12                                         | placement explicite : colonne de départ        |
| `row`       | ≥ 1                                            | placement explicite : ligne                    |
| `rowSpan`   | ≥ 1                                            | nombre de lignes occupées                      |
| `width`     | `auto` \| `<dip>`                             | largeur du contrôle dans sa cellule (pas de `vh`) ; bornée par la largeur de cellule ; sans align (ou align: stretch) le contrôle est collé au début de la cellule — pour centrer une icône : width + align: center |
| `height`    | `auto` \| `<dip>` \| `<n>vh` \| `fill` \| `stretch` | hauteur ; `fill` = la hauteur que laissent les autres lignes, `stretch` = la hauteur de sa ligne (voir ci-dessous) |
| `minHeight` | `<dip>` \| `<n>vh`                            | hauteur mini (pas d'`auto`)                    |
| `maxHeight` | `<dip>` \| `<n>vh`                            | hauteur maxi (pas d'`auto`)                    |

`<dip>` = un entier ou un décimal (ex. `120`, `120.5`). `<n>vh` = un nombre suivi de `vh` (ex. `40vh`).

## Contrôles masqués

Un contrôle masqué (`hidden` au palier, ou rendu invisible par sa configuration ou un script) ne prend
pas de cellule : les suivants remontent à sa place, à la racine comme dans une Card.

Sur un onglet fluid, un `Label` sans texte (après traduction) est masqué de la même façon. Un texte
fait d'espaces n'est pas vide. En disposition absolue, rien ne change : les labels vides y servent de fonds.

## `height: fill`

`fill` (insensible à la casse) donne au contrôle la hauteur que laissent les autres lignes : hauteur de la grille − ses marges haute et basse (2 × 16 pour l'onglet, 0 pour la grille d'une Card) − 16 par gouttière entre lignes − hauteurs des lignes fixes, partagée à parts égales entre les lignes qui contiennent un contrôle `fill`, puis bornée par `minHeight` / `maxHeight`. Jamais négatif.

- Un onglet dont un contrôle de premier niveau a `fill` ne défile que si son contenu ne tient pas : les lignes `fill` descendent alors à leur `minHeight` et l'onglet défile. Sur un palier sans `fill`, il défile comme tout onglet fluide.
- Toujours poser un `minHeight` : sans lui, le contrôle tombe à 0 si le reste ne tient pas, au lieu de faire défiler l'onglet.
- Dans une Card de hauteur auto, `fill` se comporte comme `auto`. Une Card avec une hauteur (`<dip>` ou `fill`) borne sa grille : `fill` y fonctionne.
- Avec `rowSpan`, toutes les lignes couvertes sont des lignes `fill` : le contrôle reçoit une part par ligne, plus les gouttières entre elles.
- `fill` n'a de sens que sur `height` : sur `width`, `minHeight`, `maxHeight` il est ignoré.
- Pour « même hauteur que les voisins de la ligne » dans un onglet qui défile, c'est `stretch`, pas `fill`.

Exemple — un calendrier qui occupe l'écran au-dessus d'une barre de navigation :

```jsonc
// Calendar
"responsive": { "xs": { "col": 12, "height": "fill", "minHeight": "300" } }
// ShellNode, en dessous
"responsive": { "xs": { "col": 12, "height": "80" } }
```

## `height: stretch`

`stretch` (insensible à la casse) donne au contrôle la hauteur de la ligne qu'il occupe : la plus haute
des autres cellules de cette ligne (avec `rowSpan`, la somme des lignes couvertes et de leurs gouttières),
puis bornée par son `minHeight` / `maxHeight`.

- Sans autre cellule dans sa ligne, il garde sa propre hauteur (comme `auto`).
- Plus haut que sa ligne, il est **réduit** à la ligne : son contenu ne l'agrandit pas. Poser un
  `minHeight` pour garantir un plancher — lui agrandit la ligne.
- Contrairement à `fill`, il n'empêche jamais l'onglet de défiler, même sur un contrôle de premier niveau.
- Une Card en `stretch` borne sa grille à la hauteur reçue : ses enfants en `fill` se la partagent.
- Il fonctionne aussi dans une grille bornée : `fill` y est résolu d'abord, `stretch` prend ensuite la hauteur de la ligne.
- `stretch` n'a de sens que sur `height`, et ne s'applique pas à un enfant d'en-tête de Card (il y vaut `auto`).

Exemple — une fiche à sa hauteur de contenu, une carte et une liste à côté, à la même hauteur :

```jsonc
// cdCustomerSheet (Card) : pas de height, sa hauteur de contenu fait la ligne
"responsive": { "xs": { "col": 12 }, "md": { "col": 4 } }
// cdMap (Card) et cdEvents (Card)
"responsive": { "xs": { "col": 12 }, "md": { "col": 4, "height": "stretch" } }
// Map dans cdMap, usEvents dans cdEvents
"responsive": { "xs": { "col": 12, "height": "fill", "minHeight": "200" } }
```

Sur `xs`, les trois Cards s'empilent : seule dans sa ligne, une Card en `stretch` y vaudrait de toute façon `auto`.

## Règles de validation

Ces règles sont exactement celles de `validateResponsive`. Un placement qui les viole ne doit jamais être écrit.

- ❌ `col` hors `1..12` ✅ `col` ∈ `1..12`
- ❌ `offset` hors `0..11` ✅ `offset` ∈ `0..11`
- ❌ `offset + col > 12` ✅ `offset + col ≤ 12`
- ❌ `colStart` hors `1..12`
- ❌ `row < 1` ❌ `rowSpan < 1`
- ❌ `width` ∉ `auto | <dip>` (le `vh` y est interdit : une fraction de hauteur de viewport ne dit rien d'une largeur)
- ❌ `height` ∉ `auto | <dip> | <n>vh | fill | stretch`
- ❌ `minHeight`/`maxHeight` ∉ `<dip> | <n>vh` (l'`auto` y est interdit)

## Forme de stockage

`proposal.responsive` est un objet clé = palier :

```json
"responsive": { "xs": { "col": 12 }, "sm": { "col": 6 }, "md": { "col": 4, "offset": 1 } }
```

C'est du JSON écrit directement dans le fichier du contrôle ; l'extension le sérialise en `<Responsive><At bp="..."/></Responsive>` à la synchro. La présence d'un placement fait passer `proposal.modelVersion` à `2`.
