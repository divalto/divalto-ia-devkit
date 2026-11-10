# Exemple — fiche client avec `AfterChildrenLoad` chargeant une donnée additionnelle

Scénario d'acceptation de la story : un développeur métier demande une page fiche client dont l'event `AfterChildrenLoad` charge les commandes du client et les affiche dans une grille. Il illustre l'enchaînement `divalto-page-ui` (structure + déclaration de l'`Event`) → `divalto-scriptlibrary` (code-behind), et les deux gates MCP.

## 1. Côté page (produit par `divalto-page-ui`)

`DeviceTypes/Default/customer/id/customer.id.page.json` — extrait : l'`Event` est déclaré **au niveau `page`** et pointe une `Method`.

```json
{
  "Type": "page",
  "Title": "Fiche client",
  "Events": {
    "AfterChildrenLoad": { "Method": "customerCard_afterChildrenLoad" }
  },
  "Children": {
    "myCrud": {
      "Type": "crud",
      "DataSource": "customer.id.crud",
      "Children": {
        "myTabs": {
          "Type": "tabs",
          "StaticChildren": {
            "tabOrders": {
              "Type": "tab",
              "Title": "Commandes",
              "Children": {
                "ordersGrid": { "Type": "grid", "DataSource": "orderheader.grid", "Columns": { /* … */ } }
              }
            }
          }
        }
      }
    }
  }
}
```

## 2. Gates MCP avant d'écrire le code-behind

```
list_typescript_services()
```

→ on y trouve `$component`, `$database`, `$loader`… On NE trouve PAS `$datasource`. L'intuition « charger un datasource = `$datasource.load()` » est donc fausse : c'est `$database`.

```
get_typescript_methods({ service: "$database" })
```

→ `selectAsync(dataSource: string, context?: DataSourceContext | null, params?: unknown | null, silentErrors?: boolean): Promise<SfkDataResult<T>>` — `isAsync: true`.

```
get_typescript_methods({ service: "$component" })
```

→ `getByIdAsync<T>(scriptId: string): Promise<T>` — `isAsync: true` ; `setData(data: any[]): void` — synchrone. `getById` est marqué déprécié → on prend `getByIdAsync`.

## 3. Code-behind (produit par ce skill)

`DeviceTypes/Default/customer/id/customer.id.page.scriptlibrary.ts` :

```ts
export default class customer_id_page {
  async customerCard_afterChildrenLoad() {
    $loader.showLoader();
    try {
      const result = await $database.selectAsync('orderheader.grid', null, {
        customerId: await this.currentCustomerId(),
      });

      const grid = await $component.getByIdAsync('ordersGrid');
      grid.setData(result.Data);
    } finally {
      $loader.hideLoader();
    }
  }

  private async currentCustomerId(): Promise<number> {
    const crud = await $component.getByIdAsync('myCrud');
    return crud.getValue();
  }
}
```

## 4. Vérification contre la checklist

- Nom de méthode `customerCard_afterChildrenLoad` = valeur `Method` de l'`Event` côté JSON. ✅
- `$database`, `$component`, `$loader` tous présents dans `list_typescript_services`. Aucun `$datasource` inventé. ✅
- `selectAsync` et `getByIdAsync` vérifiés via `get_typescript_methods`, `isAsync: true` → `await`. `setData`, `showLoader`/`hideLoader` synchrones → sans `await`. ✅
- Fichier `customer.id.page.scriptlibrary.ts`, segment entité en minuscules. ✅
- `getByIdAsync` (non déprécié) plutôt que `getById`. ✅

Résultat attendu : compile sous `yarn compile`, 0 service inventé, 0 méthode hallucinée.
