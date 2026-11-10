---
name: divalto-conditions
description: "Crée ou réutilise une condition Divalto (`*.condition.json`) et la référence depuis une config. Utiliser pour : autoriser ou interdire une action (CanInsert/CanUpdate/CanDelete), afficher ou masquer un élément selon le contexte, conditionner l'interprétation d'une config — au lieu d'un script impératif."
argument-hint: "Décrivez la règle (ex: autoriser la suppression seulement si le champ X vaut 1, masquer un bouton hors administrateur...)"
allowed-tools: list_condition_types, get_condition_properties, validate_divalto_file, Read, Write, Edit, Glob, Grep
---

# Conditions Divalto

## Ce qu'est une condition

Une **condition** est une règle booléenne **nommée et réutilisable**, autorée comme un fichier `*.condition.json` (type `condition`). On la référence par son nom (avec des `Params`) à deux endroits, aux sémantiques distinctes :

- **Sur une valeur conditionnelle** — `CanInsert`/`CanUpdate`/`CanDelete`/`CanValidate`/`CanDuplicate` d'un `crud`, et toute propriété de type valeur conditionnelle : les conditions **résolvent la valeur**. Ex. `CanDelete` vaut vrai seulement si elles sont satisfaites → bouton affiché/masqué ; la config reste interprétée.
- **Sur une config entière** — bloc `Conditions` présent sur n'importe quelle config : si elles ne sont pas satisfaites, la **config n'est pas interprétée** (élément non rendu).

La même condition est **réutilisable** : on la référence à plusieurs endroits avec des `Params` différents.

## Quand l'utiliser

- Autoriser/interdire une action déclarativement : `CanInsert`/`CanUpdate`/`CanDelete`/`CanValidate`/`CanDuplicate` d'un `crud`, et plus largement toute config portant un bloc `Conditions`.
- **Préférer une condition à un événement impératif** (`BeforeDelete` + script + `$token.cancel`) quand il s'agit simplement d'autoriser/interdire selon une règle. L'événement reste pour la logique impérative (effets de bord, contrôles multi-champs/async).

## Référencer une condition (depuis une config consommatrice)

```json
"CanDelete": {
  "Conditions": [
    { "Name": "maCondition", "Params": { "monParam": "valeur" }, "Operator": "And" }
  ]
}
```
- `Name` : nom de la condition (fichier `maCondition.condition.json`).
- `Params` : valeurs passées aux paramètres déclarés par la condition.
- `Operator` : combinaison en pipeline avec les conditions précédentes — `And` (défaut), `Or`, `AndNot`, `OrNot`. Ordre significatif : `(((true OP1 C1) OP2 C2) …)`.

> **Valeur** (`Can*`) : soit `true`/`false`, soit l'objet `Conditions` ci-dessus. **Config entière** : poser un bloc `Conditions` (mêmes items) au niveau de la config à conditionner.

## Créer une condition

1. **Chercher d'abord l'existant** — `Glob` `**/*.condition.json`, réutiliser si une condition couvre déjà la règle.
2. **Créer** `<nom>.condition.json` dans le périmètre d'édition (identifié par l'extension `*.condition.json`, pas par un dossier imposé).
3. **Forme** :
```json
{
  "Params": { "tableName": "string" },
  "Definition": { "Type": "dynamicfield", "Tablename": "{{tableName}}" }
}
```
   - `Params` (optionnel) : paramètres déclarés (nom → type indicatif `"string"`/`"bool"`), injectés via `{{nomParam}}` dans la `Definition`.
   - `Definition` : le mécanisme d'évaluation. **Découvrir les `Type` via `list_condition_types`** et leurs champs via `get_condition_properties({ condition: "<type>" })` (source de vérité, lue du schéma) ; sémantique comportementale et exemples dans [references/definition-types.md](references/definition-types.md).
   - **Placeholders** : `{{nomParam}}` pour un `Param` déclaré ; `{{id}}` = id de la ligne courante (clé du `crud` consommateur), plus d'autres paramètres de contexte ambiants (ex. `{{baseUser}}`) — disponibles sans les déclarer. Règle SQL sur la ligne courante : `… WHERE <clé> = {{id}}`.
4. **Valider** le fichier produit (`validate_divalto_file`, type `condition`) — contrôle léger : le schéma est permissif, il n'attrape que les erreurs grossières.

## MUST NOT

- ❌ Inventer un `Type` de `Definition` absent de `list_condition_types`. ✅ N'utiliser que ceux qu'il renvoie (ou une datasource renvoyant un booléen).
- ❌ Écrire un script/event pour une simple règle d'autorisation. ✅ Référencer (ou créer) une condition.
- ❌ Si `Definition.Type` est une datasource (ex. `sql`), renvoyer autre chose qu'un booléen. ✅ La requête doit renvoyer un booléen.
