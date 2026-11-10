# Modèles UniSearch — format typé

> **Depuis juin 2026, les UniSearch utilisent un nouveau format typé.** L'ancien format `xmlmodels/<Code>.model.json` avec `code`/`dataType`/`_root`/`_element`/`elements[]` est obsolète pour les UniSearch. Pour tous les détails, voir le skill **`divalto-unisearch-creation`** et le schéma `resources/mobile/unisearchmodel.schema.json`.

## Une UniSearch = 2 fichiers

| Fichier                                          | Rôle                                            | Où c'est documenté                                                  |
| ------------------------------------------------ | ----------------------------------------------- | ------------------------------------------------------------------- |
| `controls/{tab}_us{Nom}.json`                    | **Le contrôle** posé sur l'écran (`component: UniSearch`) | [controls.md](./controls.md) — section « Contrôle UniSearch »        |
| `unisearchs/{code}.unisearchmodel.json`          | **Le modèle** : colonnes, requête, critères, variables | Skill **`divalto-unisearch-creation`** (+ ce fichier pour le résumé)         |

Le contrôle pointe vers le modèle par son **code** (`proposal.config.xmlModel`). Créer les deux — un contrôle seul affiche une liste vide. Ce fichier ne couvre que le **modèle** ci-dessous ; pour le fichier contrôle, voir `controls.md`.

## Emplacement

Les modèles UniSearch vivent dans `Mobile/unisearchs/` (sibling de `xmlmodels/`) :

```
Mobile/
  unisearchs/
    commandesclient.unisearchmodel.json
    produits.unisearchmodel.json
```

Le nom de fichier (sans extension) **est** le code du modèle (insensible à la casse). Il n'y a **aucun** champ `code`, `dataType`, `_root`, `_element` ni `modelVersion` dans le fichier.

## Lien avec un contrôle UniSearch

Le contrôle référence ce modèle par son **code** via `proposal.config.xmlModel` (jamais un ID numérique). Format complet du fichier contrôle : [controls.md](./controls.md), section « Contrôle UniSearch ».

## Structure du fichier (modèle)

Trois sections inlinées (pas d'`elements[]` imbriqués) :

```json
{
  "label": "Libellé lisible",
  "display": {
    "displayMode": "Grid",
    "selectionMode": "Single",
    "hideHeader": false,
    "columnDefinitions": [ /* colonnes */ ],
    "lineDefinitions": [],
    "lineThemes": []
    /* + tous les attributs Display inlinés */
  },
  "query": {
    "queryMode": "manual",
    "baseQuery": "SELECT ... [WHERE] 1=1",
    "criteria": [
      {
        "criteriaCode": "1",
        "criteriaName": "...",
        "criteriaType": "field",
        "fieldName": "...",
        "fieldDataType": "Varchar",
        "operatorType": "%=%",
        "inputControlType": "TextBox",
        "isMainCriteria": true,
        "isMultiCriteria": false,
        "isActiveByDefault": false,
        "isSelectionByList": false,
        "selectionByListQuery": null,
        "selectionItems": []
        /* + languageKey, defaultFilterValue, customQuery, criteriaName */
      }
    ],
    "fields": []
    /* + queryCode, queryName, entityName */
  },
  "variable": {
    "variableCode": null,
    "variableName": null,
    "definitions": [
      { "fieldName": "entity_ID", "variableName": "entity_ID",
        "groupName": "usMyList", "translatorDefinition": null, "environment": null }
    ]
  }
}
```

**Points clés :**
- Les attributs `Display`/`Query`/`Variable` sont **inlinés** dans leur section — pas de singleton emboîté.
- Les critères sont **aplatis** directement dans `query.criteria[]` (plus de niveau `Criteria > Header`).
- Les booléens sont `true`/`false` (jamais `0`/`1`). Les champs mixtes comme `criteriaCode`, `backgroundColor`, `displayMask` sont **toujours des chaînes**.
- `id` sur les items de tableau est **optionnel** — l'omettre lors d'une création.

> Si le skill `divalto-semantic-theme` est disponible (projet mobile v7), le thème possède les
> couleurs et la typographie des contrôles : le suivre avant d'écrire `textColor`,
> `backgroundColor`, `borderColor`, `fontName` ou `fontSize`.

Pour la liste exhaustive des champs requis par section et un exemple complet validé, utiliser le skill **`divalto-unisearch-creation`**.
