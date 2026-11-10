# Référence des éléments, sections, tokens et formats

> Ceci reflète `resources/mobile/report-elements.json`, exposé via l'outil MCP `get_report_element_reference`. Ce fichier peut dériver avec le temps — **appeler l'outil MCP pour la version machine-readable et toujours à jour** avant de composer un XML complexe ou en cas de doute sur un enum.

Toutes les géométries (`left`, `top`, `width`, `height`) sont en **points** (pas des pixels). Toutes les couleurs sont des entiers **signés** 32 bits (ARGB packé), jamais une chaîne hexadécimale.

---

## Types d'éléments (`<Element type="...">`)

Chaque élément a une géométrie `left/top/width/height` en attributs, et ses propriétés en **enfants texte** (pas en attributs), sauf `<Font fontFamily="..." size="...">` qui garde ses deux attrs.

### Texte

Étiquette liée à un champ, texte statique, ou les deux (le rendu privilégie `<Texte>` sur `<Champ>` pour l'affichage).

| Enfant | Signification |
|---|---|
| `Champ` | colonne/alias lié du SELECT de la section, ou un token `lng:`/`msk:`/`%...%` |
| `Texte` | texte statique, peut embarquer `<lng>KEY</lng>`, `<msk>EXPR</msk>`, ou les tokens `%current_page%`/`%total_pages%` |
| `Font` | attrs `fontFamily`, `size`, enfant optionnel `<Bold />` |
| `ContentAlignment` | alignement du texte dans la boîte — enum : `TopLeft` `TopCenter` `TopRight` `MiddleLeft` `MiddleCenter` `MiddleRight` `BottomLeft` `BottomCenter` `BottomRight` |
| `ForeColor` | couleur du texte (ARGB signé) |
| `BackColor` | couleur de fond (ARGB signé) |
| `FormatNombre` | format numérique .NET, ou référence `@nomDeMasque` |
| `FormatDate` | format de date .NET (ex. `"d"`, `"dd/MM/yyyy"`) |
| `FormatText` | masque/format texte libre (pas d'enum fixe) |
| `FormatCasse` | conversion de casse (insensible à la casse) — enum : `None` `MAJUSCULE` `minuscule` `Phrase` `Mot` ; `None` vaut « pas de conversion » mais le designer omet le tag plutôt que de l'écrire |
| `TailleAutoV` | flag de présence : hauteur automatique |
| `TailleAutoH` | flag de présence : largeur automatique |

### Image

Image liée (ex. colonne BLOB/image de report). Pas de source statique dans le designer — toujours liée à un champ.

| Enfant | Signification |
|---|---|
| `Champ` | colonne/alias lié contenant les données image |

### Forme

Forme géométrique (rectangle/ellipse/rectangle arrondi) avec bordure et remplissage.

| Enfant | Signification |
|---|---|
| `Forme` | genre de forme — enum : `Rectangle` `Ellipse` `RoundedRectangle` |
| `PenColor` | couleur de bordure (ARGB signé) |
| `PenWidth` | épaisseur de bordure en points |
| `FillingColor` | couleur de remplissage (ARGB signé) |
| `Roundness` | rayon d'arrondi en points (uniquement `RoundedRectangle`) |

### Ligne

Ligne droite (horizontale si `width >= height`, verticale sinon).

| Enfant | Signification |
|---|---|
| `PenColor` | couleur de la ligne (ARGB signé) |
| `PenWidth` | épaisseur en points |

### Check

Case à cocher liée à un booléen, rendue comme une forme avec couleurs et marques distinctes vrai/faux.

| Enfant | Signification |
|---|---|
| `Forme` | genre de forme — enum : `Rectangle` `Ellipse` `RoundedRectangle` |
| `Champ` | colonne/alias booléen lié |
| `TexteTrue` | marque/texte affiché quand la valeur liée est vraie |
| `TexteFalse` | marque/texte affiché quand la valeur liée est fausse |
| `PenColor` | couleur de bordure (ARGB signé) |
| `FillingColorTrue` | couleur de remplissage quand vrai (ARGB signé) |
| `FillingColorFalse` | couleur de remplissage quand faux (ARGB signé) |
| `Roundness` | rayon d'arrondi en points (uniquement `RoundedRectangle`) |

### BarCode

Code-barres/2D, lié à un champ ou à une valeur statique. QRCode et PDF417 ont des tags supplémentaires spécifiques.

| Enfant | Signification |
|---|---|
| `BarCodeType` | symbologie — enum : `EAN13` `QRCode` `PDF417` `CODE39` `CODE93` `CODE128` `ITF` `CODABAR` `DataMatrix` |
| `Champ` | colonne/alias lié contenant la valeur encodée |
| `Texte` | valeur statique encodée (utilisée si `Champ` est absent) |
| `QRCodeVersion` | version QR Code (QRCode uniquement) |
| `QRCodeEncoding` | mode d'encodage QR Code (QRCode uniquement) |
| `QRCodeErrorCorrect` | niveau de correction d'erreur QR Code (QRCode uniquement) |
| `PDF417Lines` | nombre de lignes PDF417 (PDF417 uniquement) |
| `PDF417Columns` | nombre de colonnes PDF417 (PDF417 uniquement) |
| `PDF417ErrorCorrect` | niveau de correction d'erreur PDF417 (PDF417 uniquement) |

### Chart

Graphique à parité designer partielle (édition basique uniquement). Les données de série (requête + champs d'axes) vivent deux niveaux plus bas, sous `<Series><Data>`.

| Enfant | Signification |
|---|---|
| `ChartType` | genre de graphique — enum (insensible à la casse) : `Line` `Histogram` |
| `BackColor` | couleur de fond du graphique (ARGB signé) |
| `Lines` | style des lignes de grille — attrs `horizontal`/`vertical`, enum (insensible à la casse) : `none` `dotted` `solid` ; attr `color` (ARGB signé) |
| `Legend` | légende du graphique — attrs `xAxis`/`yAxis` (libellés d'axes, texte libre) |
| `Series` | conteneur des séries de données, enfant `Data` |
| `Series.Data` | élément imbriqué `<Series><Data>` portant la requête de série et les attrs `xValueFieldName`/`yValueFieldName` |

---

## Types de sections (`<Section type="...">`)

Toutes les sections partagent les mêmes attributs et flags.

**Attributs communs :** `name`, `type`, `height`, `visible`, `requete` (le SELECT de la section), `champGroup` (colonne de regroupement pour `GroupHeader`/`GroupFooter`), `visiblePage`.

**Flags communs (présence = vrai) :** `nouvellePageAvant`, `nouvellePageApres`, `basDePage`, `hauteurFixe`, `pasSurLaPremierePage`, `pasSurLaDernierePage`.

| Type | Rôle |
|---|---|
| `ReportHeader` | imprimé une seule fois, au tout début du report |
| `ReportFooter` | imprimé une seule fois, à la toute fin du report |
| `PageHeader` | imprimé en haut de chaque page |
| `PageFooter` | imprimé en bas de chaque page |
| `GroupHeader` | imprimé une fois avant chaque groupe de lignes, regroupé par `champGroup` |
| `GroupFooter` | imprimé une fois après chaque groupe de lignes, regroupé par `champGroup` |
| `Detail` | répété une fois par ligne renvoyée par le SELECT (`requete`) de la section |
| `TotalHeader` | imprimé une fois avant le contenu d'agrégats/résumé (totaux), analogue à `ReportHeader` |
| `TotalFooter` | imprimé une fois après le contenu d'agrégats/résumé (totaux), analogue à `ReportFooter` |

---

## Tokens de texte

| Token | Signification |
|---|---|
| `<lng>KEY</lng>` | lookup de traduction par clé, embarqué dans une chaîne statique `<Texte>` |
| `<msk>EXPR</msk>` | token de masque/expression, embarqué dans une chaîne statique `<Texte>` |
| `%current_page%` | numéro de page courante à l'impression |
| `%total_pages%` | nombre total de pages à l'impression |
| `'lng:alias:column'` | convention d'alias de colonne SELECT liant une clé de traduction à une colonne de données (vu dans le SQL `requete` d'une section, ex. `cic.translationKey AS 'lng:country:countryLabel'`) |

---

## Formats

| Tag | Valeurs |
|---|---|
| `FormatDate` | `d`, `D`, `dd/MM/yyyy`, ou tout format de date .NET |
| `FormatNombre` | `@nomDeMasque` (référence à un masque) ou une chaîne de format numérique .NET (ex. `0.00`) |
| `FormatText` | format/masque texte libre, pas d'enum fixe |
| `FormatCasse` | `None` `MAJUSCULE` `minuscule` `Phrase` `Mot` |

---

## Attributs de `<Etat>` (racine)

| Attribut | Signification |
|---|---|
| `table` | table principale du report |
| `margeLeft`/`margeTop`/`margeRight`/`margeBottom` | marges de page en points |
| `format` | `A4` `A3` `A5` `B5` `Legal` `Letter` `Custom` |
| `customLargeur`/`customHauteur` | dimensions personnalisées, uniquement si `format="Custom"` |
| `onePageReport` | flag de présence/`"true"` : forcer le report sur une seule page, omis si faux |
| `impressionViaPDF` | flag de présence/`"true"` : impression via PDF, omis si faux |
| `imageDPI` | entier positif ; omis (pas zéro) si non défini |

**Enfants de `<Etat>` :** `<Grille grilleLargeur="..." grilleHauteur="..." />` (pas d'accroche en points), `<GlobalFont fontFamily="..." size="..." />` (police par défaut du report), `<DefautParams>` (laissé tel quel par le designer, round-trippé sans édition — ne pas y toucher).

---

## `{code}.json` — propriétés DB du report

Fichier sibling du `.report.xml`, catégorie `dbProps` de `get_report_element_reference`.

| Champ | Type |
|---|---|
| `label` | `string` |
| `reportType` | `string \| null` |
| `isDefault` | `boolean` |
| `exportValue` | `number \| null` |
| `externalDocCode` | `string \| null` |
| `stub` | `string \| null` |
| `archiveMode` | `number \| null` |
| `archiveVersionsNumber` | `number \| null` |
| `translationKey` | `string \| null` |

Aucun champ `code` ni `_id` : le code est inféré du nom de fichier, comme pour les autres artefacts mobiles.
