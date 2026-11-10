# Reference des controles UI mobiles Divalto Weavy

> **Decouvrir les controles disponibles** : utiliser l'outil MCP `get_mobile_control_reference` pour obtenir la liste des controles, leurs proprietes config, evenements et children.
>
> - Sans params : vue d'ensemble (categories, positionnement)
> - `controlName="Chart"` : definition complete d'un controle
> - `category="Input"` : tous les controles d'une categorie
>
> **Projet mobile v7 — seulement si le skill nommé est disponible** : couleurs et typographie →
> `divalto-semantic-theme` ; icône sur un contrôle → `divalto-fontawesome-icons` ; bloc visuel
> (`Card`) ou disposition fluide → `divalto-mobile-fluid-layout`.

---

## Structure commune a tous les controles

Chaque control est un fichier JSON individuel dans le dossier `controls/` du tab. Le nom du fichier = le code du control.

```json
{
  "label": "prefixeNom",
  "component": "ComponentType",
  "position": { "left": 0, "top": 0, "width": 0, "height": 0 },
  "anchor": "Top, Left",
  "orderNumber": 0,
  "binding": { "metaColumnCode": null, "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "ComponentType",
    "modelVersion": 1,
    "common": {},
    "config": {}
  },
  "events": []
}
```

### Elements enfants du proposal

Certains controles portent des elements enfants (les series d'un graphique, les onglets d'un
calendrier, les elements d'une liste deroulante). Dans le fichier, **chaque element vit dans un
tableau nomme et type**, jamais dans un sac generique. Le nom de ce tableau est le champ `property`
que renvoie `get_mobile_control_reference` a cote de `element` :

| `element` (XML) | `property` (fichier) |
| --------------- | -------------------- |
| `Serie`         | `series`             |
| `Category`      | `category`           |
| `TabItem`       | `tabs`               |
| `SelectionByListItem` | `selectionItems` |

```json
"proposal": {
  "controlType": "Chart",
  "modelVersion": 1,
  "config": { "sqlQuery": "SELECT ...", "autoLoad": true },
  "series": [
    { "serieCode": "ca", "serieName": "CA", "chartType": "Bar", "columnNameY": "montant" },
    { "serieCode": "marge", "serieName": "Marge", "chartType": "Line", "columnNameY": "marge" }
  ]
}
```

Deux regles qui evitent les erreurs les plus couteuses :

- **L'ordre du tableau porte l'ordre des elements.** L'attribut de position (`order`, `id`,
  `lineNumber`) est reecrit depuis l'index a la synchro : ne pas l'ecrire dans le fichier.
- **Un element que la plateforme ne declare pas** (par exemple `Responsive`) se met dans
  `children[]`, et chaque entree porte son nom de balise dans `_element` — **avec le souligne**.
  Sans lui, la synchro pousse `<undefined ...>` en base. En cas de doute, verifier le fichier avec
  `validate_divalto_file({ type: "control", content })`.

### Champs importants

| Champ                    | Role                                                                                                                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `label`                  | **Aide du designer uniquement** — affiche dans le designer visual pour identifier le control. N'est PAS le texte affiche a l'ecran.                                                                |
| `proposal.text`          | **Texte affiche a l'ecran** pour les composants Label et Button. C'est ce champ qui contient le texte visible par l'utilisateur. Peut contenir du SQL inline : `"<sql>SELECT name FROM ...</sql>"` |
| `binding.metaColumnCode` | Code de la colonne pour le data binding (pas un ID numerique)                                                                                                                                      |
| `events[].scriptCode`    | Code du script lie a l'evenement (pas un ID numerique)                                                                                                                                             |

> **Erreur courante** : mettre le texte dans `label` au lieu de `proposal.text`. Le `label` ne s'affiche que dans le designer, pas a l'execution mobile. Pour un Label ou un Button, toujours renseigner `proposal.text`.

### Activation conditionnelle

```json
"activation": {
  "metaColumnId": 32,
  "operator": "IS NULL" | "IS NOT NULL" | "=" | "!=",
  "value": null | "valeur"
}
```

### Convention de nommage des controles

| Prefixe | Type             | Exemple          |
| ------- | ---------------- | ---------------- |
| `lb`    | Label            | `lbCustomerName` |
| `tb`    | TextBox          | `tbName`         |
| `tbm`   | TextBoxMultiline | `tbmDescription` |
| `cb`    | ComboBox         | `cbStatus`       |
| `chk`   | CheckBox         | `chkActive`      |
| `nud`   | NumericUpDown    | `nudQuantity`    |
| `dtp`   | DateTimePicker   | `dtpStartDate`   |
| `bt`    | Button           | `btSave`         |
| `us`    | UniSearch        | `usCustomers`    |
| `sn`    | ShellNode        | `snDetails`      |
| `tr`    | Tree             | `trCategories`   |
| `map`   | Maps             | `mapCustomers`   |
| `cal`   | Calendar         | `calPlanning`    |
| `cht`   | Chart            | `chtRevenue`     |
| `pb`    | PictureBox       | `pbPhoto`        |
| `ie`    | ImageEditor      | `ieCapture`      |
| `sig`   | Signature        | `sigValidation`  |
| `wb`    | WebBrowser       | `wbContent`      |
| `rtb`   | RichTextBox      | `rtbNotes`       |

### Evenements de script

Les evenements connectent un controle a un script SwingScript. **Un seul script par evenement par controle** (regle stricte).

#### Convention de nommage

- Code du ConfScriptControl (genere auto) : `{ControlCode}_{EventName}`
- Nom du fichier script : `form{screenCode}_{controlCode}_{event}.swing`
- Exemple : controle `CustomerDetails_btSave` + event `Click` → script `FormCustomer_btSave_Click` → fichier `formcustomer_btsave_click.swing`

#### Evenements disponibles par type de controle

Chaque controle ne supporte que certains evenements. Voici la liste exhaustive :

| Composant          | Evenements disponibles                                                                                     |
| ------------------ | ---------------------------------------------------------------------------------------------------------- |
| `Label`            | `TextChanged`, `Click`                                                                                     |
| `TextBox`          | `GotFocus`, `TextChanged`                                                                                  |
| `TextBoxMultiline` | `GotFocus`, `TextChanged`                                                                                  |
| `RichTextBox`      | `TextChanged`, `ImageInserted`                                                                             |
| `ComboBox`         | `GotFocus`, `SelectedIndexChanged`                                                                         |
| `CheckBox`         | `CheckStateChanged`                                                                                        |
| `NumericUpDown`    | `ValueChanged`, `GotFocus`                                                                                 |
| `DateTimePicker`   | `ValueChanged`, `GotFocus`                                                                                 |
| `Button`           | `Click`                                                                                                    |
| `Badge`            | `ValueChanged`                                                                                             |
| `BarcodeScanner`   | `ValueChanged`, `GotFocus`                                                                                 |
| `UniSearch`        | `ValueChanged`, `DoubleClick`, `GroupClick`, `MultiSelectionChanged`, `SingleDeleteClick`, `PullToRefresh` |
| `Tree`             | `ValueChanged`, `TreeViewSelectedNodeChanged`, `TreeViewDragAndDrop`                                       |
| `MultiSelect`      | `GotFocus`, `ValueChanged`                                                                                 |
| `Chart`            | `ValueChanged`, `DoubleClick`                                                                              |
| `Calendar`         | `DoubleClick`, `ValueChanged`, `SelectedDateChanged`, `SelectedTabChanged`                                 |
| `Maps`             | `AnnotationButtonClick`                                                                                    |
| `PictureBox`       | `ValueChanged`, `POIClick`, `Click`                                                                        |
| `ImageEditor`      | `ValueChanged`                                                                                             |
| `Signature`        | `ValueChanged`                                                                                             |
| `WebBrowser`       | `SubmitButtonClick`                                                                                        |
| `VideoPlayer`      | `PlaybackFinished`                                                                                         |
| `Timer`            | `Tick`                                                                                                     |
| `Gauge`            | _(aucun)_                                                                                                  |
| `ShellNode`        | _(aucun)_                                                                                                  |
| `Separator`        | _(aucun)_                                                                                                  |
| `FlowLayout`       | _(aucun)_                                                                                                  |
| `DynamicFields`    | _(aucun)_                                                                                                  |

#### Semantique des evenements principaux

| Evenement                     | Description                                                          |
| ----------------------------- | -------------------------------------------------------------------- |
| `Click`                       | L'utilisateur appuie sur le controle (Button, Label, PictureBox)     |
| `DoubleClick`                 | Double-tap (UniSearch, Calendar, Chart)                              |
| `ValueChanged`                | La valeur du controle change (saisie, selection, binding)            |
| `TextChanged`                 | Le texte affiché change (Label, TextBox)                             |
| `GotFocus`                    | Le controle recoit le focus (TextBox, ComboBox, NumericUpDown, etc.) |
| `CheckStateChanged`           | L'etat coche/decoche change (CheckBox)                               |
| `SelectedIndexChanged`        | L'index selectionne change (ComboBox)                                |
| `SelectedDateChanged`         | La date selectionnee change (Calendar)                               |
| `SelectedTabChanged`          | L'onglet selectionne change dans le Calendar                         |
| `Tick`                        | Le timer se declenche (Timer)                                        |
| `AnnotationButtonClick`       | Clic sur un marqueur de carte (Maps)                                 |
| `SubmitButtonClick`           | Clic sur le bouton submit du WebBrowser                              |
| `GroupClick`                  | Clic sur un groupe dans UniSearch                                    |
| `MultiSelectionChanged`       | La selection multiple change dans UniSearch                          |
| `SingleDeleteClick`           | Suppression d'un element dans UniSearch                              |
| `PullToRefresh`               | Geste pull-to-refresh dans UniSearch                                 |
| `TreeViewSelectedNodeChanged` | Changement de noeud selectionne dans Tree                            |
| `TreeViewDragAndDrop`         | Drag & drop dans Tree                                                |
| `LoadWillStart`               | Chargement sur le point de commencer (Layers)                        |
| `LoadDidFinish`               | Chargement termine (Layers)                                          |
| `LoadInterrupted`             | Chargement interrompu (Layers)                                       |
| `DidEndAnimation`             | Animation terminee (Layers)                                          |
| `DidScrollToLayer`            | Scroll vers un layer (Layers)                                        |
| `DidScrollToPosition`         | Scroll vers une position (Layers)                                    |
| `DidMakeGestureOnLayer`       | Geste sur un layer (Layers)                                          |
| `PlaybackFinished`            | Lecture video terminee (VideoPlayer)                                 |
| `ImageInserted`               | Image inseree dans RichTextBox                                       |
| `POIClick`                    | Clic sur un point d'interet (PictureBox)                             |

#### Format dans controls.json

```json
{
  "_entity": "confcontrol",
  "_id": null,
  "code": "CustomerDetails_btSave",
  "component": "Button",
  "events": [
    {
      "_id": null,
      "scriptId": null,
      "event": "Click"
    }
  ]
}
```

**Regles :**

- `_id` : toujours `null` pour un nouvel evenement (le serveur assigne l'ID)
- `scriptId` : l'ID du script (ConfScript_ID) ou `null` si pas encore connu
- `event` : le nom exact de l'evenement (respecter la casse du tableau ci-dessus)
- Un controle peut avoir **plusieurs evenements differents** mais **un seul script par evenement**

---

## Controle UniSearch (le composant le plus utilise)

Une UniSearch fonctionnelle = **deux fichiers**, jamais un seul :

1. **Le controle** (ce fichier-ci, dans `controls/`) — composant `UniSearch` qui pointe vers un modele par son **code**.
2. **Le modele** (`Mobile/unisearchs/{code}.unisearchmodel.json`) — colonnes, requete SQL, criteres, variables exportees. Sa creation est detaillee dans le skill **`divalto-unisearch-creation`** (NE PAS la dupliquer ici).

> **MUST** — creer (ou verifier l'existence de) le **modele** avant ou en meme temps que le controle. Un controle dont `config.xmlModel` pointe vers un code inexistant affiche une liste vide.

### Fichier controle

`controls/{tab}_us{Nom}.json` :

```json
{
  "label": "usCustomers",
  "component": "UniSearch",
  "position": { "left": 0, "top": 0, "width": 320, "height": 480 },
  "anchor": "Top, Bottom, Left, Right",
  "orderNumber": 0,
  "binding": { "metaColumnCode": null, "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "UniSearchControl",
    "modelVersion": 1,
    "common": {},
    "config": { "xmlModel": "Customers", "displayTitle": false }
  },
  "events": []
}
```

| Champ `config` | Type    | Role                                                                                                                                          |
| -------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `xmlModel`     | string  | **Code du modele** = nom du fichier `unisearchs/{code}.unisearchmodel.json` (sans extension, insensible a la casse). **PAS un ID numerique.**  |
| `displayTitle` | boolean | Afficher le titre de la liste. Defaut `false`. (Le numerique `0`/`1` est tolere par coercition, mais le booleen est la forme canonique.)       |

> **MUST NOT** — ne jamais ecrire d'ID numerique dans le fichier controle.
> ❌ `"config": { "xmlmodel_ID": 50000123, "displayTitle": false }`
> ✅ `"config": { "xmlModel": "Customers", "displayTitle": false }`
> L'extension resout le **code** vers l'`xmlmodel_ID` serveur au sync (via `_registry.json`). La reference MCP `get_mobile_control_reference` liste encore `xmlmodel_ID` (number) : c'est le **payload serveur**, pas le format fichier — l'ignorer pour l'edition de fichiers.

### Ancrage, taille, evenements

- **Ancrage** : une UniSearch remplit presque toujours sa zone → `anchor: "Top, Bottom, Left, Right"`. Taille par defaut `300 x 200`.
- **Evenements** : `ValueChanged`, `DoubleClick`, `GroupClick`, `MultiSelectionChanged`, `SingleDeleteClick`, `PullToRefresh` (voir le tableau des evenements plus haut). `DoubleClick` = ouvrir le detail de la ligne.
- **Runtime** : manipuler via les fonctions `UNISEARCH_*` et `SHELL_UNISEARCH_*` (groupe SwingScript `UniSearch`).

### Workflow de creation (resume)

1. Creer le **modele** `unisearchs/{code}.unisearchmodel.json` → skill **`divalto-unisearch-creation`**.
2. Creer le **controle** avec `config.xmlModel` = ce code.
3. (Optionnel) brancher les evenements utiles (ex: `DoubleClick` vers un script de navigation).
