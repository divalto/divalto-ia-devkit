---
name: divalto-unisearch-creation
description: "Crée ou modifie un modèle UniSearch Divalto Weavy (liste de recherche mobile), au format `unisearchs/{code}.unisearchmodel.json`. Utiliser pour : créer une UniSearch, ajouter des colonnes ou des thèmes d'affichage, définir la requête SQL et les critères de recherche, configurer les variables exportées, la lier à un UniSearchControl."
argument-hint: "Décrivez la UniSearch (ex: grille des commandes clients avec colonnes date/montant/statut et critères date + statut...)"
capabilities: [mobile]
---

# Création d'un modèle UniSearch (format typé)

## Quand utiliser ce skill

- Créer une nouvelle UniSearch (liste ou grille de recherche mobile)
- Ajouter ou modifier des colonnes, lignes, thèmes d'affichage
- Définir ou modifier la requête SQL (`baseQuery`) et les critères de filtrage
- Configurer les variables exportées vers d'autres écrans
- Lier un contrôle `UniSearch` à un modèle via `proposal.config.xmlModel`

---

## Emplacement du fichier

Les modèles UniSearch vivent dans :

```
Mobile/
  unisearchs/                         ← dossier dédié, sibling de xmlmodels/
    commandesclient.unisearchmodel.json
    produits.unisearchmodel.json
    ...
```

**Convention de nommage :** le nom de fichier (sans extension) **est** le code du modèle, en minuscules. Il n'y a **pas** de champ `code` dans le fichier — le code est inféré du nom de fichier. Les codes sont insensibles à la casse côté serveur.

> **Surcharge active :** si une surcharge non-racine est active (`_project.json`), le code doit porter son préfixe (ex. `final_unisearchbasiclist`, pas `finalunisearchbasiclist`). Règle complète : [divalto-mobile-screen-creation](../divalto-mobile-screen-creation/SKILL.md), section « Surcharges (overloads) ».

**Lien avec un contrôle :** dans le fichier JSON du contrôle UniSearch, référencer le code inchangé :

```json
{
  "component": "UniSearch",
  "proposal": {
    "controlType": "UniSearchControl",
    "modelVersion": 1,
    "config": { "xmlModel": "CommandesClient", "displayTitle": false }
  }
}
```

> Format complet du fichier contrôle : skill `divalto-mobile-screen-creation`, [references/controls.md](../divalto-mobile-screen-creation/references/controls.md) (section « Contrôle UniSearch »).

---

## Structure du fichier

Le fichier a **deux champs obligatoires** et **trois sections** :

```
{
  "label": string,          ← libellé lisible (requis)
  "display": { ... },       ← section Affichage (requise)
  "query":   { ... },       ← section Requête (optionnelle mais presque toujours présente)
  "variable": { ... }       ← section Variables (optionnelle)
}
```

Le fichier est validé en temps réel dans VS Code (schéma JSON enregistré pour `**/unisearchs/*.unisearchmodel.json`) et s'ouvre dans l'éditeur dédié « UniSearch Editor ».

Schéma de référence : `resources/mobile/unisearchmodel.schema.json`

---

## Section `display` (requise)

Les attributs du singleton `Display` sont **inlinés** directement dans l'objet `display`. Les tableaux répétés (`columnDefinitions`, `lineDefinitions`, `lineThemes`) sont des propriétés de cet objet.

### Champs obligatoires (core)

| Champ | Type | Valeurs | Description |
|---|---|---|---|
| `displayCode` | `string\|null` | — | Code du display (null en pratique) |
| `displayName` | `string\|null` | — | Nom affiché dans le designer |
| `languageKey` | `string\|null` | — | Clé de traduction |
| `displayMode` | enum | `List` `Grid` `Thumbnails` `ButtonBar` `StudioPlayer` | Mode d'affichage |
| `selectionMode` | enum\|null | `Single` `Multiple` `None` | Mode de sélection |
| `hideHeader` | boolean | `true`/`false` | Masquer l'en-tête |
| `noResizableColumn` | boolean | `true`/`false` | Colonnes non redimensionnables |
| `fixedColumn` | number | entier | Nombre de colonnes figées (pas un booléen) |
| `rowHeight` | number | — | Hauteur de ligne (0 = auto) |
| `displayOnly` | boolean | `true`/`false` | Lecture seule |
| `automaticQueryExecution` | boolean | `true`/`false` | Exécution automatique |
| `queryExecutionInterval` | number | entier | Intervalle de rafraichissement (0 = désactivé) |
| `resultLimitCount` | number | entier | Limite de résultats (0 = illimité) |
| `canStopQuery` | boolean | `true`/`false` | Peut stopper la requête |
| `isDynamicGrid` | boolean | `true`/`false` | Grille dynamique |
| `hideSearch` | boolean | `true`/`false` | Masquer la zone de recherche |
| `hideVerticalSeparators` | boolean | `true`/`false` | Masquer les séparateurs verticaux |
| `simpleSearchMinimumTextLength` | number | entier | Longueur min. pour la recherche simple |
| `columnDefinitions` | array | — | Colonnes de la grille |
| `lineDefinitions` | array | — | Définitions de lignes |
| `lineThemes` | array | — | Thèmes de lignes |

### Attributs optionnels (présents seulement si définis)

`badgeText`, `badgeFontName`, `badgeFontSize`, `dynamicColumnWidth`, `dynamicColumnFontSize`, `dynamicColumnFontSizeHeader`, `dynamicColumnAlignmentHeader` (`Left`|`Center`|`Right`|null).

Singletons imbriqués (rarement authoriés manuellement) : `studioPlayer` et `thumbnails`.

### `columnDefinitions[]` — champs obligatoires

Chaque colonne doit posséder tous ces champs (utiliser `null` pour les valeurs absentes de type `string|null`, `0` pour les numériques, `false` pour les booléens, `[]` pour `columnThemes`) :

`columnNumber` (number), `fieldName` (string|null), `columnWidth` (number), `grouped` (boolean), `useDisplayOptionOnGroupLine` (boolean), `dontFoldOnClick` (boolean), `allowFolding` (boolean), `folded` (boolean), `isDynamicColumn` (boolean), `columnName` (string|null), `languageKey` (string|null), `alignmentHeader` (`Left`|`Center`|`Right`|null), `fontNameHeader` (string|null), `fontSizeHeader` (number), `aggregation` (string|null), `displayMaskSubHeader` (string|null), `alignmentSubHeader` (`Left`|`Center`|`Right`|null), `fontNameSubHeader` (string|null), `fontSizeSubHeader` (number), `textColor` (string|null), `displayMask` (string|null — **toujours une chaîne**, même si tout-numérique ex: `"0"`), `alignment` (`Left`|`Center`|`Right`|`Automatic`|null), `fontName` (string|null), `fontSize` (number), `dataBarColor` (string|null), `dataBarMinType` (`Automatic`|`LowerValue`|`Number`|null), `dataBarMaxType` (`Automatic`|`UpperValue`|`Number`|null), `dataBarMinValue` (number), `dataBarMaxValue` (number), `columnThemes` (array).

`id` est **optionnel** — l'omettre lors d'une création ; l'éditeur l'assigne automatiquement.

Champ optionnel `columnWidthType` (`dip`|`auto`|`star`) : l'omettre pour une largeur en pixels. `auto` = largeur du contenu, `star` = espace restant (plusieurs colonnes `star` se le partagent, sans poids). `columnWidth` reste **toujours un entier** non nul (120 par défaut) : les anciens players ne lisent que lui. Masquer une colonne = `columnWidth: 0` sans `columnWidthType`.

❌ `"columnWidth": "*"` / `"auto"` — le player les lit comme 0 (colonne masquée).
✅ `"columnWidth": 120, "columnWidthType": "star"`

---

## Section `query` (optionnelle)

Les attributs du singleton `Query` sont **inlinés** dans l'objet `query`.

### Champs obligatoires (core)

| Champ | Type | Description |
|---|---|---|
| `queryCode` | `string\|null` | Code de la requête (null en pratique) |
| `queryName` | `string\|null` | Nom lisible |
| `queryMode` | enum `auto`\|`manual` | Mode d'exécution |
| `entityName` | `string\|null` | Entité de données |
| `baseQuery` | `string\|null` | Requête SQL. `[WHERE]` marque l'injection des critères actifs. Variables d'autres écrans : `<var>nom\|Groupe</var>` |
| `criteria` | array | Critères de filtrage (voir ci-dessous) |
| `fields` | array | Champs Studio (généralement `[]` pour le mobile) |

### `criteria[]` — champs obligatoires

Le critère est **aplati** (anciennement `Criteria > Header` — le niveau `Criteria` est supprimé, le `Header` est le critère) :

| Champ | Type | Valeurs |
|---|---|---|
| `criteriaCode` | `string\|null` | Code (toujours une chaîne, même si numérique ex: `"1"`) |
| `criteriaName` | `string\|null` | Libellé |
| `languageKey` | `string\|null` | Clé de traduction |
| `criteriaType` | enum | `field` `custom` |
| `fieldName` | `string\|null` | Colonne SQL |
| `fieldDataType` | enum | `Integer` `Double` `DateTime` `Bool` `Varchar` `Text` `Blob` |
| `operatorType` | enum\|null | `=` `!=` `=%` `%=` `%=%` `<` `>` `<=` `>=` `IS NULL` `IS NOT NULL` |
| `defaultFilterValue` | `string\|null` | Valeur par défaut (toujours chaîne) |
| `inputControlType` | enum | `Button` `CheckBox` `ComboBox` `DateTimePicker` `Label` `NumericUpDown` `PictureBox` `RadioButton` `Signature` `TextBox` `TextBoxMultiline` |
| `customQuery` | `string\|null` | Requête SQL personnalisée (type `custom`) |
| `isMainCriteria` | boolean | Critère principal |
| `isMultiCriteria` | boolean | Multi-valeurs |
| `isActiveByDefault` | boolean | Actif par défaut |
| `isSelectionByList` | boolean | Sélection par liste |
| `selectionByListQuery` | `string\|null` | Requête SQL de la liste de valeurs |
| `selectionItems` | array | Items statiques de la liste |

---

## Section `variable` (optionnelle)

### Champs obligatoires (core)

| Champ | Type | Description |
|---|---|---|
| `variableCode` | `string\|null` | Code (null en pratique) |
| `variableName` | `string\|null` | Nom lisible |
| `definitions` | array | Variables exportées |

### `definitions[]` — champs obligatoires

`fieldName` (string|null), `translatorDefinition` (string|null), `variableName` (string|null), `groupName` (string|null — ex: `"usOrders"`), `environment` (string|null).

---

## Règles de typage importantes

- **Booléens** : toujours `true`/`false`, jamais `0`/`1`.
- **Champs mixtes** (peuvent être numériques en apparence) → **toujours des chaînes** : `backgroundColor`, `activationValue`, `displayMask`, `displayMaskSubHeader`, `criteriaCode`, `listItemCode`, `defaultFilterValue`.
- **Champs numériques** qui valent 0/1 mais ne sont PAS des booléens : `columnNumber`, `fixedColumn`, `dataBarMinValue`, `dataBarMaxValue`, `queryExecutionInterval`, `resultLimitCount`.
- **`id` sur les items de tableau** : optionnel — **omettre** lors d'une création manuelle/IA, l'éditeur et le codec l'assignent automatiquement.
- **Enums fermés** : respecter exactement les valeurs listées ci-dessus (la casse compte).

> Si le skill `divalto-semantic-theme` est disponible (projet mobile v7), les couleurs des colonnes
> et des modèles acceptent un token du thème à la place d'un hex, et `fontName` / `fontSize` ne
> sont plus lus : le suivre avant d'écrire une couleur ou une police.

---

## Workflow

1. **Partir du squelette minimal** (miroir de `createDefaultUniSearch`) :
   ```json
   {
     "label": "...",
     "display": {
       "displayCode": null, "displayName": null, "languageKey": null,
       "displayMode": "List", "selectionMode": "Single",
       "hideHeader": false, "noResizableColumn": false, "fixedColumn": 0, "rowHeight": 0,
       "displayOnly": false, "automaticQueryExecution": false, "queryExecutionInterval": 0,
       "resultLimitCount": 0, "canStopQuery": false, "isDynamicGrid": false,
       "hideSearch": false, "hideVerticalSeparators": false, "simpleSearchMinimumTextLength": 0,
       "lineDefinitions": [], "lineThemes": [], "columnDefinitions": []
     },
     "query": {
       "queryCode": null, "queryName": null, "queryMode": "auto", "entityName": null,
       "baseQuery": null, "criteria": [], "fields": []
     },
     "variable": { "variableCode": null, "variableName": null, "definitions": [] }
   }
   ```

2. **Ajouter les colonnes** dans `display.columnDefinitions` — tous les champs obligatoires, `id` omis.

3. **Ajouter les critères** dans `query.criteria` — `id` omis, `criteriaCode` en chaîne.

4. **Ajouter les variables** dans `variable.definitions` — `id` omis.

5. **Valider** contre `resources/mobile/unisearchmodel.schema.json` avant d'écrire le fichier.

6. **Nommer le fichier** : `Mobile/unisearchs/{code}.unisearchmodel.json` (code en minuscules).

---

## Exemple complet et valide

Grille des commandes clients avec 2 colonnes, 1 critère et 2 variables exportées.
Fichier : `Mobile/unisearchs/commandesclient.unisearchmodel.json`

```json
{
  "label": "Commandes clients",
  "display": {
    "displayCode": null,
    "displayName": "Commandes / Clients",
    "languageKey": "Gen_Orders",
    "displayMode": "Grid",
    "selectionMode": "Single",
    "hideHeader": false,
    "noResizableColumn": false,
    "fixedColumn": 0,
    "rowHeight": 0,
    "displayOnly": false,
    "automaticQueryExecution": false,
    "queryExecutionInterval": 0,
    "resultLimitCount": 0,
    "canStopQuery": false,
    "isDynamicGrid": false,
    "hideSearch": false,
    "hideVerticalSeparators": false,
    "simpleSearchMinimumTextLength": 0,
    "lineDefinitions": [],
    "lineThemes": [],
    "columnDefinitions": [
      {
        "columnNumber": 0,
        "fieldName": "orderDate",
        "columnWidth": 120,
        "grouped": false,
        "useDisplayOptionOnGroupLine": false,
        "dontFoldOnClick": false,
        "allowFolding": false,
        "folded": false,
        "isDynamicColumn": false,
        "columnName": "Date",
        "languageKey": null,
        "alignmentHeader": null,
        "fontNameHeader": null,
        "fontSizeHeader": 0,
        "aggregation": null,
        "displayMaskSubHeader": null,
        "alignmentSubHeader": null,
        "fontNameSubHeader": null,
        "fontSizeSubHeader": 0,
        "textColor": null,
        "displayMask": null,
        "alignment": "Left",
        "fontName": null,
        "fontSize": 0,
        "dataBarColor": null,
        "dataBarMinType": null,
        "dataBarMaxType": null,
        "dataBarMinValue": 0,
        "dataBarMaxValue": 0,
        "columnThemes": []
      },
      {
        "columnNumber": 1,
        "fieldName": "totalAmount",
        "columnWidth": 100,
        "grouped": false,
        "useDisplayOptionOnGroupLine": false,
        "dontFoldOnClick": false,
        "allowFolding": false,
        "folded": false,
        "isDynamicColumn": false,
        "columnName": "Montant",
        "languageKey": null,
        "alignmentHeader": "Right",
        "fontNameHeader": null,
        "fontSizeHeader": 0,
        "aggregation": null,
        "displayMaskSubHeader": null,
        "alignmentSubHeader": null,
        "fontNameSubHeader": null,
        "fontSizeSubHeader": 0,
        "textColor": null,
        "displayMask": "#,##0.00",
        "alignment": "Right",
        "fontName": null,
        "fontSize": 0,
        "dataBarColor": null,
        "dataBarMinType": null,
        "dataBarMaxType": null,
        "dataBarMinValue": 0,
        "dataBarMaxValue": 0,
        "columnThemes": []
      }
    ]
  },
  "query": {
    "queryCode": null,
    "queryName": null,
    "queryMode": "manual",
    "entityName": null,
    "baseQuery": "SELECT o.order_ID, o.orderDate, o.totalAmount, o.status FROM sw_data_order o [WHERE] 1=1 ORDER BY o.orderDate DESC",
    "criteria": [
      {
        "criteriaCode": "1",
        "criteriaName": "Statut",
        "languageKey": null,
        "criteriaType": "field",
        "fieldName": "o.status",
        "fieldDataType": "Varchar",
        "operatorType": "=",
        "defaultFilterValue": null,
        "inputControlType": "TextBox",
        "customQuery": null,
        "isMainCriteria": false,
        "isMultiCriteria": false,
        "isActiveByDefault": false,
        "isSelectionByList": false,
        "selectionByListQuery": null,
        "selectionItems": []
      }
    ],
    "fields": []
  },
  "variable": {
    "variableCode": null,
    "variableName": null,
    "definitions": [
      {
        "fieldName": "order_ID",
        "translatorDefinition": null,
        "variableName": "order_ID",
        "groupName": "usOrders",
        "environment": null
      },
      {
        "fieldName": "status",
        "translatorDefinition": null,
        "variableName": "orderStatus",
        "groupName": "usOrders",
        "environment": null
      }
    ]
  }
}
```

> Cet exemple a été validé contre `resources/mobile/unisearchmodel.schema.json` (ajv, Draft 2020-12) — résultat : **VALID**.

---

## Points de vigilance fréquents

- Ne **jamais** inclure `code`, `dataType`, `_root`, `_element`, `modelVersion` — ces champs n'existent pas dans le nouveau format.
- Ne **jamais** utiliser la structure `elements: [{ _element: "...", ... }]` — c'est l'ancien format (`xmlmodels/`), désormais obsolète pour les UniSearch.
- `displayMask: "0"` → chaîne, pas nombre. `backgroundColor: "8000"` → chaîne, pas nombre.
- `criteriaCode: "1"` → chaîne, pas nombre.
- Les critères sont **directement** dans `query.criteria[]` — il n'y a plus de niveau `Criteria > Header` imbriqué.
