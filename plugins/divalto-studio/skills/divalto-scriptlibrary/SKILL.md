---
name: divalto-scriptlibrary
description: "Écrit ou modifie le code-behind TypeScript (`.scriptlibrary.ts`) d'une page, d'un composant, d'une entité ou des modèles d'un projet Divalto Studio, avec les services SDK (`$component`, `$database`, `$session`, `$navigation`, `$notify`…). À utiliser pour TOUTE écriture de TypeScript Divalto ou tout appel `$xxx`, même une seule ligne : handler d'événement de page, handler de bouton, hook de datasource, cycle de vie de composant."
argument-hint: "Décrivez le comportement à coder (ex: au chargement de la fiche client, charger les commandes via le datasource et les afficher dans la grille…)"
allowed-tools: list_typescript_services, get_typescript_methods, get_component_properties, Read, Write, Edit, Glob, Grep
---

# Code-behind TypeScript des pages Divalto Studio

Ce skill produit les fichiers `.scriptlibrary.ts` qui implémentent les méthodes référencées par les `Events` d'une page, les `_Click` d'un bouton, les hooks d'un datasource ou le lifecycle d'un composant. Il est le pendant de [`divalto-page-ui`](../divalto-page-ui/SKILL.md), qui produit la structure JSON et déclare les `Events` — ici on écrit le corps des méthodes qu'ils pointent.

## Règles dures (lire en premier)

> **MUST — la sortie est du TypeScript dans un fichier `.scriptlibrary.ts`. JAMAIS de C#.**
>
> Le code-behind Divalto est 100 % TypeScript exécuté côté front, qui appelle le serveur **via les services SDK** (`$database`, `$serverscript`, …). Un besoin formulé avec « serveur », « en base », « un seul aller-retour », « traitement », « batch » ne justifie **jamais** d'écrire du C# : il se traite depuis le TS via `$database` (`selectAsync`, `updateAsync`, `dataActionsAsync`…) ou `$serverscript`.
>
> - ❌ Produire une classe C#, une méthode `public async Task<...>`, un `using`, un `namespace`, un `[Module]`, ou tout fichier `.cs`.
> - ❌ Basculer en C# parce que la logique « est côté serveur » ou « touche la base ».
> - ✅ `export default class <fichier>_<type>` en TypeScript, chaque accès serveur passe par un `$xxx` vérifié par les gates.
>
> Si le besoin exige réellement du code serveur C# (méthode ODK, module métier), ce skill **n'est pas le bon** : le dire explicitement et ne pas produire de `.scriptlibrary.ts` bancal.

> **MUST — périmètre d'édition : le(s) `.scriptlibrary.ts`, rien d'autre.** Ce skill **n'édite jamais** le JSON de page/composant (ni `Events`, ni `OnClick`, ni structure), ni datasource, ni SQL, ni config.
>
> Le binding (`Events.<X>: { Method: "..." }`, `OnClick`) et son **placement** (ex. `AfterChildrenLoad` au niveau `page`, jamais sur un composant enfant) relèvent de [`divalto-page-ui`](../divalto-page-ui/SKILL.md). Ce skill **lit** le binding déclaré par page-ui pour en reprendre le nom de `Method`, et écrit la méthode correspondante dans le `.scriptlibrary.ts`.
>
> - ❌ Ajouter / modifier un `Events` ou un `OnClick` dans un `.page.json` / `.component.json`.
> - ❌ Créer la page, le bouton ou la structure : c'est `divalto-page-ui`.
> - ✅ Le binding manque pour la méthode demandée → **renvoyer à `divalto-page-ui`** pour qu'il le pose (au bon niveau, bon event), puis écrire le `.scriptlibrary.ts`.
> - ✅ Écrire `customer.id.component.scriptlibrary.ts` dont les méthodes portent exactement les noms des `Method` déjà déclarés côté page-ui.

## Quand utiliser ce skill

- Une page produite par `divalto-page-ui` déclare un `Events.AfterChildrenLoad: { Method: "..." }` ou un bouton avec `OnClick` → il faut écrire la méthode correspondante.
- Implémenter ou modifier un handler de bouton, un hook de datasource, un lifecycle de composant.
- Tout code-behind qui appelle un service SDK `$xxx` (charger des données, naviguer, notifier, lire/écrire une variable de session…).

## Procédure

> **Gate avant réponse — INTERDICTION de répondre tant que la checklist n'est pas intégralement cochée.**
>
> Un `.scriptlibrary.ts` produit par ce skill est cassé à la compilation (ou pire, à l'exécution) si l'un des points suivants n'est pas vérifié. Avant de revenir à l'utilisateur, tu DOIS pouvoir cocher :
>
> - [ ] **Langage** : la sortie est du TypeScript dans un `.scriptlibrary.ts`. Aucun C# (`.cs`, `Task<>`, `namespace`, `using`), même si le besoin parle de « serveur » / « base » / « batch » (cf. Règles dures).
> - [ ] **Périmètre** : seuls des fichiers `.scriptlibrary.ts` sont écrits. **Aucun** JSON de page/composant touché (le binding `Events`/`OnClick` et son placement = `divalto-page-ui`), aucun datasource/SQL/config (cf. Règles dures).
> - [ ] **Gate service** : chaque `$xxx` utilisé apparaît dans la sortie de `list_typescript_services` appelée dans ce tour. Aucun service inventé (le piège classique : `$datasource` n'existe pas — c'est `$database`).
> - [ ] **Gate méthode** : pour chaque appel `$xxx.maMethode(...)`, `get_typescript_methods({ service: "$xxx" })` a été appelé dans ce tour et la méthode existe, avec la signature respectée (nombre et types des paramètres, ordre, optionnels).
> - [ ] **`await` sur les méthodes async** : toute méthode dont `get_typescript_methods` renvoie `isAsync: true` (retour `Promise<…>`) est appelée avec `await`, dans une méthode elle-même `async`.
> - [ ] **Liaison page ↔ classe** : chaque `Method` déclarée dans les `Events`/`OnClick` du JSON associé a sa méthode homonyme dans la classe exportée ; inversement aucune méthode publique morte qui ne serait référencée nulle part.
> - [ ] **Nommage fichier** : `<entité>[.id].{page|component|part|models|entity}.scriptlibrary.ts`, segment `<entité>` reprenant la casse d'origine du nom logique (cf. table de nommage).
> - [ ] **`getById` déprécié** : le code privilégie `getByIdAsync` (await) ; `getById` synchrone n'est utilisé que pour un composant garanti déjà chargé (et jamais pour un composant chargé plus tard dans le cycle).
> - [ ] **Action composant typée plutôt que `setPropertyById` deviné** : pour une action qui a une méthode d'instance dédiée (activer un onglet = `setActiveTab`, alimenter une grille = `setData`…), récupérer le composant typé (`getByIdAsync<XxxComponent>(...)`) et appeler la méthode — **pas** `setPropertyById` avec un nom inventé. Le `propertyName` de `setPropertyById` est un `string` libre : il n'est **pas** vérifié par les gates SDK (piège : `SelectedTab`/`CurrentTab`/`BadgeValue` n'existent pas).
> - [ ] **Classe et méthode d'instance identifiées** : `XxxComponent` dans `getByIdAsync<XxxComponent>(...)` est exactement le `scriptClass` renvoyé par `get_component_properties({ component: "<type>" })` appelé dans ce tour (jamais un nom déduit par convention — piège : `grid` → `GridComponent` n'est pas une règle générale) ; chaque méthode appelée dessus existe dans la déclaration de cette classe (chaîne `extends` comprise) lue dans le `.d.ts` du SDK dans ce tour — ce skill n'exécute pas `tsc`, une méthode inventée n'est donc détectée par rien d'autre avant la revue humaine.
> - [ ] **Gate propriété** : tout `setPropertyById(id, propertyName, …)` restant a son `propertyName` confirmé par `get_component_properties({ component: "<type>" })` dans ce tour. Aucune propriété inventée.
>
> Si une case ne peut pas être cochée → corriger **avant** de répondre. Pas de « je vérifierai la signature après », pas de « ce service existe sûrement ».

### 1. Analyser le besoin

Identifier :

- **Type de code-behind** : page, composant, part, models, entité (détermine le suffixe du fichier et le nom de la classe).
- **Points d'entrée** : quels `Events` / `_Click` / hooks la page (ou le composant) déclare. Si le JSON existe déjà, l'ouvrir pour relever les valeurs `Method`. Si on enchaîne avec `divalto-page-ui` dans le même tour, reprendre les `Method` qu'il vient de déclarer.
- **Comportement** : quelles données charger, quoi afficher, quelles interactions.

### 2. Localiser le fichier et des exemples existants

Le code-behind vit **à côté** du `.page.json` / `.component.json` qu'il sert :

```
DeviceTypes/Default/<entité>/<entité>.page.scriptlibrary.ts
DeviceTypes/Default/<entité>/id/<entité>.id.page.scriptlibrary.ts
```

Chercher dans le workspace des `.scriptlibrary.ts` voisins pour respecter le style et la façon dont les services y sont appelés (`Grep`/`Glob`).

### 3. Lister les services SDK disponibles — GATE OBLIGATOIRE

Appel **obligatoire** avant d'écrire la moindre ligne qui utilise un `$xxx` :

```
list_typescript_services()
```

**Source de vérité unique.** La liste reflète la version du SDK réellement installée dans le workspace (`node_modules/@types/divalto-studio`). Ne jamais utiliser un `$xxx` absent de cette liste, même s'il « sonne » juste. Avant de dupliquer un helper, vérifier qu'un service ne le fournit pas déjà (sa `description` le dit).

> Piège fréquent : pour charger les données d'un datasource, l'IA invente `$datasource.load(...)`. Le service réel est **`$database`** (`selectAsync`, `getAsync`, `updateAsync`…). La gate existe précisément pour attraper ce genre d'hallucination.

### 4. Récupérer la signature de chaque méthode appelée — GATE OBLIGATOIRE

Appel **obligatoire** pour CHAQUE service dont on appelle une méthode :

```
get_typescript_methods({ service: "$component" })
get_typescript_methods({ service: "$database" })
```

Pour chaque méthode utilisée : respecter exactement les paramètres (nombre, ordre, types, optionnels) et **`await` si `isAsync: true`**. Ne jamais ajouter un paramètre ou inventer un overload qui n'apparaît pas dans la sortie.

### 5. Écrire le `.scriptlibrary.ts`

Structure canonique — une classe exportée par défaut, une méthode `async` par point d'entrée déclaré dans le JSON :

```ts
export default class <fichier>_<type> {
  // Method référencée par Events.AfterChildrenLoad de la page
  async <entité>_afterChildrenLoad() {
    const grid = await $component.getByIdAsync('grid.commandes');
    const result = await $database.selectAsync('orderheader.grid', null, { customerId: 42 });
    grid.setData(result.Data);
  }

  // Method référencée par OnClick d'un bouton
  async valider_Click() {
    $notify.info('Validé');
  }
}
```

Règles :

- **Nom de classe** = nom du fichier sans extension, séparateurs `.` remplacés par `_`, **casse conservée telle qu'écrite dans le nom de fichier** — aucune casse n'est forcée (ex. `customer.id.page` → `customer_id_page`, `customerContact.id.component` → `customerContact_id_component`). Convention mesurée sur 96,7 % des `.scriptlibrary.ts` du corpus FUNC.BackOffice.
- **Nom de méthode** = exactement la valeur `Method` déclarée dans l'`Events`/`OnClick` côté JSON (ou le nom attendu par le hook). Le binding page ↔ classe se fait **par ce nom de méthode** (`lib[methodName]` côté runtime FW.Runtime) — **pas** par le nom de la classe, qui n'est jamais lu à l'exécution : un écart de nom de méthode = handler jamais appelé ; un écart de nom de classe n'a aucun effet fonctionnel (garder la convention ci-dessus pour la lisibilité, pas par nécessité technique).
- Méthodes `async` dès qu'elles `await` un service.
- Indentation 2 espaces, pas de point-virgule manquant (respecter le style des fichiers voisins).
- Pas de commentaire qui paraphrase le code ; un commentaire seulement pour un *pourquoi* non évident.

Détails des cinq patterns (handler de page, handler de bouton, hook de datasource, lifecycle de composant, traitement async) : voir [`references/patterns.md`](./references/patterns.md). Exemple complet de bout en bout (scénario fiche client) : [`references/examples/customer-fiche-afterload.md`](./references/examples/customer-fiche-afterload.md).

### 6. Self-check de complétude (gate avant réponse)

Re-parcourir le code produit et **cocher** chaque case du « Gate avant réponse » en tête de procédure :

- [ ] Sortie en TypeScript `.scriptlibrary.ts`, **aucun C#**.
- [ ] Périmètre respecté : seuls des `.scriptlibrary.ts` écrits ; aucun JSON de page/composant modifié (binding `Events`/`OnClick` = `divalto-page-ui`).
- [ ] Chaque `$xxx` utilisé est dans la sortie de `list_typescript_services` de ce tour.
- [ ] Chaque méthode `$xxx.m(...)` a été vérifiée via `get_typescript_methods` (signature exacte).
- [ ] Chaque méthode async (`isAsync: true`) est `await`ée dans une méthode `async`.
- [ ] Chaque `Method` du JSON a sa méthode homonyme dans la classe ; pas de méthode publique morte.
- [ ] Nom de fichier conforme (`<entité>[.id].{page|component|part|models|entity}.scriptlibrary.ts`, casse d'origine conservée).
- [ ] `getByIdAsync` privilégié à `getById` déprécié.
- [ ] Chaque `getByIdAsync<XxxComponent>` utilise le `scriptClass` renvoyé par `get_component_properties`, et chaque méthode d'instance appelée dessus existe dans sa déclaration `.d.ts`.

Si une case ne peut pas être cochée → **retourner à l'étape 3, 4 ou 5**. Ne pas répondre tant que tout n'est pas coché.

### 7. Sauvegarder

Créer ou mettre à jour le fichier au bon emplacement, puis produire un résumé :

1. Fichier(s) généré(s) (chemins).
2. Services SDK utilisés et méthodes appelées (confirmer qu'aucun n'est inventé).
3. Méthodes de la classe et l'`Event`/`_Click` que chacune sert.

> Compilation : le code doit passer `yarn compile` côté workspace utilisateur. Ce skill ne compile pas lui-même — le respect strict des gates 3-4 est ce qui garantit l'absence d'erreur de typage.

---

## Conventions de nommage des fichiers

> Le segment `<entité>` reprend la casse du nom logique tel qu'il apparaît dans le workspace, même en CamelCase (`customerType` reste `customerType`, pas `customertype`) — aucune casse forcée : c'est ce que fait le corpus existant.

| Code-behind             | Pattern                                       | Exemple                                         |
| ----------------------- | --------------------------------------------- | ----------------------------------------------- |
| Page                    | `<entité>[.id].page.scriptlibrary.ts`         | `customer.id.page.scriptlibrary.ts`             |
| Composant               | `<entité>[.id].component.scriptlibrary.ts`    | `customer.id.component.scriptlibrary.ts`        |
| Part d'une page         | `<entité>.id.<nom>.part.scriptlibrary.ts`     | `customer2.id.testbutton.part.scriptlibrary.ts` |
| Modèles                 | `<entité>.id.models.scriptlibrary.ts`         | `customer.id.models.scriptlibrary.ts`           |
| Entité                  | `<entité>.entity.scriptlibrary.ts`            | `entity-views-selection.entity.scriptlibrary.ts`|

Le segment intermédiaire (`page` / `component` / `part` / `models` / `entity`) désigne le type de code-behind et n'est pas optionnel.

---

## Outils MCP

| Outil                                          | Usage                                                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `list_typescript_services()`                   | Lister les services SDK (`$xxx`) installés dans le workspace. Source de vérité — appeler avant tout `$xxx`. |
| `get_typescript_methods({ service })`          | Signatures exactes d'un service (params, types, `isAsync`). Appeler avant tout appel de méthode.       |
| `get_component_properties({ component })`      | Propriétés de config d'un composant et son `scriptClass`. Appeler avant tout `setPropertyById` (valider le `propertyName`) et avant tout `getByIdAsync<XxxComponent>` (connaître `XxxComponent`). |

> **Règle d'autorité** : `list_typescript_services` et `get_typescript_methods` sont la **seule** source de vérité sur la surface SDK (services `$xxx` et leurs méthodes). Un `$xxx` ou une méthode absent de leur sortie n'existe pas — peu importe à quel point le nom paraît plausible.
>
> **Méthodes d'instance de composant** (le type retourné par `getByIdAsync<XxxComponent>`, ex. `setActiveTab`, `setData`) ne sont pas des services `$xxx`, donc pas couvertes par `get_typescript_methods`. `XxxComponent` est le `scriptClass` renvoyé par `get_component_properties` — jamais un nom déduit par convention. Une fois la classe connue, lire sa déclaration (chaîne `extends` comprise) dans le `.d.ts` du SDK pour ses méthodes ; une méthode absente de cette déclaration n'existe pas.
>
> Le `propertyName` de `setPropertyById` reste une **propriété de config**, à valider via `get_component_properties` (pas via les outils typescript, pas via `scriptClass`).
