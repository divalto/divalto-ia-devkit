# Référence — interfaces backend & schedulers

Rappel : sur disque, les enums s'écrivent en **membre string**. Les codes numériques ci-dessous sont ce que l'extension envoie au serveur (index = ordre de déclaration, 0-based) — utiles pour comprendre/lire, **jamais à écrire sur disque**.

## Champs d'une interface (`interface`)

| Champ | Type | Rôle |
|---|---|---|
| `Name` | string | **Requis. Identité serveur**, unique (insensible à la casse). |
| `Description` | string? | Libre. |
| `Mode` | enum | Mode d'import (voir table Modes). |
| `Format` | enum | Source (voir table Formats). |
| `File` | string? | **MysqlLocal** : requête `SELECT`. **Csv/Ascii** : nom du fichier. Formats BDD externes : requête / chaîne de connexion. |
| `Folder` | string? | Dossier du fichier (CSV/Ascii), ex `"Backend_Import\\"`. |
| `Separator` | string? | Séparateur de colonnes CSV (ex `";"`). |
| `DecimalSeparator` | string? | Séparateur décimal. |
| `Header` | bool? | Le fichier a une ligne d'en-tête. |
| `StartLine` | number? | 1re ligne de données (souvent `1`). |
| `TrueValue`/`FalseValue` | string? | Représentation des booléens dans la source (souvent `"1"`/`"0"`). |
| `Encoding` | string? | Encodage du fichier. |
| `PostImport` | enum | Après import : `Nothing`/`Archive`/`Delete`. |
| `PreExport` | enum | Sur le fichier de sortie : `Replace`/`Append`/`Archive`/`Nothing`. |
| `MergeAction` | enum | Collision de clé : `None`/`KeepOriginal`/`KeepNew`. |
| `FilterType` + `StringFilter` | enum + string | Filtre des **lignes entrantes** (voir §Filtre de lignes). |
| `DataFilter` | string? | Condition SQL sur les **enregistrements existants** à supprimer/masquer. |
| `RecodeStartIndex` / `RecodeComposition` | number? / string? | Clé de recodage (voir §Recode). |
| `FlagMessage` | string? | 3 booléens empaquetés (voir §FlagMessage). |
| `ExtendedParameters` | string? | XML d'options (CSV parsing…). |
| `Category` | string? | Regroupement d'affichage, ex `"[MAIN] Useful interfaces"`. |
| `ExternalDataSource_ID` | number? | **Requis pour Weavy/Infinity uniquement.** |
| `LoadForeignTable` | bool? | Résolution FK au runtime (forcé `true` au save Studio ; garder `true`). |
| `FullExport`,`EmptyFile`,`ChildCascade`,`InlineData`,`DynamicMapping`,`DataTrackingEnabled` | bool? | Options avancées ; `false` par défaut. |
| `CompanyCodeIndex` | number? | Index de la colonne code société (multi-société). |

Champs **à ne pas écrire** : `Type` (import-only, forcé `In`), `Model_ID`/`BackInterface_ID` sur une création, `ExportQuery` (mort côté Studio).

### Modes (`Mode`)

| Code | Membre | Effet |
|---|---|---|
| 1 | `Add` | Ajoute les nouveaux. |
| 2 | `Update` | Met à jour les existants. |
| 4 | `AddUpdate` | Ajoute + met à jour. |
| 5 | `AddUpdateDelete` | Ajoute + met à jour + **supprime les absents** de la source. |
| 3 | `Delete` | **Supprime les enregistrements absents** de la source. |
| 9 | `DirectDelete` | **Supprime les enregistrements présents** dans la source. |
| 7 | `Mask` | **Masque** (hide) les absents de la source. |
| 10 | `DirectMask` | Masque les présents dans la source. |
| 8 | `AddUpdateMask` | Ajoute + met à jour + masque les absents. |
| 6 | `Reload` | Rechargement complet (sémantique runtime exacte non détaillée dans la source accessible). |
| 0 | `Unknown` | Non renseigné — à éviter sur une création. |

« Mask » = **masquer** un enregistrement, pas un masque de saisie.

### Formats (`Format`)

| Code | Membre | Note |
|---|---|---|
| 8 | `MysqlLocal` | **Cas dominant.** `File` = requête `SELECT` sur la base locale. |
| 1 | `Csv` | `Folder`+`File`, `Separator`, `Header`. |
| 2 | `Ascii` | Fichier à largeur fixe. |
| 3 | `Xml` | |
| 6/7 | `Mysql`/`Sqlserver` | Base externe (chaîne de connexion). |
| 4/5 | `Oledb`/`Odbc` | Base externe. |
| 9 | `Folder` | |
| 10/11 | `Weavy`/`Infinity` | **Requiert `ExternalDataSource_ID`** (pas de chaîne de connexion). |
| 0 | `Unknown` | À éviter. |

### Autres tables de codes

- **PostImport** : 0 `Unknown`, 1 `Nothing`, 2 `Delete`, 3 `Archive`.
- **PreExport** : 0 `Unknown`, 1 `Nothing`, 2 `Archive`, 3 `Replace`, 4 `Append`.
- **MergeAction** : 0 `None`, 1 `KeepOriginal`, 2 `KeepNew` (pas de `Unknown`).
- **FilterType** : 0 `Unknown`, puis `Inc*` (1–8) et `Ex*` (9–16) — voir §Filtre de lignes.

## Mapping (`maps[]`)

Une entrée par **colonne destination**. Champs d'une entrée (`BackInterfaceMap`) :

| Champ | Rôle |
|---|---|
| `MetaColumn_ID` | **Colonne destination** (ID dictionnaire). Seul lien vers la table cible. |
| `StartIndex` | Mode **Position** : index 0-based de la colonne source. |
| `Composition` | Mode **Composition** : expression (voir plus bas). |
| `Constant` | Mode **Constante** : valeur fixe (pas de `StartIndex`). |
| `AutoIncrement` | Mode **Auto-incrément** : `true` → bypasse toute autre contrainte de mapping. |
| `ConstantFilter` | Présent partout ; `false` par défaut. |
| `SubStringStartIndex` / `SubStringEndIndex` | Extraction sur la valeur source. ⚠ `SubStringEndIndex` est une **longueur**, pas un index (label Studio « Substring length »). |
| `EndIndex` | Fin de plage (rare). |
| `DateFormat` | Format de date de la source. |
| `NumInteger` / `NumDecimal` | Format numérique. |
| `FieldForeignTable` | Champ de résolution FK. |
| `DefaultValue` | Valeur par défaut si source vide. |
| `Transform` / `TransformConfig` | Transformation (rare). |

Les 4 modes d'adressage sont **exclusifs** par map. La colonne **clé (code unique)** DOIT être mappée avant que l'interface soit valide.

### Syntaxe de composition

Tokens joints par `+`. Un **nombre nu** = index de colonne source ; `[X]` = **littéral** `X`.

- `"0+[-]+3"` → `colonne0` + `"-"` + `colonne3`
- `"0+[-]+4+[-]+5"` → `col0-col4-col5`

Sert à fabriquer une clé/valeur composite (souvent la colonne clé).

### Recode

`RecodeStartIndex` (index de colonne) **ou** `RecodeComposition` (composition) construisent une valeur-clé par ligne ; `MergeAction` tranche en cas de collision. Import BDD/CSV seulement. *(Rare ; sémantique runtime exacte non détaillée — ne l'ajoute que si demandé.)*

## Filtre de lignes (`FilterType` + `StringFilter`)

Filtre les **lignes entrantes** de la source. `FilterType` = préfixe `Inc` (garder si match) / `Ex` (exclure si match) + critère :

- Sur la **ligne entière** : `Beg` (commence par) / `Cont` (contient) / `End` (finit par). `StringFilter` = la valeur seule.
- Sur une **colonne** : `ColBeg`/`ColCont`/`ColEnd`/`ColEqual`/`ColEmpty`. `StringFilter` packé `"<colonne>;<valeur>"`. `ColEmpty` teste la présence → **pas de valeur**.

Exemples : `FilterType: "IncColEqual"`, `StringFilter: "statut;actif"` (garder les lignes où colonne `statut` = `actif`). Absence de filtre → `FilterType: "Unknown"` (le cas le plus courant).

**≠ `DataFilter`** : `DataFilter` est une condition SQL sur les enregistrements **déjà en base** (à supprimer/masquer), ex `"YEAR(holidayDate) IN (YEAR(CURDATE()), YEAR(CURDATE()) +1)"`.

## FlagMessage

3 booléens empaquetés, membres activés joints par `;` dans l'ordre **fixe** :

1. `foreachFile` — traiter chaque fichier séparément.
2. `hideDuplicateError` — masquer les erreurs de doublon.
3. `hideNullableError` — masquer l'erreur « code unique vide ».

Ex : `"hideDuplicateError"`, ou `"foreachFile;hideDuplicateError"`. Aucun → champ absent/vide.

## `ExtendedParameters` (options CSV courantes)

```xml
<?xml version="1.0" encoding="utf8"?><intechangeOptions><csvParsingMode>strict</csvParsingMode><csvQuoteChar>"</csvQuoteChar><csvEscapeChar>"</csvEscapeChar><csvCommentChar>&#x0;</csvCommentChar></intechangeOptions>
```

## Champs d'un scheduler (`scheduler`)

| Champ | Rôle |
|---|---|
| `Name` | Requis, identité serveur, unique. |
| `DayWeek` | Jours de semaine `;`-joints, **0-based, 0=dimanche**. |
| `DayMonth` | Jours du mois `"01".."31"` `;`-joints. |
| `Month` | Mois `"01".."12"` `;`-joints. |
| `FixedSchedules` | Heures fixes `HH:mm` `;`-jointes. **`00:00` interdit** au save. |
| `StartInterval` / `EndInterval` / `IntervalDuration` | Créneau + pas en minutes (**≥ 5**). Alternative à `FixedSchedules`. |
| `Autostart` | Déclencheur d'exécution runtime (≠ activation). `false` par défaut. |
| `ConditionFolder` / `ConditionFile` / `EndFile` | Fichiers de condition (avancé). |
| `MailTrigger` / `AddEvent` | Notifications (avancé). |

**Actif ssi** `DayWeek` ∧ `DayMonth` ∧ `Month` ∧ (une heure) sont tous renseignés. Une liste vide → inactif.

Rattachements : `interfaces[]` = `{ interfaceName, position }` (par `Name` exact, ordre `position` 1-based) ; `companies[]` = `{ companyCode, position }` (vide = toutes sociétés).

---

## Exemples annotés

### 1. Import SQL → table (`MysqlLocal`, mapping par position)

`[EventTypes] Add new event types to Project` — maps tronqués :

```json
{
  "interface": {
    "Name": "[EventTypes] Add new event types to Project",
    "Mode": "Add", "Format": "MysqlLocal",
    "PostImport": "Nothing", "PreExport": "Replace",
    "Header": false, "StartLine": 1, "Separator": ";",
    "TrueValue": "1", "FalseValue": "0",
    "File": "SELECT cet.codeConfeventtype, cet.label, cet.functionName …\nFROM sw_data_confeventtype AS cet\nWHERE cet.codeConfeventtype NOT IN (SELECT et.codeeventtype FROM sw_data_eventtype AS et)",
    "FlagMessage": "hideDuplicateError",
    "MergeAction": "None", "Category": "[MAIN] Useful interfaces"
  },
  "maps": [
    { "MetaColumn_ID": 4454, "StartIndex": 0, "AutoIncrement": false, "ConstantFilter": false },
    { "MetaColumn_ID": 4455, "StartIndex": 1, "AutoIncrement": false, "ConstantFilter": false }
  ],
  "replaces": []
}
```

Colonne 0 du SELECT (`codeConfeventtype`, la clé) → `MetaColumn_ID 4454` ; colonne 1 (`label`) → `4455`. `Mode: Add` + `hideDuplicateError` = « n'ajouter que les types absents ».

### 2. Import CSV (`Csv`, `Folder`+`File`)

`[Marketing inbound] Import` :

```json
{
  "interface": {
    "Name": "[Marketing inbound] Import",
    "Mode": "AddUpdate", "Format": "Csv",
    "PostImport": "Archive", "PreExport": "Append",
    "Folder": "Backend_Import\\", "File": "sw_data_marketinginbound.csv",
    "Separator": ";", "Header": false, "StartLine": 1,
    "MergeAction": "KeepOriginal", "Category": "[MAIN] Useful interfaces"
  },
  "maps": [
    { "MetaColumn_ID": 5976, "StartIndex": 0, "AutoIncrement": false, "ConstantFilter": false },
    { "MetaColumn_ID": 5981, "StartIndex": 1, "AutoIncrement": false, "ConstantFilter": false }
  ],
  "replaces": []
}
```

Les `StartIndex` référencent l'ordre des colonnes du CSV (pas forcément séquentiel selon le mapping voulu). `PostImport: Archive` = déplacer le CSV après import.

### 3. Composition — clé composite

`[Global] RGPD - create customercontactextension`, un map parmi d'autres :

```json
{ "MetaColumn_ID": 5689, "Composition": "0+[-]+4+[-]+5" }
```

Concatène `col0-col4-col5` pour alimenter la colonne clé `5689`. Les autres colonnes restent en mode Position.

### 4. Constante

`[Migrate] Contract - version = 2` : forcer une colonne à une valeur fixe.

```json
{
  "interface": { "Name": "[Migrate] Contract - version = 2", "Mode": "Update", "Format": "MysqlLocal",
    "File": "SELECT codecontract FROM sw_data_contract WHERE version = 1" },
  "maps": [
    { "MetaColumn_ID": 4634, "StartIndex": 0, "AutoIncrement": false, "ConstantFilter": false },
    { "MetaColumn_ID": 6571, "Constant": "2", "AutoIncrement": false, "ConstantFilter": false }
  ],
  "replaces": []
}
```

Colonne clé mappée par position (col0) ; colonne `6571` forcée à `"2"` (constante, pas de `StartIndex`).

### 5. Scheduler — heure fixe quotidienne

`[SWS] Contract closing (daily)` (extrait) :

```json
{
  "scheduler": {
    "Name": "[SWS] Contract closing (daily)",
    "DayWeek": "0;1;2;3;4;5;6",
    "DayMonth": "01;02;…;31", "Month": "01;02;…;12",
    "FixedSchedules": "06:00", "Autostart": false
  },
  "interfaces": [
    { "interfaceName": "Adjust contract closing date", "position": 1 },
    { "interfaceName": "Close contract (status)", "position": 2 }
  ],
  "companies": []
}
```

*(Le fichier hérité utilise `00:00` ; sur une création, choisis une autre heure — `00:00` est rejeté au save.)*

### 6. Scheduler — intervalle

`[SWB] Action plan result` : toutes les heures, tous les jours.

```json
{
  "scheduler": {
    "Name": "[SWB] Action plan result",
    "DayWeek": "0;1;2;3;4;5;6",
    "DayMonth": "01;…;31", "Month": "01;…;12",
    "StartInterval": "00:00", "EndInterval": "23:55", "IntervalDuration": 60,
    "Autostart": false
  },
  "interfaces": [ { "interfaceName": "…", "position": 1 } ],
  "companies": []
}
```

Un scheduler **sans `DayWeek`** est **inactif** malgré un intervalle défini (une des trois listes de dates manque).
