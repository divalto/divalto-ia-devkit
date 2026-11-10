# Liaison controle → script (evenements)

## Sommaire

- Regles fondamentales
- Evenements les plus courants
- Methode recommandee : `create_mobile_entities` (un seul appel)
- Exemple : ecran avec plusieurs evenements
- Methode alternative manuelle (si MCP indisponible)
- Regles sur les IDs d'evenements (mode manuel)
- Liaison script au model (onOpen, onClose, etc.)

Un controle peut declencher un script via son tableau `events`. Chaque evenement associe **un seul script** a un controle pour un type d'evenement donne.

> **Methode preferee** : utiliser `create_mobile_entities` pour creer le script ET la liaison en un seul appel atomique.
> **Reference complete** : voir `references/controls.md` section "Evenements de script" pour la liste exhaustive des evenements par type de controle.

### Regles fondamentales

1. **Un seul script par evenement par controle** — pas de doublons d'evenements
2. **Respecter les evenements du composant** — chaque type de controle ne supporte que certains evenements (ex: Button → `Click`, TextBox → `GotFocus` + `TextChanged`)
3. **Convention de nommage stricte** :
   - Code script : `Form{Ecran}_{controlCode}_{Event}` (PascalCase) → ex: `FormCustomer_btSave_Click`
   - Fichier : `form{ecran}_{controlcode}_{event}.swing` (lowercase) → ex: `formcustomer_btsave_click.swing`
   - Label : `Form : {Ecran} / {controlCode} / {Event}` → ex: `Form : Customer / btSave / Click`
   - Code ConfScriptControl : `{ControlCode}_{Event}` → ex: `CustomerDetails_btSave_Click`

### Evenements les plus courants

| Evenement              | Composants principaux                                                        | Usage typique                               |
| ---------------------- | ---------------------------------------------------------------------------- | ------------------------------------------- |
| `Click`                | Button, Label, PictureBox                                                    | Actions utilisateur (sauvegarder, naviguer) |
| `ValueChanged`         | NumericUpDown, DateTimePicker, UniSearch, Badge, Tree, Chart, BarcodeScanner | Reagir a un changement de valeur            |
| `TextChanged`          | TextBox, TextBoxMultiline, Label, RichTextBox                                | Validation en temps reel, formatage         |
| `GotFocus`             | TextBox, ComboBox, NumericUpDown, DateTimePicker, BarcodeScanner             | Initialiser des listes, aide contextuelle   |
| `CheckStateChanged`    | CheckBox                                                                     | Activer/desactiver des sections             |
| `SelectedIndexChanged` | ComboBox                                                                     | Filtrer selon la selection                  |
| `DoubleClick`          | UniSearch, Calendar, Chart                                                   | Ouvrir un detail, editer                    |

### Methode recommandee : `create_mobile_entities` (un seul appel)

Creer le script, le fichier `.swing`, et la liaison evenement en un seul appel atomique :

```json
create_mobile_entities({
  "data": {
    "confscript": [{
      "CodeConfScript": "FormCustomer_btSave_Click",
      "Label": "Form : Customer / btSave / Click",
      "Script": "VARUPDATE_DB_BYID( sw_data_customer, <sql>label = <ctrl>CustomerDetails_tbName</ctrl></sql>, %CURRENTRECORD_ID% )\nMSGBOX( \"Client sauvegarde\" )"
    }],
    "confscriptcontrol": [{
      "CodeConfScriptControl": "CustomerDetails_btSave_Click",
      "Event": "Click"
    }]
  },
  "relations": [
    {
      "entityName": "confcontrol",
      "entityCode": "CustomerDetails_btSave",
      "targetEntity": "confscriptcontrol",
      "targetFieldName": "ConfControl_ID",
      "targetEntityCode": "CustomerDetails_btSave_Click"
    },
    {
      "entityName": "confscript",
      "entityCode": "FormCustomer_btSave_Click",
      "targetEntity": "confscriptcontrol",
      "targetFieldName": "ConfScript_ID",
      "targetEntityCode": "CustomerDetails_btSave_Click"
    }
  ]
})
```

L'outil :

1. Injecte automatiquement `OverloadID` depuis `_project.json`
2. Cree le script + scriptcontrol en une seule transaction
3. Le serveur resout les FK par code (controle existant + script fraichement cree)
4. Ecrit `scripts/form/formcustomer_btsave_click.json` + `.swing` sur disque avec les bons IDs
5. Met a jour `controls.json` avec le `scriptId`

### Exemple : ecran avec plusieurs evenements

```json
create_mobile_entities({
  "data": {
    "confscript": [
      { "CodeConfScript": "FormCustomer_tbName_TextChanged", "Label": "Form : Customer / tbName / TextChanged", "Script": "// validation" },
      { "CodeConfScript": "FormCustomer_cbStatus_SelectedIndexChanged", "Label": "Form : Customer / cbStatus / SelectedIndexChanged", "Script": "// filtrage" },
      { "CodeConfScript": "FormCustomer_btSave_Click", "Label": "Form : Customer / btSave / Click", "Script": "// sauvegarde" }
    ],
    "confscriptcontrol": [
      { "CodeConfScriptControl": "CustomerDetails_tbName_TextChanged", "Event": "TextChanged" },
      { "CodeConfScriptControl": "CustomerDetails_cbStatus_SelectedIndexChanged", "Event": "SelectedIndexChanged" },
      { "CodeConfScriptControl": "CustomerDetails_btSave_Click", "Event": "Click" }
    ]
  },
  "relations": [
    { "entityName": "confcontrol", "entityCode": "CustomerDetails_tbName", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfControl_ID", "targetEntityCode": "CustomerDetails_tbName_TextChanged" },
    { "entityName": "confscript", "entityCode": "FormCustomer_tbName_TextChanged", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfScript_ID", "targetEntityCode": "CustomerDetails_tbName_TextChanged" },
    { "entityName": "confcontrol", "entityCode": "CustomerDetails_cbStatus", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfControl_ID", "targetEntityCode": "CustomerDetails_cbStatus_SelectedIndexChanged" },
    { "entityName": "confscript", "entityCode": "FormCustomer_cbStatus_SelectedIndexChanged", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfScript_ID", "targetEntityCode": "CustomerDetails_cbStatus_SelectedIndexChanged" },
    { "entityName": "confcontrol", "entityCode": "CustomerDetails_btSave", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfControl_ID", "targetEntityCode": "CustomerDetails_btSave_Click" },
    { "entityName": "confscript", "entityCode": "FormCustomer_btSave_Click", "targetEntity": "confscriptcontrol", "targetFieldName": "ConfScript_ID", "targetEntityCode": "CustomerDetails_btSave_Click" }
  ]
})
```

### Methode alternative manuelle (si MCP indisponible)

1. Creer le script .json + .swing → attendre la sync (le serveur assigne un `_id`)
2. Lire le `_id` du script dans le .json (patche par l'extension)
3. Mettre a jour `controls.json` avec le `scriptId` reel dans le tableau `events`

### Regles sur les IDs d'evenements (mode manuel)

- `events[]._id` : toujours `null` pour un nouvel evenement
- `events[].scriptId` : l'ID **reel** du script apres sync du .json
- `events[].event` : nom exact de l'evenement (respecter la casse : `"Click"` pas `"click"`)

````

### Liaison script au model (onOpen, onClose, etc.)

Les evenements de **formulaire** (model-level) sont differents des evenements de controle. Ils se configurent dans `_model.json` :

| Evenement    | Declenchement                                     | Usage typique                                |
|--------------|---------------------------------------------------|----------------------------------------------|
| `onOpen`     | A l'ouverture du formulaire                       | Initialiser variables, charger donnees       |
| `onClose`    | A la fermeture du formulaire                      | Cleanup, validation finale, sauvegarde auto  |
| `onActivate` | Quand le formulaire redevient actif (retour)      | Rafraichir les donnees apres navigation      |
| `onTabChange`| Changement d'onglet dans le formulaire            | Charger les donnees de l'onglet              |

```json
{
  "_entity": "confmodel",
  "_id": null,
  "scripts": {
    "onOpen": null,
    "onClose": null,
    "onActivate": null,
    "onTabChange": null
  }
}
````

Convention de nommage des scripts model :

- Code : `Form{Ecran}_{Event}` → ex: `FormCustomer_Open`, `FormCustomer_Close`
- Fichier : `form{ecran}_{event}.swing` → ex: `formcustomer_open.swing`

Apres sync du script, mettre a jour avec l'ID reel :

```json
"scripts": {
  "onOpen": 50000000456,
  "onClose": null,
  "onActivate": null,
  "onTabChange": null
}
```

---
