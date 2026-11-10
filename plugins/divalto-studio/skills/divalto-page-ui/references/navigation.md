# Navigation entre pages

Une redirection interne est portée par le sous-objet `Link` (`LinkDataConfig`) d'un composant — bouton, `link`, action d'entête de `crud`, colonne de grille. Sa propriété `Target` est une **route**, pas un nom de fichier : les règles ci-dessous décrivent ce que le moteur en fait et qui n'est écrit nulle part dans le schéma.

Le reste des propriétés de `Link` — dont `Params` et le préfixe `entityFilter_` — est décrit par le schéma lui-même : `get_component_properties({ component: "LinkDataConfig" })`. Ce sous-objet n'apparaît pas dans les propriétés du composant porteur, il faut l'interroger par son nom.

Rappel de placement : `Target` / `Mode` / `Params` vivent dans `Link: { … }`, jamais à la racine du composant `link` (où `Target` est l'enum HTML `Self`/`Blank`/`Parent`/`Top`). Voir Pattern 4 de [`structure-patterns.md`](./structure-patterns.md).

## MUST 1 — ne jamais écrire le premier segment de la route

Le premier segment (`page`, `entity`, `activity`) est ajouté par le moteur d'après `Category`, sans vérifier s'il est déjà là : l'écrire soi-même produit `page/page/maPage`, qui tombe sur la page d'erreur.

❌ `"Target": "page/customer/42"`
✅ `"Target": "customer/42"` (avec `Category` absent ou `"Component"`)

| `Category` | Route obtenue | Ce que `Target` nomme |
| --- | --- | --- |
| absent, `"Component"`, `"Widget"` | `page/<config>[/<id>]` | une page (`.page.json`) |
| `"Entity"` | `entity/<config>[/<id>]` | une entité du dictionnaire |
| `"Activity"` | `activity/<config>/<id>[/<sousPage>]` | une activité (`.activity.json`) |
| `"Internal"` | la cible telle quelle | une page intégrée du framework — aucun préfixe ajouté |

Une cible qui commence par `public` ne reçoit pas de préfixe non plus.

## MUST 2 — l'identifiant `new` est le mode création

Le second segment est l'identifiant de l'enregistrement à ouvrir. La valeur littérale `new` bascule la fiche en création (envoi POST au premier enregistrement) ; toute autre valeur ouvre l'enregistrement correspondant en édition.

✅ `"Target": "customer/new"` — ouvrir une fiche client vierge
✅ `"Target": "customer/#=id#"` — ouvrir la fiche du client de la ligne courante
❌ `"Target": "customer/create"` — `create` est traité comme un identifiant : la fiche cherche l'enregistrement `create` et n'en trouve aucun

Sans identifiant (`"Target": "customer"`), la route reste valide : c'est la page telle quelle, sans contexte d'enregistrement.

## MUST 3 — `#=…#` est évalué sur le contexte du lien, pas sur la page

`Target` et les valeurs de `Params` sont des gabarits compilés au moment du clic. Le contexte d'évaluation est la fusion, dans cet ordre : paramètres de la route courante, paramètres de requête de la route courante, données fournies par le composant appelant (la ligne sélectionnée pour une grille, l'enregistrement affiché pour un `crud`). Un nom absent de ce contexte fait échouer la compilation et le lien ne navigue pas.

- `#=champ#` insère la valeur brute — la forme à utiliser dans une route.
- `#:champ#` insère la valeur échappée en HTML — pas pour une route.
- Le nom `Parent` est toujours présent dans le contexte (nom de la zone d'affichage appelante) : ne pas le réutiliser comme nom de champ.

❌ `"Params": { "customer_ID": "id" }` — chaîne littérale `"id"`, pas la valeur
✅ `"Params": { "customer_ID": "#=id#" }`

## Cible relative

Une cible qui commence par `./` ajoute un segment sous la route courante et conserve donc son premier segment. Elle n'est résolvable que si la route courante est exactement d'un segment plus courte que la route visée : base de 2 segments pour `page` et `entity`, de 3 pour `activity`. Depuis une base plus longue, le segment surnuméraire n'est pas consommé et la navigation tombe sur la page d'erreur — préférer une cible absolue en cas de doute.

## Choisir le `Mode`

`Mode` (`LinkMode`) décide de la façon d'ouvrir la cible, `Redirect` par défaut. Le schéma ne renvoie que la liste des valeurs, sans leur sens ni les mises en garde du moteur — d'où ce tableau.

| `Mode` | Effet |
| --- | --- |
| `Redirect` (défaut) | remplace la page courante |
| `Popin` | ouvre la cible dans une boîte de dialogue modale |
| `InteractivePopin` | même chose, non modale (l'utilisateur garde la main sur la page dessous) |
| `Back` | revient à la page précédente ; ferme la fenêtre ou la boîte si l'historique est vide |
| `BackAndRedirect` | revient en arrière puis navigue — la forme à utiliser après une création, pour que la fermeture de la fiche ne ramène pas sur le formulaire de création |
| `NewWindow`, `External` | ouvre un onglet du navigateur (liens externes) |
| `Preview` | ouvre la cible dans une boîte d'aperçu |
| `Refresh` | recharge la page courante |
| `Close`, `CloseAndRedirect`, `CloseInteractivePopin` | ferme la zone d'affichage courante (sans effet si c'est la zone principale) |
| `None` | ne navigue pas — utile pour neutraliser la navigation par défaut d'un composant |

**MUST NOT** — ne pas produire les modes marqués expérimentaux dans le moteur (`InfinityNoWait`, `InfinityWait`, `InfinityPopin`, `InfinityRedirect`, `InfinityClassicalOpen`, `InfinitySearchOpen`, `Window`), ni la propriété `Output` de `Link` (compatibilité ascendante uniquement).

## Vérifier avant d'écrire

Le nom de configuration mis en `Target` doit exister : vérifier le fichier `.page.json` / `.activity.json` correspondant, ou l'entité dans le dictionnaire pour `Category: "Entity"` — une cible inexistante ne se voit qu'à l'exécution.
