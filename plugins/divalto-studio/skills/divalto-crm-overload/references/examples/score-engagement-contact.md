# Exemple — « Score d'engagement sur Contact »

Scénario de gating de la feature : sur un projet CRM ouvert, l'intégrateur demande

> « Ajoute un champ *Score d'engagement* (entier 0-100) à la fiche *Contact*, affiche-le dans le formulaire et dans la liste, et calcule-le à partir du nombre d'interactions des 90 derniers jours. »

Les deux artefacts produits, tous dans le **périmètre d'édition actif** (spé pour un intégrateur). **Exemple illustratif** : les noms exacts (chemins, datasources, style de code-behind) dépendent du standard réel du projet — toujours partir du fichier standard effectivement lu (étape 2), pas de ces noms.

## 1. Fiche projet (surcharge, réécrite en entier)

La fiche Contact standard est typiquement un **`.component.json`** (`customerContact.id.component.json`, racine `"Type": "page"`, plusieurs centaines de lignes : Conditions, bindings, events). On surcharge le **même fichier, même extension**, au même chemin relatif, dans le projet : on reprend le contenu standard **intégralement** et on y ajoute le champ. La construction est déléguée au skill `divalto-page-ui` (structure fiche : `crud` en 1er enfant).

Extrait de l'ajout côté formulaire (dans un `group` du `crud`) :

```json
"engagementScore": {
  "Type": "numberbox",
  "Label": "Score d'engagement",
  "ScriptId": "script_engagementScore",
  "DataField": "engagementScore",
  "Min": 0,
  "Max": 100
}
```

Extrait de l'ajout côté liste (dans `Columns` de la grille — `customerContact.grid.datasource.json` / `customer.customercontact.grid.datasource.json`) :

```json
"engagementScore": { "Title": "Score d'engagement", "Type": "Int" }
```

> Validation : `validate_divalto_file({ type: "component" })` pour le `.component.json` ; `{ type: "datasource" }` pour les datasources de grille modifiés.

## 2. Scriptlibrary projet (calcul)

Calcule le score à partir des interactions des 90 derniers jours. **S'aligner sur le style de code du standard observé** :

- si la fiche a déjà un code-behind `.scriptlibrary.ts` avec un handler de chargement → le réécrire en entier en **préservant la logique existante** et y ajouter le calcul ;
- si la fiche utilise des scripts séparés `.script.ts` (style ancien, sans `AfterChildrenLoad`) → suivre ce style.

Identifier la **source réelle** des interactions via le dictionnaire (`get_dictionary_entity`) — entité/relation qui porte les interactions du contact — et la requêter via `$database` / `$serverscript` (services confirmés par `list_typescript_services`).

```ts
// Illustratif — nom de classe/handler à caler sur le fichier standard réel
export default class customerContactId {
  // ... logique standard existante préservée ...

  async onLoad(): Promise<void> {
    const score = await customerContactId.computeEngagementScore();
    $component.tryGetById('script_engagementScore')?.setValue(score);
  }

  private static async computeEngagementScore(): Promise<number> {
    // agréger les interactions des 90 derniers jours via $database / $serverscript
    const interactions = /* … requête sur la source réelle, fenêtre 90 j … */ 0;
    return Math.max(0, Math.min(100, interactions));
  }
}
```

> Le `numberbox` porte `ScriptId: "script_engagementScore"` pour être adressable via `$component.tryGetById`. Le calcul est déclenché au chargement de la fiche selon le mécanisme du standard (event de page si la fiche en a un, sinon script existant).

## Résultat attendu

- 2 fichiers, tous dans le projet ; le standard Contact est inchangé.
- `validate_divalto_file` passe sur le `.component.json` (type `component`) et les `datasource` produits.
- **F5** → la fiche Contact affiche le score en formulaire et en colonne de liste.
