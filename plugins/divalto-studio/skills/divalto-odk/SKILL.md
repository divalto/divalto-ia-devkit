---
name: divalto-odk
description: "Écrire du serveur ODK en C# : méthode `[DataSource]` avec son `.datasource.json`, traitement `[EntryPoint]`/`[AsyncEntryPoint]` appelé depuis une page, requêtes et CRUD par `QueryBuilder<T>`, fiche `IEntityController<T>` (EntityCrud), activité mono ou multi-état. Utiliser pour : « alimente cette grille en C# », « un bouton qui lance un traitement », « lis/écris ces données », « une fiche CRUD », « crée une activité »."
argument-hint: "Décrivez le besoin serveur (ex : alimenter une grille de commandes, un bouton qui recalcule un encours, une activité de génération de lignes…)"
allowed-tools: Read, Write, Edit, Glob, Grep, list_dictionary_entities, get_dictionary_entity, list_datasource_types, get_datasource_properties, list_activity_types, get_activity_properties, get_layoutcontent_properties, get_component_properties, validate_divalto_file
capabilities: [odk]
---

# ODK — code serveur C# et fichiers associés

ODK exécute du C# côté serveur pour un projet Divalto Studio : une classe `public`
héritant de `BaseModule` expose des méthodes marquées, et sa propriété `Database`
donne accès aux données. Ce skill oriente vers la référence qui possède le sujet,
puis porte les règles valables partout.

## Choisir la référence

| Besoin                                                                                | Marqueur / fichier                        | Référence                              |
| ------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------- |
| Alimenter un composant (grille, combobox, scalaire, métrique)                          | `[DataSource]` + `.datasource.json`       | [datasource.md](references/datasource.md)   |
| Traitement lancé explicitement depuis la page (bouton, événement), réponse immédiate   | `[EntryPoint]`                            | [point-entree.md](references/point-entree.md) |
| Traitement long en tâche de fond alimentant des données d'activité                     | `[AsyncEntryPoint]`                       | [point-entree.md](references/point-entree.md) |
| Lire, agréger ou écrire des données dans le corps d'une méthode                        | `QueryBuilder<T>`, `Insert`/`Update`/`Delete` | [requete.md](references/requete.md)    |
| Fiche CRUD sur une entité, avec `<Entité>Entity.cs`                                    | `IEntityController<T>`                    | [entitycrud.md](references/entitycrud.md)   |
| Formulaire de création → traitement → page de résultat, dans l'Activity panel          | `.activity.json` et ses fichiers          | [activite.md](references/activite.md)       |

Une méthode **sans marqueur** est rejetée à l'exécution. `[AsyncEntryPoint]`
hérite d'`[EntryPoint]`. Une méthode qui lit des données combine toujours deux
références : celle du marqueur, et [requete.md](references/requete.md) pour le corps.

## Quand ne pas utiliser ce skill

| Besoin                                                                     | Aller vers                                                        |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Grille alimentée automatiquement depuis le `.schema.json`, sans datasource  | [`divalto-entity-list`](../divalto-entity-list/SKILL.md)          |
| Accès aux données depuis une page, en TypeScript (`$database`)              | [`divalto-scriptlibrary`](../divalto-scriptlibrary/SKILL.md)      |
| Structure de la page qui consomme le résultat, nommage des fichiers         | [`divalto-page-ui`](../divalto-page-ui/SKILL.md)                  |
| CRUD schéma ou SQL sans `<Entité>Entity.cs` — ce n'est pas de l'ODK         | mécanisme distinct, hors sujet                                    |

## Règles valables sur toutes les références

**Cibler une entité réelle, jamais inventée.** Le type `T` est un modèle de
`@dbModels` issu du dictionnaire, entités standard comprises. Le choisir avec
`list_dictionary_entities` et `get_dictionary_entity`, et ajouter le `using` du
namespace `DbModels` du projet.

**Référencer les champs par leur `businessName`**, celui que renvoient ces outils :
il nomme la classe modèle pour l'entité, et la propriété C# des lambdas pour
chaque champ (`c.Name`).

- ❌ `c.name` — le nom physique n'existe pas comme propriété du modèle.
- ✅ `c.Name` — le `businessName` renvoyé par `get_dictionary_entity`.

**En projet ODK, un filtre, un tri ou un agrégat passe par le `QueryBuilder` dans
la méthode C#.**

- ❌ Un `.datasource.json` SQL écrit à la main pour filtrer ou trier.
- ✅ `.Where(…)`, `.OrderBy(…)`, `.GroupBy(…)` sur le `QueryBuilder`.

**La paire descripteur/méthode est indissociable.** Un `Type: "odkSource"` dont la
méthode C# n'existe pas est cassé à l'exécution : produire les deux dans le même
tour, avec des `{NameSpace, ModuleName, MethodName}` exactement cohérents. Si la
méthode ne peut pas être écrite, ne pas produire le JSON et dire ce qui manque.

**Chercher un exemple dans le projet ouvert**, jamais un exemple mémorisé : un
`Glob` sur `*.activity.json` ou `*.datasource.json` donne le modèle réel du projet.
