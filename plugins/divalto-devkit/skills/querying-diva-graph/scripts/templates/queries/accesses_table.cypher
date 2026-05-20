// Programs qui accedent a la table SQL $table_name via leur RecordSql / DObj.
// Chemin : Program --CONTAINS--> (DObj | RecordSQL) --ACCESSES_TABLE--> DbTable.
MATCH (p:Program)-[:CONTAINS]->(o)-[:ACCESSES_TABLE]->(t:DbTable)
WHERE t.table_name = '$table_name' OR toUpper(t.table_name) = toUpper('$table_name')
OPTIONAL MATCH (p)-[:BELONGS_TO_MODULE]->(m:ERPModule)
RETURN DISTINCT p.name AS name, m.name AS domain, p.path AS path_x12
ORDER BY name
LIMIT 25;
