# Datasources — divalto-page-ui

> **Source de vérité : les outils MCP.**
> Avant d'écrire un datasource, valider sa structure avec :
>
> - `validate_divalto_file({ type: "datasource", content })` — schéma datasource
>
> Pour connaître les entités et champs disponibles (lorsque le projet expose un dictionnaire), s'appuyer sur les outils du dictionnaire d'entités (`get_entities` / `get_entity_properties` lorsque disponibles).
>
> **`odkSource` — capacité par projet, vérifiée via les tools MCP.** Le type `odkSource` (datasource qui invoque une méthode C# via `MethodName` / `ModuleName` / `NameSpace`) est gated par la capacité projet `odk`. Signal fiable, comme pour le SQL en ERP ci-dessous : `list_datasource_types` omet `odkSource` et `get_datasource_properties` le refuse quand `odk` est inactif — jamais une question à l'utilisateur. Capacité active → déléguer au skill `divalto-odk` (référence `datasource.md`) (paire JSON + méthode C#). Capacité inactive → ne pas produire, constat direct + orientation vers script TS, datasource SQL équivalent, ou story dédiée. Détails dans `SKILL.md` step 6. Tout le reste est couvert ci-dessous ou signalé comme « non couvert » en fin de document.

> **SGBD — MariaDB.** La base de données du CRM Divalto est **MariaDB** : tout `.sql.sql` et tout `SelectSql` inline est du SQL dialecte MariaDB (fonctions déjà illustrées dans ce document : `IFNULL`, `COALESCE`, `GROUP_CONCAT`, `CONCAT`, `FIND_IN_SET`, `CONVERT(expr, UNSIGNED)`).

> **Projet ERP (Infinity) — le SQL brut n'existe pas.** Tout ce document décrit le mécanisme SQL du moteur CRM/weavy. Sur un projet ERP, ce mécanisme est **absent du moteur** : ce n'est pas une préférence de style ni une dette à migrer, un datasource SQL n'y est pas exécutable. Sont donc interdits, quel que soit le contexte : le type `sql` et tous les types qui en dérivent (`gridSource`, `scalar`, `rowaccess`, `listSource`, `metricSource`, `graphSource`, `gaugeSource`, `mapSource`, `pivotInfoSource`, `schedulerSource`, `iconSource`, `sessionSource`, `stepsSource`…), les propriétés `SelectSql`, `SelectQueryName`, `InsertSql`, `UpdateSql`, `DeleteSql`, `Aliases`, et tout fichier compagnon `.sql.sql`.
>
> **À utiliser à la place :** `odkSource` (appel d'une méthode C# ODK) et la famille Infinity — `entitySource`, `infinityListSource`, `infinityScalarSource`, `infinityMetricSource`, `infinityGraphSource`, `infinityGaugeSource`, `infinityMapSource`, `infinityZoomSource`, `infinityComboSource`, `infinityComboZoomSource`, `infinityNotesSource`, `infinityAttachedFilesSource`, `infinitywidget`.
>
> **Si le projet ERP n'a pas la capacité ODK**, `odkSource` n'est pas disponible non plus (même signal `list_datasource_types`/`get_datasource_properties` que ci-dessus) : ne pas produire de datasource. Constater directement que le projet n'a ni SQL ni ODK et l'indiquer à l'utilisateur — l'activation d'une capacité relève de la configuration projet, pas d'une question de vérification. Ne jamais retomber sur du SQL « en attendant ».
>
> Cette règle est appliquée par les outils MCP, pas seulement documentée ici : en ERP, `list_datasource_types` ne renvoie pas ces types, `get_datasource_properties` les refuse, et `validate_divalto_file` invalide tout fichier qui en porte la trace. Un contournement échouera à la validation.

---

## Règles MUST

À appliquer **avant** de regarder les exemples plus bas — un exemple qui ne respecte pas ces règles est fautif, pas un modèle.

1. **`SelectSql` inline réservé aux requêtes simples et courtes.** Une requête **complexe** — `JOIN`s, sous-requêtes, ou au-delà d'un seuil pratique de **~100 caractères** — se déplace dans un fichier compagnon **`<nom>.<datasourceType>.sql.sql`** (le segment reflète le `Type` du datasource : `scalar` → `…scalar.sql.sql`, `grid` → `…grid.sql.sql`…), référencé via `SelectQueryName` (= le nom du fichier **sans** `.sql.sql`). Un `FROM` simple et court en inline reste valide. (Seuil non documenté formellement — convention équipe.)
   - ❌ requête longue/complexe (`JOIN`s, sous-requêtes, > ~100 car.) en `SelectSql` inline → la déplacer en `.sql.sql` via `SelectQueryName`.
   - ✅ `{ "Type": "scalar", "SelectSql": "SELECT NOW()" }` (court, sans table)
   - ✅ `{ "Type": "sql", "SelectSql": "SELECT c.name FROM {{TABLE(customer, c)}} WHERE {{FILTERS}}" }` (court — inline valide)
   - ✅ `{ "Type": "sql", "SelectQueryName": "customer.grid" }` + fichier voisin `customer.grid.sql.sql` (requête complexe en fichier).

2. **Macro `{{TABLE(entity, alias)}}` au lieu de `FROM sw_data_entity AS alias`.** Inconditionnel pour tout `FROM` / `JOIN` sur une table métier (`sw_data_*`), **inline `SelectSql` comme fichier `.sql.sql`** : la macro applique automatiquement le contrôle d'accès ligne. Pas d'exception « si pas de row access prévu » — l'ajout d'un `rowaccess` plus tard ne doit pas obliger à rééditer chaque requête.
   - ❌ Double-alias : `{{TABLE(orderheader, oh)}} as oh` — la macro injecte **déjà** `AS oh`, le `as oh` ajouté produit `… AS oh as oh`, SQL invalide au runtime. Ne jamais ajouter `as <alias>` derrière `{{TABLE(...)}}`.
   - ✅ `FROM {{TABLE(orderheader, oh)}}` (l'alias `oh` est porté par la macro).
   - ❌ `FROM sw_data_customer AS c`, `INNER JOIN sw_data_customercontact AS cc ON ...`
   - ✅ `FROM {{TABLE(customer, c)}}`, `INNER JOIN {{TABLE(customercontact, cc)}} ON ...`
   - Les tables système (`sw_sys_*`) et les tables techniques de traduction peuvent rester en référence directe — elles ne portent pas de row access.

3. **`listSource` : `IdField` / `LabelField` (jamais `Id` / `Label`).** Les propriétés sont nommées avec le suffixe `Field`.
   - ❌ `{ "Type": "listSource", "Id": "...", "Label": "..." }`
   - ✅ `{ "Type": "listSource", "IdField": "...", "LabelField": "..." }`

4. **`metricSource` : `MainValueField` est requis.** Une métrique sans `MainValueField` est non fonctionnelle.
   - ❌ `{ "Type": "metricSource", "SelectQueryName": "...", "Formatters": { ... } }` (pas de `MainValueField`)
   - ✅ `{ "Type": "metricSource", "SelectQueryName": "...", "MainValueField": "amount" }`

5. **Traduction : `COALESCE` avec les colonnes réelles du projet, dans l'ordre du fallback.** Préférer `COALESCE(...)` à `IFNULL(... IFNULL(...))` imbriqué pour la lisibilité et parce que c'est SQL standard.
   - **Cas simple — entité avec une `translationKey` sur la même ligne** (pattern de `customertype.listSource.sql.sql` du projet) :
     ```sql
     SELECT COALESCE(g.translationKey, g.label) AS translationKey, g.generictype_ID
     FROM {{TABLE(generictype, g)}}
     WHERE g.dataType = 'CUSTOMER_TYPE'
     ```
   - **Cas avec traduction système** (pattern de `expensestat.list.sql.sql`) : joindre `sw_sys_languagetext` via `{{languageCode}}` et empiler le fallback :
     ```sql
     SELECT COALESCE(lt.text, g.translationKey, g.label) AS translatedLabel, g.generictype_ID
     FROM {{TABLE(generictype, g)}}
     LEFT JOIN sw_sys_language AS l ON l.codeLanguage = {{languageCode}}
     LEFT JOIN sw_sys_languagetext AS lt
       ON lt.language_ID = l.language_ID
       AND lt.codeLanguageText = g.translationKey
     WHERE g.dataType = 'CUSTOMER_TYPE'
     ```
   - ❌ `IFNULL(g.translationKey, IFNULL(lt.text, g.label))` — imbrication d'`IFNULL` pour un fallback multi-niveaux.
   - ❌ Inventer un 4e niveau de fallback non observé (`originalCode`, etc.) sans justification documentée.

6. **L'id d'un datasource est le nom de son fichier `.datasource.json`, sans `.datasource.json` — jamais celui du `.sql.sql`.** Tout appelant le désigne par cet id exact : `DataSource` dans un JSON de page, et `$datasource` dans un `.scriptlibrary.ts`. Un id qui se termine par `.sql` est toujours une erreur : le `.sql.sql` n'est pas un datasource, c'est la requête d'un datasource, référencée par `SelectQueryName`.
   - ❌ `$datasource(...)` appelé avec `customerContact.id.lastInteraction.sql` → au runtime, HTTP 500 sur `/api/remoteActions/Execute/…` avec « Cannot find datasource ».
   - ✅ fichiers `customerContact.id.lastInteraction.datasource.json` + `customerContact.id.lastInteraction.sql.sql`, datasource contenant `"SelectQueryName": "customerContact.id.lastInteraction"`, appelant utilisant l'id `customerContact.id.lastInteraction`.
   - Un datasource référencé par un appelant mais absent du périmètre d'édition n'est pas résoluble côté serveur : le créer dans le même tour, et vérifier qu'il apparaît dans le panneau SCM avant de conclure.

---

## Vue d'ensemble

Un datasource Divalto est un **descripteur JSON** (`<nom>.datasource.json`) qui peut être accompagné d'un **fichier SQL** (`<nom>.sql.sql`) lorsqu'il référence une requête nommée via `SelectQueryName`. Le type est porté par le champ discriminateur `Type` (PascalCase pour la propriété, kebab/camel pour la valeur).

```json
{
  "Type": "sql",
  "SelectQueryName": "customer.grid"
}
```

`SelectQueryName: "customer.grid"` ↔ fichier voisin `customer.grid.sql.sql`.

Alternative SQL inline pour une requête **courte et simple** (cf. règle MUST n°1 plus haut) :

```json
{
  "Type": "scalar",
  "SelectSql": "SELECT '07:00:00'"
}
```

Pour toute requête non triviale (`FROM` métier, jointures, agrégats), utiliser `SelectQueryName` + fichier `.sql.sql` voisin.

---

## Types principaux

### `sql` — Requête SQL nommée

Le type le plus courant. Référence une requête SQL via `SelectQueryName`.

```json
{
  "Type": "sql",
  "SelectQueryName": "customer.grid",
  "TableName": "customer",
  "PrimaryKey": "customer_ID_primaryKey",
  "Usages": {
    "listSource": {
      "Type": "listSource",
      "IdField": "customer_ID_primaryKey",
      "LabelField": "customerName"
    },
    "gridSource": {
      "Type": "gridSource",
      "IsReadOnlyField": "mandatory"
    }
  },
  "Aliases": {
    "contactName": "TRIM(CONCAT(IFNULL(cc.firstName,''), ' ', IFNULL(cc.lastName,'')))"
  },
  "Formatters": {
    "_createDate": { "Type": "date", "Format": "d" },
    "amount":      { "Type": "number", "Format": "n2" }
  }
}
```

### `table` — Accès direct à une table (CRUD)

Pour les opérations de lecture/écriture sur une table (typiquement la source d'un composant `crud`).

Seul `TableName` est requis. Les autres propriétés sont **optionnelles**, à n'ajouter qu'au besoin — une fiche `crud` minimale se réduit à `{ "Type": "table", "TableName": "<table>" }` :

- `PrimaryKey` — requis **uniquement** pour sélectionner des items, par ex. une grille en mode multisélection ; superflu sur une fiche mono-enregistrement.
- `ContextFields` — mappe des paramètres de contexte vers des champs de la table (cf. section dédiée plus bas).
- `Columns` — sémantique par colonne (blob, contraintes de validation) ; à ne déclarer que pour les champs concernés.
- `Constraints` — validation serveur portant sur la ligne complète.

> **CRM uniquement.** La contrainte `sqlquery` porte une requête SQL (`Sql`) : interdite sur un projet ERP, où `validate_divalto_file` invalide le fichier qui la contient.
>
> Placement colonne vs table, et validation d'une entrée isolée : voir [`Constraints` — validation côté serveur](#constraints--validation-côté-serveur) plus bas.

```json
{
  "Type": "table",
  "TableName": "customer",
  "PrimaryKey": "customer_ID",
  "ContextFields": [
    { "DatabaseFieldName": "customer_ID" },
    { "ContextParameterName": "baseUser", "DatabaseFieldName": "baseuser_ID" },
    { "ContextParameterName": "ctx_type_ID", "DatabaseFieldName": "type_ID", "Optional": true }
  ],
  "Columns": {
    "binaryData": {
      "Blob": { "Mimetype": "image/jpeg" }
    },
    "fileName": {
      "Blob": { "FilenameFieldname": "fileName" }
    }
  },
  "Constraints": [
    {
      "Type": "sqlquery",
      "Sql": "SELECT CASE WHEN {{startDate}} != '' AND {{endDate}} != '' THEN DATE({{startDate}}) <= DATE({{endDate}}) ELSE 1 END",
      "ErrorMessage": "BO_Error_StartDate_EndDate"
    }
  ]
}
```

### `listSource` — Liste de sélection

Alimente les combobox et listes déroulantes.

```json
{
  "Type": "listSource",
  "SelectQueryName": "contractModel.listSource",
  "IdField": "contractmodel_ID",
  "LabelField": "label"
}
```

### `scalar` — Valeur unique

Retourne une seule valeur (un seul champ, une seule ligne).

```json
{
  "Type": "scalar",
  "SelectQueryName": "customer.totalOutstanding.scalar"
}
```

Ou avec SQL inline :

```json
{
  "Type": "scalar",
  "SelectSql": "SELECT '07:00:00'"
}
```

### `hierarchical` — Arbre parent/enfant

Pour les arborescences simples (une seule entité, lien `parent_ID`).

```json
{
  "Type": "hierarchical",
  "SelectQueryName": "productFamily.hierarchical",
  "IdField": "productfamily_ID",
  "LabelField": "labelNotNull",
  "ParentIdField": "productfamily_ID_parentFamily",
  "OrderField": "label",
  "LazyLoading": true
}
```

### `treeviewSource` — Arbre nœuds + feuilles

Structure double : nœuds et feuilles peuvent venir de sources différentes.

```json
{
  "Type": "treeviewSource",
  "DataSourceNode": {
    "SelectQueryName": "tree.treeviewSource.node",
    "IdField": "tree_ID",
    "LabelField": "label",
    "IconField": "icon",
    "ParentIdField": "tree_ID_Parent"
  },
  "DataSourceLeaf": {
    "IdField": "baseuser_ID",
    "LabelField": "fullDesc",
    "SelectQueryName": "user.treeviewSource.leaf"
  }
}
```

### `sessionSource` — Variables de session

Charge des valeurs dans la session utilisateur (capacités, flags, configuration runtime).

```json
{
  "Type": "sessionSource",
  "SelectQueryName": "myAccount.isValidAccount.sessionSource",
  "KeyField": "keyName",
  "ValueField": "isValidAccount",
  "VisibilityField": "visibility",
  "ConvertTypeField": "convertType"
}
```

### `rowaccess` — Contrôle d'accès ligne

Définit un filtre de sécurité au niveau ligne, appliqué automatiquement via la macro `{{TABLE(entity, alias)}}` dans les requêtes consommatrices.

```json
{
  "Type": "rowaccess",
  "TableName": "intervention",
  "RowIdField": "intervention_ID",
  "SelectQueryName": "intervention.rowaccess"
}
```

### `metricSource` — KPI

Pour les composants `metric` (badge avec valeur + couleur).

```json
{
  "Type": "metricSource",
  "SelectQueryName": "customer.outstanding.total.metricSource",
  "MainValueField": "amount",
  "BadgeColorField": "badgeColor",
  "LegendField": "lng:legend",
  "Formatters": {
    "MainValueField": { "Type": "number", "Format": "n2" }
  }
}
```

| Propriété         | Description                                                         |
| ----------------- | ------------------------------------------------------------------- |
| `MainValueField`  | **Requis** — champ contenant la valeur principale (cf. règle MUST n°4) |
| `BadgeColorField` | Champ pour la couleur du badge (optionnel)                          |
| `LegendField`     | Champ de légende, préfixe `lng:` pour clé de traduction (optionnel) |

### `graphSource` — Données de graphique

```json
{
  "Type": "graphSource",
  "SelectQueryName": "product.top10.series.graphSource",
  "AbscissValueField": "codeField",
  "AbscissLabelField": "labelField",
  "Formatters": {
    "amount": { "Type": "number", "Format": "n2" }
  }
}
```

| Propriété           | Description                                       |
| ------------------- | ------------------------------------------------- |
| `AbscissValueField` | Champ pour les valeurs de l'axe X (optionnel)     |
| `AbscissLabelField` | Champ pour les libellés de l'axe X (optionnel)    |

### `gaugeSource` — Jauge

```json
{
  "Type": "gaugeSource",
  "ValueField": "percentage",
  "SelectQueryName": "analysis.current.gaugeSource"
}
```

### `pivotInfoSource` — Informations pivot

Pour les composants `planning` avec pivot (libellés latéraux).

```json
{
  "Type": "pivotInfoSource",
  "TitleField": "mainValue",
  "SubTitleField": "secondValue",
  "Aliases": {
    "mainValue":   "CONCAT(firstName, ' ', lastName)",
    "secondValue": "roleName"
  },
  "SelectQueryName": "planning.pivot.infos.pivotInfoSource"
}
```

### `schedulerSource` — Calendrier / planning

```json
{
  "Type": "schedulerSource",
  "TableName": "intervention",
  "SerieField": "sId",
  "IdField": "id",
  "StartField": "startDate",
  "EndField": "endDate",
  "ColorField": "color",
  "TitleField": "title",
  "SelectQueryName": "intervention.schedulerSource"
}
```

### `mapSource` — Géolocalisation

```json
{
  "Type": "mapSource",
  "SelectQueryName": "visitreport.position.mapSource",
  "LabelField": "visitMapLabel",
  "LongitudeField": "gpsLongitude",
  "LatitudeField": "gpsLatitude",
  "PinColorField": "pinColor"
}
```

### `iconSource` — Icône avec compteur

```json
{
  "Type": "iconSource",
  "IconField": "iconField",
  "ExponentField": "countField",
  "SelectQueryName": "notificationBar.sysNotification"
}
```

---

## Autres types (sans détail)

Documentés ailleurs ou peu utilisés dans le périmètre page UI :

- `kanbanItemsSource` / `kanbanColumnsSource` — Tableau kanban
- `signedDocument` — Document signé
- `reportGenerator` — Génération de rapport
- `dataViz` — Visualisation de données
- `defaultValue` — Valeur par défaut

---

## Propriétés transversales

### `Usages` — multi-usage d'un même datasource

Réutilise une seule requête pour plusieurs rôles. Typique : la même requête nourrit une grille **et** une combobox (listSource).

```json
"Usages": {
  "listSource": {
    "Type": "listSource",
    "IdField": "entity_ID",
    "LabelField": "entityName"
  },
  "gridSource": {
    "Type": "gridSource",
    "IsReadOnlyField": "isReadOnly"
  }
}
```

### `Aliases` — expressions SQL calculées

Déclarées au niveau du datasource et injectables par leur nom dans la requête.

```json
"Aliases": {
  "fullName": "CONCAT(firstName, ' ', lastName)",
  "statusLabel": {
    "Content": "COALESCE(lt.text, gt.translationKey, gt.label)",
    "NoAlias": true
  }
}
```

`NoAlias: true` — l'expression est inlinée sans `AS <name>`.

### `Formatters` — formatage d'affichage

Appliqués à l'affichage, sans changer la valeur stockée.

| `Type`   | `Format`        | Effet                              |
| -------- | --------------- | ---------------------------------- |
| `date`   | `d`             | Date courte (selon locale)         |
| `date`   | `g`             | Date + heure                       |
| `date`   | `t`             | Heure seule                        |
| `number` | `n0`/`n1`/`n2`  | Nombre, 0 / 1 / 2 décimales        |
| `number` | `p1`            | Pourcentage avec 1 décimale        |

```json
"Formatters": {
  "createdDate": { "Type": "date",   "Format": "d" },
  "amount":      { "Type": "number", "Format": "n2" },
  "discount":    { "Type": "number", "Format": "p1" }
}
```

Format dynamique via variable :

```json
"amount": { "Variable": "config.alias.orderlineMaskPrice" }
```

### `ContextFields` — paramètres de contexte (type `table`)

```json
"ContextFields": [
  { "DatabaseFieldName": "entity_ID" },
  { "ContextParameterName": "baseUser", "DatabaseFieldName": "baseuser_ID" },
  { "ContextParameterName": "parentId", "DatabaseFieldName": "parent_ID", "Optional": true }
]
```

### `Constraints` — validation côté serveur

> **Source de vérité = MCP `divalto-studio`.** `list_constraint_types` renvoie les types de contrainte disponibles ; `get_constraint_properties({ constraint: "<type>" })` renvoie leurs champs avec leur description, lus depuis le schéma. Découvrir les types et leurs champs via ces outils — ne pas se fier à une liste figée.
>
> La valeur à écrire dans `Type` est la **clé en minuscules** renvoyée par `list_constraint_types` (`"Type": "required"`). Le nom de la classe de configuration visible ailleurs dans les schémas (`RequiredConstraintConfig`, `SqlQueryConstraintConfig`…) n'est **pas** un `Type` valide.
>
> **Deux positions, deux familles.** Une contrainte de **colonne** va dans `Columns.<field>.Constraints` ; une contrainte de **table** va dans le `Constraints` racine (datasource ou `.schema.json` d'entité). Le schéma ne force pas ce placement — les deux classes de base sont permissives (`additionalProperties: true`, pas de `Type` en enum) — donc une contrainte posée au mauvais endroit **valide quand même** et est ensuite **silencieusement ignorée** au runtime.
>
> | Position                               | Contraintes                                          |
> | --------------------------------------- | ----------------------------------------------------- |
> | `Constraints` racine (table)            | `unique`, `sqlquery`                                  |
> | `Columns.<field>.Constraints` (colonne) | `required`, `email`, `maxlength`, `numeric`, `pattern` |
>
> Cette répartition n'est dérivable d'aucun outil MCP (`get_constraint_properties` ne renvoie que des champs ; `list_constraint_types` ne renvoie que `name`/`title`, sans famille). Pour un type qui n'apparaît pas dans ce tableau, vérifier sa famille dans le schéma plutôt que la supposer.
>
> **Valider une entrée isolée.** La validation de fichier entier ne rejette rien sur ce point (les deux bases sont permissives) : un `Constraints` avec un `Type` invalide **passe** la validation du fichier complet. Utiliser `validate_divalto_file({ type: "constraint", content: JSON.stringify({ Type: "required" }) })` pour valider une seule entrée contre le schéma `constraint` — c'est le seul mécanisme qui rejette un `Type` invalide.
>
> **`sqlquery` = CRM uniquement.** Cette contrainte porte une requête SQL (`Sql`) : sur un projet ERP, `list_constraint_types` ne la renvoie pas, `get_constraint_properties` la refuse, et `validate_divalto_file` invalide le fichier qui la contient.

```json
"Constraints": [
  {
    "Type": "sqlquery",
    "Sql": "SELECT DATE({{startDate}}) <= DATE({{endDate}})",
    "ErrorMessage": "BO_Error_Dates"
  }
]
```

---

## Convention de nommage des fichiers `.datasource.json`

| Pattern                                          | Usage                       |
| ------------------------------------------------ | --------------------------- |
| `entity.grid.datasource.json`                    | Grille de liste             |
| `entity.id.crud.datasource.json`                 | Formulaire CRUD             |
| `entity.table.datasource.json`                   | Accès table direct          |
| `entity.listSource.datasource.json`              | Liste de sélection          |
| `entity.hierarchical.datasource.json`            | Arbre                       |
| `entity.id.defaultValue.scalar.datasource.json`  | Valeur par défaut           |
| `entity.metricSource.datasource.json`            | KPI                         |
| `entity.graphSource.datasource.json`             | Graphique                   |
| `entity.schedulerSource.datasource.json`         | Calendrier                  |
| `entity.treeviewSource.datasource.json`          | Arbre nœuds/feuilles        |
| `entity.mapSource.datasource.json`               | Carte                       |
| `entity.rowaccess.datasource.json`               | Contrôle d'accès ligne      |

### Organisation en sous-dossiers

Les datasources partagés sont dans `Common/app/utils/datasource/` avec des sous-dossiers :

- `listSource/` — Listes de sélection
- `hierarchical/` — Arborescences
- `sessionSource/` — Variables de session
- `treeviewSource/` — Arbres complexes
- `table/` — Accès table
- `translation/` — Traductions

---

## Le `.sql.sql` companion

Lorsqu'un datasource pointe vers `SelectQueryName: "<nom>"`, la requête vit dans le fichier voisin `<nom>.sql.sql`.

### Convention de nommage

| Pattern fichier                       | Usage typique                                          |
| ------------------------------------- | ------------------------------------------------------ |
| `entity.grid.sql.sql`                 | Requête de grille                                      |
| `entity.id.crud.sql.sql`              | SELECT par clé primaire (fiche CRUD en lecture)        |
| `entity.listSource.sql.sql`           | Liste de sélection                                     |
| `entity.hierarchical.sql.sql`         | Arbre                                                  |
| `entity.condition.sql.sql`            | Condition booléenne                                    |
| `entity.sessionSource.sql.sql`        | Variables de session                                   |
| `entity.metricSource.sql.sql`         | KPI                                                    |
| `entity.graphSource.sql.sql`          | Données de graphique                                   |
| `entity.treeviewSource.sql.sql`       | Arbre nœuds/feuilles                                   |
| `entity.schedulerSource.sql.sql`      | Calendrier                                             |

### Paramètres dynamiques (`{{...}}`)

Le framework n'interprète **que** la syntaxe `{{...}}`. **Ne jamais écrire de paramètre SQL `@param` à la main** : la paramétrisation des valeurs (le `@p0`, `@p1`… réellement envoyé à la base) est produite **par le framework** lors de l'expansion de `{{FILTERS}}` et des variables. Écrire un `@param` soi-même est un anti-pattern (cf. table des anti-patterns) — c'est le rôle du framework, pas du `.sql.sql`.

Un token `{{...}}` est résolu par **l'un de trois services**, selon sa famille. Connaître le service d'origine évite d'inventer une variable inexistante.

#### Famille 1 — Macros SQL (expansion en fragment SQL)

Reconnues par leur mot réservé (`GenericRequestExtensions.RESERVED_WORD`) et remplacées par un morceau de SQL **avant** exécution.

| Macro                                    | Service (origine)        | Expansion                                                                 | Exemple                          |
| ---------------------------------------- | ------------------------ | ------------------------------------------------------------------------- | -------------------------------- |
| `{{FILTERS}}`                            | `BaseSqlService`         | Conditions `WHERE` issues du panneau `filters` du composant ; `(1=1)` si aucun filtre. **Le dev écrit le placeholder, le framework écrit les conditions paramétrées.** | `WHERE {{FILTERS}}`              |
| `{{TABLE(entity, alias)}}`               | `WeavySqlService`        | `sw_data_<entity> AS alias` + contrôle d'accès ligne (row access) + segments | `FROM {{TABLE(customer, c)}}`    |
| `{{TAGS(alias, field)}}`                 | `WeavySqlService`        | Sous-requête `GROUP_CONCAT` des tags de la ligne pointée par `alias`       | `{{TAGS(c, tags)}} AS tags`      |
| `{{DEVICEDATA(field, [entity], [role])}}`| `WeavySqlService`        | Clause `IN (...)` sur les données device de la session ; `0=1` si aucune. `entity`/`role` optionnels. | `WHERE {{DEVICEDATA(site_ID)}}`  |
| `{{SELF}}` *(avancé)*                    | `BaseSqlService`         | Dans une `SqlExpression` / `Alias.Content` de filtre : remplacé par la valeur du filtre calculée | (datasource JSON, pas grille)    |

> **Réservé au framework — ne jamais écrire dans un `.sql.sql` :** `{{SETTERS}}` (clause `SET` d'`UPDATE`), `{{NAMES}}` + `{{VALUES}}` (clause `INSERT`), `{{FOREIGNDATAFILTERS}}` (validation de schéma foreign). Le framework les injecte lui-même lors des opérations CRUD d'un datasource `Type: "table"` ; les poser à la main produit du SQL cassé.

#### Famille 2 — Variables nommées de session / identité

Résolues par `UserVariableService` via des handlers enregistrés (`SfkPackageExtension`), depuis la session utilisateur et les infos projet. **Globales** : disponibles dans n'importe quelle requête, sans dépendre du composant appelant.

| Variable                       | Valeur                                                        |
| ------------------------------ | ------------------------------------------------------------- |
| `{{baseUser}}`                 | ID de l'utilisateur courant                                   |
| `{{baseUserTree}}`             | IDs de la hiérarchie de l'utilisateur (filtrage hiérarchique) |
| `{{companyID}}`                | ID de la société                                              |
| `{{languageCode}}`             | Code langue courant (`fr-FR`…)                                |
| `{{languageID}}`               | ID langue courant (jointures de traduction)                   |
| `{{isAdmin}}` / `{{isSuperUser}}` | `1`/`0` — utilisateur administrateur                       |
| `{{isAdminPartner}}`           | `1`/`0` — administrateur partenaire                           |
| `{{isAdminCustomer}}`          | `1`/`0` — administrateur client                               |
| `{{deviceID}}`                 | ID du device courant                                          |
| `{{deviceType}}`               | Type de device                                                |
| `{{accountType}}`              | Type de compte                                                |
| `{{projectType}}`              | Type de projet (Weavy, Infinity…)                             |
| `{{runtimeVersion}}`           | Version du runtime                                            |
| `{{configVersion}}`            | Version de la configuration                                   |

> Liste exhaustive des handlers nommés à date. Toute autre `{{variable}}` ne figurant **pas** ici n'est pas une variable nommée — elle est résolue comme paramètre de contexte (Famille 3) et n'est donc disponible que si le composant/la page l'injecte.

#### Famille 3 — Paramètres de contexte (injectés par la page / le composant)

Quand une page exécute un datasource, la requête part avec un **ensemble de paramètres clé → valeur** qui l'accompagnent : les `ContextParameters` envoyés par le composant appelant (un `scheduler` envoie p. ex. `startDate` / `endDate`), complétés par les valeurs de session de l'utilisateur et du contexte de page que le framework fusionne. Un `{{nom}}` qui n'est **ni une macro** (Famille 1) **ni une variable nommée** (Famille 2) est résolu en cherchant `nom` dans cet ensemble, dans cet ordre : paramètres statiques → session → `ContextParameters` de la requête → contexte de page → valeur par défaut (`{{nom?defaut}}`) → erreur si requis et absent.

Comme la résolution se fait **par nom**, un projet peut injecter ses propres paramètres (`{{planningStartDate?}}`, `{{contactUser}}`, `{{param_startDate}}`…). Ceux-là sont **spécifiques au projet** : ils ne sont disponibles que sur les pages/composants qui les fournissent — ne pas les supposer présents ailleurs. Les entrées ci-dessous sont les paramètres conventionnels fournis par le framework lui-même.

| Variable                       | Origine / portée                                  | Valeur                                                              |
| ------------------------------ | ------------------------------------------------- | ------------------------------------------------------------------ |
| `{{id}}`                       | Filtre clé primaire (pages fiche / scalaires liés)| ID de la ligne courante                                            |
| `{{startDate}}` / `{{endDate}}`| Composant **scheduler / planning**                | Fenêtre de dates visible du planning. Noms littéraux, pilotés par le composant ; présents **uniquement** sur les sources scheduler/planning. |
| `{{sId}}`                      | Composant **scheduler**                           | Identifiant de série de l'événement                                |
| `{{currentBaseCulture}}` / `{{defaultBaseCulture}}` | Couche culture / traduction (BackOffice multi-culture) | ID de la culture courante / fallback — utilisés par les jointures de traduction générées |

> **Origine — important :** `{{startDate}}`/`{{endDate}}`, `{{sId}}` et `{{currentBaseCulture}}`/`{{defaultBaseCulture}}` **ne sont pas des variables nommées** (aucun handler) : ce sont des paramètres de contexte injectés par le composant ou la couche concernée, et présents seulement quand ce contexte les fournit. Sur une requête de planning, préférer donc la forme optionnelle (`{{startDate?}}`, `{{endDate?}}`) si la requête peut tourner hors fenêtre.

#### Syntaxe optionnelle (variables nommées et paramètres de contexte)

| Syntaxe          | Signification                              | Exemple                          |
| ---------------- | ------------------------------------------ | -------------------------------- |
| `{{x}}`          | Requis — exception levée si absent         | `WHERE c.customer_ID = {{id}}`   |
| `{{x?}}`         | Optionnel — `NULL` si absent               | `WHERE YEAR(orderDate) = {{year?}}` |
| `{{x?default}}`  | Optionnel — `default` si absent            | `WHERE c.parent_ID = {{parentId?0}}` |

> **Row access — MUST** : `{{TABLE(entity, alias)}}` au lieu de `FROM sw_data_entity AS alias` pour toute table métier (`sw_data_*`). La macro applique automatiquement le contrôle d'accès ligne ; sans elle, l'utilisateur verrait des lignes auxquelles il n'a pas droit, et l'ajout futur d'un `rowaccess` obligerait à rééditer chaque requête (cf. règle MUST n°2 en tête de document).

### Tables Divalto (préfixe `sw_data_` / `sw_sys_`)

#### Tables métier principales

| Table                       | Entité                              |
| --------------------------- | ----------------------------------- |
| `sw_data_customer`          | Client / Tiers                      |
| `sw_data_customercontact`   | Contact client                      |
| `sw_data_intervention`      | Intervention                        |
| `sw_data_orderheader`       | En-tête de commande                 |
| `sw_data_orderdetail`       | Ligne de commande                   |
| `sw_data_contract`          | Contrat                             |
| `sw_data_equipment`         | Équipement                          |
| `sw_data_product`           | Produit                             |
| `sw_data_baseuser`          | Utilisateur                         |
| `sw_data_deal`              | Affaire / Projet                    |
| `sw_data_generictype`       | Types génériques (énumérations)     |
| `sw_data_translation`       | Traductions métier                  |
| `sw_data_feature`           | Feature flags                       |
| `sw_data_site`              | Site / Adresse                      |
| `sw_data_leaveapplication`  | Demande de congé                    |
| `sw_data_expenseheader`     | Note de frais                       |
| `sw_data_document`          | Document                            |

#### Tables système

| Table                                | Usage                            |
| ------------------------------------ | -------------------------------- |
| `sw_sys_language`                    | Langues                          |
| `sw_sys_languagetext`                | Textes système traduits          |
| `sw_sys_device`                      | Appareils                        |
| `sw_sys_devicedata`                  | Données par appareil             |
| `sw_data_permission_profile`         | Profils de permissions           |
| `sw_data_permission_profileaccess`   | Accès par profil                 |

### Patterns SQL courants

#### 1. Requête de grille

```sql
SELECT
  c.customer_ID AS customer_ID_primaryKey,
  c.codeCustomer,
  c.customerName,
  gt.label AS statusLabel,
  c._createDate
FROM {{TABLE(customer, c)}}
LEFT JOIN sw_data_generictype AS gt
  ON gt.generictype_ID = c.generictype_ID_customerType
WHERE {{FILTERS}}
ORDER BY c.customerName ASC
```

`{{FILTERS}}` est remplacé par les conditions issues du panneau `filters` du composant consommateur. En absence de filtre, il devient `1=1`.

#### 2. Liste de sélection avec traduction

Deux niveaux de complexité selon le besoin :

**Forme simple** — entité avec une `translationKey` déjà résolue par le projet (pattern de `customertype.listSource.sql.sql`) :

```sql
SELECT
  g.generictype_ID,
  COALESCE(g.translationKey, g.label) AS translationKey
FROM {{TABLE(generictype, g)}}
WHERE g.dataType = 'CUSTOMER_TYPE'
ORDER BY translationKey
```

**Forme avec JOIN de traduction système** — quand `translationKey` est une clé à résoudre via `sw_sys_languagetext` :

```sql
SELECT
  g.generictype_ID,
  COALESCE(lt.text, g.translationKey, g.label) AS translatedLabel
FROM {{TABLE(generictype, g)}}
LEFT JOIN sw_sys_language AS l
  ON l.codeLanguage = {{languageCode}}
LEFT JOIN sw_sys_languagetext AS lt
  ON lt.language_ID = l.language_ID
  AND lt.codeLanguageText = g.translationKey
WHERE g.dataType = 'CUSTOMER_STATUS'
ORDER BY translatedLabel
```

**Priorité de traduction** (forme avec JOIN) : `lt.text` (texte système résolu) > `g.translationKey` (clé non résolue) > `g.label` (libellé brut).

#### 3. Condition booléenne

```sql
SELECT EXISTS(
  SELECT 1 FROM sw_data_deal AS d
  WHERE d.isProject = 1 AND d.deal_ID = {{id}}
)
```

#### 4. Hiérarchie (CTE récursive)

```sql
WITH RECURSIVE rec_profiles (permission_profile_ID) AS (
  SELECT ppa.permission_profile_ID
  FROM sw_data_permission_profileaccess AS ppa
  WHERE ppa.baseuser_ID = {{baseUser}}
  UNION ALL
  SELECT pp.permission_profile_ID_parent
  FROM rec_profiles AS rp
  INNER JOIN sw_data_permission_profile AS pp
    ON pp.permission_profile_ID = rp.permission_profile_ID
  WHERE pp.permission_profile_ID_parent IS NOT NULL
)
SELECT DISTINCT key_value FROM ...
```

#### 5. Statuts via `generictype`

```sql
SELECT
  e.entity_ID,
  gt.label AS statusLabel,
  gt.tag AS statusTag,
  gt.originalCode AS statusCode
FROM {{TABLE(entity, e)}}
INNER JOIN sw_data_generictype AS gt
  ON gt.generictype_ID = e.generictype_ID_status
WHERE gt.dataType = 'ENTITY_STATUS'
```

#### 6. Métrique / KPI

```sql
SELECT
  SUM(oh.amountExcl) AS amount,
  COUNT(*) AS count
FROM {{TABLE(orderheader, oh)}}
WHERE oh.customer_ID = {{id}}
  AND {{FILTERS}}
```

#### 7. Graphique (séries)

```sql
SELECT
  MONTH(oh.orderDate) AS month,
  SUM(oh.amountExcl) AS amount,
  SUM(oh.goalAmount) AS goal
FROM {{TABLE(orderheader, oh)}}
WHERE YEAR(oh.orderDate) = {{year?}}
GROUP BY MONTH(oh.orderDate)
ORDER BY month
```

#### 8. Session source (capacités utilisateur)

```sql
WITH RECURSIVE rec_profiles (...) AS (...)
SELECT
  'Capacity.Customer.List' AS keyName,
  (EXISTS(SELECT 1 FROM ... WHERE ...)) AS isAuthorized,
  'boolean' AS convertType,
  'hidden' AS visibility
```

### Jointure de traduction (pattern standard)

Pour obtenir un libellé traduit côté SQL — joindre `sw_sys_languagetext` via `{{languageCode}}`, puis empiler le fallback avec `COALESCE` :

```sql
-- 1. Joindre la langue courante
LEFT JOIN sw_sys_language AS l ON l.codeLanguage = {{languageCode}}

-- 2. Joindre le texte système (traduction de base)
LEFT JOIN sw_sys_languagetext AS lt
  ON lt.language_ID = l.language_ID
  AND lt.codeLanguageText = entity.translationKey

-- 3. COALESCE pour la priorité du fallback
SELECT COALESCE(lt.text, entity.translationKey, entity.label) AS translatedLabel
```

**Priorité du fallback** : `lt.text` (texte système résolu pour la langue courante) > `entity.translationKey` (clé non résolue) > `entity.label` (libellé brut).

### Filtrage par tag `generictype`

Les énumérations Divalto reposent sur `sw_data_generictype`, filtrables par `tag` (sémantique) ou `originalCode` (technique).

```sql
-- Inclure un statut spécifique
WHERE gt.tag = 'DRAFT'

-- Filtrer par type de données
WHERE gt.dataType = 'CONTRACT_STATUS'

-- Filtrer par code original
WHERE gt.originalCode IN ('NEW', 'ACKNOWLEDGED')
```

> Le filtrage d'exclusion des statuts supprimés (ex. `tag != 'DELETED'`) n'est pas une convention systématique du projet — à n'ajouter que si le besoin métier ou la mécanique de soft-delete spécifique au client l'exige.

### Opérateurs SQL courants

| Pattern                          | Usage                                            |
| -------------------------------- | ------------------------------------------------ |
| `IFNULL(value, default)`         | Valeur par défaut si NULL                        |
| `COALESCE(v1, v2, v3)`           | Premier non-NULL                                 |
| `CONCAT(a, ' ', b)`              | Concaténation                                    |
| `TRIM(value)`                    | Suppression des espaces                          |
| `DATE(value)`                    | Extraction de date                               |
| `YEAR(date)` / `MONTH(date)`     | Extraction année/mois                            |
| `FIND_IN_SET(val, list)`         | Recherche dans liste CSV                         |
| `CONVERT(expr, UNSIGNED)`        | Conversion de type                               |
| `GROUP_CONCAT(DISTINCT val)`     | Agrégation en chaîne                             |
| `EXISTS(SELECT 1 FROM ...)`      | Test d'existence                                 |

---

## Anti-patterns à éviter

> Voir aussi la section « Règles MUST » en tête de document — la table ci-dessous récapitule les anti-patterns courants.

| Erreur                                                                     | Correction                                                                                  |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Écrire un paramètre SQL `@param` / `@paramName` à la main pour filtrer      | Le framework ne lit **que** `{{...}}`. Utiliser `{{FILTERS}}` (filtres du composant), une variable nommée ou un paramètre de contexte `{{...}}` ; la paramétrisation `@p0/@p1` est produite par le framework (cf. « Paramètres dynamiques ») |
| Inventer une variable de contexte (`{{startDate}}`, `{{x}}`) là où le composant ne l'injecte pas | Vérifier la famille d'origine : `{{startDate}}`/`{{endDate}}` n'existent que sur les sources scheduler/planning ; une variable nommée doit figurer dans la liste Famille 2 ; sinon employer la forme optionnelle `{{x?}}` |
| `SelectSql` inline contenant une requête **complexe** (`JOIN`s, sous-requêtes, > ~100 car.) | `SelectQueryName: "<nom>"` + fichier `<nom>.sql.sql` voisin ; `SelectSql` réservé aux requêtes courtes et simples (cf. règle MUST n°1) |
| Double-alias après `{{TABLE(...)}}` (`{{TABLE(orderheader, oh)}} as oh`)   | Rien après la macro — elle injecte déjà `AS oh` (cf. règle MUST n°2)                        |
| `FROM sw_data_customer AS c` (ou tout `sw_data_*` métier en dur)           | `FROM {{TABLE(customer, c)}}` — inconditionnel (cf. règle MUST n°2)                         |
| `listSource` avec `Id` / `Label` au lieu de `IdField` / `LabelField`       | Les propriétés portent le suffixe `Field` (cf. règle MUST n°3)                              |
| `metricSource` sans `MainValueField`                                       | `MainValueField` requis — la métrique est non fonctionnelle sans (cf. règle MUST n°4)       |
| `IFNULL` imbriqué pour un fallback de traduction multi-niveaux             | Utiliser `COALESCE(...)` (lisibilité + SQL standard) — cf. règle MUST n°5                   |
| Pas de `{{FILTERS}}` sur une requête de grille                             | Ajouter `WHERE {{FILTERS}}` (ou `WHERE … AND {{FILTERS}}`) — sinon le panneau filtres est inerte |
| Concaténer `SelectQueryName` avec l'extension `.sql.sql`                   | `SelectQueryName` = nom du `.sql.sql` **sans** `.sql.sql`                                   |
| Formater une date/un nombre côté SQL (`DATE_FORMAT`, `FORMAT`…)            | Laisser le SQL renvoyer la valeur brute, déclarer un `Formatters` côté JSON                 |
| `SELECT *` dans une grille                                                 | Sélectionner explicitement les colonnes consommées (lisibilité + perf + traçabilité d'usage) |
| Inventer un type de datasource hors de la liste documentée                 | Vérifier le `Type` via `validate_divalto_file` ; tout type inconnu est probablement un piège |
| Produire un datasource `odkSource` sans avoir vérifié la capacité via les tools MCP | Vérifier via `list_datasource_types`/`get_datasource_properties` (jamais une question à l'utilisateur) ; capacité active → déléguer à `divalto-odk` (référence `datasource.md`) ; capacité inactive → constat direct + alternatives (cf. `SKILL.md` step 6). |

---

## Types non couverts ici (gaps)

Le skill se limite à ce qui est documenté dans la curation `feb/mcp2`. Les types suivants existent côté `FW.Runtime` mais ne sont pas couverts par ce document :

- **`odkSource`** — Capacité par projet, vérifiée via `list_datasource_types`/`get_datasource_properties` (cf. le paragraphe dédié en tête de ce document) : jamais une question à l'utilisateur (cf. `SKILL.md` step 6). Story sœur « MCP méthodes & services TS » prévue pour le support natif.
- **`infinityCompanySource`, `infinityComboSource`, `infinityComboZoomSource`, `infinityEntitySource`, `infinityGaugeSource`, `infinityGraphSource`, `infinityListSource`, `infinityMapSource`, `infinityMetricSource`, `infinityNotesSource`, `infinityScalarSource`, `infinityZoomSource`, `infinitywidget`, `infinityAttachedFilesSource`** — Connecteurs Divalto Infinity. Non couverts (cas spécifiques ERP legacy).
- **`httpsource`, `divarestapi`, `vaultsource`** — Connecteurs externes. Non couverts.
- **`entitySource`, `dictionarysource`, `treelist`, `treeview2Source`, `hierarchical2`** — Variantes ou types historiques. Non couverts.
- **`staticScalar`, `static`, `stepsSource`** — Cas spécifiques. Non couverts.
- **`todo`, `todocomment`, `todostate`** — Composants TODO. Non couverts.
- **`schedulerSettings`, `workWeek`, `customDays`, `mapOverlaySource`, `dataVizSerie`, `companyInfos`, `companyInfosTurnover`, `getQuantyCompanySource`, `getQuantyContactSource`, `index`** — Cas pointus, hors usages courants page UI.

En cas de besoin sur l'un de ces types, ouvrir une story dédiée plutôt que d'extrapoler à partir de ce document.
