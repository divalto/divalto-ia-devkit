# Méthode serveur appelable — `[EntryPoint]` / `[AsyncEntryPoint]`

## Sommaire

- Table de décision du marqueur
- `[EntryPoint]` — traitement synchrone appelé depuis la page
- Atteindre la méthode depuis la page — le périmètre décide
- `[AsyncEntryPoint]` — traitement long en tâche de fond
- Nommage — une seule source de vérité
- Anti-exemples

Une méthode C# ODK exposée à l'UI vit dans une classe **`public` qui hérite de `BaseModule`**. Son **marqueur** décide comment l'écran l'appelle. Ce skill possède les deux marqueurs d'appel explicite — `[EntryPoint]` (synchrone) et `[AsyncEntryPoint]` (tâche de fond) — et la table qui les départage du cas datasource.

Il délègue :

- le **corps de requête/écriture** (`QueryBuilder`, CRUD) → [requete.md](requete.md) ;
- la **rédaction du `.scriptlibrary.ts`** qui appelle la méthode → [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md) ; **par où** l'atteindre relève de ce skill (§ ci-dessous) ;
- le cas **datasource** (`[DataSource]` + `.datasource.json`) → [datasource.md](datasource.md).

## Table de décision du marqueur

Choisir le marqueur **avant** d'écrire la méthode :

| Besoin | Marqueur | `.datasource.json` | Skill propriétaire |
| --- | --- | --- | --- |
| Alimenter automatiquement un composant (grille, combobox, scalaire, métrique) | `[DataSource]` | **oui** | `datasource.md` |
| Traitement déclenché explicitement depuis la page (bouton, événement), réponse immédiate | `[EntryPoint]` | non | **ce skill** |
| Traitement long / asynchrone en tâche de fond, qui alimente des données d'activité | `[AsyncEntryPoint]` | non | **ce skill** |

Une méthode **sans marqueur** est rejetée à l'exécution. `[AsyncEntryPoint]` hérite d'`[EntryPoint]`.

## `[EntryPoint]` — traitement synchrone appelé depuis la page

- Méthode `public` d'un `BaseModule`, marquée `[EntryPoint]`.
- **Paramètres** : primitives, ou un objet de paramètres (`class`/`record`) dont les propriétés portent les valeurs de l'UI.
- **Retour** : la valeur renvoyée (primitive, entité, liste). La page l'appelle depuis un
  `.scriptlibrary.ts` ; par où elle l'atteint dépend du périmètre — voir la section suivante.

```csharp
using Demo.DbModels;

namespace Demo.Sql;

public class CrudModule : BaseModule
{
    [EntryPoint]
    public string InsertCustomer(CustomerParameters parameters)
    {
        CustomerModel customer = Database.CreateModel<CustomerModel>();
        customer.Code = parameters.Code;
        customer.Name = parameters.Name;
        Database.Insert(customer);                    // corps CRUD → requete.md
        return $"Client {customer.Name} ajouté (id {customer.Id})";
    }
}

public record CustomerParameters
{
    public string? Code { get; set; }
    public string? Name { get; set; }
}
```

Le corps (requête, CRUD) est délégué à `requete.md` ; ici seuls comptent le marqueur, la signature et l'objet de paramètres.

## Atteindre la méthode depuis la page — le périmètre décide

**En périmètre standard**, le compilateur produit un client TypeScript typé,
`<Module>.entrypoints.scriptlibrary.ts`, à côté du `.cs`. La page l'importe et appelle sa méthode.
**Ne pas écrire ce fichier à la main** : il est régénéré et les modifications sont perdues.

**En périmètre projet, ce compagnon n'est pas produit** — la génération ne couvre que le standard
à ce jour. Rien ne le signale : le `.ts` qui l'importe se compile sans erreur, et c'est
l'exécution qui tombe sur `<Module> is not defined`. Appeler alors le serveur directement, ce que
le client généré fait en interne :

```ts
const MODULE = { NameSpace: 'MonProjet.MonDomaine', ModuleName: 'MonModule' };

await $serverscript.executeMethodAsync({ ...MODULE, MethodName: 'MaMethode' }, { ResultType: 'Void' });
```

- `ResultType` suit le type de retour C# : `'Void'`, `'String'`, `'Number'`, `'Boolean'`, `'Date'`
  ou `'Object'` — ce dernier se type avec `executeMethodAsync<MonType>(…)`.
- Les paramètres se passent dans `Parameters`, keyés par le **nom réel** du paramètre C# :
  `{ ...MODULE, MethodName: 'MaMethode', Parameters: { monParametre } }`.

Cette forme perd le typage et la vérification des noms : une faute de frappe sur `MethodName` ou
sur une clé de `Parameters` ne se voit qu'à l'exécution. C'est un contournement d'une limite
actuelle de l'outillage, pas la cible — quand la génération couvrira le périmètre projet, le
client typé redeviendra la seule bonne réponse.

## `[AsyncEntryPoint]` — traitement long en tâche de fond

Pour un traitement qui dépasse un aller-retour synchrone (import, calcul de masse). Il **n'a pas de retour** : il écrit ses lignes dans des **données d'activité** (`IActivityData<T>`) qu'un `[DataSource]` séparé expose ensuite à la grille (→ `datasource.md`), et publie sa progression.

- `[AsyncEntryPoint("<activityName>", "<activityState>")]` — nom et état d'activité passés en paramètres.
- `Services.GetRequired<IActivityService>()` → `GetActivityData<T>("<clé>")` (la même clé que le `TableWatchers` du `.datasource.json`).
- `UpdateActivityProgress(...)` publie l'avancement.

```csharp
using Divalto.ODK.Models.Activity;    // IActivityData<T>
using Divalto.ODK.Models.Data.Table;  // ActivityEntity — autre namespace, les deux sont requis
using Demo.DbModels;

namespace Demo.LongProcess;

public class LongProcessModule : BaseModule
{
    private IActivityService ActivityService => Services.GetRequired<IActivityService>();

    [AsyncEntryPoint("activity.demo.async", "resultState")]
    public void FillActivityData(ImportParameters parameters)
    {
        IActivityData<MyLine> lines = ActivityService.GetActivityData<MyLine>("importDataKey");

        for (int i = 0; i < parameters.LineCount; i++)
        {
            lines.Insert(new MyLine { Name = $"Ligne {i}", Age = i * 10 });
            int done = i + 1;
            ActivityService.UpdateActivityProgress($"{(double)done / parameters.LineCount:P0} — {done}/{parameters.LineCount}");
        }
    }
}

public partial class MyLine : ActivityEntity
{
    public partial string? Name { get; set; }
    public partial int? Age { get; set; }
}
```

Les lignes d'activité (`ActivityEntity`) ne sont pas des entités du dictionnaire : elles vivent le temps de l'activité. La grille qui les affiche = une méthode `[DataSource]` sur la même clé `GetActivityData<T>` (→ `datasource.md`).

**Les deux usings sont requis et vivent dans des namespaces distincts** : `IActivityData<T>` dans `Divalto.ODK.Models.Activity`, `ActivityEntity` dans `Divalto.ODK.Models.Data.Table`. N'en poser qu'un donne `CS0246`, suivi d'une cascade de `CS9248` sur chaque `partial property` — le générateur n'émet pas la partie implémentation tant que la classe de base ne résout pas.

## Nommage — une seule source de vérité

`{NameSpace, ModuleName, MethodName}` est ce que la page transmet au serveur — via le client
généré côté standard, en littéral côté projet. Les choisir une fois, lisibles, et ne pas les
renommer sans mettre à jour l'appel : côté standard il faut régénérer le client, côté projet rien
ne relie les deux, la casse ne se voit qu'à l'exécution.

## Anti-exemples

- ❌ `[EntryPoint]` (ou `[AsyncEntryPoint]`) sur une méthode qui alimente une grille → c'est un `[DataSource]` (→ `datasource.md`).
- ❌ Écrire à la main le fichier `<Module>.entrypoints.scriptlibrary.ts` → côté standard il est généré et sera écrasé ; côté projet il n'existe pas, et le fabriquer ne le rendra pas résolvable.
- ❌ Importer ce compagnon depuis une page du **périmètre projet** → l'import se compile, puis la page tombe sur `<Module> is not defined`. Passer par `$serverscript.executeMethodAsync`.
- ❌ Attendre un retour d'un `[AsyncEntryPoint]` → il écrit des données d'activité, il ne renvoie rien.
