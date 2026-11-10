# Le conteneur `Card`

Une Card est une surface qui regroupe d'autres contrôles dans la grille fluide. Elle n'existe que
sur un onglet fluide : `_tab.json` doit porter `"screenMode": "fluid"`.

## Une Card ne déclare pas ses enfants

C'est l'**enfant qui désigne sa Card**, dans son propre `proposal`, via le champ `parent`. La Card
et ses enfants sont des contrôles **frères** du même onglet — seul le `proposal` les relie. C'est
volontaire : les scripts continuent d'adresser un contrôle dans une Card exactement comme s'il
était à la racine (`CONTROL_SET_VALUE("TXT_NOM", …)`).

`parent` vaut le **`label`** de la Card, pas son code. La comparaison est insensible à la casse.

## Le breakpoint d'un enfant vient de la largeur de la Card, pas de l'onglet

Le moteur mobile résout chaque `ResponsiveGridLayout` à partir de la largeur **qui lui est
allouée**, pas de la largeur de l'écran : c'est une *container query*, pas une *viewport
query*. La grille de l'onglet résout SON breakpoint depuis la largeur de l'appareil ; la
grille interne d'une Card résout LE SIEN depuis la largeur de sa propre cellule. Les deux
peuvent diverger — et divergent dès qu'une Card n'occupe pas toute la largeur de l'onglet.

Exemple chiffré (grille à 12 colonnes, gouttière 16, marges de l'onglet 16 en haut et en bas et 48
sur les côtés à partir de 600, marge de la Card 24 sur les côtés — les constantes réelles du runtime) :

- Appareil de 1280 dip, une Card à `col: 6`, deux enfants à `{ xs: { col: 12 }, lg: { col: 6 } }`.
- Breakpoint de l'onglet sur 1280 − 2×16 = 1248 → `lg`.
- Les cellules sont posées sur 1280 − 2×48 = 1184 : une colonne = (1184 − 16×11) / 12 = 84.
- Cellule de la Card (6 colonnes) = 6×84 + 5×16 = 584.
- Grille de la Card = 584 − 2×24 = 536 → breakpoint `xs` (celui de la Card), **pas** `lg`.
- À `xs`, les enfants prennent leur valeur `xs` : `col: 12` → ils
  **s'empilent** sur l'appareil, alors qu'un aperçu qui prendrait le breakpoint de l'onglet
  les afficherait à tort côte à côte (`col: 6`).

**Une Card ne rend donc jamais un breakpoint plus grand que celui de l'onglet, et souvent
plus petit** : plus le `col` de la Card est réduit, plus sa cellule est étroite, plus tôt
elle retombe sur un breakpoint inférieur. Un enfant à l'intérieur d'une Card ne doit donc
jamais présumer qu'il verra le même breakpoint que l'onglet.

## Forme JSON

La Card :

```json
{
  "label": "CARD_CLIENT",
  "component": "Card",
  "orderNumber": 10,
  "proposal": {
    "controlType": "Card",
    "modelVersion": 2,
      "responsive": { "xs": { "col": 12 }, "lg": { "col": 6 } }
  }
}
```

Un enfant :

```json
{
  "label": "TXT_NOM",
  "component": "TextBox",
  "orderNumber": 20,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 2,
    "parent": "CARD_CLIENT",
      "responsive": { "xs": { "col": 12 }, "lg": { "col": 6 } }
  }
}
```

## Titre et en-tête

La Card peut afficher une ligne d'en-tête au-dessus de sa grille : un titre à gauche (gras),
et à droite les enfants placés en en-tête, dans l'ordre des contrôles, à leur largeur naturelle sauf `width` explicite.

- Titre : `proposal.common.title`, un texte libre où les balises `[#…#]` sont permises. On peut aussi
  utiliser `proposal.common.languageKey`, qui l'emporte. Si les deux sont vides, il n'y a pas de titre.
- Titre à l'exécution : `CONTROL_SET_VALUE("CARD_X", "…")` le change, `CONTROL_GET_VALUE("CARD_X")` le
  renvoie. Une valeur vide masque le titre. Un titre posé par script reste en place quand le formulaire
  se rafraîchit : ni `title` ni `languageKey` ne le remplacent.
- Enfant d'en-tête : `"parentSlot": "header"` à côté de `"parent"`.
- Taille d'un enfant d'en-tête : seuls `width`, `height`, `minHeight` et `maxHeight` de son `responsive`
  s'appliquent, au breakpoint de la Card. `width` n'accepte qu'une valeur en dip ; `height: "fill"` et `"stretch"` valent `auto`.

### Card bord à bord autour d'une carte

Une Card sans titre dont le seul enfant visible du corps est une `Maps` passe bord à bord : pas de
marge intérieure, la carte prend les coins arrondis de la Card. Les enfants masqués ne comptent pas.
Les enfants d'en-tête ne l'empêchent pas : ils sont posés par-dessus la carte, en haut. Un titre, lui,
garde la marge.

Cas de référence : une Card « Aujourd'hui », un lien « Voir l'agenda » en en-tête, une recherche dans le corps,
deux boutons côte à côte en bas.

```json
[
  { "label": "CARD_JOUR", "component": "Card", "orderNumber": 10,
    "proposal": { "controlType": "Card", "modelVersion": 2,
      "common": { "title": "Aujourd'hui" }, "responsive": { "xs": { "col": 12 } } } },
  { "label": "LBL_AGENDA", "component": "Label", "orderNumber": 20,
    "events": [{ "event": "Click", "scriptCode": "…" }],
    "proposal": { "controlType": "Label", "modelVersion": 2, "parent": "CARD_JOUR", "parentSlot": "header",
      "common": { "text": "Voir l'agenda" } } },
  { "label": "SRCH_CLIENT", "component": "UniSearch", "orderNumber": 30,
    "proposal": { "controlType": "UniSearch", "modelVersion": 2, "parent": "CARD_JOUR",
      "responsive": { "xs": { "col": 12 } } } },
  { "label": "BTN_TACHE", "component": "Button", "orderNumber": 40,
    "proposal": { "controlType": "Button", "modelVersion": 2, "parent": "CARD_JOUR",
      "common": { "text": "Nouvelle tâche" }, "responsive": { "xs": { "col": 6 } } } },
  { "label": "BTN_RDV", "component": "Button", "orderNumber": 50,
    "proposal": { "controlType": "Button", "modelVersion": 2, "parent": "CARD_JOUR",
      "common": { "text": "Nouveau rendez-vous" }, "responsive": { "xs": { "col": 6 } } } }
]
```

## MUST

- ✅ `"modelVersion": 2` sur la Card **et** sur chaque enfant. En dessous de 2, ni le placement ni
  le rattachement ne sont lus, et tout retombe à plat pleine largeur.
- ✅ `screenMode: "fluid"` sur l'onglet.
- ✅ Le `col` d'un enfant est relatif aux **12 colonnes de la Card**. Un `col: 6` dans une Card en
  `col: 6` occupe donc un quart de l'écran.
- ✅ Le **breakpoint** d'un enfant est résolu depuis la largeur de la Card, pas depuis celle de
  l'onglet (voir « Le breakpoint d'un enfant vient de la largeur de la Card » ci-dessus).
- ✅ L'ordre d'affichage vient de `orderNumber`, comme partout ailleurs.
- ✅ `parentSlot` vaut exactement `"header"`, en minuscules. Toute autre valeur laisse l'enfant dans la grille.

## MUST NOT

- ❌ Écrire `<Parent name="…"/>` à la main → ✅ écrire `proposal.parent` (l'extension sérialise).
- ❌ Une Card enfant d'une autre Card → rendue à la racine par l'app.
- ❌ Un `parent` qui ne correspond à aucune Card de l'onglet → l'enfant repart à la racine.
- ❌ Deux Cards de même `label` dans un onglet → la première prend tous les enfants ; les Cards
  perdantes ne sont pas rendues du tout.
- ❌ Deux contrôles de même `label` dans un onglet → le doublon n'est pas rendu du tout et reste
  invisible aux scripts et à la sauvegarde.
- ❌ Un placement (`col`, `offset`, `newRow`, `hidden`, `align`, `colStart`, `row`, `rowSpan`) sur un
  enfant d'en-tête → il est ignoré. ✅ N'y écrire que des tailles (`width`, `height`, `minHeight`, `maxHeight`).
- ❌ Un `parentSlot: "footer"` → il n'existe pas : placer les boutons de bas de Card en derniers enfants de la grille.
- ❌ Une Card sans enfant → bloc quasi vide, presque toujours une erreur de configuration.
- ❌ Donner une couleur de fond à la Card. Le Studio ne l'expose pas : la Card suit la couleur de
  surface du thème, donc le basculement clair/sombre. Une configuration sémantique viendra plus
  tard ; d'ici là, aucun attribut de couleur à écrire.

## Conseils (pas des interdictions)

- ⚠️ Poser une hauteur sur la Card n'est pas bloqué : la grille l'honore comme pour n'importe quel
  contrôle. Mais la Card ne défile pas et ne rogne pas : un contenu plus haut que la Card déborde
  par-dessus ce qui la suit. Le designer le signale (contour orange) ; `validate_responsive_layout`
  ne le voit pas. Laisser la Card se dimensionner sur son contenu reste la valeur par défaut recommandée.

Toutes ces règles sont remontées par l'outil MCP `validate_responsive_layout` (règles `card-*`).
