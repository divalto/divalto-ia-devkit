# cypher-recipes.md

Recettes Cypher exploitees par `querying-diva-graph`. Alignees sur `docs/MCP-DIVA-GRAPH.md` (schema, labels, relations, limites APOC).

## Conventions

- Toutes les requetes incluent `LIMIT` (15 a 25) -- aucune requete ouverte
- Pour les noms de fonction/procedure : toujours unir `Function OR Procedure OR DObj` (cf. MCP-DIVA-GRAPH.md section "Piege")
- Les proprietes attendues : `p.name`, `p.path`, `m.name`, `m.prefix`, `t.table_name`, `t.entity`, `f.field_name`
- Les resultats sont **advisory X.12** -- marquage systematique dans le JSON consolide

## 7 templates

### by_keyword -- fuzzy search sur noms

```cypher
MATCH (p:Program)
WHERE toLower(p.name) CONTAINS toLower('$keyword')
OPTIONAL MATCH (p)-[:BELONGS_TO_MODULE]->(m:ERPModule)
RETURN p.name AS name, m.name AS domain, p.path AS path_x12
ORDER BY name LIMIT 25;
```

Usage : decouvrir des programs similaires ("famille", "reglement", "rtl").

### by_module -- programs d'un module

```cypher
MATCH (p:Program)-[:BELONGS_TO_MODULE]->(m:ERPModule)
WHERE m.prefix = '$module_prefix' OR toLower(m.name) CONTAINS toLower('$module_prefix')
RETURN p.name AS name, m.name AS domain, p.path AS path_x12
ORDER BY p.name LIMIT 25;
```

Usage : lister les programs d'un domaine ERP (RT_, GT_, CC_...).

### accesses_table -- qui touche une table

```cypher
MATCH (p:Program)-[:CONTAINS]->(o)-[:ACCESSES_TABLE]->(t:DbTable)
WHERE t.table_name = '$table_name' OR toUpper(t.table_name) = toUpper('$table_name')
OPTIONAL MATCH (p)-[:BELONGS_TO_MODULE]->(m:ERPModule)
RETURN DISTINCT p.name AS name, m.name AS domain, p.path AS path_x12
ORDER BY name LIMIT 25;
```

Usage : impact analysis sur une table (qui accede a CLI, RTFTAB, etc.).

### callers_of -- remonter les appelants

```cypher
MATCH (callee)
WHERE (callee:Function OR callee:Procedure OR callee:DObj)
  AND callee.name = '$function_name'
MATCH (caller)-[:CALLS]->(callee)
  WHERE (caller:Function OR caller:Procedure OR caller:DObj)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(caller)
RETURN caller.name AS caller_name, prog.name AS program_name, labels(caller)[0] AS caller_kind
ORDER BY caller_name LIMIT 25;
```

Usage : impact analysis sur une fonction (Check_*, Get_*, Construire_*).

### dynamic_callers_of -- appelants dynamiques

```cypher
MATCH (callee)
WHERE (callee:Function OR callee:Procedure)
  AND callee.name = '$function_name'
MATCH (caller)-[r:DYNAMIC_CALL]->(callee)
  WHERE (caller:Function OR caller:Procedure)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(caller)
RETURN caller.name AS caller_name, prog.name AS program_name,
       labels(caller)[0] AS caller_kind, r.call_type AS call_type
ORDER BY caller_name LIMIT 25;
```

Usage : completer `callers_of` (statique) par les invocations dynamiques -- utile pour impact analysis exhaustif. Volumes ordre de grandeur : ~3 200 DYNAMIC_CALL vs ~355 000 CALLS (1 %) -- la plupart des fonctions n'ont aucun appelant dynamique.

### xmt_callers_of -- appelants XMT (transactions)

```cypher
MATCH (callee)
WHERE (callee:Function OR callee:Procedure)
  AND callee.name = '$function_name'
MATCH (caller)-[r:XMT_CALL]->(callee)
  WHERE (caller:Function OR caller:Procedure)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(caller)
RETURN caller.name AS caller_name, prog.name AS program_name,
       labels(caller)[0] AS caller_kind,
       r.xmt_function AS xmt_function, r.target_sequence AS target_sequence
ORDER BY caller_name LIMIT 25;
```

Usage : identifier les invocations via le pattern transaction Divalto (`xmt_call`, `g3_xmt_call`, `tnt_xmt_call`, `ga_xmt_call`, `xmt_call_sql`, ...). Volumes ordre de grandeur : ~1 400 XMT_CALL. Complete `callers_of` et `dynamic_callers_of` pour une couverture d'impact analysis complete.

### similar_entity -- entites metier similaires

```cypher
MATCH (t:DbTable)
WHERE t.table_name = '$entity_pattern'
   OR toUpper(t.table_name) = toUpper('$entity_pattern')
   OR toLower(t.entity) CONTAINS toLower('$entity_pattern')
OPTIONAL MATCH (t)-[:HAS_FIELD]->(f:DbField)
WITH t, collect(DISTINCT f.field_name)[..10] AS fields
RETURN t.entity AS entity_name, t.table_name AS table_name, fields
LIMIT 15;
```

Usage : trouver des patterns d'entite metier comparables (Client, Article, FamRglt). L'entite metier est portee par la propriete `DbTable.entity` (chaine).

## Limitations connues

| Limitation | Impact | Reference |
|-----------|--------|-----------|
| Snapshot X.12, pas X.13 | Faux positifs/negatifs sur toute modification post-X.12 | MCP-DIVA-GRAPH.md section "Avertissement" |
| `RecordField` label vide | Pas de query champs d'un RecordSql | MCP-DIVA-GRAPH.md section "Decouvertes -- Limitation 4" |
| `scope_type=procedure` non source-faithful | Compter les populations source = filesystem X.13 | MCP-DIVA-GRAPH.md section "Decouvertes -- Piege 5" |
| APOC `apoc.meta.schema` sandboxed | Pas d'introspection via APOC ; utiliser `db.labels()`/`db.relationshipTypes()` | MCP-DIVA-GRAPH.md section "APOC disponible" |
| Pas de relation `OverWrittenBy` explicite | Detection des surcharges = grep X.13 (searching-erp-sources) | -- |

## Ajouter une nouvelle recette

Procedure :
1. Ecrire le `.cypher` avec des `$variable` et `LIMIT` defini
2. L'ajouter dans `scripts/query_neo4j.py` section "generate_queries" avec son declencheur
3. Ajouter un scenario dans `evals.json`
4. Documenter ici avec usage + reference X.12

Limites : `LIMIT 25` max pour les listes, `LIMIT 15` pour les entites (plus coûteuses). Jamais de requete ouverte.
