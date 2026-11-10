---
name: divalto-mobile-fluid-layout
description: "Convertit la disposition absolue d'un onglet mobile Divalto Weavy en disposition fluide responsive (breakpoints xs/sm/md/lg), ou modifie un placement responsive existant. Utiliser pour : migrer un onglet vers le fluide, rendre un écran mobile responsive, générer le placement col/offset/newRow par palier depuis les positions absolues, regrouper des contrôles dans une Card, lui donner un titre ou placer un lien/bouton dans son en-tête."
argument-hint: "Indiquez l'onglet mobile à convertir en fluide (ex: la fiche client de la fonction customer)."
allowed-tools: Read, Write, Edit, Glob, Grep
capabilities: [mobile, mobile-v7]
---

# Conversion d'un onglet mobile en disposition fluide

## Quand utiliser ce skill

- Convertir un onglet mobile en positionnement absolu vers le fluide (responsive)
- Rendre un écran mobile existant adaptatif à plusieurs largeurs d'appareil
- Adapter ou corriger un placement `responsive` déjà présent sur un onglet
- Générer le placement `col`/`offset`/`newRow` par palier (`xs`/`sm`/`md`/`lg`) à partir des positions absolues des contrôles
- Regrouper des contrôles d'un onglet fluide dans une ou plusieurs `Card`
- Donner un titre à une `Card` ou placer un contrôle (lien, bouton) dans son en-tête, à droite du titre : voir [references/cards.md](./references/cards.md)

## Le workflow (5 étapes)

1. **Localiser l'onglet et ses contrôles** — lire `_tab.json` (`width`, `height`, `screenMode`) et chaque `controls/*.json` de l'onglet ciblé.
2. **Comprendre l'écran** — reconstruire la disposition source (colonnes, lignes) depuis la géométrie `position` de chaque contrôle. Voir [references/breakpoint-heuristics.md](./references/breakpoint-heuristics.md).
3. **Décider le placement par palier** — reflow ancré depuis le palier de conception vers les autres paliers. Voir [references/breakpoint-heuristics.md](./references/breakpoint-heuristics.md).
4. **Écrire `proposal.responsive`** (+ `modelVersion: 2`) pour chaque contrôle concerné, et passer `screenMode` à `"fluid"` dans `_tab.json`.
5. **Auto-valider** : appeler l'outil MCP `validate_responsive_layout` avec le code de l'onglet, puis corriger **toutes** les issues remontées (`error` et `warning`) avant de terminer. L'outil relit les fichiers on-disk : il valide l'état réellement écrit, pas ce que tu crois avoir écrit. Voir [references/fluid-contract.md](./references/fluid-contract.md) pour les règles.

## MUST NOT

- ❌ Écrire le XML `<Responsive>` à la main → ✅ écrire le JSON `proposal.responsive` (l'extension le sérialise en XML à la synchro).
- ❌ Modifier `position`, `position.left`, `position.top`, `position.width`, `position.height` → ✅ ne toucher que `proposal.responsive` (le positionnement absolu reste le repli).
- ❌ Écrire un placement où `offset + col > 12`, ou toute autre violation des règles du contrat → ✅ respecter les règles de [references/fluid-contract.md](./references/fluid-contract.md).
- ❌ Répéter des champs inchangés à chaque palier → ✅ cascade mobile-first (poser la base à `xs`, ne redéfinir dans `sm`/`md`/`lg` que ce qui change réellement).

## Références

- Arbre de fichiers mobile, format des contrôles et `screenMode` : voir [divalto-mobile-screen-creation](../divalto-mobile-screen-creation/SKILL.md) (non redocumenté ici).
- Contrat du layout fluide et règles de validation : [references/fluid-contract.md](./references/fluid-contract.md)
- Conteneur `Card` (regrouper des contrôles, titre `common.title`, enfant d'en-tête `parentSlot: "header"`) : [references/cards.md](./references/cards.md)
- Raisonnement multi-breakpoints (reflow ancré) : [references/breakpoint-heuristics.md](./references/breakpoint-heuristics.md)
- Exemple travaillé : [references/examples/INDEX.md](./references/examples/INDEX.md)
