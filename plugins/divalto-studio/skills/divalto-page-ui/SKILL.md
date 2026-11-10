---
name: divalto-page-ui
description: "Crée, modifie ou valide une page CRM Divalto Studio (`.page.json`) et ses composants imbriqués (grid, crud, tabs, filters, form, button…) avec leurs datasources. Utiliser pour : créer une page ou une fiche CRUD, ajouter un composant à une page qui existe déjà (bouton sur une fiche, champ dans un groupe, onglet), configurer un filtre, brancher une grille sur une requête SQL."
argument-hint: "Décrivez la page à construire (ex: liste de clients avec filtres et export Excel, fiche client avec onglet contacts...)"
allowed-tools: list_components, get_component_properties, list_constraint_types, get_constraint_properties, list_datasource_types, get_datasource_properties, validate_divalto_file, Read, Write, Edit, Glob, Grep
---

# Construction de pages CRM Divalto Studio

## Quand utiliser ce skill

- Créer un `.page.json`
- Afficher une entité **sous forme de liste** — choisir entre la vue d'entité `entityList` (pilotée par le schéma) et un `grid` SQL fait main selon le contexte (cf. étape 1)
- Ajouter ou modifier des composants (grid, crud, tabs, filters, form…) à l'intérieur d'une page
- Créer le datasource SQL associé (couple `.datasource.json` + `.sql.sql`)
- S'inspirer des patterns existants du projet

## Procédure

> **Gate avant réponse — INTERDICTION de répondre tant que la checklist n'est pas intégralement cochée.**
>
> Une page produite par ce skill est cassée à l'exécution si l'un des points suivants n'est pas vérifié. Avant de revenir à l'utilisateur, tu DOIS pouvoir cocher :
>
> - [ ] **Complétude** : pour chaque `DataSource: "<x>"` du JSON page → `<x>.datasource.json` est dans la sortie de ce tour (créé OU réutilisé après vérification de son contrat — cf. étape 6).
> - [ ] **Complétude** : pour chaque `SelectQueryName: "<x>"` des datasources produits → `<x>.sql.sql` est dans la sortie de ce tour.
> - [ ] **Structure fiche** : si la page est une fiche (édition / consultation d'une entité par son `id`), le **1er enfant** de `page.Children` est un `crud` ; son `Children` n'est ni absent ni vide ; aucun `crud` n'est placé à l'intérieur d'un `tab` (cf. squelette canonique à l'étape 5).
> - [ ] **Placement metric / KPI** : si la sortie contient un `metric` (ou widget KPI), il est enfant d'une `tab` ; sur une fiche, c'est un onglet dédié du `crud` (cf. Pattern 6 de `structure-patterns.md`) ; jamais sibling de `crud` au niveau `page`.
> - [ ] **Nommage** : chaque fichier `.datasource.json` / `.sql.sql` est préfixé par **l'entité métier source des données**, pas par la hiérarchie de la page consommatrice (cf. étape 6). Exception unique : datasource `crud` qui suit le nom de la page de fiche.
> - [ ] **SQL complexe en fichier** : une requête **complexe** — `JOIN`s, sous-requêtes, ou > ~100 caractères — n'est pas en `SelectSql` inline → `SelectQueryName: "<nom>"` + fichier voisin `<nom>.sql.sql` (cf. règle MUST n°1 de [`references/datasources.md`](./references/datasources.md)). Un `FROM` simple et court en inline reste valide.
> - [ ] **SQL hygiene** : tout `FROM` / `JOIN` sur une table métier (`sw_data_*`) — inline `SelectSql` **comme** fichier `.sql.sql` — passe par `{{TABLE(entity, alias)}}`, jamais `FROM sw_data_<entité>` en dur. **Pas de double-alias** : `{{TABLE(...)}}` injecte déjà `AS <alias>`, donc pas de `as <alias>` ajouté derrière (`{{TABLE(orderheader, oh)}} as oh` → `… AS oh as oh`, SQL invalide au runtime).
> - [ ] **Casing colonne** : dans les sous-objets de `Columns`, **toutes** les propriétés de la colonne (`BaseColumnConfig` / `ColumnConfig`) s'écrivent **première lettre en minuscule**, sans exception — `type`, `title`, `width`, `columnTemplate`, `primary`, `sortable`, `filterable`, `hidden`, `style`, `format`, `textAlign`, `textWrap`, `sum`, `count`, `average`, `min`, `max`, `locked`, `link`, `picture`, `editable`, `badge`, `events`… La PascalCase ne s'applique **jamais** à une propriété de colonne (`Width`, `ColumnTemplate`, `Type` → ❌ ; `width`, `columnTemplate`, `type` → ✅). Un `Type` PascalCase y est même lu comme le **discriminant de composant**, pas comme le type de données. Vrai pour **toute** colonne, y compris une colonne calculée / de comptage qu'on vient d'ajouter (`"orderCount": { "title": "...", "type": "number" }`, pas `{ "Title": "...", "Type": "number" }`).
> - [ ] **Placement `Events`** : aucun `Events: { ... }` n'est placé sur un composant enfant (`grid`, `crud`, etc.) ; le seul niveau autorisé pour `AfterChildrenLoad` / `BeforeUnload` / etc. est `page`. `AfterLoad` sur `grid` n'existe pas — c'est `AfterChildrenLoad` au niveau page qu'il faut utiliser.
> - [ ] **Projet ERP (Infinity) — le SQL brut n'existe pas** : sur un projet ERP, la sortie ne contient **aucun** datasource de type `sql` ou dérivé (`gridSource`, `scalar`, `listSource`, `metricSource`, `graphSource`, `rowaccess`…), **ni `table`** (`TableNameDataSourceConfig` — traité comme faisant partie de la même famille SQL en ERP, même si le moteur ne le refuse pas techniquement), **aucune** propriété `SelectSql` / `SelectQueryName` / `InsertSql` / `UpdateSql` / `DeleteSql` / `Aliases`, et **aucun** fichier `.sql.sql`. À la place : si la capacité `odk` est **active**, `odkSource` (méthode C# ODK) — la famille Infinity (`entitySource`, `infinityListSource`, `infinityScalarSource`…) est alors **dépréciée** pour tout besoin de liste/filtre/tri/agrégat, ne pas la proposer pour du nouveau code, même si le moteur continue de la renvoyer/l'accepter. Si `odk` est **inactive**, la famille Infinity reste la seule alternative légitime. Signal fiable pour `sql`/dérivés : en ERP, `list_datasource_types` ne les renvoie pas et `get_datasource_properties` les refuse — c'est un refus du moteur, pas un avis de style ; ne pas contourner (cf. [`references/datasources.md`](./references/datasources.md)). `table`, lui, **reste renvoyé par le moteur même en ERP** (il n'est jamais gated techniquement), qu'`odk` soit actif ou non : son absence de refus outil n'est **pas** une autorisation — il est banni en ERP par convention produit, pas par capacité. Cet item **prime** sur les deux items SQL ci-dessus : en ERP il n'y a pas de requête à déplacer en `.sql.sql`, il n'y a pas de requête.
> - [ ] **`odkSource` — capacité par projet** : signal fiable — `list_datasource_types` ne renvoie pas `odkSource` et `get_datasource_properties` le refuse quand la capacité `odk` est inactive (même mécanisme que le point SQL ci-dessus). Capacité active → déléguer au skill `divalto-odk` (référence `datasource.md`) pour produire la paire JSON + méthode C# (jamais construite ici). Capacité inactive → aucun `Type: "odkSource"` dans la sortie ; informer directement l'utilisateur que l'ODK n'est pas activé sur ce projet (constat, pas une question) + les 3 alternatives (cf. step 6).
> - [ ] **Cible de navigation** : chaque `Link.Target` produit est une route **sans son premier segment** — le moteur ajoute `page`/`entity`/`activity` d'après `Category`, donc l'écrire soi-même donne `page/page/<config>` et tombe sur la page d'erreur (❌ `"page/customer/42"` → ✅ `"customer/42"`). Une fiche en création se cible par l'identifiant littéral `new` (cf. [`references/navigation.md`](./references/navigation.md)).
>
> Si une case ne peut pas être cochée → corriger **avant** de répondre. Pas de « je m'en occupe après », pas de « le fichier existe sûrement déjà » sans l'avoir effectivement ouvert pour valider son contrat, pas de « la structure peut être ajustée plus tard ».
>
> La règle s'applique aussi en mode édition : ajouter une grille à une page existante = produire dans le même tour la modif de la page **et** les nouveaux datasource(s)/`.sql.sql` référencés, en respectant la structure et le nommage.

### 1. Analyser le besoin

Identifier :

- **Type de page** : liste d'entité (`entityList` **ou** `grid`, cf. règle ci-dessous), fiche (crud + onglets), tableau de bord, formulaire simple
- **Entité métier** : client (`customer`), intervention (`intervention`), commande (`orderheader`), produit (`product`)…
- **Fonctionnalités attendues** : filtres, export Excel, onglets, navigation vers une autre page
- **Datasources requis** : grille, fiche, listes de sélection, valeurs scalaires…

> **MUST — « afficher une entité sous forme de liste » ne veut PAS dire « toujours `grid` ». La liste principale d'une entité est une vue d'entité `entityList`, pas un `grid` SQL fait main.** Quand l'utilisateur demande de lister une entité (« la liste des clients », « afficher les articles », « une page qui liste les X »), **ne pas générer par réflexe un `grid` + datasource SQL** : pour une entité standard, le composant adapté est sa **vue d'entité** (`entityViews` / `entityList`), pilotée par le schéma — colonnes, filtres, tris et sélection sont hérités du dictionnaire de l'entité, et non recodés à la main.
>
> - **`entityList`** (dans `entityViews`) — *liste d'entité pilotée par le schéma*. À choisir pour la **liste principale autonome d'une entité standard** : « page de liste des clients », « lister les interventions », « écran de gestion des articles ». Sa création est possédée par le skill [`divalto-entity-list`](../divalto-entity-list/SKILL.md) — **déléguer** (ce skill n'écrit pas la vue d'entité lui-même).
> - **`grid`** — *tableau SQL fait main* : `DataSource` SQL + `Columns` explicites, tri / filtres / export / totaux. À choisir pour : (1) une **sous-liste imbriquée** dans une fiche (enregistrements liés dans un onglet d'un `crud`, ex. « sur la fiche d'un tiers, ses devis en cours ») ; (2) des **données ad-hoc** non adossées à une entité standard (résultat calculé, jointures, agrégat sur mesure).
>
> Signaux → `entityList` (déléguer à `divalto-entity-list`) : « page de liste de <entité> », « lister les <entité> », « écran de gestion des <entité> », « toutes les <entité> » comme **page autonome**. Signaux → `grid` (ce skill) : « sur la fiche … », « dans l'onglet … », « les X liés à … » (imbriqué), ou « tableau de <résultat calculé / requête / jointure> » (ad-hoc SQL).
>
> - ❌ « Crée la page de liste des clients » → `grid` + `customer.grid.datasource.json` + SQL à la main (recode ce que la vue d'entité fournit déjà).
> - ✅ « Crée la page de liste des clients » → déléguer à `divalto-entity-list` (vue d'entité liée à `customer`).
> - ✅ « Sur la fiche client, affiche ses devis en cours » → `grid` dans un onglet du `crud` (sous-liste imbriquée).
> - ✅ « Tableau du CA mensuel par commercial » (agrégat calculé) → `grid` sur un datasource SQL dédié.

### 2. Rechercher des exemples existants

Chercher dans le workspace les fichiers similaires (pages **et** datasources) pour respecter les conventions du projet :

```
DeviceTypes/Default/<entité>/
DeviceTypes/Default/<entité>/id/
Common/app/utils/datasource/
```

Consulter aussi [`references/examples/INDEX.md`](./references/examples/INDEX.md) pour des cas types curés.

### 3. Lister les composants disponibles

Appel **obligatoire** :

```
list_components()
```

### 4. Récupérer le schéma de chaque composant utilisé

Appel **obligatoire** pour CHAQUE type qui sera utilisé :

```
get_component_properties({ component: "<type>" })
```

**Source de vérité unique.** Ne jamais ajouter une propriété qui n'apparaît pas dans le schéma retourné, même si elle existe sur d'autres frameworks (`Style.*`, `css.*`, attributs HTML…).

### 5. Générer le `.page.json`

> **MUST — si la page est une fiche, le `crud` est le 1er enfant de `page.Children`.** Quand l'utilisateur demande une fiche (édition / consultation d'une entité par son `id` — formulations type « page fiche X », « page de détail Y », « fiche client », « fiche fournisseur », « fiche intervention »…), la structure de la page **commence par** un `crud` qui enveloppe tout le reste (onglets, groupes, grilles imbriquées). Le `crud` n'est **jamais** placé à l'intérieur d'un `tab` ou d'un autre conteneur.
>
> Squelette canonique d'une fiche — **à utiliser comme point de départ** :
>
> ```json
> {
>   "Type": "page",
>   "Title": "Fiche <entité>",
>   "Children": {
>     "myCrud": {                          // 1er enfant de la page = crud
>       "Type": "crud",
>       "DataSource": "<entité>.id.crud",
>       "CanInsert": true,
>       "CanUpdate": true,
>       "CanDelete": true,
>       "Children": {                      // crud a TOUJOURS des Children non vides
>         "myTabs": {
>           "Type": "tabs",
>           "StaticChildren": {
>             "tabFields": {               // 1er onglet = champs de la fiche
>               "Type": "tab",
>               "Title": "...",
>               "Children": {
>                 "myGroup": {
>                   "Type": "group",
>                   "Children": {
>                     "field1": { "Type": "textbox", "Label": "...", "DataField": "<colonne>" }
>                   }
>                 }
>               }
>             },
>             "tabList": {                 // autres onglets = sous-listes liées
>               "Type": "tab",
>               "Title": "...",
>               "Children": {
>                 "myGrid": { "Type": "grid", "DataSource": "<entité-liée>.grid", "Columns": { /* … */ } }
>               }
>             }
>           }
>         }
>       }
>     }
>   }
> }
> ```
>
> - ❌ `page > tabs > tab > crud` (CRUD imbriqué dans un onglet) → save/cancel ne couvre qu'un seul onglet ; les autres onglets ne partagent pas la session d'édition.
> - ❌ `crud` sans `Children` (ou avec onglets/groupes vides) → fiche **blanche** à l'exécution, aucun champ affiché.
> - ✅ Le `crud` enveloppe les onglets ; chaque onglet de saisie a au minimum un `group > textbox/email/…` lié via `DataField`.

> **MUST — placement des `Events` (`AfterChildrenLoad`, `BeforeUnload`, etc.) : toujours au niveau `page`, jamais sur un composant enfant (`grid`, `crud`, etc.).** Pour réagir au chargement d'une grille ou d'une fiche, on bind un `AfterChildrenLoad` **sur la page** qui pointe vers une méthode du `scriptlibrary` de la page. Le composant `grid` n'a pas d'event `AfterLoad` natif — c'est un piège classique parce que le nom est plausible.
>
> - ❌ `{ "Type": "grid", "Events": { "AfterLoad": { "Method": "..." } } }` (event sur le grid — n'existe pas)
> - ❌ Tout `Events` sur `crud`, `tabs`, `tab`, `group` au lieu de la `page` (sauf besoin documenté du composant lui-même)
> - ✅ `{ "Type": "page", "Events": { "AfterChildrenLoad": { "Method": "myPage_afterChildrenLoad" } }, "Children": { ... } }` — la méthode vit dans `<page>.scriptlibrary.ts`.
>
> Cf. pages de référence : `divarestapiforeign.page.json`, `emailingSettings.id.page.json`, `foreigns.page.json` (toutes 3 utilisent `Events.AfterChildrenLoad` au niveau page).
>
> **MUST — déléguer le code-behind à `divalto-scriptlibrary`.** Dès qu'un `Events`/`OnClick` déclaré ici pointe une `Method`, c'est ce skill qui **pose le binding** (au bon niveau : `Events` au niveau `page`) ; la **rédaction de la méthode** dans le `.scriptlibrary.ts` revient à [`divalto-scriptlibrary`](../divalto-scriptlibrary/SKILL.md) — l'appeler ensuite. Lui vérifie via MCP que les services SDK (`$component`, `$database`…) et leurs méthodes/propriétés existent avant de les appeler ; il **n'édite pas** ce JSON. Répartition : page-ui = structure + events + placement ; scriptlibrary = corps de la méthode.

Autres règles :

- Hiérarchie d'imbrication détaillée (page de liste, dashboard, fiche+dashboard, etc.) : voir [`references/structure-patterns.md`](./references/structure-patterns.md). Pattern 6 en particulier pour le placement d'un widget KPI / `metric` sur une fiche : **toujours dans une `tab` du `crud`** (jamais sibling de `crud` au niveau `page`).
- Lien vers une autre page (composition de `Link.Target`, mode d'ouverture, gabarits `#=…#`) : voir [`references/navigation.md`](./references/navigation.md). Les propriétés du sous-objet `Link` se lisent par `get_component_properties({ component: "LinkDataConfig" })` : il n'apparaît pas dans les propriétés du composant porteur.
- Conventions de nommage : voir ci-dessous
- Indentation 2 espaces
- PascalCase pour les propriétés de composant **et les valeurs énumérées** (`Operator: "Contains"`, pas `"contains"`). **Exception : les sous-objets de `Columns`** — **toutes** les propriétés d'une colonne (`BaseColumnConfig` / `ColumnConfig`) s'écrivent première lettre en minuscule, sans exception : `type`, `title`, `width`, `columnTemplate`, `primary`, `sortable`, `style`, `format`, `sum`… (`{ "type": "string", "title": "...", "width": 120 }`, jamais `{ "Type": "...", "Width": 120, "ColumnTemplate": "..." }`). Un `Type` PascalCase y désigne le discriminant de composant, pas le type de données de la colonne.

### 6. Générer ou réutiliser le(s) datasource(s)

> **Avant de nommer un datasource, identifier l'entité métier source des données.**
>
> Pose-toi la question : *« quelle table / quelle entité fournit les données affichées par ce composant ? »*. La réponse est TOUJOURS le préfixe du nom de fichier, jamais la page qui les consomme :
>
> - Grille de contacts d'une fiche client → entité source = `customercontact` → ✅ `customercontact.grid.datasource.json` (❌ `customerfiche.id.contacts.grid.*`)
> - Combobox de types de clients dans un filtre → entité source = `customertype` → ✅ `customertype.listSource.datasource.json` (❌ `customer.list.type.listSource.*`)
> - Métrique d'encours total sur la fiche client → entité source = `orderheader` (les commandes du client) → ✅ `orderheader.customeroutstanding.metricSource.*` (❌ `customer.id.outstanding.metricSource.*`)
>
> **Cas particulier — datasource `crud`** : le datasource d'un composant `crud` est nommé d'après la page de fiche elle-même (`<entité-fiche>.id.crud.*`), car il est lié 1:1 à cette page. La page est elle-même nommée d'après l'entité éditée (typiquement renommée en cas de collision : `customerfiche.id.crud.*` quand `customer.*` est déjà pris).
>
> En cas de collision avec un datasource existant → qualifier par le contexte, **toujours** préfixé par l'entité source : `customercontact.fromfiche.grid.*`, `customertype.simple.listSource.*`.

**Itérer sur chaque** valeur `DataSource: "<x>"` apparaissant dans la page produite à l'étape 5. Pour chacune :

1. Vérifier si `<x>.datasource.json` existe déjà dans le workspace (cf. étape 2).
2. **Existant** → ouvrir et lire le fichier, puis valider qu'il expose le **contrat attendu par le composant consommateur** :
   - `combobox` / `list` → `IdField` + `LabelField` au niveau racine OU dans `Usages.listSource`.
   - `metric` → `MainValueField`.
   - `grid` → champs cohérents avec les `Columns` du composant.
   - `crud` → `Type: "table"` (ou `sql` selon le cas), `Tablename` et `PrimaryKey` adaptés.

   Si le contrat n'est pas exposé → soit compléter le datasource existant (typiquement en ajoutant un `Usages.<role>`), soit créer un datasource dédié sous un autre nom. **Jamais** brancher un consommateur sur un datasource incomplet : la grille / la combobox / la métrique sera cassée à l'exécution.
3. **Inexistant** → créer `<x>.datasource.json` avec son `Type` (`sql`, `table`, `listSource`, `scalar`, `metricSource`, `hierarchical`, `treeviewSource`, `mapSource`…).
4. Si le datasource utilise `SelectQueryName: "<y>"` → créer dans le même tour `<y>.sql.sql`.

Voir [`references/datasources.md`](./references/datasources.md) pour : la liste des types couverts, leurs propriétés, les paramètres dynamiques `{{...}}` (3 familles selon le service d'origine — macros SQL `{{FILTERS}}`/`{{TABLE(…)}}`/`{{TAGS(…)}}`, variables nommées de session `{{baseUser}}`/`{{languageCode}}`…, paramètres de contexte injectés par le composant `{{id}}`/`{{startDate}}`/`{{endDate}}`…), les conventions sur les tables `sw_data_*` et les patterns SQL courants.

> **Filtres : jamais de `@param` à la main.** Pour filtrer une grille selon le panneau `filters`, écrire `WHERE {{FILTERS}}` (ou `AND {{FILTERS}}`) — le framework génère lui-même les conditions paramétrées. Produire des `@param` / `@paramName` SQL soi-même est cassé : le framework ne lit que la syntaxe `{{...}}` (cf. anti-patterns de `datasources.md`).

> **`odkSource` — capacité par projet, vérifiée via les tools MCP, jamais par une question à l'utilisateur.**
>
> Le type `odkSource` (datasource ciblant une méthode C# via `MethodName` / `ModuleName` / `NameSpace`) est gated par la capacité projet `odk`. Le signal est **fiable et tool-based** — même mécanisme que le blocage SQL en ERP ci-dessus : `list_datasource_types` omet `odkSource` de la liste, et `get_datasource_properties('odkSource')` renvoie une erreur explicite, quand `odk` est inactif. Ne jamais demander à l'utilisateur de vérifier ou de confirmer ce statut — le déterminer par ces deux tools.
>
> **MUST — appeler `list_datasource_types` avant de choisir un type, pour TOUTE demande de liste/filtre/tri/agrégat sur une entité, indépendamment du vocabulaire de la demande.** Ce n'est **pas** conditionné à un vocabulaire ODK explicite (« ma méthode C# », « module »…) — une demande aussi neutre que « liste les clients filtrés par ville » doit déclencher le même appel.
>
> **Le choix entre `odkSource` et un type SQL/`table`/Infinity dépend du type de projet, pas d'une préférence automatique :**
>
> - **Projet ERP (Infinity)** : `table`/`sql`/dérivés sont **bannis par convention produit** (cf. item de gate ci-dessus), même quand le moteur les renvoie sans les refuser. Capacité `odk` **active** → `odkSource` est alors la **seule** option pour tout besoin de liste/filtre/tri/agrégat, **aucune question à poser** sur le type — déléguer directement à `divalto-odk` (référence `datasource.md`). La famille Infinity (`entitySource`, `infinityListSource`, `infinityScalarSource`…) est **dépréciée** dès que `odk` est actif, même pour un filtre simple qu'elle saurait exprimer nativement — ne pas la proposer. Capacité `odk` **inactive** → la famille Infinity redevient la seule alternative légitime.
> - **Projet CRM** : `table`/`sql` restent des types légitimes (pas de convention de bannissement, pas de dépréciation liée à `odk`). Si la demande est **suffisamment précise** pour indiquer qu'elle nécessite une logique serveur C# (mention explicite, calcul métier non exprimable en SQL simple…), déléguer à `divalto-odk` (référence `datasource.md`). Si la demande est **générique/ambiguë** (ex. « liste les clients filtrés par ville » sans autre précision, alors que `odkSource` **et** `table`/`sql` sont tous deux disponibles) → **ne pas trancher seul** : poser la question à l'utilisateur (`table`/`sql` classique, ou méthode C# ODK ?) avant de produire quoi que ce soit.
>
> - ❌ En ERP + `odk` actif, choisir `Type: "table"` **ou** un type Infinity (`entitySource`, `infinityListSource`…) pour lister/filtrer une entité du dictionnaire au seul motif qu'il figure dans `list_datasource_types` et « fonctionne » — ni `table` (jamais gated par le moteur) ni la famille Infinity (dépréciée dès `odk` actif) ne sont des preuves de bon choix ; seul `odkSource` l'est.
> - ❌ En CRM, sur une demande générique où les deux familles de types sont disponibles, choisir silencieusement l'une ou l'autre sans demander — l'ambiguïté doit remonter à l'utilisateur, pas être résolue par une préférence par défaut.
> - ❌ Si l'appel `list_datasource_types` échoue, ne répond pas, ou revient vide/incomplet — se replier sur un type par analogie avec des exemples du workspace ou du standard. Retenter l'appel une fois ; en cas d'échec persistant, **s'arrêter** et signaler l'impossibilité de déterminer les capacités du projet, sans produire de fichier.
>
> **Capacité active** (`list_datasource_types` renvoie `odkSource`) et le choix ci-dessus retient `odkSource` : ne pas construire le JSON `odkSource` soi-même — **déléguer au skill `divalto-odk` (référence `datasource.md`)**, qui génère la paire indissociable `.datasource.json` + méthode C# `[DataSource]`.
>
> **Capacité inactive** (`list_datasource_types` omet `odkSource`, ou `get_datasource_properties` refuse) : ne pas produire de datasource `odkSource`. Constat direct, sans question :
>
> > « `odkSource` n'est pas disponible sur ce projet : la capacité ODK n'y est pas activée. Voici 3 alternatives possibles : [1/2/3 contextualisée]. »
>
> **Trois alternatives à proposer :**
>
> 1. **Script TS appelant un service** côté `scriptlibrary.ts` de la page, depuis un `Events.AfterChildrenLoad` ou un event de bouton — approche standard quand on a besoin d'orchestrer du code applicatif.
> 2. **Datasource SQL équivalent** si la méthode C# ne fait qu'agréger des données accessibles en SQL.
> 3. **Ouvrir une story dédiée** (référence projet : story sœur « MCP méthodes & services TS ») si le besoin est nouveau et qu'aucune alternative ne convient.
>
> - ❌ Créer `<entité>.summary.datasource.json` avec un contrat ODK sans avoir vérifié la capacité via `list_datasource_types`/`get_datasource_properties`.
> - ❌ Demander à l'utilisateur de confirmer ou vérifier que la capacité ODK est activée — le tool le sait déjà.
> - ✅ Capacité active → déléguer à `divalto-odk` (référence `datasource.md`). Capacité inactive → constat direct + alternatives, sans question.
>
> `validate_divalto_file` accepte `odkSource` (le schéma sous-jacent est permissif) et ne vérifie pas la capacité `odk` : un fichier ODK qui passe la validation n'est **pas** une preuve que la capacité est utilisable dans le projet — c'est juste que le format JSON est syntaxiquement correct. Se fier à `list_datasource_types`/`get_datasource_properties` pour le statut de la capacité, pas à `validate_divalto_file`.

### 7. Valider chaque fichier généré

Appel **obligatoire** AVANT de sauvegarder, pour CHAQUE fichier produit ou modifié à l'étape 5/6 :

```
validate_divalto_file({ type: "page",       content: "<json>" })
validate_divalto_file({ type: "datasource", content: "<json>" })
```

Corriger toutes les erreurs avant de continuer.

### 8. Self-check de complétude (gate avant réponse)

Re-parcourir la sortie de ce tour et **cocher** chaque case de la checklist du « Gate de complétude » en tête de procédure :

- [ ] Tout `DataSource: "<x>"` du JSON page a son `<x>.datasource.json` dans la sortie.
- [ ] Tout `SelectQueryName: "<x>"` des datasources produits a son `<x>.sql.sql` dans la sortie.
- [ ] Aucun consommateur n'est branché sur un datasource **existant non validé** (cf. étape 6 point 2).
- [ ] **Si la page est une fiche** : le 1er enfant de `page.Children` est un `crud`, et son `Children` n'est ni absent ni vide (cf. squelette canonique à l'étape 5).
- [ ] **Si un `metric` (ou widget KPI) est dans la sortie** : il est enfant d'une `tab` ; sur une fiche, c'est un onglet dédié du `crud` (cf. Pattern 6) ; **jamais** sibling de `crud` au niveau `page`.
- [ ] **Nommage** : chaque fichier `.datasource.json` / `.sql.sql` est préfixé par l'entité source des données (cf. étape 6), et **pas** par la hiérarchie de la page consommatrice. Exception unique : datasource `crud` qui suit le nom de la page de fiche.
- [ ] **SQL complexe en fichier** : aucune requête **complexe** (`JOIN`s, sous-requêtes, > ~100 car.) produite ou modifiée dans ce tour n'est en `SelectSql` inline → `SelectQueryName` + fichier `<nom>.sql.sql` séparé. Un `FROM` simple et court inline reste valide. La règle MUST n°1 de [`references/datasources.md`](./references/datasources.md) est exécutable ici.
- [ ] **SQL hygiene** : tout `FROM` / `JOIN` sur table métier (`sw_data_*`), inline comme en fichier, passe par `{{TABLE(entity, alias)}}` — jamais `FROM sw_data_<entité>` en dur, et **pas de `as <alias>` ajouté après `{{TABLE(...)}}`** (double-alias `AS oh as oh` invalide au runtime). La règle MUST n°2 de [`references/datasources.md`](./references/datasources.md) est exécutable ici.
- [ ] **Casing colonne** dans les sous-objets de `Columns` : **toutes** les propriétés en première lettre minuscule, sans exception (`type`, `title`, `width`, `columnTemplate`, `format`, `style`, `primary`, `sortable`, `sum`…) — ❌ `{ "Type": "...", "Width": 120, "ColumnTemplate": "..." }`, ✅ `{ "type": "...", "width": 120, "columnTemplate": "..." }`. Un `Type` PascalCase y est lu comme discriminant de composant et casse la colonne. Y compris pour une colonne calculée / de comptage ajoutée dans ce tour.
- [ ] **Placement `Events`** : aucun `Events` sur un composant enfant (`grid`, `crud`, etc.) ; le seul niveau autorisé pour `AfterChildrenLoad` / `BeforeUnload` / etc. est `page`. `AfterLoad` sur `grid` n'existe pas — utiliser `AfterChildrenLoad` au niveau page.
- [ ] **Projet ERP (Infinity) — le SQL brut n'existe pas** : sur un projet ERP, aucun datasource de type `sql` ou dérivé (`gridSource`, `scalar`, `listSource`, `metricSource`, `graphSource`, `rowaccess`…), **ni `table`** (banni par convention produit en ERP, même si le moteur ne le refuse pas techniquement), aucune propriété `SelectSql` / `SelectQueryName` / `InsertSql` / `UpdateSql` / `DeleteSql` / `Aliases`, aucun fichier `.sql.sql` — à la place `odkSource` si `odk` actif, sinon la famille Infinity (`entitySource`, `infinityListSource`…). Signal fiable pour `sql`/dérivés : `list_datasource_types` ne les renvoie pas et `get_datasource_properties` les refuse — mais l'absence de refus outil sur `table` n'est **pas** une autorisation. Cet item **prime** sur les deux items SQL ci-dessus (cf. [`references/datasources.md`](./references/datasources.md)).
- [ ] **`odkSource` — capacité par projet** : signal fiable — `list_datasource_types` ne renvoie pas `odkSource` et `get_datasource_properties` le refuse quand la capacité `odk` est inactive (même mécanisme que le point SQL ci-dessus). Capacité active → déléguer au skill `divalto-odk` (référence `datasource.md`) pour produire la paire JSON + méthode C# (jamais construite ici). Capacité inactive → aucun `Type: "odkSource"` dans la sortie ; informer directement l'utilisateur que l'ODK n'est pas activé sur ce projet (constat, pas une question) + les 3 alternatives (cf. step 6).
- [ ] **Infinity déprécié en ERP dès `odk` actif** : sur un projet ERP où `odk` est actif, la sortie ne contient **aucun** datasource de la famille Infinity (`entitySource`, `infinityListSource`, `infinityScalarSource`…) pour un besoin de liste/filtre/tri/agrégat — même si le type reste renvoyé/accepté par le moteur, il est déprécié dès que `odkSource` est disponible ; seul `odkSource` (délégué à `divalto-odk` (référence `datasource.md`)) est valide dans ce cas.
- [ ] **Ambiguïté `odkSource` vs `table`/`sql` en CRM** : sur un projet CRM (pas ERP) où `list_datasource_types` renvoie à la fois `odkSource` et `table`/`sql`, si la demande était générique (ni vocabulaire ODK explicite, ni besoin manifestement SQL) → une question a été posée à l'utilisateur avant de produire un fichier, pas un choix silencieux.

Si une case ne peut pas être cochée → **retourner à l'étape 5 ou 6** pour produire/corriger, puis revalider (étape 7). **Ne pas répondre à l'utilisateur tant que toutes les cases ne sont pas cochées.**

### 9. Sauvegarder

Créer ou mettre à jour les fichiers aux emplacements corrects.

Produire un résumé final :

1. Les fichiers générés (chemins)
2. Les composants utilisés
3. Les datasources créés ou réutilisés (et pour les réutilisés : confirmer que le contrat consommateur est exposé)
4. Les corrections appliquées lors de la validation

---

## Autorisations et conditions

`Can*` et tout bloc `Conditions` acceptent une règle, pas seulement `true`/`false`. Pour créer ou réutiliser une condition, déléguer au skill [divalto-conditions](../divalto-conditions/SKILL.md) — ne pas écrire de script/event pour une simple autorisation.

## Clés de traduction

Pour créer ou réutiliser une **clé de traduction** (au lieu de `translationKey: null` ou d'un libellé en dur), déléguer au skill [divalto-translations](../divalto-translations/SKILL.md) — ne pas écrire de texte utilisateur en dur dans une définition générée.

## Conventions de nommage

### Identifiants dans le JSON

| Élément                       | Convention            | Exemple                                  |
| ----------------------------- | --------------------- | ---------------------------------------- |
| ID composant enfant           | camelCase             | `myGrid`, `filterPanel`, `tab1`          |
| ScriptId                      | `script_` + camelCase | `script_myGrid`, `script_nameField`      |
| Propriétés Divalto            | PascalCase            | `Type`, `DataSource`, `Children`, `Columns`, `Title` |
| Référence DataSource (grille) | `<entité>.grid`       | `customer.grid`                          |
| Référence DataSource (table)  | `<entité>.table`      | `customer.table`                         |
| Référence DataSource (CRUD)   | `<entité>.id.crud`    | `customer.id.crud`                       |
| Référence DataSource (lookup) | `<entité>.listSource` | `status.listSource`                      |
| Événements (Scripts)          | `<entité>.<événement>` | `customer.afterLoad`, `customer.beforeInsert` |

### Fichiers

> **MUST — casse minuscule.** Le segment `<entité>` (et tout segment d'usage) est **toujours en minuscules** dans le nom de fichier, même si le nom logique de l'entité est en CamelCase.
>
> - ❌ `customerType.listSource.datasource.json`, `CustomerContact.grid.sql.sql`, `Customer.id.page.json`
> - ✅ `customertype.listSource.datasource.json`, `customercontact.grid.sql.sql`, `customer.id.page.json`

> **MUST — préfixe = entité source de données, pas hiérarchie de la page consommatrice.** Un fichier `.datasource.json` / `.sql.sql` est nommé d'après **l'entité métier dont il sert les données**, jamais d'après le chemin de la page qui le consomme. Un même datasource doit pouvoir être réutilisé depuis plusieurs pages ; un nom calé sur une hiérarchie de page rend cette réutilisation impossible et masque la provenance des données.
>
> - ❌ `customercard.id.contacts.grid.datasource.json` (préfixé par la page `customercard.id` qui le consomme)
> - ❌ `customer.id.crud.contacts.grid.sql.sql` (chemin de consommation imbriqué)
> - ✅ `customercontact.grid.datasource.json` + `customercontact.grid.sql.sql` (entité = `customercontact`, usage = `grid`)
> - ✅ En cas de collision avec un fichier existant : qualifier par l'usage ou le contexte, **toujours** en partant de l'entité de donnée : `customercontact.fromfiche.grid.*`, `customercontact.attached.grid.*`, etc.

| Fichier                         | Pattern                                                              | Exemple                                       |
| ------------------------------- | -------------------------------------------------------------------- | --------------------------------------------- |
| Page de liste                   | `<entité>.page.json`                                                 | `customer.page.json`                          |
| Page de fiche                   | `<entité>.id.page.json`                                              | `customer.id.page.json`                       |
| Code-behind d'une page          | `<entité>[.id].page.scriptlibrary.ts`                                | `customerlist.page.scriptlibrary.ts`, `customer.id.page.scriptlibrary.ts` |
| Code-behind d'un composant      | `<entité>[.id].component.scriptlibrary.ts`                           | `customer.id.component.scriptlibrary.ts`      |
| Code-behind « part » d'une page | `<entité>.id.<nom>.part.scriptlibrary.ts`                            | `customer2.id.testbutton.part.scriptlibrary.ts` |
| Code-behind modèles             | `<entité>.id.models.scriptlibrary.ts`                                | `customer.id.models.scriptlibrary.ts`         |
| Code-behind d'une entité        | `<entité>.entity.scriptlibrary.ts`                                   | `entity-views-selection.entity.scriptlibrary.ts` |
| Datasource grille               | `<entité>.grid.datasource.json`                                      | `customer.grid.datasource.json`               |
| Datasource CRUD                 | `<entité>.id.crud.datasource.json`                                   | `customer.id.crud.datasource.json`            |
| Requête SQL                     | `<entité>.<usage>.sql.sql`                                           | `customer.grid.sql.sql`                       |

> **Infix `.{page|component|models|part|entity}.` sur les scriptlibrary** : la convention `<entité>[.id].scriptlibrary.ts` n'est pas suffisante seule — le segment intermédiaire désigne le type de code-behind (page, composant, modèles, part de page, entité). Vérifié contre les fichiers de référence du projet `/tmp/divalto-studio/SFKR/Std_0.0.0.0/`.

### Emplacement type

```
DeviceTypes/Default/<entité>/
├── <entité>.page.json                  ← page de liste
├── <entité>.page.scriptlibrary.ts
├── <entité>.grid.datasource.json
├── <entité>.grid.sql.sql
└── id/
    ├── <entité>.id.page.json           ← page de fiche
    ├── <entité>.id.page.scriptlibrary.ts
    ├── <entité>.id.crud.datasource.json
    └── <entité>.id.crud.sql.sql
```

---

## Outils MCP

| Outil                                      | Usage                                                                                                       |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `list_components()`                        | Lister tous les types de composants disponibles. Appeler avant toute génération.                            |
| `get_component_properties({ component })`  | Schéma exhaustif d'un type — source de vérité pour les propriétés et leurs valeurs.                         |
| `validate_divalto_file({ type, content })` | Valider un JSON avant sauvegarde. `type` ∈ {`page`, `component`, `datasource`, `entity`, …}.                |

> **Règle d'autorité** : `get_component_properties` est la source de vérité unique pour les propriétés. `validate_divalto_file` est un garde-fou — un succès de validation ne confirme pas qu'une propriété existe (le schéma sous-jacent est permissif en certains points). Si une propriété n'apparaît pas dans `get_component_properties`, elle n'existe pas, même si la validation accepte le fichier.
