# Types de `Definition` d'une condition

Le `Type` (clé du `Definition`) choisit le mécanisme d'évaluation. Sinon : une datasource renvoyant un booléen.

> **Source de vérité = MCP `divalto-studio`.** `list_condition_types` renvoie l'ensemble des types disponibles ; `get_condition_properties({ condition: "<type>" })` renvoie leurs champs avec leur description, lus depuis le schéma. Découvrir les types et leurs champs via ces outils — ne pas se fier à une liste figée. Ce fichier ne réplique pas cette liste : il donne la **sémantique comportementale** et les **idiomes** que le schéma ne porte pas.

> **Projet ERP (Infinity) — pas de condition résolue par du SQL.** Un `Definition.Type` valant `sql` (ou tout autre type de datasource dérivé du SQL) repose sur un mécanisme absent du moteur ERP. Interdit, que la condition vive dans un `.condition.json` dédié ou en ligne dans un `.page.json` / `.component.json`. Les propriétés `SelectSql`, `SelectQueryName` et `Aliases` sont interdites au même titre.
>
> **À utiliser à la place :** les types de condition natifs listés par `list_condition_types` (`session`, `userParameter`, `contextparameter`, `businessfeatureflag`, `databaseapi`, `dynamicfield`, `rowaccesscondition`), ou un datasource non-SQL renvoyant un booléen (`odkSource`, `entitySource`).
>
> Attention : `list_condition_types` ne liste **pas** les types de datasource, en ERP comme en CRM. L'absence de `sql` dans cette liste n'est donc pas le signal du refus — c'est `validate_divalto_file` qui invalide le document.

## Notes comportementales (non portées par le schéma)

- `session` : replie sur `ParameterName` si `VariableName` est absent.
- `userParameter` : vrai si le paramètre utilisateur (`companyID`, `isAdmin`, `isAdminPartner`, `isAdminCustomer`, `languageCode`, `accountType`…) vaut `CompareValue` ; converti en booléen si `CompareValue` est absent.
- `contextparameter` : `StaticParameterName` prioritaire sur `DynamicParameterName`.
- `businessfeatureflag` : `Enabled` vaut `true` par défaut.
- `rowaccesscondition` : requiert `EntityName` dans les `Params` ; `RowId` par défaut = id de l'URL.
- `dynamicfield` : vrai si la table a au moins un champ dynamique autorisé.
- Datasource (`sql`…) en `Definition.Type` : la requête doit renvoyer un booléen.

Paramétrage : déclarer dans `Params` du fichier, injecter via `{{nomParam}}` dans la `Definition`.

## Exemples réels (verbatim)

### `userParameter` (simple)
```json
{ "Definition": { "Type": "userParameter", "VariableName": "isAdminCustomer" } }
```

### `contextparameter`
```json
{ "Definition": { "Type": "contextparameter", "StaticParameterName": "WithAdmin" } }
```

### `databaseapi`
```json
{ "Definition": { "Type": "databaseapi", "MigrationLevel": "AccountTypeMigrated" } }
```

### `dynamicfield` paramétré
```json
{
  "Params": { "tableName": "string" },
  "Definition": { "Type": "dynamicfield", "Tablename": "{{tableName}}" }
}
```

### `businessfeatureflag` paramétré
```json
{
  "Params": { "Id": "string", "Enabled": "bool" },
  "Definition": { "Type": "businessfeatureflag", "FlagIdParameterName": "Id", "EnabledParameterName": "Enabled" }
}
```

### Datasource SQL (doit renvoyer un booléen) — CRM uniquement
```json
{ "Definition": { "Type": "sql", "SelectSql": "SELECT 1" } }
```

### Datasource SQL paramétré — CRM uniquement
```json
{
  "Params": { "variable": "string" },
  "Definition": {
    "Type": "sql",
    "SelectSql": "SELECT CAST(IFNULL(value,0) AS UNSIGNED) FROM sw_data_basevariablegroup AS bvg LEFT JOIN sw_data_basevariable AS bv ON bvg.basevariablegroup_ID = bv.basevariablegroup_ID AND CodeBasevariable = '{{variable}}' WHERE CodeBasevariablegroup = 'SWS.Options'"
  }
}
```
