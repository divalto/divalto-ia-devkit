---
name: divalto-studio-platform
description: "Explique la plateforme Divalto Studio : les couches, quel type de fichier porte quoi, l'organisation d'un projet et le rôle du `.project.json`, les motifs UI, TypeScript et C#. Utiliser pour : « comment marche Divalto », « à quoi sert ce fichier », « où placer ce fichier », découverte d'un projet."
argument-hint: "Ce que vous cherchez à comprendre (ex : la structure d'un projet, les types de retour C#, le rôle d'un .project.json…)"
allowed-tools: Read, Glob, Grep, list_components, list_datasource_types, list_dictionary_entities
---

# La plateforme Divalto Studio

## Quand utiliser ce skill

- Comprendre l'organisation d'un projet Divalto ou le rôle d'un type de fichier.
- Situer une demande avant de choisir le skill de fabrication adapté.
- Retrouver les motifs de base côté UI, TypeScript client ou C# serveur.

Pour **fabriquer** un fichier, ce skill ne suffit pas : les règles d'écriture sont
dans le `CLAUDE.md` du projet, et chaque famille a son skill dédié
(`divalto-page-ui`, `divalto-scriptlibrary`, `divalto-odk`, `divalto-dictionary`…).

## Les couches

Divalto Studio est une plateforme de développement en mode service. On décrit une
application métier plutôt que de la coder de bout en bout :

| Couche                                 | Technologie        | Type de fichier                     |
| -------------------------------------- | ------------------ | ----------------------------------- |
| Écrans                                 | descripteurs JSON  | `.component.json`, `.page.json`     |
| Logique client (événements, scripts)   | TypeScript         | `.scriptlibrary.ts`                 |
| Logique serveur (API, règles métier)   | C#                 | `.cs`                               |
| Modèles de liste et de fiche CRUD      | JSON               | `.entity.json`                      |
| Source de données (SQL direct ou C#)   | JSON               | `.datasource.json`                  |
| Requêtes SQL                           | SQL                | `.sql`                              |
| Widgets de tableau de bord             | JSON               | `.dashboard.json`, `.widget.json`   |
| Points d'entrée et navigation          | JSON               | `.program.json`, `.activity.json`   |

Tous ces fichiers sont rangés en dossiers et synchronisés vers un stockage en
nuage cloisonné par client.

## Organisation d'un projet

```text
<projet>/
  Common/                    fichiers partagés par tous les environnements
  DeviceTypes/
    extranet/                personnalisations propres à l'extranet
    Default/                 personnalisations par défaut
  ProjetX/                   fichiers propres à l'environnement ProjetX
     projetx.project.json    configuration du projet
  ProjetY/
     projety.project.json
```

Un `.project.json` est obligatoire pour utiliser un dossier racine autre que
`DeviceTypes` ou `Common` :

```json
{
  "ProjectType": "Private",
  "Dependencies": ["autreprojet"],
  "DeviceType": "Default"
}
```

`Dependencies` sert au code C# ; `DeviceType` vaut `Default` s'il est omis.

## Motifs d'interface

- Une page est décrite en JSON et composée de composants imbriqués : grille,
  filtres, formulaires, onglets.
- Chaque composant a un jeu de propriétés défini par le schéma. Le `CLAUDE.md`
  impose de les découvrir par `list_components` et `get_component_properties`
  avant d'écrire.
- Une page peut avoir un code-behind TypeScript pour ses événements et sa logique
  client. Il suit le nom de la page : `<nompage>.scriptlibrary.ts`.
- La liaison de données passe par les propriétés `DataSource` des composants, qui
  peuvent viser un `.datasource.json` dédié.

Le type `odkSource` désigne une méthode C# qui retourne des données, mais il
n'existe que sur les projets où la capacité ODK est active. Vérifier avec
`list_datasource_types` avant de l'employer ; sinon utiliser `sql`, `table` ou les
types Infinity selon le projet.

```json
{
  "Type": "odkSource",
  "MethodName": "MyMethod",
  "ModuleName": "MyDataSourceModule",
  "NameSpace": "myNamespace"
}
```

## Scripts client TypeScript

- Les scripts s'attachent aux événements des composants (`AfterLoad`,
  `BeforeInsert`…).
- Ils manipulent les composants par `$component.tryGetById(id)`, où l'identifiant
  est la propriété `ScriptId` du composant.
- Le typage vient des fichiers de déclaration `.d.ts` du SDK Divalto.

## Scripts serveur C#

Un fichier C# expose des méthodes `[EntryPoint]` ou `[DataSource]`.

```csharp
[EntryPoint]
public string Text()
{
    return "Hello from C#";
}
```

```csharp
[DataSource]
public ListDataResult PopulateList(DataSourceContext context)
{
    var data = new List<ListDataValue>
    {
        new() { Id = "123", Label = "Label 1" },
        new() { Id = "456", Label = "Label 2" }
    };

    return new ListDataResult(data);
}
```

Une datasource retourne l'un des types de résultat prévus :

| Type                   | Usage                                                    |
| ---------------------- | -------------------------------------------------------- |
| `DataResult<T>`        | données de forme quelconque, en liste                     |
| `ScalarDataResult<T>`  | une valeur unique                                         |
| `ListDataResult`       | une liste d'éléments pour listes déroulantes, grilles…    |
