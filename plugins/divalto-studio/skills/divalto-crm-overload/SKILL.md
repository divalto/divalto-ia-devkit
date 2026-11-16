---
name: divalto-crm-overload
description: "Surcharge un projet CRM Divalto Studio : ajoute un champ calculé à une fiche, l'affiche en formulaire et en liste, calcule sa valeur par scriptlibrary, dans le périmètre d'édition actif. Utiliser dès qu'une demande vise une donnée absente du standard sur une entité CRM, même formulée indirectement : « ajoute un champ X à la fiche Y », « stocke une info en plus sur le Contact », « calcule un score à partir de … », « personnalise la fiche X »."
argument-hint: "Décrivez la surcharge attendue (ex: ajoute un champ Score d'engagement 0-100 à la fiche Contact, affiche-le en formulaire et en liste, calcule-le sur les interactions des 90 derniers jours)."
allowed-tools: specialize_file, list_components, get_component_properties, validate_divalto_file, get_dictionary_entity, list_dictionary_entities, list_typescript_services, get_typescript_methods, Read, Write, Edit, Glob, Grep
---

# Surcharge CRM Divalto Studio par l'IA

Orchestre la production d'une **surcharge projet** complète à partir d'une demande en langage naturel sur un projet CRM ouvert dans Studio. Une surcharge typique touche deux artefacts qui doivent rester cohérents dans le même tour :

1. **Page** — `.page.json` / `.component.json` qui surcharge la page standard (formulaire + colonne de liste), en y exposant le champ.
2. **Scriptlibrary** — `.scriptlibrary.ts` qui calcule la valeur du champ.

Ce skill est un **coordinateur** : il pose la règle de surcharge et l'enchaînement, et délègue le détail de chaque artefact aux capacités existantes (skill [`divalto-page-ui`](../divalto-page-ui/SKILL.md) pour la page, outils MCP TS pour le scriptlibrary).

> **Prérequis** : le skill [`divalto-page-ui`](../divalto-page-ui/SKILL.md) doit être disponible (livré par le même plugin `divalto-studio`). S'il est absent, traiter la page directement avec les outils MCP `list_components` / `get_component_properties` / `validate_divalto_file` plutôt qu'échouer.

## Quand utiliser ce skill

- L'utilisateur demande, en langage naturel, d'**enrichir une entité CRM** existante du standard (champ + affichage + calcul).
- Une demande qui combine plusieurs artefacts (« ajoute … affiche … calcule … ») sur un projet ouvert.
- Toute formulation de **surcharge** d'un fichier standard (« surcharge la page X », « personnalise la fiche Y »).
- Une demande **abstraite ou indirecte** d'ajout/stockage d'une donnée absente du standard sur une entité (« spécifie une méthode pour ajouter des infos supplémentaires sur le Contact », « stocke une info en plus sur le client »).

Pour une page nouvelle sans surcharge → utiliser directement [`divalto-page-ui`](../divalto-page-ui/SKILL.md).

## La règle de surcharge (cœur du skill)

> **MUST — écrire dans le périmètre d'édition actif uniquement.** Un fichier hors du périmètre actif est en **lecture seule** ; ne pas l'écrire. Pour un intégrateur, le périmètre actif est `spe` → la surcharge va en spé. La surcharge n'est **pas** intrinsèquement « spé » : la duplication de surcharge existe aussi **en standard** (un écran de `Common/` peut être surchargé pour un `DeviceType` donné — la résolution prend en compte le DeviceType). C'est l'**autorisation du chemin cible** qui tranche (lecture seule ou non selon le périmètre actif + le droit `CanModifyStandard`), pas une règle « jamais le standard ».
>
> **MUST — surcharger = réécrire au chemin résolu correct, fichier intégral.** La surcharge partage le **même chemin relatif** que le fichier surchargé, au niveau de spécificité voulu (DeviceType, périmètre) ; on ne préfixe pas par un dossier `Spé`/`Std` en dur — la racine est résolue par le périmètre actif. Il n'existe **aucun mécanisme de patch partiel à ce jour** — le fichier est écrit **en entier** (reprendre le contenu surchargé complet, puis appliquer la modification).
>
> Voir [`references/overload-mechanics.md`](./references/overload-mechanics.md) pour la résolution de chemin et les pièges.

> **Gate avant réponse — INTERDICTION de répondre tant que la checklist n'est pas intégralement cochée.**
>
> - [ ] **Périmètre actif respecté** : aucun fichier écrit/modifié hors du périmètre d'édition actif (un chemin read-only pour ce périmètre n'est pas écrit).
> - [ ] **Chemin de surcharge** : chaque fichier surchargé est écrit au **même chemin relatif** que le fichier surchargé, au bon niveau de spécificité (DeviceType/périmètre), **réécrit en entier**.
> - [ ] **Cohérence des 2 artefacts** : le champ exposé dans la page (form + liste) est bien celui alimenté par le scriptlibrary — mêmes nom et type partout.
> - [ ] **Validation** : `validate_divalto_file` passe sur **chaque** fichier JSON produit (`component`, `page`, `datasource`…). Le `.scriptlibrary.ts` est validé via les services TS.
> - [ ] **Page déléguée** : la page a été construite/modifiée en respectant le gate du skill [`divalto-page-ui`](../divalto-page-ui/SKILL.md) (structure fiche, datasources complets, placement des `Events`, etc.).
>
> Si une case ne peut pas être cochée → corriger **avant** de répondre.

## Procédure

### 1. Analyser la demande

Identifier :

- **Entité CRM cible** : `contact`, `customer`, `orderheader`… (le nom métier dans la demande → entité du dictionnaire).
- **Les artefacts requis** : champ ? affichage (formulaire / colonne de liste) ? calcul ?
- **La source du calcul** : quelles données alimentent la valeur (ex. « interactions des 90 derniers jours » → table/entité d'interactions liée au contact).

### 2. Lire le standard (lecture seule)

Localiser et **lire** les fichiers standard concernés sans les modifier :

- Page(s) de la fiche / liste de l'entité : `Glob`/`Grep` sur `**/<entité>*.page.json`.
- Contrat de l'entité au dictionnaire : `get_dictionary_entity({ name: "<entité>" })` pour connaître ses champs, types et relations (ex. la relation Contact → interactions pour le calcul).

> Le contenu standard lu sert de **base intégrale** à la version projet : on part de lui, on applique la modification, on écrit le tout dans le projet.

### 3. Page projet (surcharge)

> **MUST — surcharger au même nom ET même extension que le standard** (cf. CLAUDE.md racine du contexte IA, section *File Naming & Uniqueness* — `.component.json`/`.page.json` partagent le même namespace, ne jamais renommer). Ex. `customerContact.id.component.json` → `customerContact.id.component.json`. Valider avec le type correspondant : `validate_divalto_file({ type: "component" })` pour un `.component.json`, `{ type: "page" }` pour un `.page.json`.

> **MUST — créer le fichier de surcharge via `specialize_file`, pas un `cp`.** Pour spécialiser un fichier standard vers le périmètre projet (`spe`), appeler `specialize_file({ path })` (chemin absolu du fichier standard). L'outil exécute la vraie commande déterministe de l'extension : il crée le fichier au bon chemin résolu **et** l'enregistre côté serveur. Ne **jamais** copier le fichier au shell (`cp`) — ça atterrit sur le disque mais ne synchronise pas. Ensuite, éditer le `spePath` retourné. Pour un `.scriptlibrary.ts`, l'outil génère un stub `extends Standard` — ne pas dupliquer le fichier standard.

Déléguer la construction au skill [`divalto-page-ui`](../divalto-page-ui/SKILL.md), en lui passant :

- la **base** = contenu intégral du fichier de fiche/liste standard lu à l'étape 2 ;
- la **modification** = exposer le nouveau champ en **formulaire** et en **colonne de liste**.

`divalto-page-ui` est **propriétaire** du choix des composants, du format des `Columns`, des datasources et de l'hygiène SQL (`FROM` → `.sql.sql` + `{{TABLE()}}`), du placement des `Events`, de la structure fiche — **ne pas redéfinir ces règles ici**, déléguer et laisser ses gates s'appliquer.

Écrire le résultat au **même chemin relatif et même extension** que le fichier standard, dans le projet, **réécrit en entier**.

> **Attention réécriture intégrale** : une fiche standard peut faire >1000 lignes (Conditions de capacité, `ScriptedFields`, Events). La réécriture intégrale doit **préserver tout l'existant** verbatim et n'ajouter que le champ — repartir du contenu lu à l'étape 2, ne rien omettre. Vérifier après coup que le fichier produit contient toujours l'intégralité des composants standard.

### 4. Scriptlibrary projet (calcul)

1. `list_typescript_services()` puis `get_typescript_methods(...)` pour découvrir les services `$xxx` disponibles (datasource, serverscript…) — **ne pas inventer** de service.
2. Créer le `.scriptlibrary.ts` de surcharge via `specialize_file({ path })` (même base + même infixe que le fichier de fiche : `<fiche>.component.scriptlibrary.ts` pour un `.component.json`), puis l'éditer. `export default class` + handler bindé sur un event **au niveau racine** (`AfterChildrenLoad`) qui calcule la valeur du champ. Voir [`references/overload-mechanics.md`](./references/overload-mechanics.md#scriptlibrary) pour les deux squelettes.

   > **MUST — surcharger un scriptlibrary standard = `extends Standard`, jamais dupliquer.** Si un `.scriptlibrary.ts` **existe en standard**, la spé doit en **hériter** : `import Standard from 'Standard/<DeviceType>/<nomFichier>'; export default class <NomClasse> extends Standard {}`, puis ajouter/redéfinir **seulement** les méthodes voulues (appeler `super` pour étendre un handler existant). Ne **jamais** recopier le corps du scriptlibrary standard — c'est exactement le stub que `specialize_file` génère. La règle de réécriture intégrale ne vaut **pas** ici : le code standard hérité reste actif.
   >
   > **Sinon (pas de scriptlibrary standard à hériter)** : écrire un code-behind neuf (`export default class` sans `extends`). Si le standard utilise des scripts séparés `.script.ts` (style ancien, sans `AfterChildrenLoad`), suivre ce style. Ne jamais écraser le code standard.
3. Valider via les services TS (pas d'API `$` hors de la liste de l'étape 1).

### 5. Valider chaque fichier généré

`validate_divalto_file` sur **chaque** JSON produit (`component`, `page`, `datasource`). Corriger avant de continuer.

### 6. Self-check (gate avant réponse)

Re-cocher chaque case du gate en tête de procédure. Tant qu'une case ne peut pas être cochée → retourner à l'étape concernée, corriger, revalider. **Ne pas répondre tant que tout n'est pas coché.**

### 7. Résumé final

Produire :

1. Les fichiers générés (chemins **relatifs au projet** — confirmer qu'aucun ne touche le standard).
2. Le champ exposé (nom, type).
3. La page surchargée (base reprise + modification appliquée).
4. Le scriptlibrary (event bindé + service appelé).
5. Les corrections appliquées en validation.
6. Rappeler que **F5** affiche le résultat sur le projet.

## Exemple de référence

Scénario de gating de la feature — « Score d'engagement sur Contact » : voir [`references/examples/score-engagement-contact.md`](./references/examples/score-engagement-contact.md) (les deux artefacts de bout en bout, sur des formes réelles).

## Outils MCP

| Outil | Usage |
| --- | --- |
| `specialize_file({ path })` | Spécialise un fichier standard vers le périmètre projet (`spe`) (commande déterministe de l'extension, sync serveur). À utiliser au lieu d'un `cp`. Refuse en périmètre standard (`std`) : y éditer le standard. |
| `get_dictionary_entity({ name })` | Contrat d'une entité (champs, types, relations) — pour lire la base et la source du calcul. |
| `list_dictionary_entities()` | Découvrir le nom exact d'une entité. |
| `list_components()` / `get_component_properties({ component })` | Source de vérité des composants de page (délégué à `divalto-page-ui`). |
| `list_typescript_services()` / `get_typescript_methods(...)` | Services `$xxx` du scriptlibrary — source de vérité, ne rien inventer. |
| `validate_divalto_file({ type, content })` | Valider chaque JSON avant écriture. `type` ∈ {`component`, `page`, `datasource`, …}. Utiliser `component` pour un `.component.json`, `page` pour un `.page.json`. |
