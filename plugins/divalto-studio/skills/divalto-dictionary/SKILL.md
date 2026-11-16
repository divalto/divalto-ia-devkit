---
name: divalto-dictionary
description: "Manipule le dictionnaire de données Divalto Studio (tables, colonnes, index, vues) en éditant les JSON sous `Dictionary/<layer>/`. Utiliser pour : ajouter ou modifier une colonne, créer une table, ajouter un index, créer une vue, traduire un libellé, surcharger un champ du standard. N'écrit que dans le périmètre d'édition actif."
argument-hint: "Décrivez l'opération (ex: ajoute une colonne `score` Int sur l'entité Contact, surcharge le libellé FR de `name` sur Customer, ajoute un index Mobile sur Contact.email)."
allowed-tools: list_dictionary_entities, get_dictionary_entity, validate_divalto_file, Read, Write, Edit, Glob, Grep
capabilities: [mobile]
---

# Manipulation du dictionnaire Divalto Studio

Le dictionnaire vit sous forme de **fichiers JSON, une ligne BDD par fichier**, dans un dossier dédié `Dictionary/` à la racine du workspace, avec **un sous-dossier par couche (« layer »)** de la chaîne d'overloads :

```
<workspaceRoot>/Dictionary/
├── _chain.json            ← chaîne ordonnée des layers (racine → actif) + layer éditable
└── <layer>/               ← une couche = un overload (ex. std, puis la spé du projet)
    ├── _registry.json     ← IDs BDD de la couche (auto)
    ├── entities/<code>/…
    └── views/<code>/…
```

Le layer racine est le standard ; le **dernier** layer de la chaîne est la couche **active (éditable)** — typiquement la spé du projet. Les layers non-racine sont **sparse** : ils ne contiennent que les records réellement surchargés. Le nom d'un dossier `<layer>` est le code de l'overload correspondant.

Toute modif est faite **localement sur disque**, puis synchronisée vers BDD par le mécanisme de push SCM du projet (pas par ce skill). Ce skill décrit **uniquement comment écrire les fichiers correctement**.

## Quand utiliser ce skill

- Ajouter, modifier ou supprimer une **colonne** d'une entité.
- Créer une nouvelle **entité** (table) ou en changer les propriétés (libellé, traductions, droits API).
- Ajouter/modifier/supprimer un **index**.
- Créer ou modifier une **vue** SQL et ses colonnes.
- **Surcharger** un champ du standard côté spé (ex. changer la longueur, le masque, le libellé).
- Ajouter une traduction (libellé `fr` / `en` / …) sur une entité, une colonne ou une vue.

Pour ajouter un champ ET l'afficher dans une page CRM ET le calculer, utiliser le skill coordinateur [`divalto-crm-overload`](../divalto-crm-overload/SKILL.md) — il délègue ici pour la partie dico.

## La règle d'or — périmètre d'édition actif uniquement

> **MUST — ne modifier QUE les fichiers du périmètre d'édition actif.** Le workspace marque comme lecture seule (`files.readonlyInclude`) les fichiers de l'autre périmètre. Ce verrou est **logique** (sync VS Code + serveur), pas un droit POSIX : un `Write` qui « ne casse pas » n'est **pas** une preuve d'autorisation. Cf. le contexte permanent.
>
> - Périmètre spé actif (cas standard intégrateur) → écrire **uniquement** dans le dossier de la couche **active** (`Dictionary/<layerActif>/...`). Les autres couches (dont le standard) se lisent, **ne se modifient pas**.
> - Périmètre std actif (devs R&D, `divalto.enableStandardMode = true` + capability `CanModifyStandard`) → la couche active est le standard ; écrire **uniquement** dans son dossier. Les couches spé se lisent, **ne se modifient pas**.
> - ❌ Contourner le verrou via Bash / `fs.writeFile` direct sur un chemin read-only — l'écriture peut passer sur disque mais ne sera **pas** synchronisée et corrompt l'état local.
>
> Si la tâche semble exiger d'écrire dans l'autre périmètre → **arrêter et demander**. Pour une surcharge depuis le std, proposer le même chemin relatif côté spé (cf. [`references/overrides.md`](./references/overrides.md)).

## Gate avant réponse

> **INTERDICTION de répondre tant que la checklist n'est pas intégralement cochée.**
>
> - [ ] **Pas de modification d'entité système** : ne jamais créer/modifier/surcharger une entité dont `namespace` vaut `"system"` (ni ses colonnes/index). Ce sont des tables framework, en lecture seule pour l'intégrateur. Elles sont masquées de l'éditeur ; si une tâche semble l'exiger, **arrêter et demander**.
> - [ ] **Périmètre respecté** : aucun fichier écrit en dehors du périmètre d'édition actif.
> - [ ] **Aucun `code` / `name` dans le JSON** : pour entité, colonne, index, vue, view-column — l'identifiant est porté **par le nom du fichier ou du dossier**, jamais par une propriété JSON. Idem : pas de `metaTable_ID`, `metaColumn_ID`, `overloadId` dans les fichiers (ils vivent dans `_registry.json`, géré automatiquement).
> - [ ] **Pas de sentinelles** : aucune valeur `"Ø"`, `-2147483648`, `-9223372036854776000`, `-1.7976931348623157e308`, `"0001-01-01T00:00:00"` dans le JSON. Si une valeur doit être « héritée du parent » côté spé, **omettre la clé** entièrement.
> - [ ] **Override spé = sparse** : un fichier écrit en spé ne contient **que** les clés qui diffèrent réellement du std. Pas de réplication exhaustive du std.
> - [ ] **Préfixe d'overload sur toute création spé** : un record **créé** dans la couche spé (entité, colonne, index, vue, colonne de vue qui n'existe **pas** dans le std) a son code/nom préfixé par `<codeOverload>_` (ex. `final_`). Cf. [Préfixe d'overload](#préfixe-doverload-création-spé). Une **surcharge** d'un record std garde le code std (pas de préfixe) — l'exemption ne vaut que si le même code existe déjà en std.
> - [ ] **Schéma respecté** : valeurs d'enum strictement dans les listes (`ColumnType`, `IndexTarget`, `SqlModeCode`) — cf. [`references/schemas.md`](./references/schemas.md). `additionalProperties: false` sur tous les schémas → aucune clé inconnue.
> - [ ] **ForeignKey complet** : toute colonne `type: "ForeignKey"` a un `foreignEntity: "<code>"` (le code de l'entité ciblée, pas son `schemaTable`).
> - [ ] **Index — `columns` référence des CODES de colonne** : les entrées du tableau `columns` d'un index sont les **codes** (= noms de fichiers `*.metacolumn.json` sans suffixe), pas les `schemaColumn` physiques.
> - [ ] **Validation** : pour chaque fichier produit ou modifié, `validate_divalto_file({ type: "<metatable|metacolumn|metaindex|metaview|metaviewcolumn>", content })` passe. Les types dico utilisent le préfixe `meta*` (le type `entity` du MCP désigne autre chose — l'entité métier d'une page).
> - [ ] **Pas de push manuel** : la sync vers BDD est faite par le mécanisme SCM du projet ; ne pas appeler d'endpoint API ni de commande de push depuis ce skill.
>
> Si une case ne peut pas être cochée → corriger **avant** de répondre.

## Procédure

### 1. Identifier l'entité cible

Si l'utilisateur cite une entité par son nom métier (`Contact`, `Customer`, `OrderHeader`), résoudre son **code de dictionnaire** :

```
list_dictionary_entities()           // découverte
get_dictionary_entity({ code })      // table + colonnes + index, vue cross-layer
```

Le code de l'entité est ce qui apparaît dans `Dictionary/<layer>/entities/<code>/`. Il diffère parfois du `schemaTable` physique (`sw_data_contacts` → code `contacts`).

### 2. Résoudre le périmètre actif

- Vérifier le périmètre d'édition actif (status bar VS Code « Spécialisé » ou « Standard », ou la config `divalto.enableStandardMode`).
- Calculer le chemin cible :
  - le chemin cible vit dans le dossier de la **couche active** de la chaîne : `Dictionary/<layerActif>/...` (spé du projet en périmètre spé, standard en périmètre std)
- ❌ Si l'utilisateur demande une modif dont la cible « naturelle » est l'autre périmètre (ex. « modifie le standard » alors qu'on est en spé), **ne pas y écrire** — proposer soit une **surcharge spé** (cf. [`references/overrides.md`](./references/overrides.md)), soit demander de basculer de périmètre.

### 3. Construire le chemin de fichier

| Élément       | Chemin                                                                                | L'identifiant est porté par… |
| ------------- | ------------------------------------------------------------------------------------- | ----------------------------- |
| Entité        | `Dictionary/<layer>/entities/<code>/metatable.json`                                   | le dossier `<code>`           |
| Colonne       | `Dictionary/<layer>/entities/<entityCode>/columns/<columnCode>.metacolumn.json`       | le nom de fichier             |
| Index         | `Dictionary/<layer>/entities/<entityCode>/indexes/<indexName>.metaindex.json`         | le nom de fichier             |
| Vue           | `Dictionary/<layer>/views/<viewCode>/metaview.json`                                   | le dossier `<viewCode>`       |
| Colonne de vue | `Dictionary/<layer>/views/<viewCode>/columns/<columnCode>.metaviewcolumn.json`        | le nom de fichier             |

> **MUST — l'identifiant n'apparaît jamais dans le JSON.** Pas de `code`, pas de `name` (sauf `name` au sens de la vue physique, qui est une propriété distincte du code, cf. ci-dessous). Le reader / writer recalcule l'identifiant depuis le chemin.

#### Préfixe d'overload (création spé)

> **MUST — tout record CRÉÉ dans la couche spé porte le code de l'overload courant comme préfixe : `<codeOverload>_<base>`.** Studio 4s l'impose (`BaseOverloadsManager.GetOverloadItemCode` : `code = CurrentOverload.CodeOverload + "_" + base`). Ça vaut pour **tous** les types créés en spé : entité (dossier `final_devis/`), colonne (`final_montant.metacolumn.json`), index (`final_idxClient.metaindex.json`), vue (dossier `final_devisActifs/`), colonne de vue (`final_total.metaviewcolumn.json`). Le standard n'a pas de préfixe.
>
> - **Création spé-only** (le code n'existe **pas** en std) → préfixe **obligatoire**. Ex. nouvelle table `final_devis`, nouvelle colonne `final_montant` dans `final_devis`.
> - **Surcharge** d'un record std (même code présent en std) → **garder le code std, sans préfixe**. Ex. surcharger la colonne `name` de `customer` → fichier spé `name.metacolumn.json` (PAS `final_name`). Le code doit être strictement identique entre les deux couches pour qu'elles s'associent.
> - **Exception — colonne code fonctionnelle** : la colonne `code<entityCode>` (ex. entité `final_spefeb` → colonne `codefinal_spefeb`) est nommée d'après l'entité, **pas** d'après l'overload : **pas** de préfixe `final_` supplémentaire (ce serait `final_codefinal_spefeb`, à proscrire).
>
> **Trouver `<codeOverload>`** : c'est le `codeoverload` de l'overload spé du projet (table `sw_sys_overload`), résolu au *Load dictionary from server*. En pratique, c'est le préfixe commun des entités déjà présentes sous `Dictionary/<layerActif>/entities/` (ex. `final_*`). En cas de doute, l'inférer de l'existant ou demander — ne pas inventer un préfixe.

### 4. Écrire le fichier (création ou modification)

Squelettes minimaux ; ajouter seulement les clés qui ont une valeur à écrire. Toutes les clés sont **optionnelles** au niveau du schéma — un fichier de surcharge spé ne porte que les champs surchargés.

**Entité** (`<code>/metatable.json`) :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/entity.schema.json",
  "label": "Contact",
  "schemaTable": "sw_data_contacts",
  "sqlModeCode": "CaseInsensitive",
  "api": { "read": true, "insert": true, "update": true, "delete": false },
  "translations": { "fr": "Contact", "en": "Contact" }
}
```

**Colonne** (`<entityCode>/columns/<columnCode>.metacolumn.json`) :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/column.schema.json",
  "schemaColumn": "score",
  "type": "Int",
  "server": { "edit": true, "visible": true },
  "mobile": { "available": true, "edit": false, "visible": true }
}
```

ForeignKey :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/column.schema.json",
  "schemaColumn": "customer_id",
  "type": "ForeignKey",
  "foreignEntity": "customer"
}
```

**Index** (`<entityCode>/indexes/<indexName>.metaindex.json`) :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/index.schema.json",
  "target": "Both",
  "columns": ["Email", "DateCreated"]
}
```

> `columns` contient les **codes** des colonnes (= leurs noms de fichier sans `.metacolumn.json`), pas leur `schemaColumn`. Si l'index doit pointer la colonne `Email` dont le fichier est `Email.metacolumn.json` mais dont `schemaColumn` est `email_addr`, on écrit `"Email"`.

**Vue** (`<viewCode>/metaview.json`) :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/view.schema.json",
  "label": "Contacts actifs",
  "name": "sw_view_active_contacts",
  "query": "SELECT id, name, email FROM sw_data_contacts WHERE active = 1",
  "api": { "read": true }
}
```

Pour une vue, `name` (= nom physique côté BDD) **est** dans le JSON. C'est le **code** logique (= nom du dossier `<viewCode>`) qui en est absent.

**Colonne de vue** (`<viewCode>/columns/<columnCode>.metaviewcolumn.json`) :

```json
{
  "$schema": "https://divalto.com/schemas/dictionary/viewcolumn.schema.json",
  "columnName": "email",
  "type": "Varchar",
  "visible": true,
  "filterable": true
}
```

### 5. Surcharger un champ du standard côté spé

Cas typique : changer la longueur d'une colonne du standard ou ajouter une traduction sans toucher au standard.

> **MUST — un fichier spé est SPARSE : seules les clés réellement surchargées y figurent.** Le pull arrière (resync std → spé) repose sur cette sparsité ; un fichier spé qui réplique le std intégralement provoque un push qui réécrit toutes les colonnes serveur comme « surchargées », même celles qui ne devraient pas l'être.

Exemple — surcharge du libellé FR de la colonne `Name` sur `Customer`, sans toucher au reste :

```
// Dictionary/<layerActif>/entities/customer/columns/Name.metacolumn.json
{
  "$schema": "https://divalto.com/schemas/dictionary/column.schema.json",
  "translations": { "fr": "Raison sociale" }
}
```

C'est tout. Pas de `schemaColumn`, pas de `type`, pas de `server`/`mobile` — ces champs sont hérités du fichier standard. Voir [`references/overrides.md`](./references/overrides.md) pour les pièges (override partiel d'un sous-objet, override pour « repasser à la valeur défaut » via `null`, etc.).

### 6. Valider

Pour **chaque** fichier produit ou modifié :

```
validate_divalto_file({ type: "metatable",      content: "<json>" })  // <code>/metatable.json
validate_divalto_file({ type: "metacolumn",     content: "<json>" })  // *.metacolumn.json
validate_divalto_file({ type: "metaindex",      content: "<json>" })  // *.metaindex.json
validate_divalto_file({ type: "metaview",       content: "<json>" })  // <viewCode>/metaview.json
validate_divalto_file({ type: "metaviewcolumn", content: "<json>" })  // *.metaviewcolumn.json
```

> **Source de vérité.** Les schémas sont `additionalProperties: false` — une clé inconnue échoue. Si la validation passe, le fichier est conforme au contrat on-disk. C'est ce filet de sécurité qui te permet de savoir tout de suite si tu t'es trompé sur un enum (`type`, `target`, `sqlModeCode`) ou si tu as oublié de retirer un `code` / `id` du JSON.

Corriger toutes les erreurs avant de continuer.

### 7. Pas de push manuel

La synchro BDD se fait via le push SCM du projet (commande `Divalto: Push` ou équivalent). **Ne pas** appeler la `DatabaseAPI` directement ni exécuter de script de push depuis ce skill.

---

## Pièges courants

- **Confondre `code` et `schemaColumn`** : `code` = identifiant logique porté par le fichier (`CodeContact`), `schemaColumn` = nom physique en BDD (`code_contact`). Les références d'index utilisent toujours le **code**.
- **Inclure un `id` dans le JSON** : les IDs BDD vivent dans `_registry.json`, géré par le writer. Un `id` ou `metaColumn_ID` écrit en dur dans un fichier sera **ignoré** au push ; pire, il peut perturber le diff SCM.
- **Mettre `"Ø"` ou `-2147483648` pour dire « hérité »** : ce sont des sentinelles serveur. Côté disque, héritage = **clé absente**.
- **Réécrire le fichier std au lieu de créer la surcharge** : verrou logique read-only — l'écriture peut passer sur disque mais l'état réel du dico n'est pas modifié et le sync sera incohérent.
- **Index `target: "Mobile"` sur une colonne non `mobile.available`** : l'index sera créé mais inactif en mobile à l'exécution. Vérifier que la colonne est `mobile.available: true` si l'index est ciblé mobile.

## Outils MCP

| Outil                                       | Usage                                                                                          |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `list_dictionary_entities()`                | Lister les entités disponibles dans le dictionnaire (cross-layer).                             |
| `get_dictionary_entity({ code })`           | Récupérer la définition complète d'une entité (table + colonnes + index, fusion std+spé).      |
| `validate_divalto_file({ type, content })`  | Valider un JSON avant sauvegarde. Pour le dico : `type` ∈ {`metatable`, `metacolumn`, `metaindex`, `metaview`, `metaviewcolumn`}. ⚠️ `entity` est réservé à l'entité-page, pas à `MetaTable`. |
