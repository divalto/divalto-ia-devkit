---
name: divalto-backend
description: "Crée ou modifie une interface d'échange (import) ou un scheduler Divalto Studio, en JSON sous `Backend/Interfaces/` et `Backend/Schedulers/`. Utiliser pour : « crée un backend », « import CSV vers … », « interface d'échange », « scheduler tous les jours à … », mapper des colonnes source vers destination, planifier ou enchaîner des interfaces. Import seulement."
argument-hint: "Décrivez l'import ou la planification (ex : importer sw_data_marketinginbound.csv dans la table marketinginbound en Add/Update ; ou : tous les jours à 06:00 lancer les 3 interfaces DN…)"
allowed-tools: Read, Write, Edit, Glob, Grep
capabilities: [mobile]
---

# Fabriquer un backend (interface d'import) et un scheduler Divalto

Une **interface backend** décrit un *import* de données : une source (requête SQL sur la base locale, ou fichier CSV) dont chaque enregistrement est écrit dans une table du dictionnaire selon un *mapping* colonne→colonne. Un **scheduler** enchaîne des interfaces et décide *quand* elles tournent.

Ce skill produit des **fichiers JSON sur disque** dans le projet ouvert :

```
<projet>/Backend/
├── _reference.json          ← marqueur « catalogue chargé » (ne pas fabriquer)
├── Interfaces/<Nom>.json    ← une interface (mapping + remplacements imbriqués)
└── Schedulers/<Nom>.json    ← un scheduler (interfaces + sociétés imbriquées)
```

Tu écris le JSON ; **l'extension se charge du push** vers SRV.DatabaseAPI (conversion des enums en codes numériques, insert/update, résolution des FK). Ta responsabilité : un JSON conforme au contrat, avec des valeurs qui existent réellement dans le projet.

## Quand utiliser ce skill

- Créer une interface d'import (SQL→table, ou CSV→table).
- Ajouter/modifier un mapping de colonnes, un filtre de lignes, un recodage.
- Créer un scheduler ou l'activer (planning jours + mois + heures).
- Rattacher des interfaces (et éventuellement des sociétés) à un scheduler.

Ne couvre PAS le moteur d'exécution (externe — Divalto Harmony/One) ni le dictionnaire lui-même : pour créer une table/colonne destination, c'est [`divalto-dictionary`](../divalto-dictionary/SKILL.md).

## Règles dures — lire AVANT d'écrire du JSON

> **MUST — Écrire les enums en clair (le *membre string*), jamais le code numérique.**
> ✅ `"Mode": "AddUpdate"`, `"Format": "MysqlLocal"`, `"PreExport": "Replace"`
> ❌ `"Mode": 3`, `"Format": 8` — l'extension convertit en int au bord HTTP ; un nombre sur disque casse le round-trip.

> **MUST NOT — Ne pas écrire `Type` ni `Out`.** L'échange est **import uniquement** : Studio ne câble plus l'export. Omets `Type` ; l'extension force `In`. N'écris jamais `"Type": "Out"`.

> **MUST NOT — Ne jamais écrire `MetaTable_ID` dans un map.** C'est un champ fantôme absent du contrat DatabaseAPI. La table destination est **toujours dérivée** du `MetaColumn_ID` via le dictionnaire. Ne stocke que `MetaColumn_ID`.

> **MUST — Utiliser des `MetaColumn_ID` réels, jamais inventés.** Chaque map cible une colonne du dictionnaire par son ID numérique. Résous-le depuis le registre du projet : `<projet>/Dictionary/_registry.json` → `MetaColumn["<table>.<colonne>"].id` (forme `{ "MetaColumn": { "contacts.codeContact": { "id": 7814, … } } }`). Un ID inventé écrit dans la mauvaise colonne ou fait échouer le push.

> **MUST — Le `Name` est l'identité serveur.** Le nom de fichier en dérive par percent-encoding des caractères illégaux (`/`→`%2F`, `>`→`%3E`, `:`→`%3A`, etc.). Écris le fichier sous ce nom encodé ; le champ `Name` du JSON garde le nom original exact. Deux items ne peuvent pas partager le même `Name` (unicité insensible à la casse).

> **MUST — Pour un item NEUF, omettre `Model_ID` / `BackInterface_ID` / `BackScheduler_ID`.** Ces IDs viennent du serveur. Les poser sur une création provoque une collision ; les omettre sur une modification transforme l'UPDATE en INSERT. Sur un item déjà poussé, conserve l'ID tel que lu.

## Anatomie d'une interface

```json
{
  "interface": { …SysBackInterfaceModel… },
  "maps":     [ …une entrée par colonne destination… ],
  "replaces": [ …remplacements de valeurs, souvent []… ]
}
```

Le cas dominant : `Format: "MysqlLocal"`, le champ **`File` contient une requête `SELECT`**, et chaque map adresse une colonne du SELECT par sa **position 0-based** (`StartIndex`). Le cas fichier : `Format: "Csv"`, `Folder`+`File` pointent le fichier, `StartIndex` = index de colonne dans le CSV.

### Workflow — fabriquer une interface

1. **Source.** SQL sur la base → `Format: "MysqlLocal"`, `File` = le `SELECT` (colonnes dans l'ordre voulu). Fichier CSV → `Format: "Csv"`, `Folder` (ex `"Backend_Import\\"`) + `File` (ex `"sw_data_x.csv"`), `Separator`, `Header`.
2. **Table destination + colonnes.** Identifie la table cible et, pour chaque colonne à remplir, son `MetaColumn_ID` (registre dictionnaire). La table n'est jamais écrite : elle découle des `MetaColumn_ID`.
3. **Mode d'import** (`Mode`) : `Add` / `Update` / `AddUpdate` / `AddUpdateDelete` / `Delete` / `Reload` / masquages (`Mask`, `DirectMask`, `AddUpdateMask`) / suppressions directes (`DirectDelete`). Voir le tableau des modes dans [reference.md](references/reference.md).
4. **Mapping.** Un map par colonne destination. Adressage exclusif : **Position** (`StartIndex`), **Composition** (`Composition`), **Constante** (`Constant`), ou **Auto-incrément** (`AutoIncrement: true`). La colonne **clé (code unique)** DOIT être mappée. Détail des modes → [reference.md](references/reference.md).
5. **Options utiles :** `PreExport` (`Replace`/`Append`) côté fichier de sortie ; `PostImport` (`Nothing`/`Archive`/`Delete`) après import ; `MergeAction` en cas de collision de clé (`None`/`KeepOriginal`/`KeepNew`) ; `DataFilter` = condition SQL sur les enregistrements existants ; `FlagMessage` = 3 cases empaquetées. Filtre de lignes entrantes = `FilterType`+`StringFilter`.

### Gabarit minimal — import SQL

```json
{
  "interface": {
    "Name": "[MonModule] Import quelque chose",
    "Mode": "AddUpdate",
    "Format": "MysqlLocal",
    "PostImport": "Nothing",
    "PreExport": "Replace",
    "Header": false,
    "StartLine": 1,
    "Separator": ";",
    "TrueValue": "1",
    "FalseValue": "0",
    "File": "SELECT code, label\nFROM sw_data_source\nWHERE …",
    "MergeAction": "None",
    "Category": "[MAIN] Useful interfaces"
  },
  "maps": [
    { "MetaColumn_ID": 4454, "StartIndex": 0, "AutoIncrement": false, "ConstantFilter": false },
    { "MetaColumn_ID": 4455, "StartIndex": 1, "AutoIncrement": false, "ConstantFilter": false }
  ],
  "replaces": []
}
```

Le 1er map (`StartIndex: 0`) cible en général la colonne clé. Aligne l'ordre des colonnes du `SELECT` avec les `StartIndex`.

## Anatomie d'un scheduler

```json
{
  "scheduler": { …SysBackSchedulerModel… },
  "interfaces": [ { "interfaceName": "<Nom exact d'une interface>", "position": 1 } ],
  "companies":  [ ]
}
```

`interfaces[]` liste les interfaces à lancer **dans l'ordre `position`** (1-based), référencées par leur `Name` exact. `companies[]` restreint aux sociétés listées (souvent vide = toutes).

### Règle d'activation (à connaître absolument)

Un scheduler est **actif** ssi les **quatre** conditions sont remplies :

- `DayWeek` non vide — jours de semaine, **0-based, 0 = dimanche … 6 = samedi**, `;`-joint (ex tous les jours : `"0;1;2;3;4;5;6"`)
- `DayMonth` non vide — jours du mois `"01".."31"`, `;`-joint
- `Month` non vide — mois `"01".."12"`, `;`-joint
- **une heure** : soit `FixedSchedules` (liste `HH:mm` `;`-jointe), soit un intervalle valide (`StartInterval` + `EndInterval` + `IntervalDuration` > 0).

Si l'une des trois listes de dates est vide → **inactif**, même avec une heure. Un scheduler qui ne doit pas encore tourner : laisse une liste vide.

Contraintes de saisie : `FixedSchedules` **ne peut pas contenir `00:00`** (rejeté à l'enregistrement) ; `IntervalDuration` doit être **≥ 5** minutes quand il est posé. Pour un top de minuit, préfère un intervalle ou une heure ≠ `00:00`. *(Des définitions héritées peuvent encore contenir `00:00` ; ne le reproduis pas sur une création.)*

> **`Autostart` ≠ activation.** `Autostart` est le *déclencheur d'exécution* runtime, pas la planification. Le laisser à `false` par défaut ; l'activation dépend uniquement des 4 conditions ci-dessus.

### Gabarit — scheduler quotidien à heure fixe

```json
{
  "scheduler": {
    "Name": "[MonModule] Import quotidien",
    "Description": "…",
    "DayWeek": "0;1;2;3;4;5;6",
    "DayMonth": "01;02;03;04;05;06;07;08;09;10;11;12;13;14;15;16;17;18;19;20;21;22;23;24;25;26;27;28;29;30;31",
    "Month": "01;02;03;04;05;06;07;08;09;10;11;12",
    "FixedSchedules": "06:00",
    "Autostart": false
  },
  "interfaces": [
    { "interfaceName": "[MonModule] Import quelque chose", "position": 1 }
  ],
  "companies": []
}
```

Pour un intervalle plutôt qu'une heure fixe : remplace `FixedSchedules` par `"StartInterval": "08:00", "EndInterval": "23:00", "IntervalDuration": 15`.

## Référence complète

Champs exhaustifs, tableaux des codes d'enum, modes de mapping (composition `0+[-]+3`, substring, recode), `FlagMessage`, filtre de lignes, et exemples réels annotés (SQL, CSV, composition, constante, scheduler intervalle) : **[references/reference.md](references/reference.md)**.
