// Appelants DYNAMIQUES d'une fonction/procedure (invocations non resolues statiquement).
// Proprietes sur la relation DYNAMIC_CALL : line, context, call_type (function_call | procedure_call).
// Complementaire a callers_of (qui suit la relation CALLS statique).
MATCH (callee)
WHERE (callee:Function OR callee:Procedure)
  AND callee.name = '$function_name'
MATCH (caller)-[r:DYNAMIC_CALL]->(callee)
  WHERE (caller:Function OR caller:Procedure)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(caller)
RETURN caller.name AS caller_name, prog.name AS program_name,
       labels(caller)[0] AS caller_kind, r.call_type AS call_type
ORDER BY caller_name LIMIT 25;
