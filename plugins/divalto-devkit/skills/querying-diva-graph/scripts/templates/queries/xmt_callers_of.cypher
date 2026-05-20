// Appelants XMT d'une fonction/procedure (pattern transaction Divalto : xmt_call, g3_xmt_call, tnt_xmt_call, ...).
// Proprietes sur la relation XMT_CALL : line, context, xmt_function, target_sequence.
// Complementaire a callers_of (qui suit la relation CALLS statique) et dynamic_callers_of.
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
