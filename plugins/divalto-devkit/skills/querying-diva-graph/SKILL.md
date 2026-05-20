---
name: querying-diva-graph
description: >
  Interroge le graphe Neo4j diva-mcp (snapshot X.12 advisory) pour explorer le standard
  ERP Divalto. Produit une liste priorisee de candidats (programs, fonctions, tables,
  entites, relations) a partir d'un request.json issu du parser de demande. Toutes les
  sorties portent le disclaimer "snapshot X.12" et sont destinees a etre verifiees
  dans les sources X.13 par le skill searching-erp-sources. A utiliser a partir d'un
  `request.json` pour obtenir une liste priorisee de candidats avant verification dans
  les sources. Gere la degradation gracieuse si diva-mcp est indisponible (rapport avec
  candidates vides et `neo4j_status: unavailable`).
---

# Querying DIVA Graph

## Contenu

- Utilisation rapide
- Mode generate : produire les requetes Cypher
- Mode consolidate : fusionner les resultats bruts
- Templates Cypher
- Disclaimers X.12 obligatoires
- Degradation gracieuse (MCP indispo)
- Scripts disponibles
- References

---

## Utilisation rapide

Le workflow complet se fait en **deux appels** orchestres par le LLM :

### Etape 1 -- generer les requetes

```
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode generate --request request.json
```

Sortie : liste de requetes Cypher parametrees (stdout JSON). L'orchestrateur LLM les execute via `mcp__diva-mcp__read_neo4j_cypher`.

### Etape 2 -- consolider les resultats

```
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode consolidate --request request.json --results raw_results.json
```

Sortie : `candidates_x12.json` avec programs, fonctions, tables, entites priorisees et disclaimers.

---

## Mode generate : produire les requetes Cypher

Le script lit `request.json`, selectionne les templates pertinents selon les keywords detectes, et genere les requetes Cypher prêtes a executer.

Les templates sont dans `scripts/templates/queries/` :

| Template | Declencheur (dans request.json) | Variable Cypher |
|----------|--------------------------------|-----------------|
| `by_keyword.cypher` | `keywords_techniques` non vide | `$keyword` (un appel par keyword) |
| `by_module.cypher` | `domaine_pressenti` non null | `$module_prefix` |
| `accesses_table.cypher` | `donnees` contient nom MAJUSCULE | `$table_name` |
| `callers_of.cypher` | `keywords_techniques` contient nom PascalCase | `$function_name` |
| `dynamic_callers_of.cypher` | idem `callers_of` -- appelants via `DYNAMIC_CALL` | `$function_name` |
| `xmt_callers_of.cypher` | idem `callers_of` -- appelants via `XMT_CALL` (transactions) | `$function_name` |
| `similar_entity.cypher` | `donnees` contient 1+ element | `$entity_pattern` |

Chaque requete est parametree avec `LIMIT 25` (voir `reference/x12-advisory-rules.md`).

## Mode consolidate : fusionner les resultats bruts

Le script attend en `--results` un JSON de la forme :

```json
{
  "by_keyword:famille": [ { /* rows Neo4j */ } ],
  "by_module:RT_": [ { /* rows */ } ],
  ...
}
```

(Les cles sont `<template_name>:<parameter_value>`, l'orchestrateur LLM genere ces cles apres execution MCP.)

La consolidation :
- Deduplique par `program.name` / `function.name` / `table.name`
- Additionne les scores (plus une entite apparait dans plusieurs requetes, plus elle est pertinente)
- Ajoute `disclaimers` systematiques
- Retourne `candidates_x12.json` (format decrit dans [reference/x12-advisory-rules.md](reference/x12-advisory-rules.md))

---

## Templates Cypher

Les 7 templates couvrent les cas d'usage principaux :

| Fichier | Cas d'usage |
|---------|-------------|
| `by_keyword.cypher` | Fuzzy search sur Program dont le nom contient un mot-cle |
| `by_module.cypher` | Lister les programs d'un module ERP (via BELONGS_TO_MODULE) |
| `accesses_table.cypher` | Programs qui accedent a une table SQL (via CONTAINS -> ACCESSES_TABLE) |
| `callers_of.cypher` | Appelants statiques d'une fonction/procedure (via CALLS) |
| `dynamic_callers_of.cypher` | Appelants dynamiques (via DYNAMIC_CALL) -- invocations non resolues statiquement |
| `xmt_callers_of.cypher` | Appelants via pattern transaction XMT (via XMT_CALL) |
| `similar_entity.cypher` | Entite metier attachee a une DbTable (via propriete DbTable.entity) |

Voir `reference/cypher-recipes.md` pour les details et les limites.

---

## Disclaimers X.12 obligatoires

Tout candidat retourne par ce skill porte les champs :

- `source: "diva-mcp-x12"`
- `status: "X.12"` (a passer en CONFIRME/DISPARU/NOUVEAU par la phase 3)

Le JSON de sortie contient toujours une section `disclaimers` :

```json
{
  "disclaimers": [
    "Snapshot X.12 du standard ERP -- ne reflete pas X.13",
    "Toute recommandation d'action doit etre verifiee par searching-erp-sources"
  ]
}
```

Voir `reference/x12-advisory-rules.md` pour les regles d'usage strict.

---

## Degradation gracieuse (MCP indispo)

Si l'orchestrateur LLM ne peut pas executer les requetes (MCP deconnecte, timeout, erreur), il invoque :

```
py .claude/skills/querying-diva-graph/scripts/query_neo4j.py \
    --mode consolidate --request request.json --results "{}" \
    --neo4j-status unavailable
```

Le script retourne un `candidates_x12.json` vide avec :
- `neo4j_status: "unavailable"`
- `disclaimers` incluant "Neo4j inaccessible : la phase de verification X.13 devient source principale"
- Tous les tableaux de candidats vides

L'orchestrateur continue avec `searching-erp-sources` en mode "recherche X.13 directe" (sans orientation Neo4j).

---

## Scripts disponibles

```
scripts/query_neo4j.py                       # Mode generate + mode consolidate
scripts/templates/queries/
  by_keyword.cypher
  by_module.cypher
  accesses_table.cypher
  callers_of.cypher
  similar_entity.cypher
```

Les `.cypher` sont des templates texte avec `$variable`. Le script les formate en Cypher executable pret pour le MCP.

---

## References

- `reference/cypher-recipes.md` -- recettes detaillees par cas d'usage (copier-coller vers le MCP)
- `reference/x12-advisory-rules.md` -- regles d'usage advisory-only et format des disclaimers
