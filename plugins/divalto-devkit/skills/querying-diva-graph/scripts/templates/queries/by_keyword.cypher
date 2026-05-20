// Fuzzy search sur noms de Program, Function, Procedure, DObj contenant $keyword.
// Retourne jusqu'a 25 programs (les sous-symboles qui matchent remontent vers leur Program englobant).
// PIEGE : les mots metier francais (ex: "contremarque") matchent souvent uniquement des
//         Function/Procedure/DObj, pas les Program qui utilisent des abreviations (ex: gtppctm310).
//         Cf. le mapping concept francais -> abreviation DIVA (cote orchestrateur).
MATCH (n)
WHERE (n:Program OR n:Function OR n:Procedure OR n:DObj)
  AND toLower(n.name) CONTAINS toLower('$keyword')
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(n)
WITH DISTINCT
  CASE WHEN 'Program' IN labels(n) THEN n ELSE prog END AS program_node
WHERE program_node IS NOT NULL
OPTIONAL MATCH (program_node)-[:BELONGS_TO_MODULE]->(m:ERPModule)
RETURN
  program_node.name AS name,
  coalesce(m.name, 'unknown') AS domain,
  program_node.path AS path_x12
ORDER BY name
LIMIT 25;
