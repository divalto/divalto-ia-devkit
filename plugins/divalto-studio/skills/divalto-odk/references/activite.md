# Activité ODK — assemblage des fichiers (mono-état et multi-état)

## Sommaire

- Quand utiliser
- Délégation
- Les cinq fichiers — carte d'assemblage
- Procédure — 1. Découvrir le schéma avant d'écrire
- Procédure — 2. Le `.activity.json`
- Procédure — 3. Le formulaire de création — flattening intégral
- Procédure — 4. La méthode qui lance l'activité
- Procédure — 5. La ou les pages d'état
- Procédure — 6. Multi-état — plusieurs étapes, une page par étape
- Validation
- Gate de complétude — avant de répondre
- Anti-exemples

Une **activité** encadre un traitement C# lancé depuis un formulaire de création et dont le
résultat s'affiche sur une page d'état, ouverte depuis l'**Activity panel**. Ce skill possède
**l'assemblage** — comment les cinq fichiers se référencent entre eux — pas le contenu de
chacun, déjà possédé par les skills sœurs.

Source de vérité des champs : les tools `list_activity_types` et `get_activity_properties` (§1).
Pour un exemple de bout en bout, chercher une activité existante du projet ouvert
(`Glob` sur `*.activity.json`) — jamais un exemple mémorisé.

## Quand utiliser

- Créer une activité : formulaire de création → traitement C# → page de résultat, **un seul
  état** déclaré dans `States`.
- Faire évoluer une activité en plusieurs étapes, chacune sa page, avec des transitions entre
  états → §6.

**Ne PAS utiliser :**

| Besoin | Aller vers |
| --- | --- |
| Un traitement lancé par un bouton, sans formulaire de création ni page d'activité | [point-entree.md](point-entree.md) |
| Une fiche CRUD (création/édition classique d'une entité) | [entitycrud.md](entitycrud.md) |

## Délégation

- Marqueur et enveloppe de la méthode qui lance l'activité (`[EntryPoint]`/`[AsyncEntryPoint]`) → [point-entree.md](point-entree.md).
- Paire `.datasource.json` + méthode `[DataSource]` (formulaire ou page de résultat), `TableWatchers` → [datasource.md](datasource.md).
- Regroupement des champs en layoutcontent, `get_layoutcontent_properties` → [entitycrud.md](entitycrud.md).
- Corps QueryBuilder / CRUD à l'intérieur d'une méthode → [requete.md](requete.md).
- Composants de la page d'état (`grid`, `Columns`…) → tools génériques de composants + [`divalto-page-ui`](../../divalto-page-ui/SKILL.md).
- `Header.Actions` : chaque entrée appelle une méthode du `.scriptlibrary.ts` de même basename que le `.activity.json` ; le contenu TypeScript relève de [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md).

## Les cinq fichiers — carte d'assemblage

Toute référence se fait par **basename**, jamais par chemin ni extension :

| Fichier | Référencé depuis | Champ |
| --- | --- | --- |
| `<nom>.activity.json` | — | son basename **est** le nom de l'activité |
| `<groupe>.layoutcontent.json` (un par groupe) | `<nom>.activity.json` | `CreationForm.Content[]` |
| `<nom>.<état>.activitystatepage.json` (un par état) | `<nom>.activity.json` | `States.<état>.Page` |
| `.datasource.json` de pré-remplissage | `<nom>.activity.json` | `CreationForm.InitialDataDataSource` |
| `.datasource.json` de la page d'état | `<nom>.<état>.activitystatepage.json` | `Children.<c>.DataSource` |
| module C# (`SubmitParameters`) | `<nom>.activity.json` | `{NameSpace, ModuleName, MethodName}` |

## Procédure — 1. Découvrir le schéma avant d'écrire

**MUST** : `list_activity_types` puis `get_activity_properties` sur `activity` et sur chaque
classe utile (`ActivityHeaderConfig`, `ActivityStateConfig`…) **avant** d'écrire le
`.activity.json`. Ne jamais deviner une valeur de `Level`, `Submit` ou `Header` : ces outils sont
la source de vérité.

## Procédure — 2. Le `.activity.json`

**Le basename du fichier EST le nom de l'activité** — l'argument passé à `InitActivity` dans la
méthode de lancement (§4). Renommer le fichier casse l'appel. `States` déclare **une entrée par
état** (mono-état : une seule), chaque entrée pointant sa page via `Page`. `Header` porte
`MainActionLabel` (bouton principal ouvrant le formulaire de création / lançant l'activité depuis
l'Activity panel) et, en option, `Actions` (boutons additionnels, délégués ci-dessus).

```json
{
  "Label": "Mon programme de démo",
  "States": { "defaultstate": { "Label": "Résultat", "Page": "<basename>.result" } },
  "Header": { "MainActionLabel": "Créer une activité" },
  "CreationForm": {
    "Content": ["<groupe>"],
    "InitialDataDataSource": "<basename>.init",
    "Submit": { "Label": "Lancer l'activité" },
    "SubmitParameters": { "MethodName": "StartActivity", "ModuleName": "ActivityModule", "NameSpace": "<NameSpace>" }
  }
}
```

## Procédure — 3. Le formulaire de création — flattening intégral

Le regroupement des champs en layoutcontent est délégué à
[entitycrud.md](entitycrud.md). Règle propre à l'activité :
chaque champ de chaque layoutcontent du `CreationForm` est une **propriété de la classe
paramètre**, et cette classe est **l'unique paramètre** de la méthode ciblée par
`SubmitParameters`.

```
layoutcontent Fields    →    classe paramètre           →    signature de l'EntryPoint
"NombreLignes"          →    …Parameters.NombreLignes   →    Lancer(<Classe> parameters)
```

**Le paramètre doit s'appeler `parameters`.** À la soumission, le formulaire envoie ses champs
aplatis sous une **clé fixe** : `Parameters: { parameters }`. Le serveur lie ensuite chaque
paramètre C# **par son nom**. Une signature en primitives échoue donc à l'exécution —
`Lancer(int nombreLignes)` produit `Parameter 'nombreLignes' not found for method Lancer`.

❌ Ne pas transposer la signature d'un `[EntryPoint]` appelé depuis une page : celui-là est
appelé par le client TypeScript généré, qui envoie `Parameters: { nombreLignes }` — keyé sur le
nom réel — et accepte donc des primitives. Les deux chemins ne portent pas le même contrat.

La classe paramètre sert aussi à ce que `SetParametersValues` stocke (§4) et à ce que renvoie
le `[DataSource]` cible d'`InitialDataDataSource` (paire déléguée à `datasource.md`).

## Procédure — 4. La méthode qui lance l'activité

Marqueur et enveloppe délégués à
[point-entree.md](point-entree.md). Propre à ce skill : l'ordre des
trois appels, avant de remplir les données du résultat.

```csharp
[EntryPoint]
public void StartActivity(MyParameters parameters)
{
    var activityService = Services.GetRequired<IActivityService>();
    activityService.InitActivity("<basename du .activity.json>", "<état de States>");
    activityService.SetParametersValues(parameters);
    var data = activityService.GetActivityData<MyEntity>("myDataKey");
    // ... remplir data via data.Insert(...), en lisant parameters
}
```

Le nom `parameters` est imposé par la liaison (§3). `SetParametersValues` reçoit directement
l'objet reçu : aucune recopie champ par champ.

## Procédure — 5. La ou les pages d'état

**Une page par état déclaré dans `States`** (mono-état : une seule). `ActivityForm: "Show"`
affiche en plus le formulaire de création en lecture seule sur la page. Les composants
(grille…) et leurs propriétés sont délégués à `divalto-page-ui` ; leur `.datasource.json` et la
méthode `[DataSource]` cible, `TableWatchers` compris, sont délégués à
[datasource.md](datasource.md). Conséquence propre à l'activité :
sans `TableWatchers`, la grille de résultat reste figée jusqu'à un rechargement manuel, alors
même que le traitement a inséré ses lignes.

## Procédure — 6. Multi-état — plusieurs étapes, une page par étape

Les §§2-5 restent valables tels quels. Le multi-état ajoute une page par état supplémentaire
dans `States`, et une méthode de transition par passage d'un état à un autre.

**Ce que le multi-état ajoute à la carte d'assemblage ci-dessus :**

| Fichier | Référencé depuis | Champ |
| --- | --- | --- |
| `<page d'état>.activitystatepage.scriptlibrary.ts` | `<page d'état>.activitystatepage.json` | `Children.<bouton>.Events.Click.Method` |
| `[EntryPoint]` de transition (module C#) | ce `.scriptlibrary.ts` | client TypeScript généré |

**`States` et l'état de départ.** Une entrée par état, `Label` et `Page` requis pour chacune.
L'état de départ effectif est le **2ᵉ argument** d'`InitActivity(nom, état)` ou
d'`[AsyncEntryPoint(nom, état)]` : le seul endroit qui le décide. `InitialState` / `EndState`
sont des champs optionnels **déclaratifs**, qu'aucun code du runtime ne lit à ce jour ; les
renseigner ne fixe pas l'état de départ et ne termine aucune activité.
`get_activity_properties` reste la source de vérité des champs (§1).

**La transition.** Un `[EntryPoint]` par transition, dont le corps est un unique
`UpdateActivityState("<clé de States>")`, idempotent (rien ne se passe si l'activité est déjà
dans l'état visé). Le client bascule sur la page du nouvel état au retour de l'appel — rien à
déclencher côté page.

```csharp
[EntryPoint]
public void PasserEnSynthese() =>
    Services.GetRequired<IActivityService>().UpdateActivityState("synthese");
```

**Où vit le bouton.** Composant enfant de la page d'état, portant `Events.Click.Method` — sa
structure relève de [`divalto-page-ui`](../../divalto-page-ui/SKILL.md), la rédaction de la méthode
de [`divalto-scriptlibrary`](../../divalto-scriptlibrary/SKILL.md). Le `.scriptlibrary.ts` porte le
basename de la page d'état.

**La clé d'état.** La clé passée à `UpdateActivityState` doit être littéralement une des clés de
`States` ; rien ne le vérifie à la compilation.

**`EnsureCurrentActivityState`.** Assertion, pas garde : elle lève si l'état courant ne
correspond pas à celui attendu. Elle ne branche pas — une transition n'en a pas besoin.

**`SubPages`.** Un état peut aussi déclarer des `SubPages` : des vues annexes atteignables sans
changer d'état, par alias d'URL. Un nouvel état est une **étape** du workflow ; une SubPage est
une **vue** de l'étape courante. Écrire une SubPage n'est pas couvert ici — demander la marche à
suivre plutôt que l'improviser.

## Validation

```
validate_divalto_file({ type: "activity", content: "<json>" })
validate_divalto_file({ type: "activitystatepage", content: "<json>" })
validate_divalto_file({ type: "datasource", content: "<json>" })
```

`layoutcontent` n'est pas encore validable (#38306) — ne pas appeler l'outil pour ce type. Le
module C# est validé par la compilation ODK, pas par cet outil.

## Gate de complétude — avant de répondre

- [ ] `<nom>.activity.json` produit, référencé uniquement par son propre basename.
- [ ] `SubmitParameters` pointe une méthode C# réelle, produite dans le même tour.
- [ ] Chaque champ layoutcontent du formulaire de création a sa propriété dans la classe
      paramètre, et cette classe est l'unique paramètre — nommé `parameters` — de l'`[EntryPoint]`.
- [ ] `InitActivity` puis `SetParametersValues` appelés, dans cet ordre, avant de remplir les
      données de résultat.
- [ ] Une page de résultat produite pour **chaque** état déclaré dans `States`.
- [ ] `activity`, `activitystatepage` et `datasource` produits passent `validate_divalto_file`.
- [ ] Chaque transition est un `[EntryPoint]` appelant `UpdateActivityState` avec une clé
      littéralement présente dans `States`, appelé depuis le `.scriptlibrary.ts` de la page.
- [ ] L'état de départ est celui passé à `InitActivity` / `[AsyncEntryPoint]` — aucun
      comportement ne repose sur `InitialState` / `EndState`.

## Anti-exemples

- ❌ `StartActivity(int nombreLignes)` — des primitives à plat sur la méthode ciblée par
  `SubmitParameters` : le lancement échoue sur `Parameter 'nombreLignes' not found`.
- ❌ `StartActivity(MyParameters p)` — bon type, mauvais nom : le paramètre doit s'appeler
  `parameters`, c'est la clé sous laquelle le formulaire poste ses champs.
- ❌ Renommer `<nom>.activity.json` sans mettre à jour l'argument d'`InitActivity` — le basename
  **est** le nom de l'activité.
- ❌ Écrire le `.activity.json` sans avoir appelé `get_activity_properties` — deviner `Level` ou
  `Submit` produit un champ qui n'existe pas dans le schéma.
- ❌ Omettre `TableWatchers` sur le datasource de la grille de résultat — elle ne se rafraîchira
  qu'au rechargement manuel de la page.
- ❌ `UpdateActivityState("Synthese")` quand `States` déclare `synthese` — l'activité pointe une
  page qui ne se résout pas.
- ❌ Déclarer `InitialState` en attendant qu'il fixe l'état de départ.
- ❌ Poser `EnsureCurrentActivityState` en tête de chaque transition « par précaution » — elle
  lève au lieu de brancher.
- ❌ Déclarer un `CurrentSort` sur une grille **et** un `OrderBy` sur la requête de la méthode
  qui l'alimente : `SelectDataResult` fusionne le tri de l'écran et celui de la requête, et le
  moteur SQL refuse une colonne répétée dans l'`ORDER BY`. La grille échoue à l'affichage alors
  que tout compile et valide — laisser le tri au `context`.
- ❌ Ajouter un état pour afficher une vue annexe de l'étape courante — c'est ce que `SubPages`
  couvre, un état est une étape du workflow.
- ✅ `<nom>.activity.json` + `<groupe>.layoutcontent.json` +
  `<nom>.<état>.activitystatepage.json` + `<résultat>.datasource.json` + le module C#
  (`StartActivity(<Classe> parameters)`), tous reliés par basename et noms cohérents.
