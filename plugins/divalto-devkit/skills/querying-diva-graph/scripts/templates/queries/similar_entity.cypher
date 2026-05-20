// Entite metier attachee a une DbTable : propriete DbTable.entity (chaine).
// Recherche par nom de table ou par nom d'entite.
MATCH (t:DbTable)
WHERE t.table_name = '$entity_pattern'
   OR toUpper(t.table_name) = toUpper('$entity_pattern')
   OR toLower(t.entity) CONTAINS toLower('$entity_pattern')
OPTIONAL MATCH (t)-[:HAS_FIELD]->(f:DbField)
WITH t, collect(DISTINCT f.field_name)[..10] AS fields
RETURN t.entity AS entity_name, t.table_name AS table_name, fields
LIMIT 15;
