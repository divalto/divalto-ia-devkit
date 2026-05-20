// Liste les programs d'un module ERP identifie par son prefixe ($module_prefix = GT_, RT_, CC_...).
// La relation BELONGS_TO_MODULE est dirigee Program -> ERPModule.
// PIEGE : le graphe stocke m.prefix en lowercase sans underscore (ex: 'gt' et non 'GT_').
//         Le normaliser cote requete pour accepter les deux formes de saisie.
MATCH (p:Program)-[:BELONGS_TO_MODULE]->(m:ERPModule)
WHERE toLower(m.prefix) = toLower(replace('$module_prefix', '_', ''))
   OR toLower(m.name) CONTAINS toLower('$module_prefix')
RETURN p.name AS name, m.name AS domain, p.path AS path_x12
ORDER BY p.name
LIMIT 25;
