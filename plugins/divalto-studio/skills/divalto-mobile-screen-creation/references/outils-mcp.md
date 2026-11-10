# Outils MCP disponibles

## Sommaire

- Controles UI disponibles
- Groupes de fonctions SwingScript
- Base de donnees : MariaDB
- Workflow obligatoire
- Creation et modification — tout se fait par fichiers
- Regles d'utilisation MCP
- Workflow de validation des scripts

Utiliser les outils MCP pour decouvrir les tables, colonnes, controles et fonctions disponibles avant de generer du code :

| Outil                          | Usage                                                                                                    | Quand l'appeler                                                                                                                                                                                                                                                                                 |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_mobile_control_reference` | Obtenir les definitions des controles UI mobiles (proprietes, evenements, children, positionnement)      | **Avant** de creer ou modifier un controle — pour connaitre les proprietes `config` disponibles, les evenements, et les elements children. Modes : sans params = categories et positionnement ; `controlName="Chart"` = definition complete ; `category="Input"` = tous les controles de saisie |
| `get_entities`                 | Lister toutes les tables du dictionnaire Divalto (`sw_data_*`)                                           | **Avant** d'ecrire une requete SQL dans un script SwingScript, une `selectionQuery` de ComboBox, ou une `query` de Maps/Tree                                                                                                                                                                    |
| `get_entity_properties`        | Obtenir les colonnes d'une table (noms, types, cles)                                                     | **Avant** de configurer un `metaColumnId` dans un binding, d'ecrire un SELECT, ou de mapper un `defaultValue` dans `_hidden-fields.json`                                                                                                                                                        |
| `get_swingscript_reference`    | Chercher des fonctions SwingScript par nom ou groupe (555 fonctions, 20 mots-cles, 54 variables systeme) | **Avant** d'utiliser une fonction SwingScript — pour obtenir la signature exacte, les parametres et les surcharges. Modes : sans params = lister les groupes ; `search="CONTROL"` = chercher par nom ; `group="GPS"` = lister un groupe                                                         |
| `validate_swingscript`         | Valider la syntaxe d'un script SwingScript                                                               | **Apres** avoir ecrit ou modifie un script `.swing` — retourne les erreurs avec ligne, colonne et message                                                                                                                                                                                       |
| `validate_mobile_code`         | Verifier qu'un code d'entite porte le prefixe de la surcharge active                                     | **Avant** de nommer/creer toute entite (fonction, modele, onglet, controle, script, unisearch). Renvoie `{ valid, expectedPrefix, suggested }`. Voir « Surcharges (overloads) »                                                                                                                 |

### Controles UI disponibles

Utiliser `get_mobile_control_reference({ controlName: "..." })` pour obtenir les proprietes config, evenements et children d'un controle.

| Controle           | Categorie  | Utilite                                    | Quand l'utiliser                                                                            |
| ------------------ | ---------- | ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `Label`            | Basic      | Affichage de texte statique ou dynamique   | Titre, libelle de champ, compteur, fond de zone colore                                      |
| `TextBox`          | Input      | Saisie de texte mono-ligne                 | Nom, email, telephone, code, recherche rapide                                               |
| `TextBoxMultiline` | Input      | Saisie de texte multi-lignes               | Commentaire, description, notes longues                                                     |
| `ComboBox`         | Input      | Liste deroulante de selection              | Statut, type, categorie — alimente par SQL ou items statiques                               |
| `CheckBox`         | Input      | Case a cocher (booleen)                    | Actif/inactif, option oui/non, validation                                                   |
| `NumericUpDown`    | Input      | Saisie numerique avec +/-                  | Quantite, compteur, nombre entier                                                           |
| `DateTimePicker`   | Input      | Selecteur de date et/ou heure              | Date de debut/fin, echeance, rendez-vous                                                    |
| `RichTextBox`      | Input      | Editeur de texte riche avec formatage      | Description formatee, email template, rapport                                               |
| `MultiSelect`      | Input      | Selection multiple dans une liste          | Tags, competences, filtres multiples                                                        |
| `Button`           | Action     | Bouton d'action                            | Sauvegarder, supprimer, scanner, ouvrir URL, action metier                                  |
| `UniSearch`        | Data       | Liste de recherche avec colonnes           | Liste principale de donnees (clients, commandes, interventions) — composant le plus utilise |
| `Tree`             | Data       | Arbre hierarchique                         | Catalogue produits par categorie, structure organisationnelle                               |
| `Maps`             | Data       | Carte geographique avec POI                | Localisation clients, itineraires, geolocalisation                                          |
| `Calendar`         | Data       | Calendrier avec evenements                 | Planning, rendez-vous, interventions                                                        |
| `Chart`            | Data       | Graphique (Bar, Line, Pie, Point, Mask)    | Dashboard KPI, statistiques, tableau de bord                                                |
| `Gauge`            | Data       | Jauge graphique                            | Indicateur de progression, KPI                                                              |
| `ShellNode`        | Navigation | Noeud de navigation                        | Barre d'actions en bas d'ecran, panneau embarque vers un sous-ecran                         |
| `PictureBox`       | Media      | Affichage d'image                          | Photo client, logo, image produit (chargee depuis la base)                                  |
| `ImageEditor`      | Media      | Capture et edition de photo                | Prise de photo terrain (camera/galerie), annotation                                         |
| `Signature`        | Media      | Capture de signature tactile               | Validation client, bon de livraison, acceptation                                            |
| `WebBrowser`       | Media      | Contenu web embarque                       | Documentation, page externe, contenu HTML dynamique                                         |
| `VideoPlayer`      | Media      | Lecteur video                              | Tutoriel, demo produit                                                                      |
| `BarcodeScanner`   | Device     | Scanner de codes-barres integre            | Scan produit, inventaire, reception marchandise                                             |
| `Timer`            | System     | Minuteur programmable (non visible)        | Rafraichissement periodique, chronometre, timeout                                           |
| `DynamicFields`    | Advanced   | Champs dynamiques (runtime)                | Formulaires configurables par l'utilisateur, champs custom                                  |
| `Separator`        | Layout     | Ligne de separation visuelle               | Separation entre groupes de champs                                                          |
| `FlowLayout`       | Layout     | Conteneur a disposition automatique        | Disposition flexible de sous-elements                                                       |
| `Badge`            | Basic      | Badge de notification                      | Compteur non-lu, indicateur d'alerte                                                        |

### Groupes de fonctions SwingScript

Utiliser `get_swingscript_reference({ group: "..." })` avec le nom du groupe pour obtenir les signatures exactes.

| Groupe                               | Nb  | Description                                                                                               |
| ------------------------------------ | --- | --------------------------------------------------------------------------------------------------------- |
| `Gestion des variables`              | 39  | Lecture/ecriture de variables shell, script, serveur, initialisation depuis SQL                           |
| `Fonctionnalités internes au script` | 34  | CALL_SCRIPT, INCLUDE, RETURN, ASK, MSGBOX, ASKVALUE, boucles FOREACH                                      |
| `Fonctions de l'arborescence`        | 32  | Navigation (GOTO_FUNCTION, GOTO_NODE), manipulation d'elements par alias/code, toolbox                    |
| `Formulaire`                         | 29  | CONTROL_SET_VALUE, CONTROL_VISIBLE, CONTROL_ENABLE, couleurs, focus, ComboBox, images                     |
| `Application`                        | 29  | Parametres app, theme, badges, changement de societe, evenements reseau                                   |
| `UniSearch`                          | 44  | Rafraichissement, selection, colonnes, recherche, export, themes de cellules, filtres                     |
| `Gestion de chaînes`                 | 24  | CONCAT, REPLACE, FIND, TRIM, LEFT, RIGHT, SUBSTRING, UPPER, LOWER, REGEX                                  |
| `Gestion de fichiers`                | 25  | FILE_OPEN/CLOSE/READ/COPY/DELETE, fichiers INI, PDF, CSV, base64                                          |
| `Gestion des opérations`             | 13  | ADD, SUB, MULT, DIV, MODULO, PERCENT, DATEADD, DATEDIFF, DAYOFWEEK                                        |
| `GPS`                                | 15  | GPS_START/STOP, position, tracking, recording, distance, precision                                        |
| `Maps`                               | 12  | Centre, zoom, series, itineraires, types de carte, POI                                                    |
| `Calendrier`                         | 11  | Selection date/evenement, mode d'affichage, onglets, synchronisation device                               |
| `Communication`                      | 13  | MAIL, SENDSMS, DIAL, SYNCHRO, SEND_TEAMS, ouverture fichiers, orientation                                 |
| `Layers`                             | 13  | Animations, positions magnetiques, alpha, blur, scroll, taille des layers                                 |
| `XML`                                | 12  | Creation/lecture/modification de documents XML, attributs, serialisation                                  |
| `BARCODE`                            | 11  | Scanner codes-barres (camera, peripherique), evenements scan/connexion                                    |
| `Arbre`                              | 8   | TreeView : selection, expand/collapse, drag & drop, refresh                                               |
| `Control`                            | 5   | Alignement, remplissage ComboBox depuis texte                                                             |
| `Control.Calendar`                   | 7   | Refresh, selection, onglets calendrier                                                                    |
| `Control.Chart`                      | 3   | Refresh, affichage series, texte sur graphique                                                            |
| `Multimedia`                         | 4   | Lecture audio/video, enregistrement audio                                                                 |
| `POI`                                | 6   | Points d'interet sur PictureBox (ajout, suppression, selection)                                           |
| `Contact`                            | 5   | Ajout/mise a jour/suppression de contacts device                                                          |
| `Contacts`                           | 5   | Carnet d'adresses device (ajout, suppression, synchronisation)                                            |
| `Database`                           | 4   | Integrite, schema, info champs, import depuis fichier                                                     |
| `Debug`                              | 4   | Console, activation debug, gestion fichiers debug                                                         |
| `Documents`                          | 2   | Serialisation document vers/depuis la base                                                                |
| `DynamicDesigner`                    | 2   | Options et scripts dynamiques sur controles                                                               |
| `DynamicFields`                      | 2   | Champs dynamiques (chargement/sauvegarde)                                                                 |
| `Environnements`                     | 3   | Creation/suppression d'environnements                                                                     |
| `Timer`                              | 3   | Demarrage/arret de timers periodiques                                                                     |
| `WebBrowser`                         | 3   | Contenu HTML depuis URL, fichier ou chaine                                                                |
| `Peer Network`                       | 6   | Serveur de partage d'ecran entre devices                                                                  |
| `Accessoire Nogema`                  | 6   | Connexion hardware Nogema (lecture/ecriture)                                                              |
| `Other`                              | 105 | Bluetooth LE, ports serie, cryptographie (MD5, CRC, base64), JSON avance, PDF, MultiSelectView, et divers |

### Base de donnees : MariaDB

La base de donnees mobile Divalto Weavy utilise **MariaDB** (compatible MySQL). Toutes les requetes SQL dans les scripts SwingScript, les `selectionQuery` de ComboBox, les `query` de Maps/Tree doivent utiliser la **syntaxe MariaDB/MySQL** :

- Concatenation de chaines : `CONCAT(a, b)` (pas `||`)
- Fonctions : `IFNULL()`, `COALESCE()`, `TRIM()`, `NOW()`, `DATE_FORMAT()`
- Guillemets : backticks `` ` `` pour les identifiants reserves, apostrophes `'` pour les chaines
- Pas de `LIMIT x OFFSET y` SQLite — utiliser `LIMIT y, x` ou `LIMIT x OFFSET y` (syntaxe MySQL)
- Booleens : `0` / `1` (pas `true` / `false`)
- Types date : `DATE`, `DATETIME`, `TIMESTAMP`

### Workflow obligatoire

```
Pour creer ou modifier des elements :
1. get_mobile_control_reference({ controlName })   → proprietes config, evenements disponibles
2. get_entities() + get_entity_properties()        → tables et colonnes pour SQL et binding
3. get_swingscript_reference({ search: "..." })    → signature exacte des fonctions
4. Creer/modifier les fichiers JSON et .swing directement sur le filesystem
5. validate_swingscript({ content })               → valider CHAQUE script
6. L'utilisateur review les changements dans le panel Source Control (SCM)
7. L'utilisateur clique "Sync to Server" quand il est satisfait

IMPORTANT — Synchronisation manuelle :
- Les modifications de fichiers NE SONT PAS envoyees automatiquement au serveur
- Les fichiers restent locaux jusqu'a ce que l'utilisateur lance explicitement "Sync to Server"
- Le panel SCM montre les fichiers modifies/ajoutes/supprimes vs l'etat serveur
- L'utilisateur peut annuler (Discard) des changements individuels dans le SCM
```

**Exemple :**

```
Appel : get_entities()
→ trouve "sw_data_intervention" avec colonnes intervention_ID, codeIntervention, ...

Appel : get_entity_properties("sw_data_intervention")
→ { intervention_ID (int, PK), codeIntervention (string), customer_ID (int, FK), ... }

Script SwingScript :
VARINITIALIZE_SCRIPT_BYSQL( "SELECT codeIntervention, customer_ID FROM sw_data_intervention WHERE intervention_ID = '123'" )
```

### Creation et modification — tout se fait par fichiers

Toute creation et modification se fait en editant les fichiers sur le filesystem. L'extension detecte les changements via le panel Source Control (SCM) et les soumet au serveur quand l'utilisateur lance "Sync to Server".

**Pour creer un nouvel element :**

- Creer le dossier/fichier au bon endroit dans l'arborescence `Mobile/`
- Le nommer avec le bon code (le nom du fichier/dossier = le code de l'entite)
- Remplir uniquement les champs metier (label, position, binding...) — PAS d'IDs ni de `_entity`
- Au sync, l'extension detecte le fichier comme "added" et le cree sur le serveur

**Pour modifier un element existant :**

- Editer le fichier JSON ou .swing directement
- Au sync, l'extension detecte le fichier comme "modified" et met a jour le serveur

**Pour supprimer un element :**

- Supprimer le fichier du disque
- Au sync, l'extension detecte le fichier comme "deleted" et supprime sur le serveur

> **Regle d'or** : editer les fichiers, laisser le SCM montrer les changements, sync quand pret.
> **Ne PAS utiliser d'IDs numeriques dans les fichiers.** Les IDs sont geres par `_registry.json` (auto-maintenu).

#### Exemple : creer un bouton avec un script

1. Creer le fichier script metadata :
   `scripts/form/formcustomer_btsave_click.json`

   ```json
   { "label": "Form : Customer / btSave / Click", "scriptType": null, "sourceFile": "formcustomer_btsave_click.swing" }
   ```

2. Creer le fichier script source :
   `scripts/form/formcustomer_btsave_click.swing`

   ```swing
   VARUPDATE_DB_BYID( sw_data_customer, <sql>label = <ctrl>tbName</ctrl></sql>, %CURRENTRECORD_ID% )
   MSGBOX( "Sauvegarde" )
   ```

3. Creer le fichier control :
   `functions/customer/iphone/customersmartphone/details/controls/customerdetails_btsave.json`

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

4. L'extension montre les 3 fichiers dans le panel SCM. L'utilisateur review et sync.

#### Conventions de code

- **Control code** : `{TabCode}_{prefixeType}{NomChamp}` → ex: `customerdetails_btsave`
- **Script code** : `{OverloadCode}_{TabCode}_{ControlCode}_{Event}` → ex: `formcustomer_btsave_click`
- **OverloadID** : injecte automatiquement par l'extension au sync depuis `_project.json`

### Regles d'utilisation MCP

- **Toujours appeler `get_entities`** avant de supposer l'existence d'une table
- **Toujours appeler `get_entity_properties`** avant d'utiliser un nom de colonne dans un SQL, un binding `metaColumnId`, ou un `_hidden-fields.json`
- **Ne jamais inventer** un nom de colonne sans l'avoir verifie via `get_entity_properties`
- **Toujours appeler `validate_swingscript`** apres avoir ecrit un script `.swing` pour verifier sa validite
- Si des erreurs sont retournees, les corriger puis re-valider jusqu'a obtenir `valid: true`

### Workflow de validation des scripts

```
1. Ecrire le script .swing
2. validate_swingscript({ content: "..." })   → erreurs eventuelles
3. Si erreurs → corriger le script et re-valider
4. Repeter jusqu'a valid: true
5. Ecrire le fichier .swing final
```

**Erreurs courantes detectees :**

- Blocs non fermes (`IF` sans `ENDIF`, `WHILE` sans `ENDWHILE`, etc.)
- Parentheses non equilibrees
- Chaines non terminees (guillemet manquant)
- `THEN` manquant apres `IF`
- Labels invalides (`:` manquant apres `#label`)
- `GOTO` vers un label inexistant
- Noms de fonctions inconnus (378 fonctions connues)

---
