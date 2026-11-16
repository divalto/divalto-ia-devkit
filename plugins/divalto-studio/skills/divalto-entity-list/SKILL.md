---
name: divalto-entity-list
description: "Affiche une entité Divalto en liste principale autonome via son `.schema.json` et sa vue d'entité (`entityViews`/`entityList`). Utiliser pour : « page de liste des clients », « lister les articles », « écran de gestion des interventions », filtrer un sous-ensemble d'entité, activer la sélection multiple. Pour une sous-liste dans une fiche ou un tableau calculé, c'est un `grid` : voir divalto-page-ui."
argument-hint: "Décrivez l'entité à lister (ex: page de liste des clients, lister seulement mes localisations, articles en sélection multiple...)"
allowed-tools: list_dictionary_entities, get_dictionary_entity, get_component_properties, validate_divalto_file, specialize_file, Read, Write, Edit, Glob, Grep
---

# Liste d'entité Divalto

## Le schéma : ce qui définit la liste d'une entité

Dans Divalto, un **schéma** est un fichier `.schema.json` (type `schema`) qui **décrit une table et ses règles**. C'est lui qui définit ce qu'une liste de l'entité affiche et contient :

- `TableName` — la table de la base (obligatoire).
- `Columns` — colonnes natives (`"label": {}`) ou calculées (`Data.SqlExpression`, **interdit en projet ERP** — cf. section ci-dessous), avec `Label`, `Ignore`, `Data.ForeignEntity`, `Data.Formatter`…
- `DataFilters` — **pré-filtres non visibles et non modifiables** dans l'UI (`{ "FieldName": "...", "Value": "..." }`) : c'est le mécanisme pour ne lister qu'un **sous-ensemble** de l'entité.
- `ViewsDefaultSettings.Listing` — colonnes et tris par défaut de la liste ; `Identification`, `Actions`, `Constraints`, `Triggers`…

Une entité a **un schéma par défaut** (`<table>.schema.json`). Rien n'interdit d'en définir un **spécifique** pour filtrer / présenter autrement la même table : fichier `<table>[<qualifier>].schema.json`, **même `TableName`** + `DataFilters` propres. Ex. `generictype[dayOfWeek].schema.json`, `baseuserlocation[mine].schema.json`.

## La vue d'entité : exposer le schéma en liste

La liste principale d'une entité n'est **pas** un `grid` SQL fait main : c'est une **vue d'entité** (`entityViews` > `entityList`, types `entityviews`/`entitylist`) déclarée dans le `.entity.json`, dont le `Entity` = **nom du schéma**. Le runtime **déduit la vue liste par défaut** à partir du schéma — un `.entity.json` minimal suffit, on ne déclare `entityViews` / `entityList` que pour personnaliser.

## Interdit en projet ERP : le SQL brut dans un `.schema.json`

Plusieurs propriétés du schéma reposent sur le mécanisme SQL du moteur CRM, **absent du moteur ERP (Infinity)** : ce n'est pas une préférence de style, un SQL brut n'y est pas exécutable.

- `Columns.<colonne>.Data.SqlExpression` — colonne **calculée** (`CalculatedFieldConfig`, type `calculated`), qu'elle porte l'expression en clair (`SqlExpression`) ou un fichier compagnon (`QueryName` → `.sql.sql`).
- `Triggers` — chaque `TriggerConfig` accepte `Sql` et `SqlQueryName`.
- `ViewsDefaultSettings` — chaque `DefaultViewSettingConfig` accepte `SqlQueryName` et `Aliases`.

Ne jamais les renseigner sur un projet ERP. `validate_divalto_file({ type: "schema", … })` invalide le fichier si l'une de ces traces y figure, et `list_schema_types` n'y expose pas le type `calculated`. À la place : une **méthode C# ODK** pour une valeur calculée ou une logique déclenchée à l'écriture, les **`DataFilters`** du schéma pour restreindre ce que la liste affiche.

## Router la liste via ODK (`IsOdkEntity`)

Sur un projet avec la capacité ODK active, `"IsOdkEntity": true` sur le schéma fait passer la requête de la **liste** par BusinessHub/ODK au lieu du SQL direct — voir [`divalto-odk`](../divalto-odk/SKILL.md) (référence `entitycrud.md`) pour son usage et sa complémentarité avec `EntityConfigName` (qui relie liste ↔ fiche, un sujet distinct). Ne le renseigner que sur demande explicite.

## Quand l'utiliser

- Liste **principale autonome** d'une entité : « page de liste des clients », « lister les interventions ».
- Ne lister qu'un sous-ensemble → **schéma filtré** (`DataFilters`).
- Paramétrer une vue, activer la sélection multiple (`AllowSelection`).

**Quand NE PAS l'utiliser → c'est un `grid` ([divalto-page-ui](../divalto-page-ui/SKILL.md)) :**

- **Sous-liste imbriquée** dans une fiche (enregistrements liés dans un onglet d'un `crud`, ex. « sur la fiche d'un tiers, ses devis en cours »).
- **Données ad-hoc** non adossées à une entité : résultat calculé, jointures, agrégat sur mesure.

## Procédure

### 1. Trouver le schéma et l'entité

- Schémas existants : `Glob **/*.schema.json` (souvent sous `DeviceTypes/Default/entity/utils/schema/`). Le **nom du schéma** = le nom de fichier sans `.schema.json` (qualifier `[...]` inclus).
- Champs de la table (pour écrire `Columns` / `DataFilters`) : `list_dictionary_entities` puis `get_dictionary_entity({ name })`.
- Modifier un fichier **standard** : en périmètre projet (`spe`, standard en lecture seule) → override projet via `specialize_file` (cf. [divalto-crm-overload](../divalto-crm-overload/SKILL.md)), ne jamais éditer le standard ; en périmètre standard (`std`) → éditer le fichier standard lui-même (`specialize_file` refuse).

### 2. (Si filtrage) créer un schéma spécifique

Pour ne lister qu'un sous-ensemble, créer `<table>[<qualifier>].schema.json` avec la même `TableName` et ses `DataFilters` :

```json
{
  "TableName": "generictype",
  "DataFilters": [
    { "FieldName": "dataType", "Value": "DAY_OF_WEEK" }
  ]
}
```

Le nom du schéma est alors `generictype[dayOfWeek]`. Sinon, réutiliser le schéma par défaut de l'entité.

### 3. Exposer le schéma en liste (`.entity.json`)

Forme minimale — le runtime déduit la vue liste par défaut depuis le schéma :

```json
{
  "Type": "entity",
  "EntityName": "generictype[dayOfWeek]"
}
```

`EntityName` = le nom du schéma à lister (par défaut ou filtré).

### 4. Personnaliser la vue (optionnel)

Seulement si la vue par défaut ne convient pas. Vérifier d'abord les propriétés via `get_component_properties({ component: "entityviews" })` et `get_component_properties({ component: "entitylist" })`. `entityList` expose notamment `Entity`, `AllowSelection`, `Selection`.

```json
{
  "Type": "entity",
  "EntityName": "customer",
  "Children": {
    "ev": {
      "Type": "entityviews",
      "Entity": "customer",
      "Children": {
        "list1": { "Type": "entitylist", "Entity": "customer", "AllowSelection": true }
      }
    }
  }
}
```

`Entity` = nom du schéma, identique sur le conteneur et la liste. Les colonnes / filtres / tris restent définis par le **schéma**, pas recodés ici en SQL.

### 5. Valider

```
validate_divalto_file({ type: "schema", content: "<json>" })   // pour un .schema.json
validate_divalto_file({ type: "entity", content: "<json>" })   // pour le .entity.json
```

Corriger toutes les erreurs avant de sauvegarder.

## Conventions

- Schéma par défaut : `<table>.schema.json`. Schéma filtré / spécifique : `<table>[<qualifier>].schema.json` (même `TableName`).
- Fichier d'entité : `<entité>.entity.json`. Propriétés Divalto (`Type`, `TableName`, `EntityName`, `Entity`, `DataFilters`, `Columns`) en PascalCase.

## Anti-patterns

| Erreur | Correction |
| ------ | ---------- |
| Liste principale d'une entité générée comme `grid` + datasource SQL | Exposer l'entité via son schéma (`.schema.json`) + `.entity.json` ; la vue liste en découle. |
| Filtrer la liste en codant un `WHERE` SQL dans un `grid` | Créer un schéma spécifique `<table>[<qualifier>].schema.json` avec `DataFilters` et lister ce schéma. |
| Déclarer tout le bloc `entityViews` / `entityList` alors que la vue par défaut suffit | `{ "Type": "entity", "EntityName": "<schéma>" }` suffit — le runtime déduit la vue. |
| `entityList` / `entityViews` placé dans un `.page.json` | Se déclare dans le `.entity.json`, sous `Children`. |
| `Columns` recodées en SQL sur l'`entityList` | Les colonnes appartiennent au **schéma** (`.schema.json`), pas à la vue. |
| Éditer un `.schema.json` / `.entity.json` standard pour personnaliser, en périmètre projet (`spe`) | Override projet via `specialize_file` (cf. divalto-crm-overload). En périmètre standard (`std`), éditer le standard est la voie normale. |
