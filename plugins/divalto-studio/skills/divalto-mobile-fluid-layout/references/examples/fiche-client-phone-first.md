# Fiche client phone-first : conversion en fluide avec expansion depuis xs

## Quand l'utiliser

Un onglet mobile a été conçu pour smartphone (design phone-first) avec des champs empilés pleine largeur, et on veut le rendre responsive pour qu'il exploite la largeur disponible sur tablette et desktop tout en restant fidèle au design d'origine sur téléphone.

## Composants

- `TextBox` — Nom, Prénom, Email, Téléphone
- `Button` — bouton d'enregistrement

## Fichiers

```text
Mobile/functions/customer/iphone/customersmartphone/details/
├── _tab.json
└── controls/
    ├── customerdetails_tbname.json
    ├── customerdetails_tbfirstname.json
    ├── customerdetails_tbemail.json
    ├── customerdetails_tbphone.json
    └── customerdetails_btsave.json
```

## JSON

### Contexte (avant conversion)

`_tab.json` déclare `width: 375` → l'ancre de conception est le palier **xs** (voir [references/breakpoint-heuristics.md](../breakpoint-heuristics.md#2-breakpoint-dancrage)). Les 5 contrôles sont empilés en positionnement absolu, dans l'ordre de lecture, chacun `width ≈ 359` — c'est-à-dire ≈ pleine largeur à 375px, soit `col ≈ 12` :

1. `tb_name` (Nom)
2. `tb_firstname` (Prénom)
3. `tb_email` (Email)
4. `tb_phone` (Téléphone)
5. `bt_save` (bouton Enregistrer)

### `_tab.json`

```json
{
  "label": "Details",
  "tabName": "Details",
  "translationKey": "Gen_Details",
  "screenMode": "fluid",
  "openByDefault": false,
  "visible": true,
  "orderNumber": 1,
  "width": 375,
  "height": 600,
  "autoScroll": true,
  "activationString": null
}
```

### `controls/customerdetails_tbname.json`

```json
{
  "label": "tbName",
  "component": "TextBox",
  "position": { "left": 8, "top": 16, "width": 359, "height": 32 },
  "anchor": "Top, Left, Right",
  "orderNumber": 0,
  "binding": { "metaColumnCode": "name", "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 2,
    "common": {},
    "config": { "keyboardType": "Default", "inlineEdition": false },
    "responsive": { "xs": { "col": 12 }, "sm": { "col": 6 } }
  },
  "events": []
}
```

### `controls/customerdetails_tbfirstname.json`

```json
{
  "label": "tbFirstname",
  "component": "TextBox",
  "position": { "left": 8, "top": 56, "width": 359, "height": 32 },
  "anchor": "Top, Left, Right",
  "orderNumber": 1,
  "binding": { "metaColumnCode": "firstname", "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 2,
    "common": {},
    "config": { "keyboardType": "Default", "inlineEdition": false },
    "responsive": { "xs": { "col": 12 }, "sm": { "col": 6 } }
  },
  "events": []
}
```

### `controls/customerdetails_tbemail.json`

```json
{
  "label": "tbEmail",
  "component": "TextBox",
  "position": { "left": 8, "top": 96, "width": 359, "height": 32 },
  "anchor": "Top, Left, Right",
  "orderNumber": 2,
  "binding": { "metaColumnCode": "email", "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 2,
    "common": {},
    "config": { "keyboardType": "EmailAddress", "inlineEdition": false },
    "responsive": { "xs": { "col": 12 }, "sm": { "col": 6 } }
  },
  "events": []
}
```

### `controls/customerdetails_tbphone.json`

```json
{
  "label": "tbPhone",
  "component": "TextBox",
  "position": { "left": 8, "top": 136, "width": 359, "height": 32 },
  "anchor": "Top, Left, Right",
  "orderNumber": 3,
  "binding": { "metaColumnCode": "phone", "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 2,
    "common": {},
    "config": { "keyboardType": "Phone", "inlineEdition": false },
    "responsive": { "xs": { "col": 12 }, "sm": { "col": 6 } }
  },
  "events": []
}
```

### `controls/customerdetails_btsave.json`

```json
{
  "label": "btSave",
  "component": "Button",
  "position": { "left": 8, "top": 176, "width": 359, "height": 44 },
  "anchor": "Top, Left, Right",
  "orderNumber": 4,
  "binding": { "metaColumnCode": null, "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "Button",
    "modelVersion": 2,
    "common": {},
    "config": {},
    "text": "Enregistrer",
    "responsive": { "xs": { "col": 12 }, "md": { "col": 6, "offset": 3 } }
  },
  "events": [{ "event": "Click", "scriptCode": "formcustomer_btsave_click" }]
}
```

### Lecture du reflow

- **`xs`** (téléphone) : tout est empilé pleine largeur — c'est le design tel qu'il a été dessiné.
- **`sm`** : les 4 champs texte passent à `col: 6`, donc 2 par ligne (Nom + Prénom, puis Email + Téléphone par wrap naturel — chaque ligne se remplit exactement à 12, donc aucun `newRow` n'est nécessaire). Le bouton reste `col: 12` (hérité de `xs`, pas de redéfinition à `sm`).
- **`md`** : le bouton passe à `col: 6, offset: 3` et se centre (`offset + col = 3 + 6 = 9 ≤ 12`).

## Pièges

1. ❌ Redéfinir `bt_save` à `sm` pour "sécuriser" le rendu → ✅ ne pas ajouter d'entrée `sm` : le bouton hérite `xs.col:12` jusqu'à ce que `md` le redéfinisse, conformément à la cascade mobile-first.
2. ❌ Oublier de repasser `screenMode` à `"fluid"` dans `_tab.json` → ✅ sans ce champ, le placement `responsive` est ignoré et l'onglet reste rendu en absolu.
3. ❌ Considérer `xs` comme un palier à déduire → ✅ `xs` est la base du design phone-first : on la recopie telle quelle, le travail de reflow ne porte que sur `sm`/`md`/`lg`.
4. ❌ Toucher `position`/`width` des contrôles pour "aider" le rendu fluide → ✅ le positionnement absolu reste inchangé, seul `proposal.responsive` porte l'adaptation.
