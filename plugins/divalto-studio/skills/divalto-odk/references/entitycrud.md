# EntityCrud ODK — fiche CRUD basée sur une entité

## Sommaire

- Quand utiliser
- Délégation
- Interdit : le SQL brut dans un `.schema.json`
- Procédure — création d'un EntityCrud neuf
- Procédure — enrichissement d'un EntityCrud existant
- Extras optionnels (seulement si nécessaire)
- Validation
- Gate de complétude — avant de répondre

Un **EntityCrud** est une fiche CRUD (création / édition) basée sur une entité, **ODK de bout en bout** : la présence de `<Entité>Entity.cs` implémentant `IEntityController<T>` signifie qu'ODK/`BusinessHub.Runtime` s'exécute derrière la fiche. Ce skill produit la config d'un EntityCrud et l'agrège avec l'EntityList existante de la même entité (EntityZoom) via `EntityConfigName`.

## Quand utiliser

- Créer une **fiche CRUD** sur une entité (« un EntityCrud pour X »).
- **Enrichir** un EntityCrud existant : ajouter une méthode `IEntityController<T>`, un `Layouts`, une mise en page.

**Ne PAS utiliser :**

- Simple **liste** principale d'une entité, sans fiche → [`divalto-entity-list`](../../divalto-entity-list/SKILL.md).
- **CRUD schéma/SQL sans `<Entité>Entity.cs`** : ce n'est pas un EntityCrud (pas d'ODK) — mécanisme distinct, hors sujet.
- Ne pas confondre avec `EntityCrudConfig` (`Type: "entitycrud"`) : composant non enregistré, sans usage réel.

## Délégation

- Le `.entity.json` et le `.schema.json` de base (lister l'entité) appartiennent à [`divalto-entity-list`](../../divalto-entity-list/SKILL.md) — les **réutiliser**, ne pas les recréer.
- Les mécaniques du module C# (classe dérivant de `BaseModule`, placement sous une racine de projet `.project.json`) suivent [datasource.md](datasource.md). Le contrat `IEntityController<T>` est propre à ce skill.

## Interdit : le SQL brut dans un `.schema.json`

Deux propriétés racine de `SchemaConfig` reposent sur le mécanisme SQL du moteur CRM, absent en ERP :

- `Triggers` — chaque `TriggerConfig` accepte `Sql` et `SqlQueryName`.
- `ViewsDefaultSettings` — chaque `DefaultViewSettingConfig` accepte `SqlQueryName` et `Aliases`.

Ne jamais les renseigner sur un projet ERP. `validate_divalto_file({ type: "schema", … })` invalide le fichier si l'une de ces traces y figure. Pour une logique déclenchée à l'écriture, passer par une méthode C# ODK ; pour une vue filtrée, par les `DataFilters` du schéma.

## Procédure — création d'un EntityCrud neuf

Toujours produire le **socle fonctionnel** (entité + schéma + 2 layouts + layoutcontent + `<E>Entity.cs`). En projet ODK vierge (aucun `using <X>.DbModels;` dans le C#, pas de racine `.project.json`) : **s'arrêter** et signaler que le périmètre C# doit d'abord être amorcé — hors périmètre de ce skill (voir #40183).

### 1. Base entité / schéma

Réutiliser ou créer, via [`divalto-entity-list`](../../divalto-entity-list/SKILL.md), `<e>.entity.json` (`{ "Type": "entity", "EntityName": "<E>" }`) et `<e>.schema.json` (TableName, Columns, Identification). Champs de l'entité via `list_dictionary_entities` / `get_dictionary_entity`.

### 2. Ajouts EntityCrud au schéma

Propriétés racine vérifiées via `get_schema_properties(schema="schema")`. Ajouter au `.schema.json` :

```json
{
  "EntityConfigName": { "Target": "<E>", "Category": "Entity" },
  "Identification": { "IdField": "<TABLE>_ID", "TitleField": "<champ titre>" },
  "Layouts": { "Create": "default_create.<e>", "Edit": "default_edit.<e>" }
}
```

`EntityConfigName` relie l'EntityList à la fiche (EntityZoom) ; `Layouts` active l'EntityCrud et **doit** pointer des `.layout.json` réellement produits (§3).

**Optionnel — router la liste via ODK (`OdkEntityName`).** `SchemaConfig.OdkEntityName` (nom de l'entité ODK interrogée) fait passer la **liste** de l'entité par BusinessHub/ODK au lieu du chemin SQL direct actuel ; c'est ce qui active ensuite BusinessName / query builder / colonnes calculées côté C# sur cette liste. Complémentaire à `EntityConfigName`, pas redondant : `EntityConfigName` relie liste ↔ fiche (agrégation EntityZoom), `OdkEntityName` route la requête de la liste elle-même — les deux coexistent. Ne l'ajouter que sur demande explicite, jamais par défaut sur un EntityCrud créé.

```json
{
  "EntityConfigName": "customerAddress",
  "OdkEntityName": "CustomerAddress"
}
```

La valeur est le nom du modèle ODK exposé côté BusinessHub (ex. pilote `CustomeraddressModel` → `"CustomerAddress"`, cf. `customeraddress.schema.json` dans FW.Runtime), pas nécessairement identique casse pour casse au nom de la classe C#. Une colonne calculée reste une **colonne normale** dans `Columns` (ex. `"FullAddress": {}` sur ce même pilote, sans flag) : c'est une propriété C# du modèle, exposée comme n'importe quel champ — rien de spécifique à déclarer côté schéma. Propriété encore taguée « PoC » côté Framework Web (PR #16544) : susceptible d'évoluer.

**Schéma mutualisé — `IdField`.** Si le schéma existe déjà (EntityList présente), il est **partagé** entre la liste et la fiche. `IdField` doit pointer la PK `<TABLE>_ID` ; si l'existant pointe autre chose, **ne pas le corriger en silence** — le changer impacte aussi la liste (liens de ligne, routage `/entity/<E>/<id>`, sélection). ❌ patcher `IdField` d'un schéma partagé sans prévenir. ✅ signaler l'écart à l'utilisateur et confirmer avant de modifier.

### 3. Layouts (obligatoires)

Propriétés via `get_layout_properties`. Produire `default_create.<e>.layout.json` et `default_edit.<e>.layout.json` :

```json
{
  "Label": "Page d'édition par défaut",
  "Form": { "Content": ["<groupe>.<e>"], "Level": "single", "ReadOnly": false }
}
```

`Form.Content` référence le(s) basename(s) de layoutcontent (§4).

### 4. Layoutcontent

Propriétés via `get_layoutcontent_properties`. Champs `{}` déduits du dictionnaire.

**Regroupement :**
- L'utilisateur **spécifie un découpage** → le respecter.
- Sinon, entité avec **beaucoup de champs** → **demander** comment regrouper.
- Sinon → **un seul** groupe `general_informations.<e>.layoutcontent.json`, tous les champs éditables :

```json
{ "Label": "Informations générales", "Fields": { "<Champ1>": {}, "<Champ2>": {} } }
```

### 5. `<E>Entity.cs` (toujours produit)

`namespace Entity;` · classe dérivant de `BaseModule` implémentant `IEntityController<<E>Model>` :

```csharp
using Divalto.ODK.Models.Data.Table;
using <Produit>.DbModels;

namespace Entity;

public class <E>Entity : BaseModule, IEntityController<<E>Model>
{
}
```

- **Classe vide = résultat valide.** `IEntityController<T>` expose 8 méthodes **toutes optionnelles** (`GetAll`, `GetById`, `Create`, `Update`, `Delete`, `ResolveLabel`, `EntityFormat`, `EntityPrivileges`) ; retour `null` = comportement base par défaut.
- **MUST NOT** surcharger une méthode sans logique métier réelle. ❌ implémenter les 8 « pour faire complet ». ✅ n'ajouter que celle(s) demandée(s) (ex. `EntityPrivileges` pour des droits, `EntityFormat` pour titre/sous-titre).
- Nom du module **`Entity.<E capitalisé>Entity`** (sinon `EntityService` échoue « Can't find entity module »).
- `<Produit>.DbModels` : **découvrir** par `Grep` d'un `using <X>.DbModels;` dans le C# existant du projet ; type `<E>Model` = BusinessName de l'entité (tools dico). Aucun usage trouvé → s'arrêter (projet vierge, #40183). ❌ deviner/copier un namespace d'un autre produit.
- Placer sous une racine de projet (`.project.json`), cf. [datasource.md](datasource.md).

## Procédure — enrichissement d'un EntityCrud existant

1. `Glob` les fichiers présents de l'entité (`<e>.entity.json`, `<e>.schema.json`, `<E>Entity.cs`, `*.<e>.layout.json`, `*.<e>.layoutcontent.json`).
2. N'ajouter **que** le manquant demandé : une méthode dans le `.cs` existant (sans le recréer), un bloc `Layouts`, un layout/layoutcontent.
3. Noms strictement cohérents entre fichiers.

**MUST NOT** dupliquer un fichier déjà présent. ❌ réécrire `<E>Entity.cs` en entier pour ajouter une méthode. ✅ éditer le fichier existant et n'ajouter que la méthode.

## Extras optionnels (seulement si nécessaire)

- `*.dictionaryentity.metadata.json` — **seulement** si les BusinessNames ne sont pas exposés (entité dico historique). Sa découverte MCP n'existe pas encore (#40296) : l'ajouter uniquement sur demande explicite.

## Validation

Valider chaque JSON produit. `type` **et** `content` sont **obligatoires** (chaînes) — ne jamais appeler l'outil à vide :

```
validate_divalto_file({ type: "entity", content: "<json>" })       // .entity.json
validate_divalto_file({ type: "schema", content: "<json>" })       // .schema.json
validate_divalto_file({ type: "layout", content: "<json>" })       // .layout.json
validate_divalto_file({ type: "enumeration", content: "<json>" })  // .enum.json (si produit)
```

`layoutcontent` n'est pas encore validable (#38306) — ne pas l'appeler pour ce type. Le `<E>Entity.cs` est validé par la compilation ODK, pas par cet outil.

## Gate de complétude — avant de répondre

- [ ] `<E>Entity.cs` produit (classe vide = valide), module `Entity.<E capitalisé>Entity`.
- [ ] `Layouts` du schéma pointe des `.layout.json` produits ; chaque layout référence des layoutcontent produits.
- [ ] `EntityConfigName` présent (agrégation avec l'EntityList).
- [ ] En enrichissement : aucun fichier existant dupliqué.
- [ ] Chaque JSON produit passe `validate_divalto_file` (hors `layoutcontent`, cf. #38306).
