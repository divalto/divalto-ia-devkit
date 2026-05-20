# x12-advisory-rules.md

Regles strictes d'usage des resultats Neo4j `diva-mcp`. Ces regles sont **obligatoires** -- leur violation constitue une regression metier critique.

## Le probleme : X.12 n'est pas X.13

Le graphe est un snapshot de la version X.12 de l'ERP Divalto. La version en production est X.13. Consequences (extrait de `docs/MCP-DIVA-GRAPH.md`) :

- Une fonction presente dans X.12 peut avoir ete supprimee/renommee en X.13
- Une table presente en X.12 peut avoir des champs differents en X.13
- Un pattern detecte a 90 % en X.12 peut etre a 0 % en X.13 (reecriture)
- Des fonctions/tables X.13 ne figurent pas dans le graphe

## Regle 1 -- Marquage systematique

Toute valeur extraite de Neo4j porte obligatoirement :

```json
{
  "source": "diva-mcp-x12",
  "status": "X.12"
}
```

Le status evolue en phase 3 (verification X.13) vers l'un de :
- `CONFIRME X.13` -- present en X.13, signature inchangee
- `DISPARU X.13` -- absent en X.13 (refactor, renommage)
- `NOUVEAU X.13` -- trouve en X.13 hors du graphe

## Regle 2 -- Disclaimers dans le rapport

Le JSON `candidates_x12.json` contient toujours :

```json
{
  "disclaimers": [
    "Snapshot X.12 du standard ERP -- ne reflete pas X.13",
    "Toute recommandation d'action doit etre verifiee par searching-erp-sources"
  ]
}
```

Si MCP indisponible, ajouter :

```
"Neo4j inaccessible : la phase de verification X.13 devient source principale."
```

## Regle 3 -- Jamais de garde-fou bloquant

Aucun script ou workflow ne doit **refuser** une modification X.13 sur la base d'une donnee X.12. Exemples interdits :

- "La fonction X n'existe pas dans le graphe, donc on refuse de creer un appel a X"
- "La table Y n'a pas le champ Z dans le graphe, donc on refuse d'ajouter une reference a Z"

Toute contradiction apparente est a trancher par la phase 3 sur X.13 ou par le developpeur.

## Regle 4 -- Bornes de requete

Toute requete Cypher executee par `querying-diva-graph` ou par l'orchestrateur LLM doit inclure :

- `LIMIT N` avec `N <= 25` (`N <= 15` pour les entites couteuses)
- Pas de `COLLECT` sans borne (`[..10]`, `[..25]`)
- Timeout cote MCP : si une requete traine > 30 s, l'orchestrateur annule et continue sans ce resultat

## Regle 5 -- Read-only

Ce skill utilise **exclusivement** `mcp__diva-mcp__read_neo4j_cypher`. L'outil d'ecriture `write_neo4j_cypher` est **interdit** -- modifier le graphe depuis un skill de lecture introduirait une inconsistance. Aucune exception.

## Regle 6 -- Degradation gracieuse obligatoire

Si le MCP est inaccessible (deconnexion, erreur, timeout global), le skill **ne plante pas**. Il retourne un `candidates_x12.json` vide avec `neo4j_status: "unavailable"` et permet a la phase 3 de prendre le relais en mode "recherche X.13 directe".

Test recommande : scenario `neo4j-indispo` dans `evals.json`.

## Regle 7 -- Pas de cache local

Les resultats Neo4j ne sont pas caches entre les appels. Chaque demande relance le pipeline complet. Raison : le graphe peut etre rafraichi entre deux sessions, et un cache local entrainerait un decalage supplementaire X.12/X.13/cache.

## Regle 8 -- Distribution : diva-mcp est une dependance optionnelle

Ce skill **est distribue** dans le zip des skills DIVA, mais sa dependance au MCP `diva-mcp` est **optionnelle** :

- Le skill lui-meme ne contient aucun secret
- Le token du MCP reside uniquement dans `.mcp.json` (non distribue)
- Chez un collaborateur qui n'a pas configure `diva-mcp`, les invocations MCP echouent et le skill bascule automatiquement en `neo4j_status: unavailable` (mode direct)

**Consequence cote orchestrateur `analyzing-diva-request`** : il gere la degradation gracieuse automatiquement. Le rapport final porte la mention "Couverture Neo4j : absente" et `searching-erp-sources` utilise uniquement les keywords techniques pour chercher dans l'ERP X.13 local.

**Installation cote collaborateur** : si le collaborateur souhaite activer la recherche Neo4j, il doit configurer `.mcp.json` avec une URL `diva-mcp`. Sans cette configuration, le skill fonctionne quand meme en mode degrade.

## References

- `docs/MCP-DIVA-GRAPH.md` -- source canonique des regles d'usage, avertissement X.12, limitations APOC
- `docs/RECHERCHE-ERP.md` -- workflow hybride, format des disclaimers dans le rapport
