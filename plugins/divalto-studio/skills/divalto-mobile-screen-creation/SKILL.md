---
name: divalto-mobile-screen-creation
description: "Crée, modifie ou paramètre un écran mobile Divalto Weavy (anciennement SwingMobility). Utiliser pour : créer un écran, ajouter un onglet, configurer un contrôle (Label, TextBox, ComboBox, UniSearch, Button, Maps, Tree, Chart, Signature…), écrire un SwingScript, lier des données, gérer les événements de formulaire, paramétrer un webhook mobile."
argument-hint: "Decrivez l'ecran mobile a construire (ex: fiche intervention avec onglets equipements et pieces, liste clients avec carte GPS, ecran de saisie commande avec catalogue produits...)"
capabilities: [mobile]
---

# Creation d'ecrans mobiles Divalto Weavy

## Quand utiliser ce skill

- Creer un nouvel ecran mobile (smartphone ou tablette) dans un projet Divalto Weavy
- Ajouter un onglet, des controles ou des evenements a un ecran existant
- Ecrire un script SwingScript pour la logique metier ou les evenements de formulaire
- Configurer la navigation entre ecrans (ShellNode, GOTO_FUNCTION)
- Lier des donnees a des controles via le binding (metaColumnId)
- Creer des fonctions reutilisables en SwingScript
- Parametrer des webhooks pour l'integration externe

---

## Architecture d'un projet mobile

```
Mobile/
  _project.json                          # Config projet (projectCode, currentOverloadId, overloads[])
  _registry.json                         # Mapping code → ID serveur (auto-maintenu, ne pas editer)
  _baseline.json                         # Hashes pour le change tracking (auto-maintenu)
  displays/                              # Definitions de plateformes (1 JSON par display)
    iphone.json                          # { label, platform, width, height }
    common.json
  functions/                             # Hierarchie complete : function → display → model → tab → controls
    customer/                            # Un dossier par fonction
      _function.json                     # { label, functionName, tableName, translationKey }
      iphone/                            # Sous-dossier par display (code du display)
        customersmartphone/              # Sous-dossier par model (code du model)
          _model.json                    # { label, icon, tabPageStyle, scripts: { onOpen, onClose } }
          _hidden-fields.json            # [{ metaColumnCode, defaultValue }] (optionnel)
          details/                       # Sous-dossier par tab (code du tab)
            _tab.json                    # { label, tabName, visible, orderNumber, screenMode, ... }
            controls/                    # Un fichier JSON par controle
              customerdetails_lbname.json
              customerdetails_tbname.json
              customerdetails_btaction.json
          addresses/
            _tab.json
            controls/
              customeraddresses_uslist.json
  scripts/                               # Logique metier SwingScript
    form/                                # Gestionnaires d'evenements de formulaire
      formcustomer_open.json             # Metadata : { label, scriptType, sourceFile }
      formcustomer_open.swing            # Code source SwingScript
      formcustomer_btaction_click.json
      formcustomer_btaction_click.swing
    func/                                # Fonctions utilitaires reutilisables
      func_getcustomerinfo.json
      func_getcustomerinfo.swing
```

### Regles cles de l'architecture fichier

- **Pas d'IDs dans les fichiers** : les fichiers contiennent uniquement des donnees metier (label, position, binding...). Les IDs serveur sont dans `_registry.json` (auto-maintenu).
- **Les codes sont les noms de fichiers/dossiers** : le code d'un control est le nom de son fichier (sans `.json`), le code d'un tab est le nom de son dossier, etc.
- **Un fichier par control** : chaque control est un fichier JSON individuel dans `controls/`, pas un tableau dans un fichier unique.
- **Scripts = .json + .swing** : le `.json` contient les metadata (label, scriptType, sourceFile), le `.swing` contient le code source.

---

## Outils MCP disponibles

> Reference complete : [references/outils-mcp.md](./references/outils-mcp.md)

Les outils MCP mobiles, leurs parametres et leurs retours. Les descriptions faisant foi sont celles que le serveur `divalto-studio` expose.

## Procedure etape par etape

> Reference complete : [references/procedure.md](./references/procedure.md)

Le deroule complet de creation d'un ecran, etape par etape, du modele XML jusqu'au cablage des scripts.

## Composants UI disponibles

> Voir la reference detaillee : [references/controls.md](./references/controls.md)

| Composant          | Usage                     | Proprietes `config` cles                                                       |
| ------------------ | ------------------------- | ------------------------------------------------------------------------------ |
| `Label`            | Affichage texte, titres   | `shadowOffsetX/Y`, `blurRadius`, `model`                                       |
| `TextBox`          | Saisie texte mono-ligne   | `keyboardType`, `inlineEdition`, `password`, `clearButton`, `placeholder`      |
| `TextBoxMultiline` | Saisie texte multi-lignes | `keyboardType`                                                                 |
| `ComboBox`         | Liste deroulante          | `selectionMode`, `emptyElement`, `selectionQuery`                              |
| `CheckBox`         | Case a cocher             | —                                                                              |
| `NumericUpDown`    | Saisie numerique +/-      | —                                                                              |
| `DateTimePicker`   | Selecteur date/heure      | —                                                                              |
| `Button`           | Bouton d'action           | `imageCode`                                                                    |
| `UniSearch`        | Liste de recherche        | `xmlModel` (code du modèle), `displayTitle`. **2 fichiers** : contrôle ([references/controls.md](./references/controls.md)) + modèle (skill `divalto-unisearch-creation`). Voir [references/xmlmodel.md](./references/xmlmodel.md) |
| `ShellNode`        | Noeud de navigation       | `codeAlias`, `displayType` (PagePanel/ActionBar)                               |
| `Tree`             | Arbre hierarchique        | `allowMultiSelection`, `isExpanded`, `nodeQuery`, `contentQuery`               |
| `Maps`             | Carte geographique        | `mapType`, `initialZoomLevel`, `initialLatitude/Longitude`, serie avec `query` |
| `Chart`            | Graphique                 | —                                                                              |
| `PictureBox`       | Affichage image           | —                                                                              |
| `ImageEditor`      | Capture/edition photo     | —                                                                              |
| `Signature`        | Saisie signature          | —                                                                              |
| `Calendar`         | Calendrier                | —                                                                              |
| `Timer`            | Minuteur                  | —                                                                              |
| `WebBrowser`       | Contenu web embarque      | —                                                                              |
| `DynamicFields`    | Champs dynamiques         | —                                                                              |
| `RichTextBox`      | Editeur texte riche       | —                                                                              |
| `Separator`        | Separateur visuel         | —                                                                              |

---

## Liaison controle → script (evenements)

> Reference complete : [references/evenements.md](./references/evenements.md)

Comment un controle declenche un script : evenements par famille de controle, arguments recus, et cablage cote XML.

## Surcharges (overloads)

### Concept

Le systeme de surcharge permet de creer des variantes d'un ecran sans modifier l'original. Par exemple : un ecran "MASTER" de base et un overload "FINAL" qui modifie certains controles.

### Comment ca fonctionne dans les fichiers

Chaque fichier JSON contient les metadonnees de surcharge :

```json
{
  "_entity": "confcontrol",
  "_id": 50000000789,
  "_overloadId": 3,
  "_overloadParentId": 50000000100,
  "code": "CustomerDetails_tbName",
  ...
}
```

- **`_overloadId`** : l'overload auquel appartient cet element (ex: `3` = "FINAL")
- **`_overloadParentId`** : l'ID de l'element parent dans la chaine (l'element original qu'on surcharge)

### Regles pour l'IA

1. **Ne JAMAIS creer de surcharges manuellement** — l'extension gere automatiquement la creation d'overrides quand on modifie un element herite d'un overload parent
2. **Creer les elements normalement** — ne pas renseigner `_overloadId` ni `_overloadParentId`. L'extension et le MCP tool les injectent automatiquement depuis `_project.json`
3. **Ne pas modifier `_overloadId` ni `_overloadParentId`** dans les fichiers existants
4. **Les elements herites (provenant d'un overload parent) ne doivent pas etre supprimes** — ils sont masques automatiquement par le designer
5. **Les codes d'overrides sont prefixes automatiquement** — quand un element parent est modifie dans un overload enfant, le code unique est prefixe avec le code de l'overload (ex: `btSave` → `FINAL_btSave`). Ne PAS prefixer manuellement

### Identifier un element surcharge

Un element est reellement surcharge quand :

- `_overloadId` est non-null et non-zero
- ET `_overloadId` n'est PAS l'overload racine (le premier overload sans parent dans `_project.json`)

Les elements surcharges sont affiches avec une barre de couleur dans le designer et une icone coloree dans la tree view.

---

## Binding et positionnement

### Binding de donnees

Le `metaColumnId` lie un controle a une colonne de la table de la fonction.

> **Appeler `get_entity_properties("sw_data_myentity")` pour obtenir les identifiants de colonnes valides avant de configurer un binding.**

```json
"binding": {
  "metaColumnId": 1788,
  "defaultValue": null,
  "displayMask": null
}
```

### Activation conditionnelle

Rendre un controle visible/actif selon une condition :

```json
"activation": {
  "metaColumnId": 32,
  "operator": "IS NULL",
  "value": null
}
```

Operateurs : `"IS NULL"`, `"IS NOT NULL"`, `"="`, `"!="`.

### Positionnement absolu

Les controles utilisent un systeme de coordonnees absolues en pixels :

```json
"position": { "left": 8, "top": 16, "width": 304, "height": 32 }
```

### Ancrage (responsive)

L'ancrage definit comment le controle s'adapte au redimensionnement :

| Anchor                       | Comportement                   |
| ---------------------------- | ------------------------------ |
| `"Top, Left"`                | Position fixe en haut a gauche |
| `"Top, Left, Right"`         | S'etire horizontalement        |
| `"Top, Bottom, Left, Right"` | Remplit toute la zone          |
| `"Bottom, Left, Right"`      | Ancre en bas, pleine largeur   |
| `"Top, Right"`               | Position fixe en haut a droite |

**Patterns smartphone :** Utiliser `"Top, Left, Right"` pour les champs pleine largeur avec `left: 8`, `width: 304` sur iPhone (320px).

**Patterns tablette :** Utiliser des largeurs fixes (ex: `width: 208`) avec `"Top, Left"` pour le layout en colonnes.

---

## Langage SwingScript — Resume

> Voir la reference complete : [references/swingscript.md](./references/swingscript.md)

### Syntaxe d'interpolation

| Syntaxe                               | Contexte                                                 |
| ------------------------------------- | -------------------------------------------------------- |
| `<var>fieldName\|GroupName</var>`     | Variable shell (lecture)                                 |
| `<varscript>variableName</varscript>` | Variable de script / argument                            |
| `<ctrl>controlName</ctrl>`            | Valeur d'un controle UI                                  |
| `<sql>SELECT ...</sql>`               | Execution SQL inline (scalaire)                          |
| `<lng>TranslationKey</lng>`           | Cle de traduction                                        |
| `<msk>value\|format</msk>`            | Formatage (date: `d`, heure: `HH:mm:ss`, nombre: `0.00`) |
| `<row>fieldName</row>`                | Champ de la ligne courante (dans FOREACH)                |
| `%variable%`                          | Variable systeme (`%now%`, `%baseuser_ID%`, `%gps_fix%`) |
| `<ifempty>value\|default</ifempty>`   | Valeur par defaut si vide                                |
| `<calc>expression</calc>`             | Calcul arithmetique                                      |

### Flux de controle

```swing
// Condition
IF ( condition ) THEN
  // ...
ELSE
  // ...
ENDIF

// Boucle (ancre + GOTO)
#StartLoop:
IF ( condition ) THEN
  PAUSE( "0.5" )
  GOTO StartLoop
ENDIF

// Appel de fonction avec retour
result = CALL_SCRIPT( "Func_MyFunction", arg1, arg2 )

// Inclusion (meme scope)
INCLUDE( "FuncMyHelper" )

// Iteration sur lignes SQL
EXECUTE_SCRIPT_FOREACH_ROW( "Func_ProcessRow", "sql", query )

// Retour de valeur
RETURN( result )
```

### APIs principales

| Categorie           | Fonctions                                                                                                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Controles UI**    | `CONTROL_SET_VALUE`, `CONTROL_GET_VALUE`, `CONTROL_VISIBLE`, `CONTROL_ENABLE`, `CONTROL_BACKCOLOR`, `CONTROL_FORECOLOR`, `CONTROL_SETIMAGE`, `CONTROL_FILLCOMBO_SQL`, `CONTROL_SET_PLACEHOLDER` |
| **Navigation**      | `GOTO_FUNCTION`, `GOTO_ELEMENTBYALIAS`, `GOTO_NODEBYALIAS`, `CLOSE`, `OPEN_URL`                                                                                                                 |
| **Variables shell** | `VARSET_SHELL`, `VARGET_SHELL`, `VARDEL_SHELL`, `VARDELGROUP_SHELL`, `VARSET_SHELL_BYSQL`, `VARINITIALIZE_SHELL`                                                                                |
| **Base de donnees** | `VARADD_DB`, `VARADD_DB_FROMSQL`, `VARUPDATE_DB_BYID`, `VARUPDATE_DB_BYFILTER`, `VARDEL_DB_BYID`, `VARGET_DBSQL`, `VARGET_DBFIELD_BYID`, `EXECUTESQL`                                           |
| **Scripts**         | `CALL_SCRIPT`, `INCLUDE`, `EXECUTE_SCRIPT_FOREACH_ROW`, `RETURN`, `RETURN_JSON`                                                                                                                 |
| **UniSearch**       | `UNISEARCH_REFRESH`, `UNISEARCH_SELECTID`, `UNISEARCH_SELECTEDID`, `UNISEARCH_SETTITLE`, `SHELL_UNISEARCH_REFRESH`, `SHELL_UNISEARCH_SELECTEDID`                                                |
| **UI feedback**     | `MSGBOX`, `ASK`, `WAITINGMESSAGE`, `WAITINGMESSAGEHIDE`, `DISPLAY_TITLE`                                                                                                                        |
| **Formulaire**      | `FORM_ISINIT`, `FORM_SET_TABPAGE`, `SET_FORMUPDATED`                                                                                                                                            |
| **Carte**           | `MAPS_CENTERSERIE`, `MAPS_REFRESHSERIE`, `MAPS_SETMAPTYPE`, `MAPS_ZOOMLEVEL`                                                                                                                    |
| **Calendrier**      | `CALENDAR_SCROLLTOHOUR`, `CALENDAR_SELECTDATE`                                                                                                                                                  |
| **GPS**             | `GPS_START`, `GPS_STOP`, `GPS_GETLONGITUDE`, `GPS_GETLATITUDE`                                                                                                                                  |
| **Documents JSON**  | `DOCUMENT_CREATE_DOCUMENT`, `DOCUMENT_CREATE_OBJECT`, `DOCUMENT_ADD_PROPERTY_TO_OBJECT`, `DOCUMENT_SERIALIZE`, `JSON_GET_FROM_PATH`, `JSON_EXISTS_FROM_PATH`                                    |
| **Chaines**         | `EQUALS`, `LEN`, `REPLACE`, `CONCAT`, `TRIM`, `FIND`, `TRANSLATE`                                                                                                                               |
| **Dates**           | `DATEDIFF`, `%now%`                                                                                                                                                                             |
| **Timer**           | `TIMER_START`, `TIMER_STOP`                                                                                                                                                                     |

---

## Patterns d'architecture

### Pattern 1 : Ecran de fiche (details + onglets)

```
Screen (tabPageStyle: "Segmented")
  Tab "Details" (orderNumber: 1, autoScroll: true)
    Label + TextBox (code)
    Label + TextBox (nom)
    Label + ComboBox (type/statut)
    Label + DateTimePicker (date)
  Tab "Notes" (orderNumber: 2)
    UniSearch (liste de notes)
    ShellNode (ActionBar: ajouter/modifier)
  Tab "Documents" (orderNumber: 3)
    UniSearch (liste de documents)
```

### Pattern 2 : Ecran de liste avec recherche

```
Screen (tabPageStyle: "None")
  Tab "List" (autoScroll: false)
    TextBox (recherche, avec placeholder)
    UniSearch (liste principale, anchor: fill)
    ShellNode (ActionBar: actions)
```

### Pattern 3 : Ecran de saisie commande (multi-modes)

```
Screen (tabPageStyle: "None")
  Tab "Catalog" (orderNumber: 10)
    Label (background, subtotal)
    Button (display mode toggle)
    TextBox (recherche)
    UniSearch (catalogue produits, anchor: fill)
  Tab "Products" (orderNumber: 20)
    UniSearch (lignes de commande)
  Tab "History" (orderNumber: 60)
    DateTimePicker (debut) + DateTimePicker (fin)
    Button (refresh)
    UniSearch (historique)
```

### Pattern 4 : Ecran carte avec POI

```
Screen (tabPageStyle: "Segmented")
  Tab "Map" (autoScroll: false)
    Maps (anchor: fill, serie avec query SQL pour les POI)
  Tab "List" (autoScroll: false)
    UniSearch (memes donnees en liste)
```

### Pattern 5 : Ecran intervention avec timer

```
Screen (tabPageStyle: "Segmented")
  Tab "Intervention" (1024x768)
    3 zones Label (background: request, equipments, times)
    Buttons (timer: play/pause/next)
    Labels (durees, statuts)
  Tab "Parts" (UniSearch + ShellNode)
  Tab "Checklist" (UniSearch)
  Tab "Photos" (UniSearch + ImageEditor)
```

---

## Cycle de vie des evenements

### Formulaire

1. **onOpen** : Initialiser les controles, charger les donnees, positionner les variables
2. **onActivate** : Rafraichir l'affichage quand l'ecran redevient actif
3. **onTabChange** : Mettre a jour l'onglet courant
4. **ValueChanged** : Reagir aux changements de valeur (ComboBox, UniSearch, TextBox)
5. **Click** : Reagir aux clics de boutons
6. **DoubleClick** : Ouvrir un detail (sur UniSearch)
7. **CheckStateChanged** : Reagir aux changements de case a cocher
8. **onClose** : Nettoyage, sauvegarde d'etat, validation

### Navigation par noeuds (Node)

1. **node_open** : Initialiser le titre, rafraichir la liste

### Webhooks

1. **webhook_before** : Validation des entetes, extraction des parametres
2. **webhookrules\_[entity]** : Validation metier par entite
3. **webhook_after** : Post-traitement, invalidation de cache

---

## Conventions de nommage

| Element                 | Convention                 | Exemple                                                      |
| ----------------------- | -------------------------- | ------------------------------------------------------------ |
| Code ecran (common)     | PascalCase entite          | `Customer`, `Order`, `Intervention`                          |
| Code ecran (smartphone) | PascalCase + Smartphone    | `CustomerSmartphone`, `OrderSmartphone`                      |
| Code onglet             | PascalCase entite + onglet | `CustomerDetails`, `OrderProducts`                           |
| Code controle           | TabCode_prefixeNom         | `CustomerDetails_tbName`, `OrderCatalog_usCatalog`           |
| Code script form        | Form{Ecran}\_{Event}       | `FormCustomer_Open`, `FormOrder_Close`                       |
| Code script form+ctrl   | Form{Ecran}_{ctrl}_{Event} | `FormCustomer_tbName_ValueChanged`                           |
| Code script func        | Func\_{Description}        | `Func_GetCustomerInfo`, `Func_LoadPermissions`               |
| Code script node        | Node{Entity}\_{Event}      | `NodeCustomerNotes_Open`                                     |
| Code scriptcontrol      | {ControlCode}\_{Event}     | `CustomerDetails_btSave_Click`                               |
| Fichier script          | minuscule_underscore.swing | `formcustomer_open.swing`, `func_getcustomerinfo.swing`      |
| Groupe de variables     | PascalCase                 | `"Order"`, `"Customer"`, `"GPS"`, `"Options"`                |
| Cle de traduction       | Prefixe_Nom                | `Gen_Details`, `sw_data_customer_name`, `Msg_NoItemSelected` |

---

## Regles et bonnes pratiques

### Creation d'elements

1. **Utiliser `create_mobile_entities`** pour toute creation impliquant des FK croisees (scripts + evenements, ecrans complets)
2. **Editer les fichiers directement** uniquement pour modifier des elements existants (qui ont deja un `_id`)
3. **Ne jamais inventer d'IDs numeriques** — le serveur les assigne automatiquement
4. **Ne jamais renseigner `_overloadId`** — le MCP tool et l'extension l'injectent automatiquement
5. **Toujours valider les scripts** avec `validate_swingscript` apres ecriture

### Design d'ecrans

6. **Toujours utiliser des cles de traduction** (`<lng>Gen_*</lng>`) pour les textes utilisateur — pour creer ou reutiliser une cle (au lieu de `translationKey: null` ou d'un libelle en dur), deleguer au skill [divalto-translations](../divalto-translations/SKILL.md)
7. **Adapter le layout** : ancrage `Top, Left, Right` sur smartphone, positions fixes sur tablette
8. **Prefixer les controles** avec le code de l'onglet pour eviter les collisions de noms

### Scripts SwingScript

9. **Nettoyer les variables** avec `VARDELGROUP_SHELL` dans les scripts `onClose`
10. **Documenter les fonctions** avec des commentaires `// @description`, `// @param`, `// @return`
11. **Utiliser CALL_SCRIPT** pour les fonctions avec retour, **INCLUDE** pour les blocs partages
12. **Tester les valeurs nulles** avec `LEN()` avant d'utiliser une variable
13. **Grouper les variables** par domaine metier (Order, Customer, GPS, Options, Selection)

### Surcharges (overloads)

14. **Ne jamais creer de surcharges manuellement** — le systeme les gere automatiquement
15. **Ne pas modifier les elements herites** du parent via edition de fichier — utiliser le designer ou le MCP tool
16. **Les codes d'override sont prefixes automatiquement** (`btSave` → `FINAL_btSave`)

## References

- [Controles UI complets](./references/controls.md) — tous les composants avec proprietes, evenements par type de controle
- [Langage SwingScript](./references/swingscript.md) — syntaxe, APIs, patterns avances
