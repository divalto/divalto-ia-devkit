---
name: divalto-translations
description: "Crée ou complète des clés de traduction dans le catalogue local `Translations/` (`<lang>.json` par layer et par entité). Utiliser pour : créer une clé, réutiliser une clé existante au lieu d'un libellé en dur ou d'un `translationKey: null`, traduire un libellé d'écran, corriger la valeur d'une langue. N'écrit que sur le layer actif."
argument-hint: "Décrivez l'opération (ex: crée une clé pour le libellé « Valider la commande » de mon écran mobile, complète la valeur DE de la clé Order_Submit)."
allowed-tools: Read, Write, Edit, Glob, search_translation_keys, get_translation_key, validate_divalto_file
capabilities: [mobile]
---

# Clés de traduction Divalto Studio

Le catalogue de traductions vit sous forme de **fichiers JSON par langue**, dans un dossier dédié `Translations/` à la racine du workspace, avec **un sous-dossier par couche (« layer »)** de la chaîne d'overloads puis **un sous-dossier par entité de traduction** :

```
<workspaceRoot>/Translations/
├── _chain.json                ← chaîne ordonnée des layers (racine → actif)
├── _reference.json            ← langues ({Language_ID, CodeLanguage, Enabled}) + entités ({LanguageEntity_ID, Name, folder})
└── <layer>/<entityFolder>/<lang>.json   ← map plate clé → valeur, triée par clé
```

Chaque `<lang>.json` est une **map plate `clé → valeur`**. Une valeur est soit le **texte nu** (disponible mobile — le défaut), soit la forme objet `{ "text": "...", "mobileExcluded": true }` **réservée à l'exclusion mobile** (`true` littéral uniquement ; l'absence du flag encode « disponible »).

Toute modif est faite **localement sur disque**, puis synchronisée par le push SCM du projet (pas par ce skill). Ce skill décrit **uniquement comment écrire les fichiers correctement**.

## Quand utiliser ce skill

- Créer une **nouvelle clé** de traduction avec ses valeurs par langue (au lieu de laisser `translationKey: null` ou un libellé en dur dans une définition générée).
- **Réutiliser** une clé existante pour un libellé — toujours chercher avant de créer.
- **Compléter ou corriger** la valeur d'une langue sur une clé existante.

Hors périmètre : supprimer/renommer une clé, la changer d'entité, créer une langue ou une entité de traduction — ces opérations passent par l'éditeur ou le serveur, pas par ce skill.

## La règle d'or — layer actif uniquement

> **MUST — n'écrire QUE dans le dossier du layer actif.** Le layer actif est la **dernière entrée** de `layers` dans `Translations/_chain.json`. Les autres layers (dont la racine/standard) se lisent, **ne se modifient pas**.
>
> - ✅ Modifier une clé portée par un layer inférieur → écrire la clé **sur le layer actif** (override), fichier `Translations/<layerActif>/<entityFolder>/<lang>.json`.
> - ❌ Éditer un fichier d'un layer non actif, même « pour corriger juste une valeur ».

## Gate avant réponse

> **INTERDICTION de répondre tant que la checklist n'est pas intégralement cochée.**
>
> - [ ] **Catalogue disponible** : `search_translation_keys` répond. S'il refuse ou n'est pas exposé, **s'arrêter** — voir l'interdiction de repli à l'étape 1.
> - [ ] **Réutiliser-avant-créer** : avant toute création, chercher la clé avec `search_translation_keys`. L'unicité des clés est **company-wide et insensible à la casse** — une clé qui n'existe que dans un autre layer ou une autre entité existe déjà. Si une clé équivalente existe, la réutiliser au lieu d'en créer une.
> - [ ] **Layer actif** : aucun fichier écrit hors de `Translations/<layerActif>/` (dernière entrée de `_chain.json`).
> - [ ] **Clé valide** : clé trimmée non vide ; au moins une valeur de langue non vide.
> - [ ] **Toutes les langues `Enabled` remplies à la création** : une clé créée porte une valeur pour **chaque** langue `Enabled: true` de `_reference.json`. Les valeurs fournies par l'utilisateur sont autoritaires ; traduire toi-même les langues restantes.
> - [ ] **Entité existante uniquement** : le dossier cible est le `folder` d'une entrée `entities` de `_reference.json` — **jamais** un nouveau dossier d'entité (le push résout dossier → `LanguageEntity_ID` via le manifeste ; un dossier inconnu ne pousse pas). Choisir l'entité où vivent les clés similaires (celle du même écran/module).
> - [ ] **Nom de fichier** : `<lang>.json` = le `CodeLanguage` de la langue, minusculé/sanitizé — reprendre les noms de fichiers déjà présents dans l'arbre pour les langues existantes.
> - [ ] **Fichiers triés par clé** : chaque fichier modifié reste trié alphabétiquement par clé.
> - [ ] **Forme de valeur** : texte nu par défaut ; la forme objet `{text, mobileExcluded: true}` **uniquement** pour exclure du mobile — jamais `mobileExcluded: false` (absence = disponible).
> - [ ] **Validation** : pour chaque fichier produit ou modifié, `validate_divalto_file({ type: "translation", content })` passe.
> - [ ] **Pas de push manuel** : la sync serveur est faite par le push SCM du projet.
>
> Si une case ne peut pas être cochée → corriger **avant** de répondre.

## Procédure

### 1. Chercher la clé (réutiliser-avant-créer)

```
search_translation_keys({ query: "valider la commande" })   # nom de clé OU texte, insensible à la casse
get_translation_key({ key: "Order_Submit" })                # toutes les langues d'une clé candidate
```

Le tool lit le catalogue replié — même chaîne d'overloads, mêmes langues activées que l'éditeur. Un champ `total` dans la réponse signale un résultat tronqué : affiner la requête plutôt que relever `limit`.

> **Outil indisponible ⇒ arrêt.** Si `search_translation_keys` refuse, n'est pas démarré ou n'est pas exposé : relayer sa consigne et s'arrêter, sans chercher la clé ailleurs. Règle complète — et ses ❌/✅ — dans la section « Translation keys » du `CLAUDE.md` du projet.

- La clé existe avec le bon sens → **réutiliser** ce nom de clé, ne rien écrire (ou compléter une langue manquante, cf. étape 4).
- La clé existe avec un autre sens → choisir un **autre nom** ; ne jamais créer un doublon qui ne diffère que par la casse.
- La convention de nommage suit celle des clés **voisines** du projet cible (préfixes observés, casse) — ce skill n'impose pas de règle propre.

### 2. Résoudre le layer actif et l'entité

- Layer actif = dernière entrée de `layers` dans `Translations/_chain.json`.
- Entité = un `folder` **existant** de `_reference.json` (`entities[].folder`), choisi par proximité : là où vivent les clés du même écran/module (le champ `entity` rendu à l'étape 1 le montre).

### 3. Créer la clé (toutes les langues Enabled)

Pour chaque langue `Enabled: true` de `_reference.json` (`languages[].CodeLanguage`), ajouter la clé dans `Translations/<layerActif>/<entityFolder>/<lang>.json` (créer le fichier s'il n'existe pas encore sur le layer actif) :

```json
{
  "Order_Submit": "Valider la commande"
}
```

Valeurs utilisateur = autoritaires ; traduire les langues restantes. Exclusion mobile demandée → forme objet :

```json
{
  "Order_Submit": { "text": "Valider la commande", "mobileExcluded": true }
}
```

Maintenir le **tri alphabétique par clé** à l'insertion.

### 4. Compléter/modifier une valeur de langue existante

Écrire la clé avec sa nouvelle valeur dans le `<lang>.json` du **layer actif** (même chemin relatif que la clé d'origine). Ne toucher ni aux autres layers, ni aux autres clés du fichier.

### 5. Valider

Pour **chaque** fichier produit ou modifié :

```
validate_divalto_file({ type: "translation", content: "<json>" })
```

> Le schéma valide la forme (map clé → valeur, forme objet stricte) mais **pas** l'unicité ni le layer — ces deux invariants reposent sur les étapes 1 et 2. Corriger toute erreur avant de continuer.

## Pièges courants

- **Créer une variante de casse** (`order_submit` vs `Order_Submit`) : l'unicité serveur est insensible à la casse — la collision n'éclate qu'au push. La recherche de l'étape 1 est le filet : elle est déjà insensible à la casse.
- **Écrire `mobileExcluded: false`** : la forme objet n'accepte que `true` littéral ; « disponible mobile » = texte nu.
- **Créer un dossier d'entité** : un dossier absent de `_reference.json` ne se résout pas au push. Toujours une entité existante.
- **Ne remplir que la langue de l'utilisateur** : une clé créée sans toutes les langues `Enabled` laisse des trous visibles dans les autres locales.
