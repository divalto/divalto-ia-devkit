# Datasource ODK — paire JSON + méthode C# `[DataSource]`

## Sommaire

- Quand utiliser
- Règle centrale — la paire est indissociable
- Procédure
- Anti-exemples

Une datasource `Type: "odkSource"` relie un composant (consommateur de datasource) à une méthode C# `[DataSource]` qui produit ses lignes via le QueryBuilder. Ce skill possède la génération de **la paire complète** : le descripteur JSON **et** la méthode C# qu'il cible. Il délègue le corps QueryBuilder de la méthode à [requete.md](requete.md), et les conventions de nommage de fichiers datasource à [`divalto-page-ui`](../../divalto-page-ui/SKILL.md).

## Quand utiliser

- Un composant consommateur de datasource doit être alimenté par une **méthode C#** `[DataSource]`, lignes produites par le **QueryBuilder** : sur une entité du **dictionnaire** (standard comprise), des données d'**activité** (`GetActivityData<T>`), **calculées** ou **externes**.

**Ne PAS utiliser :**

- Grille à **récupération automatique depuis le schéma** (`.schema.json`), **sans datasource** → **déléguer à [`divalto-entity-list`](../../divalto-entity-list/SKILL.md)**.
- En projet ODK, un besoin de filtre / tri / agrégat se traite **dans la méthode C# via le QueryBuilder**, jamais par un datasource SQL fait main.
- Traitement appelé **explicitement** depuis la page (bouton, événement) ou en **tâche de fond** → [point-entree.md](point-entree.md) (`[EntryPoint]` / `[AsyncEntryPoint]`), pas une datasource.

## Règle centrale — la paire est indissociable

**MUST — un `Type: "odkSource"` n'existe jamais sans sa méthode C#.** Le `.datasource.json` référence une méthode par `{NameSpace, ModuleName, MethodName}`. Produire un `odkSource` dont la méthode n'existe pas = datasource **cassé à l'exécution**. Donc, dans le **même tour** :

1. le `.datasource.json` (`Type: "odkSource"`) ;
2. **et** la méthode C# `[DataSource]` cible, dans un module `BaseModule`, aux `{NameSpace, ModuleName, MethodName}` **exactement cohérents** avec le JSON.

Si la méthode C# ne peut pas être écrite (type de retour inconnu, périmètre C# absent…) → **ne pas produire le JSON** et signaler que le datasource serait incomplet, avec ce qu'il manque.

## Procédure

### 1. Router

Confirmer que le besoin est bien un **datasource alimenté par une méthode C#** (cf. « Quand utiliser »). Grille à récupération automatique depuis le schéma, sans datasource → `divalto-entity-list`, s'arrêter.

### 2. Cibler le modèle de retour

Identifier le type `T` de `DataResult<T>` (le modèle des lignes).

**MUST NOT — ne jamais interroger le dictionnaire pour un besoin déjà calculé.** Si le libellé du besoin est une formule/algorithme/agrégat sans référence à un objet métier concret (ex. jours ouvrés restants, compteur, délai calculé), sa nature est **calculée**, tranchée immédiatement, avant tout appel outil — y compris `list_dictionary_entities`/`get_dictionary_entity` par acquis de conscience ou pour chercher une source faisant autorité (calendrier, table de référence). Aucune vérification dictionnaire n'est jamais justifiée dans ce cas, quelle qu'en soit la motivation.

- ❌ Pour « jours ouvrés restants avant la fin du mois », appeler `list_dictionary_entities` pour voir s'il existe un calendrier ERP (`MCALEN…`) avant de conclure au calcul — le libellé ne nomme aucune entité, la nature était déjà tranchée.
- ✅ Pour ce même besoin, traiter `T` comme calculée dès la lecture du besoin, sans aucun appel dictionnaire.

Le dictionnaire n'est interrogé **que** si le besoin nomme ou implique explicitement une entité métier (clients, factures…) : `list_dictionary_entities` (appeler avec `includeViews: false` — une vue ne génère pas de DBModel ODK, seules les tables sont exploitables ici) / `get_dictionary_entity`. Sinon, utiliser le contexte modèles du projet. Ne pas inventer d'entité (`MyEntity`…).

**MUST NOT — ne jamais conclure à un dictionnaire vide sur une liste filtrée vide.** Avec `includeViews: false`, la réponse porte `excludedCount` : le nombre de vues écartées. Un bloc `entities` vide avec `excludedCount > 0` signifie que le dictionnaire ne contient que des vues — il faut le dire à l'utilisateur, pas annoncer un dictionnaire sans entité.

- ❌ `entities[0]` avec `excludedCount: 12` → « le dictionnaire du projet est vide ».
- ✅ `entities[0]` avec `excludedCount: 12` → « le dictionnaire ne contient que des vues (12), dont aucune ne génère de DBModel ODK exploitable ici ».

### 3. Fixer les noms — une seule source de vérité

Choisir `{NameSpace, ModuleName, MethodName}` **une fois** et les réutiliser à l'identique dans le JSON et le C# :

- `NameSpace` : espace de noms du module (ex. `Activity`).
- `ModuleName` : nom de la classe `BaseModule` (ex. `DemoListeModule`).
- `MethodName` : nom de la méthode `[DataSource]` (ex. `PopulateGrid`).

Nom du fichier `.datasource.json` : préfixé par **l'entité/donnée source**, minuscules — convention `divalto-page-ui` (§ *Conventions de nommage*).

### 4. Écrire le `.datasource.json`

```json
{
  "Type": "odkSource",
  "MethodName": "<MethodName>",
  "ModuleName": "<ModuleName>",
  "NameSpace": "<NameSpace>",
  "PrimaryKey": "<clé primaire du modèle, ex. ID>"
}
```

`PrimaryKey` : clé primaire du modèle renvoyé.

**Données d'activité uniquement** — ajouter le champ `TableWatchers` (clé passée à `GetActivityData<T>`) ; l'omettre pour les données calculées/externes. JSON complet du cas activité :

```json
{
  "Type": "odkSource",
  "MethodName": "<MethodName>",
  "ModuleName": "<ModuleName>",
  "NameSpace": "<NameSpace>",
  "PrimaryKey": "<clé primaire du modèle, ex. ID>",
  "TableWatchers": ["<clé GetActivityData>"]
}
```

### 4bis. Vérifier / amorcer le périmètre C#

**MUST — le `.cs` de l'étape 5 doit vivre sous une racine de projet C#.** Avant de l'écrire, vérifier qu'une telle racine existe dans le périmètre actif ; sinon, l'amorcer de façon déterministe. **Ne jamais improviser** une structure (`CSharp.public`/`CSharp.private`…) en s'inspirant d'un autre projet — c'est le défaut qui rend le résultat instable d'une session à l'autre.

1. **Déterminer le périmètre actif.**
   - `Glob` `*.code-workspace` à la racine du workspace. 0 ou plusieurs résultats → périmètre indéterminable, **s'arrêter et demander** à l'utilisateur quelle racine utiliser.
   - `Read` ce fichier, extraire `folders` (`{path, name}`) et `settings["files.readonlyInclude"]`.
   - Retirer de `folders` les entrées dont le `name` est `Mobile Configuration`, `Dictionary`, `Translations` ou `Backend` (folders catalogue, hors périmètre C#, verrouillés par un mécanisme différent).
   - `files.readonlyInclude` absent/vide, ou nombre de folders restants après filtrage ≠ 2 → **s'arrêter et demander.**
   - Pour chacun des 2 folders restants, tester la clé `<folder.path>/**` dans `files.readonlyInclude` : `true` → folder verrouillé (inactif) ; absent ou `false` → folder actif. Exactement 1 folder actif attendu ; 0 ou 2 candidats actifs → **s'arrêter et demander.**
2. **Assurer `@dbModels` pour l'entité ciblée — avant tout le reste.**
   **MUST — ne jamais présumer qu'une entité du dictionnaire (std ou spé) a déjà sa classe DbModel générée, ni qu'`@dbModels` ne peut pas être créé depuis rien.** Une entité peut avoir été créée après le dernier amorçage — cas typique d'une entité **spé** créée via [entitycrud.md](entitycrud.md), dont la classe C# ne provient que d'une génération **delta** scopée au projet (jamais rejouée automatiquement) ; et `@dbModels` peut n'avoir **jamais été généré du tout** pour ce produit (cas réel sur un produit neuf) — `generate_dbmodels_sources` couvre aussi ce cas (auto-détection standard/delta, provisionne depuis rien si besoin ; son contrat d'outil dit explicitement de l'appeler « whenever … `@dbModels` is not present »). `list_dictionary_entities`/`get_dictionary_entity` fusionnent std+spé sans distinguer l'origine — impossible de savoir a priori si la classe existe déjà.
   - Modèle `T` de l'étape 2 (Cibler le modèle de retour) issu du **dictionnaire** → appeler `generate_dbmodels_sources` (aucun paramètre) **inconditionnellement**, qu'un `@dbModels.project.json` existe déjà ou non. Idempotent : l'appeler même quand les sources sont déjà à jour ne coûte qu'un aller-retour.
   - Erreur retournée → **s'arrêter ici**, ne rien écrire (ni `.project.json`, ni `.datasource.json`, ni `.cs`) et signaler que le datasource serait incomplet, avec le message d'erreur reçu (application de la Règle centrale : la méthode C# ne peut pas être écrite). C'est la **seule** condition d'arrêt liée à `@dbModels` — ne jamais s'arrêter sur la seule absence constatée d'un `@dbModels.project.json` sans avoir tenté l'appel.
   - Succès → `@dbModels` est garanti présent pour la suite (étape 3 : `Dependencies` s'ajoute sans re-vérification).
   - `T` issu de données d'**activité**, **calculées** ou **externes** → ne pas appeler, aucun DbModel n'est concerné ; continuer directement à l'étape 3.
3. **Vérifier l'existant.** `Glob` `**/*.project.json` sous la racine du folder actif. Un `.project.json` isolé, au périmètre étroit et sans rapport (ex. un projet de compilation interne scopé à un seul dossier technique, sans aucun module `[DataSource]`/`[EntryPoint]` à proximité), **ne compte pas** comme racine générique pour des modules ODK — chaque `.project.json` ne couvre que son propre dossier (voir `CSharpService`/`ensureInitCSharpFilesAsync` : chaque `.project.json` trouvé produit son propre `.csproj` indépendant, aucun n'en "couvre" un autre).
   - Un résultat à l'**emplacement canonique** (`CSharp/csharp.project.json` relatif à la racine du folder actif — le chemin même que cette étape écrit en cas d'amorçage, cf. plus bas) **compte toujours** comme racine ODK généraliste, **même sans aucun module `[DataSource]`/`[EntryPoint]` à proximité** — c'est l'état normal juste après un premier amorçage, avant l'écriture de son premier module ; ne pas le confondre avec un `.project.json` isolé sans rapport. **Ne pas grep pour ce cas** : l'emplacement seul suffit.
   - Pour tout **autre** résultat (chemin non canonique), vérifier sa pertinence : `Grep` `\[DataSource\]|\[EntryPoint\]` dans son dossier — au moins un module existant confirme que c'est une racine ODK généraliste réutilisable.
   - Au moins un résultat **pertinent** (emplacement canonique, ou module ODK existant à proximité) → racine déjà amorcée, **ne rien réécrire**, passer à l'étape 5.
   - Résultat(s) trouvé(s) mais aucun n'est pertinent (ex. seul un `.project.json` isolé à un chemin non canonique et sans module ODK existe) → traiter comme "aucun résultat" ci-dessous ; ne pas présumer qu'il faille le réutiliser, et ne jamais le modifier. En cas de doute sur la pertinence d'un `.project.json` trouvé, **s'arrêter et demander** plutôt que présumer.
   - Aucun résultat pertinent → amorcer le gabarit provisoire :
     - `T` vient du **dictionnaire** (donc `@dbModels` garanti présent depuis l'étape 2) → `Write` `CSharp/csharp.project.json` (chemin relatif à la racine du folder actif) avec :
       ```json
       { "ProjectType": "Public", "Dependencies": ["@dbModels"] }
       ```
     - `T` issu de données d'activité/calculées/externes → `Write` `CSharp/csharp.project.json` avec :
       ```json
       { "ProjectType": "Public" }
       ```
       Pas de `Dependencies` : ce module n'en a pas besoin.
     - Dans les deux cas, un `.project.json` vient d'être écrit → appeler `regenerate_csharp_scope` (aucun paramètre) pour régénérer `.csproj`/`.slnx`. Erreur retournée → s'arrêter et la signaler, ne pas écrire le `.cs` de l'étape 5.

Ces deux outils pilotent l'extension elle-même (commande réelle) ; ne jamais écrire de `.csproj`/`.slnx`/sources `@dbModels` à la main. Ce tour rend la méthode `[DataSource]` de l'étape 5 compilable immédiatement, sans rechargement de fenêtre.

Gabarit provisoire, pas définitif : structure étayée par un usage réel (ODK.ERP, équipe Factory) mais non actée officiellement. Si la décision finale diverge, ce gabarit se corrige par une simple édition de cette étape — pas de code à toucher.

### 5. Écrire la méthode C# `[DataSource]` (le fichier paire)

Placer le `.cs` dans le périmètre d'édition actif. **Seule contrainte d'emplacement : il doit vivre sous une racine de projet — un dossier (lui-même ou un parent) contenant un `.project.json`.** Nouveau fichier → `Write` ; ce n'est pas une surcharge, donc pas de `specialize_file`.

Squelette — **cas données d'activité** :

```csharp
using Divalto.ODK;

namespace <NameSpace>
{
    public class <ModuleName> : BaseModule
    {
        [DataSource]
        public DataResult<<T>> <MethodName>(DataSourceContext context)
        {
            // Données d'activité :
            var data = Services.GetRequired<IActivityService>().GetActivityData<<T>>("<clé>");
            var query = data.CreateQuery();
            return data.SelectDataResult(query, context);
        }
    }
}
```

- Attribut **`[DataSource]`** (jamais `[EntryPoint]` pour alimenter une grille).
- Paramètre **`DataSourceContext context`** (pas `IDataSourceContext`).
- Retour **`DataResult<T>`**, produit par `…SelectDataResult(query, context)`.
- **Corps de requête (filtre / tri / agrégat) délégué à [requete.md](requete.md)** ; la pagination et le tri de l'écran viennent du `context` via `SelectDataResult`. Ici, ne poser que le squelette correct et un `CreateQuery()` minimal.
- **Cas dictionnaire / calculées / externes** : mêmes invariants (`[DataSource]`, `DataSourceContext`, `DataResult<T>`, retour via `SelectDataResult`) ; seule la construction de `query` diffère — QueryBuilder sur l'entité concernée à la place de la ligne `GetActivityData<T>(…)` (corps délégué à [requete.md](requete.md)). **Ne pas réutiliser `GetActivityData` hors données d'activité.**

### 6. Valider

`validate_divalto_file({ type: "datasource", content })` sur le JSON. (Le C# est validé par la compilation ODK, pas par cet outil.)

### 7. Gate de complétude — avant de répondre

- [ ] Pour **chaque** `.datasource.json` `Type: "odkSource"` produit → la méthode `{NameSpace}.{ModuleName}.{MethodName}` **existe dans la sortie de ce tour**.
- [ ] `{NameSpace, ModuleName, MethodName}` **strictement identiques** entre JSON et C#.
- [ ] Attribut `[DataSource]`, paramètre `DataSourceContext context`, retour `DataResult<T>`.
- [ ] Aucun `odkSource` orphelin. Si la méthode n'a pas pu être écrite → JSON **non** produit + message de datasource incomplet.
- [ ] Si `T` (étape 2) vient du dictionnaire, `generate_dbmodels_sources` a été appelé (étape 4bis-2) **avant** tout le reste — que `@dbModels` existait déjà ou non, que la racine C# existait déjà ou non. Une erreur retournée a arrêté le tour sans rien écrire ; un succès n'a jamais été confondu avec un arrêt.
- [ ] Si aucune racine C# n'existait dans le périmètre actif (étape 4bis-3), `CSharp/csharp.project.json` a été écrit **avant** la méthode C#, et `regenerate_csharp_scope` a été appelé avant l'étape 5 — sans attendre un rechargement de fenêtre.

Si une case ne peut être cochée → corriger avant de répondre.

## Anti-exemples

- ❌ Créer `demoliste.grid.datasource.json` (`Type: "odkSource"`) et s'arrêter — la méthode C# n'existe pas, grille cassée au runtime.
- ✅ `demoliste.grid.datasource.json` **+** `DemoListeModule.cs` avec `[DataSource] DataResult<T> PopulateGrid(DataSourceContext context)`, noms cohérents.
- ❌ `[EntryPoint]` sur la méthode qui alimente la grille (c'est un point d'entrée d'activité, pas une datasource).
- ❌ `IDataSourceContext` en paramètre (type inexistant côté SDK ; c'est `DataSourceContext`).
- ❌ Improviser une structure `CSharp.public`/`CSharp.private` (ou toute autre) en s'inspirant d'un autre projet quand aucune racine C# n'existe — amorcer selon l'étape 4bis, jamais par analogie.
- ❌ Sauter à l'étape 5 sans appeler `generate_dbmodels_sources` au seul motif que la racine C# était déjà amorcée — une entité (std ou spé) peut avoir été créée après le dernier amorçage, sa classe DbModel n'est jamais garantie à jour.
- ❌ S'arrêter et signaler un datasource incomplet au seul motif qu'aucun `@dbModels.project.json` n'existe nulle part, sans avoir appelé `generate_dbmodels_sources` — l'outil provisionne aussi ce cas depuis rien (produit neuf) ; ne bloquer que si l'appel lui-même retourne une erreur.
- ❌ Traiter un `.project.json` isolé et sans rapport (ex. un projet de compilation interne scopé à un seul dossier technique comme un dictionnaire de champs) comme preuve que « la racine C# est déjà amorcée » — chaque `.project.json` ne couvre que son propre dossier, il peut coexister sans conflit avec un nouvel amorçage ailleurs dans le même périmètre actif.
- ❌ Réamorcer (réécrire `CSharp/csharp.project.json`, rappeler `regenerate_csharp_scope`) au seul motif qu'aucun module `[DataSource]`/`[EntryPoint]` n'existe encore à cet emplacement canonique — un root juste amorcé, avant l'écriture de son premier module, est un état normal, pas une preuve d'absence de racine.