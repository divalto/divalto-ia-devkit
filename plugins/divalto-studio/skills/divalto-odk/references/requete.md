# Requête ODK — API `Database` + `QueryBuilder<T>`

`Database` (propriété d'un module `BaseModule`) accède aux données du projet. `Database.CreateQuery<T>()` produit un `QueryBuilder<T>` que l'on affine par chaînage, puis que l'on exécute (`Select`, `SelectFirst`, `Count`, `SelectDataResult`). Les écritures passent par `Insert`/`Update`/`Delete` et leurs variantes de masse.

Ce skill possède **le corps de requêtage/écriture uniquement**. Il délègue :

- le marqueur et l'enveloppe de la méthode → [datasource.md](datasource.md) (`[DataSource]`) ou [point-entree.md](point-entree.md) (`[EntryPoint]` / `[AsyncEntryPoint]`) ;
- l'accès aux données **côté page (TypeScript, `$database`)** → [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md).

## Quand utiliser

- Remplir le corps C# d'une méthode ODK qui lit, agrège ou écrit des données.

**Ne PAS utiliser :**

- Choisir/écrire le marqueur de la méthode (`[DataSource]`, `[EntryPoint]`…) → skills ci-dessus.
- Accès données depuis un `.scriptlibrary.ts` → `divalto-scriptlibrary` (`$database`), jamais du C# pour ça.
- En projet ODK, un filtre/tri/agrégat ne se traite **jamais** par un datasource SQL fait main : il passe par le `QueryBuilder` dans la méthode C#.

## 1. Cibler l'entité modèle `T`

`T` est un modèle de `@dbModels` (issu du dictionnaire, entités standard comprises). Le choisir via `list_dictionary_entities` / `get_dictionary_entity` — **ne jamais inventer d'entité** (`MyEntity`…) ni de champ. Ajouter le `using` du namespace `DbModels` du projet.

Les références se font par le **`businessName`** renvoyé par ces outils : celui de l'entité nomme la classe modèle, celui de chaque champ nomme la propriété C# des lambdas (`c.Name`). **Ne jamais référencer un champ par son nom physique** (`name`) — il n'existe pas comme propriété du modèle.

## 2. Lire

`using Divalto.ODK.Models.Data.Query;` est requis pour les lambdas et `DbFunctions`.

```csharp
// Filtre lambda (recommandé, typé)
var query = Database.CreateQuery<CustomerModel>()
    .Where(c => c.IsBlocked == false && c.City == "Paris")
    .OrderBy(c => c.Name);

IEnumerable<CustomerModel> rows = Database.Select(query);   // liste
CustomerModel? first = Database.SelectFirst(query);         // premier
long total = Database.Count(query);                          // nombre de lignes
```

Affiner la requête :

- **Filtre** — lambda (`c => c.Status == "ACTIVE"`, `c => c.Name.StartsWith(prefix)`), `DbFunctions.Like(c.Name, "Dup%")`, `DbFunctions.Between(c.Date, from, to)`, ou SQL brut à paramètres positionnels (`.Where("cli.tiers = ?", code)`) quand la lambda ne suffit pas.
- **Champs** — `.SelectFields(c => new { c.Name, c.City })` (par défaut toutes les colonnes). Chaînable.
- **Tri** — `.OrderBy(c => c.Name)` / `.OrderByDesc(c => c.CreatedAt)`.
- **Jointure** — sélectionner un champ d'une entité liée via une propriété de navigation crée la jointure **implicitement** (`c => new { c.Name, c.MainSupplier.Name }`), sans `.Join()`.
- **Agrégat** — `.GroupBy(c => c.CustomerId).Having(g => g.Sum(x => x.Amount) > 1000)`.
- **Pagination** — `.ForPage(page, pageSize)` (première page = 1 ; `pageSize` vaut 20 par défaut). L'API n'a **ni `Take` ni `Limit`** : une limite fixe s'écrit `.ForPage(1, n)`.
- **Confidentialité** — `.WithRestrictions()` (table principale), `.WithJoinRestrictions()` (masque les champs des jointures confidentielles), `.WithInheritedRestrictions()` (cache la ligne entière). À activer explicitement.

Pour alimenter un composant (grille…), renvoyer `Database.SelectDataResult(query, context)` : le `context` applique **pagination, tri et filtres de l'écran** automatiquement, et répond de lui-même aux demandes de comptage de l'écran. Ne pas ajouter de `.ForPage(…)` à une requête servie par `SelectDataResult` — l'écran pilote déjà la pagination ; `ForPage` sert aux lectures hors écran (`Select`). Le squelette de la méthode `[DataSource]` reste possédé par `datasource.md`.

## 3. Écrire (CRUD)

```csharp
// Créer
CustomerModel customer = Database.CreateModel<CustomerModel>();
customer.Code = parameters.Code;
customer.Name = parameters.Name;
Database.Insert(customer);            // customer.Id renseigné après insertion

// Modifier / supprimer une entité chargée
Database.Update(customer);
Database.Delete(customer);

// Masse, sur une requête — renvoie le nombre de lignes affectées
int updated = Database.UpdateWhere(new CustomerModel { Name = value },
                                   Database.CreateQuery<CustomerModel>().Where(c => c.Code.StartsWith(filter)));
int deleted = Database.DeleteWhere(Database.CreateQuery<CustomerModel>().Where(c => c.Code.StartsWith(filter)));
```

## Anti-exemples

- ❌ Inventer `MyEntity` / des champs non vérifiés → cibler l'entité réelle via `get_dictionary_entity` (étape 1).
- ❌ Écrire un datasource SQL fait main pour filtrer/trier en ODK → `QueryBuilder` dans la méthode C#.
- ❌ Réécrire ici le marqueur `[DataSource]`/`[EntryPoint]` ou l'appel TypeScript → skills délégués.
