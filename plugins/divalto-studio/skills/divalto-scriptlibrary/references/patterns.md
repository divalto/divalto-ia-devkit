# Patterns de code-behind `.scriptlibrary.ts`

Cinq patterns couvrent l'essentiel du code-behind Divalto. Chaque exemple est dérivé de fichiers de référence réels du projet (`FW.Runtime/.../Config/DeviceTypes/Default/`). Dans tous les cas, les services `$xxx` et leurs méthodes doivent avoir été vérifiés via `list_typescript_services` / `get_typescript_methods` avant d'être écrits.

> Rappel transverse : la classe est `export default class`, une méthode `async` par point d'entrée, nom de méthode = valeur `Method` côté JSON.

## 1. Handler d'event de page (`AfterChildrenLoad`, `BeforeUnload`)

Côté page (`divalto-page-ui`), les `Events` sont déclarés **au niveau `page`** et pointent une `Method` :

```json
{
  "Type": "page",
  "Events": {
    "AfterChildrenLoad": { "Method": "customerCard_afterChildrenLoad" },
    "BeforeUnload":      { "Method": "customerCard_beforeUnload" }
  },
  "Children": { /* … */ }
}
```

Code-behind correspondant :

```ts
export default class customer_id_page {
  async customerCard_afterChildrenLoad() {
    // les composants enfants sont chargés → on peut les récupérer et les alimenter
    const pays = await $component.getByIdAsync('script_customer_country');
    pays.setData(20000000329); // FRANCE
  }

  async customerCard_beforeUnload() {
    // nettoyage de l'état de session posé pendant la vie de la page
    await $session.removeAsync('setfilter_customer_ID');
  }
}
```

- `AfterChildrenLoad` est le point où les composants enfants sont garantis présents — c'est là qu'on initialise des valeurs ou qu'on déclenche un chargement. `grid` n'a **pas** d'event `AfterLoad` ; le composant ne s'auto-réagit pas, c'est la page qui orchestre.
- `BeforeUnload` sert au nettoyage (état de session, abonnements).

## 2. Handler de bouton (`_Click`)

Le bouton déclare sa méthode côté JSON (`OnClick` / `Events`), suffixée `_Click` par convention :

```ts
export default class customer_id_component {
  async valider_Click() {
    $notify.info('Validé');
  }

  async desactiverValider_Click() {
    $component.setPropertyById('buttonValider', 'Disabled', true);
  }
}
```

- `$notify.info(message)` / `success` / `error` : retour utilisateur synchrone.
- `$component.setPropertyById(scriptId, propertyName, value)` : muter une propriété d'un composant (Label, Disabled…) sans le re-récupérer.

## 3. Hook de datasource (chargement de données)

Charger les données d'un datasource et alimenter une grille — le cas du scénario d'acceptation. **`$database`, pas `$datasource`** (qui n'existe pas) :

```ts
export default class divarestapiforeign_page {
  async loadData() {
    $loader.showLoader();
    try {
      // selectAsync(dataSource, context?, params?, silentErrors?)
      const results = await $database.selectAsync('orderheader.grid', null, { customerId: 42 });

      const grid = await $component.getByIdAsync('grid.commandes');
      grid.setData(results.Data);
    } finally {
      $loader.hideLoader();
    }
  }
}
```

- Le 1er argument de `selectAsync` est le **nom du datasource** (le même que `DataSource: "<x>"` côté JSON, produit par `divalto-page-ui`).
- `results.Data` porte les lignes ; `setData` les pousse dans la grille.
- **`hideLoader()` dans un `finally`** : si `selectAsync`/`getByIdAsync` lève, le loader doit quand même être masqué — sinon l'UI reste bloquée en chargement. Tout `showLoader()` est apparié à un `hideLoader()` dans le `finally` du même bloc.

## 4. Lifecycle de composant

Un composant a son propre code-behind (`<entité>.id.component.scriptlibrary.ts`) et son propre `afterChildrenLoad`, indépendant de celui de la page :

```ts
export default class customer_id_component {
  async customer_id_component_afterChildrenLoad() {
    const comp = await $component.getByIdAsync('script_baseuserCustomer');
    const v = comp.getValue();
    // … initialisation dépendant de la valeur courante
  }

  async scrollToProjects() {
    const tabs = $component.tryGetById('script_tabs_main');
    if (tabs) {
      tabs.setActiveTab('projectsTab');
      tabs.scroll();
    }
  }
}
```

- `tryGetById` / `tryGetByIdAsync` renvoient `null` si le composant n'est pas présent (garder le `if`). **Sync** `tryGetById` si le composant est déjà chargé ; **async** `await tryGetByIdAsync` si son chargement n'est pas garanti — même asymétrie que `getById` (déprécié) vs `getByIdAsync`.
- `getByIdAsync` (vs `getById` **déprécié**) attend le chargement du composant : c'est le défaut sûr.

## 5. Traitement async

Toute méthode qui `await` un service est `async`. Enchaîner plusieurs appels async, gérer le retour, alimenter l'UI :

```ts
export default class customer_id_page {
  async refreshOutstanding_Click() {
    const result = await $database.selectAsync('orderheader.customeroutstanding', null, {
      customerId: this.currentId(), // helper local à implémenter selon le contexte de la page
    });

    if (result.Data.length === 0) {
      $notify.info('Aucune commande en cours');
      return;
    }

    const metric = await $component.getByIdAsync('outstandingMetric');
    metric.setData(result.Data[0].Total);
  }
}
```

- **Vérifier `isAsync` via `get_typescript_methods`** : `selectAsync` et `getByIdAsync` retournent `Promise<…>` → `await` obligatoire. `setData`, `setPropertyById`, `$notify.info` sont synchrones → pas d'`await`.
- Oublier un `await` sur un `Promise` ne fait pas échouer la compilation mais casse l'exécution (on manipule la promesse au lieu de la valeur) — d'où la gate.

---

## Erreurs fréquentes à éviter

| ❌ Erreur                                              | ✅ Correct                                                       |
| ----------------------------------------------------- | --------------------------------------------------------------- |
| `$datasource.load('customer.grid')`                   | `await $database.selectAsync('customer.grid', null, params)`    |
| `$component.getById('x')` pour un composant chargé tard | `await $component.getByIdAsync('x')`                            |
| `$component.tryGetById('x')` pour un composant optionnel chargé tard | `await $component.tryGetByIdAsync('x')`                  |
| Appel `selectAsync(...)` sans `await`                 | `const r = await $database.selectAsync(...)`                    |
| `grid` avec un `Events.AfterLoad` côté JSON            | `AfterChildrenLoad` au niveau **page** → méthode du scriptlibrary |
| Méthode dont le nom ≠ `Method` déclarée côté JSON      | nom de méthode = exactement la valeur `Method` / `OnClick`      |
| Un service ou une méthode jamais passé par les 2 gates | `list_typescript_services` + `get_typescript_methods` d'abord   |
| `$loader.showLoader()` … `hideLoader()` sans `try/finally` | `showLoader()` puis `try { … } finally { $loader.hideLoader(); }` |
| Activer un onglet via `setPropertyById('tabs', 'CurrentTab'/'SelectedTab', …)` (propriété + index devinés) | `const tabs = await $component.getByIdAsync<TabsComponent>('tabs'); tabs.setActiveTab('monOnglet');` (méthode d'instance typée, id d'onglet) |
| `setPropertyById(id, '<prop>', …)` avec une propriété non vérifiée | valider `<prop>` via `get_component_properties` ; si l'action a une méthode dédiée (`setActiveTab`, `setData`…), l'utiliser |
