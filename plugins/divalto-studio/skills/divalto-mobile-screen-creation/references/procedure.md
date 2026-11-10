# Procedure etape par etape

## Sommaire

- 0. Decouvrir les entites de donnees
- REGLE CRITIQUE : pas d'IDs dans les fichiers
- Surcharges (overloads)
- References de fonction dans l'arborescence (nav tree)
- Format des fichiers control
- Ordre de creation des fichiers
- 1. Definir la fonction metier
- 2. Creer l'ecran (\_model.json)
- 3. Creer les onglets (\_tab.json)
- 4. Ajouter les controles (un fichier par control)
- 5. Configurer les champs caches (\_hidden-fields.json) (optionnel)
- 6. Ecrire les scripts SwingScript
- 7. Configurer la navigation

### 0. Decouvrir les entites de donnees

Avant de creer un ecran, identifier la table de donnees cible :

```
get_entities()                              → liste des tables sw_data_*
get_entity_properties("sw_data_myentity")   → colonnes, types, cles primaires/etrangeres
```

Cela determine :

- Le `tableName` de la fonction (etape 1)
- Les `metaColumnId` pour les bindings des controles (etape 4)
- Les `metaColumnId` pour les champs caches (etape 5)
- Les colonnes a utiliser dans les requetes SQL des scripts (etape 6)

### REGLE CRITIQUE : pas d'IDs dans les fichiers

Les fichiers sur disque ne contiennent **aucun ID numerique**. Pas de `_id`, pas de `functionId`, pas de `tabId`, pas de `scriptId`.

- **Les codes sont les noms de fichiers/dossiers** : le code d'une entite est derive de son emplacement dans l'arborescence
- **Les FK sont resolues par l'arborescence** : un control dans `functions/customer/iphone/customersmartphone/details/controls/` est automatiquement lie au tab `details`, au model `customersmartphone`, au display `iphone`, a la function `customer`
- **Les scripts sont lies par code** : dans le champ `events[].scriptCode` du control, on met le code du script (pas un ID)
- **Le registre `_registry.json`** mappe les codes vers les IDs serveur — il est auto-maintenu par l'extension, ne jamais l'editer

### Surcharges (overloads)

L'extension stampe le `OverloadID` courant au sync mais **ne renomme PAS le code** : le code que tu donnes au fichier/dossier EST le code canonique (fichier = serveur = registre). Comme le Studio C# (qui prefixe a la saisie), c'est donc a toi de prefixer les codes des elements **neufs** quand une surcharge non-racine est active.

**Determiner le prefixe** : dans `_project.json`, prendre `currentOverloadId` puis le `code` correspondant dans `overloads[]`. La surcharge racine (`parentId: null`, typiquement `MASTER`) ne prefixe PAS ; toute autre surcharge prefixe avec `{code}_` en minuscules.

**Element neuf en surcharge non-racine → le code MUST commencer par `{overloadcode}_`.** En cas de doute, appeler l'outil MCP `validate_mobile_code({ code })` avant de nommer l'entite : il renvoie `valid` + le code corrige suggere. Le sync **rejette** tout code neuf mal prefixe. Exemple, surcharge `FINAL` active :

- ✅ `final_customer`, `final_customerdetails_btsave`, `final_unisearchbasiclist`
- ❌ `customer`, `finalunisearchbasiclist` (sans `_` : traite comme un code distinct, pas comme une surcharge → relations parent/enfant cassees au sync)

Tous les artefacts d'une meme surcharge portent le meme prefixe (fonctions, modeles, onglets, controles, scripts, unisearch). En cas de doute, regarder les artefacts existants du projet.

**Override d'un element d'une surcharge parente** (ex. modifier depuis `FINAL` un controle defini dans `MASTER`) : gere automatiquement par l'extension. **Ne PAS creer ces overrides manuellement.**

Les fichiers sur disque ne contiennent jamais de champ `_overloadId` / `_overloadParentId`.

### References de fonction dans l'arborescence (nav tree)

Un item de l'arborescence qui ouvre un ecran reference sa fonction (feature) par **code** : `feature` dans le fichier item (`{code}.json` ou `_item.json`), `rootFeature` dans `_tree.json`. Le sync resout cette reference par code cote serveur.

**Avant de referencer une feature, la fonction MUST exister dans `functions/{code}/_function.json`** — soit deja presente, soit creee dans le meme lot. Sinon le sync echoue avec `PrimaryKeyNotFoundException` (code introuvable). Verifier l'existence du dossier `functions/{code}/` AVANT de creer/modifier l'item.

- ✅ item `feature: "final_componentlibrary_unisearch_menu"` **et** dossier `functions/final_componentlibrary_unisearch_menu/` present
- ❌ referencer une feature dont le dossier `functions/` n'existe pas, ou dont le code differe (ex. `unisearchmenu` vs `unisearch_menu`)

Le champ `image` d'un item de navigation et le champ `themePicture` d'un arbre sont des codes de `sw_data_confthemepicture` : `image` stocke le `CodePicture` court, `themePicture` stocke le `CodeConfThemePicture` complet. Dans l'editeur, les deux se choisissent via le sélecteur visuel d'images (grille de miniatures filtrée par thème et plateforme).

#### Icônes Font Awesome

**MUST NOT : un `codePicture` de thème ne doit jamais commencer par un préfixe Font
Awesome** (`fa-`, `fas-`, `far-`, `fad-`, etc.). Un code image est analysé comme une
icône Font Awesome AVANT toute recherche en base — fidèle au Player, qui fait de même —
donc un `codePicture` qui ressemble à un code Font Awesome rend le glyphe correspondant à
la place de l'image de thème visée, sans erreur. Exemples réels tirés de la table
livrée : `far-left` rend le glyphe `left`, `far-right` rend `right`.

- ✅ un `codePicture` de thème qui ne commence par aucun des préfixes ci-dessus
- ❌ un `codePicture` de thème nommé `far-left` ou `far-right` (rend un glyphe Font
  Awesome au lieu de l'image attendue)

#### Gérer les images du thème (fichiers `theme/{code}/pictures/`)

Les images du thème sont des **fichiers** sous `Mobile/theme/{code}/pictures/`, suivis par le SCM et poussés au prochain « Sync to server » (comme les écrans). Côté éditeur, la commande **« Manage Theme Images »** (ou le bouton « Manage… » du sélecteur) fait l'ajout/édition/suppression. Pour le faire à la main (ou en tant qu'agent), respecter ce contrat :

**Disposition** — une image = deux fichiers dans le dossier de son thème :
```
Mobile/theme/{sanitize(theme)}/pictures/{sanitize(fullCode)}.json   ← propriétés
Mobile/theme/{sanitize(theme)}/pictures/{sanitize(fullCode)}.{ext}  ← octets de l'image
```
- `fullCode` = `CodeConfThemePicture` = `{theme}-{platform}-{code}` (plateforme vide ⇒ segment du milieu vide, ex. `WEAVY19--IconA`).
- `sanitize(x)` = passer en **minuscules** et remplacer tout caractère hors `[A-Za-z0-9_-]` par `_`. **Le nom de fichier doit être `sanitize(fullCode)`** (sinon le prochain pull régénère un nom sanitizé → doublon). `{ext}` ∈ `png|jpg|jpeg|gif|bmp`.

**Schéma du `.json`** (valeurs réelles, non sanitizées) :
```json
{ "code": "IconA", "label": "Mon icône", "category": null,
  "platform": "iOS", "enabled": true, "theme": "WEAVY19",
  "image": "weavy19-ios-icona.png" }
```
Le champ `image` est le **nom du fichier sidecar** (= `sanitize(fullCode).{ext}`), dans le même dossier.

**Opérations** :
- **Ajouter** : générer/obtenir le fichier image, le copier en `theme/{sanitize(theme)}/pictures/{sanitize(fullCode)}.{ext}`, puis écrire le `.json` à côté.
- **Modifier les propriétés** (label/category/platform/enabled) : éditer le `.json`. ⚠️ changer `code`/`platform`/`theme` change le `fullCode` ⇒ renommer les deux fichiers en conséquence (sinon : supprimer + recréer).
- **Remplacer l'image** : écraser le sidecar (mettre à jour `image`/l'extension si le format change).
- **Supprimer** : retirer le `.json` **et** le sidecar.

Une image référencée par un item (`image`), un arbre (`themePicture`) ou un control reste utilisée — vérifier avant de supprimer (le SCM montre de toute façon la suppression en attente avant le sync).

### Format des fichiers control

Chaque control est un **fichier JSON individuel** dans le dossier `controls/` du tab. Le nom du fichier est le code du control.

```
functions/customer/iphone/customersmartphone/details/controls/
  customerdetails_lbname.json       ← un fichier par control
  customerdetails_tbname.json
  customerdetails_btsave.json
```

Chaque fichier contient uniquement les donnees metier :

```json
{
  "label": "Save",
  "component": "Button",
  "position": { "left": 8, "top": 400, "width": 304, "height": 44 },
  "anchor": null,
  "orderNumber": 10,
  "proposal": { "controlType": "Button", "modelVersion": 1, "config": {} },
  "binding": { "metaColumnCode": null, "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "events": [{ "event": "Click", "scriptCode": "formcustomer_btsave_click" }]
}
```

**PAS de `_id`, `_entity`, `_tabId`, `tabId`, `code`** dans le fichier — le code est le nom du fichier, les FK sont resolues par l'arborescence.

### Ordre de creation des fichiers

Tous les fichiers sont crees localement puis synces en une seule operation. L'extension gere l'ordre de soumission au serveur (parents avant enfants). Creer les fichiers dans cet ordre logique :

1. **`functions/{code}/_function.json`** — definition de la fonction
2. **`scripts/{prefix}/{code}.json` + `.swing`** — scripts (avant les controls qui les referencent)
3. **`displays/{code}.json`** — existe deja en general (pre-cree au load)
4. **`functions/{fn}/{display}/{model}/_model.json`** — definition de l'ecran
5. **`functions/{fn}/{display}/{model}/{tab}/_tab.json`** — definition de l'onglet
6. **`functions/{fn}/{display}/{model}/{tab}/controls/{ctrl}.json`** — un fichier par control
7. **`functions/{fn}/{display}/{model}/_hidden-fields.json`** — champs caches (optionnel)

> Pas besoin d'attendre entre les creations — tout reste local jusqu'au sync explicite.

### 1. Definir la fonction metier

Creer le dossier et fichier : `functions/myentity/_function.json`

```json
{
  "label": "My Entity",
  "functionName": "MyEntity",
  "tableName": "sw_data_myentity",
  "translationKey": null,
  "designerType": "dynamic"
}
```

- Le **code** de la fonction est le nom du dossier (`myentity`)
- `tableName` : table de donnees liee (vide `""` si l'ecran n'a pas de table propre)

### 2. Creer l'ecran (\_model.json)

Creer : `functions/myentity/iphone/myentitysmartphone/_model.json`

Le placement dans l'arborescence definit les liens : dossier parent `iphone` = display, dossier parent `myentity` = function.

```json
{
  "label": "My Entity",
  "icon": null,
  "tabPageStyle": "Segmented",
  "tabPagePosition": null,
  "activation": null,
  "translationKey": null,
  "scripts": {
    "onOpen": null,
    "onClose": null,
    "onActivate": null,
    "onTabChange": null
  }
}
```

- Le **code** du model est le nom du dossier (`myentitysmartphone`)
- Les `scripts.onOpen/onClose` contiennent le **code du script** (pas un ID), ex: `"formmyentity_open"`

**Proprietes cles :**

| Propriete             | Valeurs                                                        | Description                           |
| --------------------- | -------------------------------------------------------------- | ------------------------------------- |
| `tabPageStyle`        | `"None"`, `"None_NoInteraction"`, `"PageIndicator"`, `"Segmented"`, `"SegmentedWithPageIndicator"`, `"Arrow"`, `"ArrowWithPageIndicator"` | Style de navigation inter-onglets |
| `tabPagePosition`     | `null`, `"Default"`, `"Top"`, `"Bottom"`                       | Position des onglets                  |
| `activation`          | `null` ou `"<sql>SELECT condition</sql>"`                      | Condition SQL d'affichage de l'ecran  |
| `scripts.onOpen`      | Code script ou `null`                                          | Script execute a l'ouverture          |
| `scripts.onClose`     | Code script ou `null`                                          | Script execute a la fermeture         |
| `scripts.onActivate`  | Code script ou `null`                                          | Script execute a l'activation         |
| `scripts.onTabChange` | Code script ou `null`                                          | Script execute au changement d'onglet |

### 3. Creer les onglets (\_tab.json)

Creer : `functions/myentity/iphone/myentitysmartphone/details/_tab.json`

Le **code** du tab est le nom du dossier (`details`).

```json
{
  "label": "Details",
  "tabName": "Details",
  "translationKey": "Gen_Details",
  "screenMode": "portrait",
  "openByDefault": false,
  "visible": true,
  "orderNumber": 1,
  "width": 320,
  "height": 600,
  "autoScroll": true,
  "activationString": null
}
```

**Proprietes cles :**

| Propriete          | Description                              |
| ------------------ | ---------------------------------------- |
| `orderNumber`      | Ordre d'affichage (1, 2, 3...), seul critère d'ordre des onglets, quel que soit leur `screenMode` |
| `screenMode`       | `"portrait"`, `"landscape"` ou `"fluid"` |
| `width` / `height` | Dimensions du contenu (null = auto-fill) |
| `autoScroll`       | Defilement automatique du contenu        |
| `activationString` | Condition SQL d'affichage de l'onglet    |

**Dimensions recommandees :**

- iPhone : `320` x `600`
- iPad/Common : `1024` x `768` (ou `600` x `600` pour les sous-panneaux)

### 4. Ajouter les controles (un fichier par control)

Chaque control est un fichier JSON individuel dans `controls/`. Le nom du fichier est le code du control.

Voir la reference complete : [controls.md](controls.md)

**Label :** `controls/myentitydetails_lbname.json`

> **Important** : le `label` est une aide du designer (pas visible a l'execution).
> Le texte affiche a l'ecran est dans `proposal.text` (ou via `binding` + `translationKey`).

```json
{
  "label": "lbName",
  "component": "Label",
  "position": { "left": 8, "top": 16, "width": 150, "height": 32 },
  "anchor": "Top, Left",
  "orderNumber": 0,
  "binding": { "metaColumnCode": null, "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": "sw_data_myentity_name",
  "proposal": { "controlType": "Label", "modelVersion": 1, "common": {}, "config": {}, "text": "Name" },
  "events": []
}
```

**TextBox avec event :** `controls/myentitydetails_tbname.json`

```json
{
  "label": "tbName",
  "component": "TextBox",
  "position": { "left": 168, "top": 16, "width": 144, "height": 32 },
  "anchor": "Top, Left, Right",
  "orderNumber": 1,
  "binding": { "metaColumnCode": "name", "defaultValue": null, "displayMask": null },
  "activation": null,
  "update": null,
  "translationKey": null,
  "proposal": {
    "controlType": "TextBox",
    "modelVersion": 1,
    "common": {},
    "config": { "keyboardType": "Default", "inlineEdition": false }
  },
  "events": [{ "event": "ValueChanged", "scriptCode": "formmyentity_tbname_valuechanged" }]
}
```

**Champs importants :**

- `binding.metaColumnCode` : code de la colonne dans la table (pas un ID numerique)
- `events[].scriptCode` : code du script a executer (pas un ID)
- Pas de `code`, `_id`, `_entity`, `tabId` — le code est le nom du fichier, le tab est le dossier parent

**Convention de nommage des controles :** `{TabCode}_{prefixeType}{NomChamp}`

| Prefixe | Type de controle |
| ------- | ---------------- |
| `lb`    | Label            |
| `tb`    | TextBox          |
| `cb`    | ComboBox         |
| `dp`    | DateTimePicker   |
| `bt`    | Button           |
| `ck`    | CheckBox         |
| `up`    | NumericUpDown    |
| `us`    | UniSearch        |
| `sn`    | ShellNode        |
| `pb`    | PictureBox       |
| `ie`    | ImageEditor      |
| `sg`    | Signature        |
| `ch`    | Chart            |
| `mp`    | Maps             |

### 5. Configurer les champs caches (\_hidden-fields.json) (optionnel)

Creer : `functions/myentity/iphone/myentitysmartphone/_hidden-fields.json`

```json
[
  { "metaColumnCode": "baseuser_id", "defaultValue": "%baseuser_ID%" },
  { "metaColumnCode": "creatdate", "defaultValue": "%now%" }
]
```

C'est un tableau JSON direct (pas de wrapper). `metaColumnCode` est le code de la colonne (pas un ID numerique).

````

**Variables systeme disponibles :**

- `%baseuser_ID%` : ID de l'utilisateur courant
- `%now%` : horodatage courant
- `<ifempty>value||default</ifempty>` : valeur conditionnelle

### 6. Ecrire les scripts SwingScript

Voir la reference complete : [swingscript.md](swingscript.md)

**Metadata du script :** `scripts/form/formmyentity_open.json`

```json
{
  "label": "Form : My Entity / Open",
  "scriptType": null,
  "sourceFile": "formmyentity_open.swing"
}
````

**Script (.swing) :**

```swing
// Initialiser les controles
CONTROL_SET_VALUE( "lbTitle", "<sql>SELECT name FROM sw_data_myentity WHERE myentity_ID = '<var>myentity_ID|MyEntity</var>'</sql>" )

// Charger les options
CALL_SCRIPT( "Func_LoadMyEntityOptions" )

// Conditionner la visibilite
IF ( EQUALS( "<var>isReadOnly|MyEntity</var>", "1" ) ) THEN
  CONTROL_ENABLE( "tbName", "0" )
  CONTROL_ENABLE( "cbStatus", "0" )
ENDIF
```

### 7. Configurer la navigation

**Via ShellNode (controle de navigation) :**

```json
{
  "component": "ShellNode",
  "proposal": {
    "controlType": "ShellNodeControl",
    "modelVersion": 1,
    "config": {
      "codeAlias": "TargetScreenCode",
      "displayType": "ActionBar"
    }
  }
}
```

**Via script SwingScript :**

```swing
GOTO_FUNCTION( "TargetFunctionCode" )
```

---
