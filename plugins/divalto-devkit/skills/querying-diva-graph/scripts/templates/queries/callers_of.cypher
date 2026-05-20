// Appelants d'une fonction ou procedure $function_name via la relation CALLS.
// Union Function/Procedure/DObj pour ne pas rater d'appels.
MATCH (callee)
WHERE (callee:Function OR callee:Procedure OR callee:DObj)
  AND callee.name = '$function_name'
MATCH (caller)-[:CALLS]->(callee)
  WHERE (caller:Function OR caller:Procedure OR caller:DObj)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(caller)
RETURN caller.name AS caller_name, prog.name AS program_name, labels(caller)[0] AS caller_kind
ORDER BY caller_name
LIMIT 25;
