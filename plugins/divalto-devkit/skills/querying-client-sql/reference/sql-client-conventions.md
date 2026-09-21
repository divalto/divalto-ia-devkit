# Conventions d'ecriture SQL cote base client Divalto

Detail des 4 conventions d'or et de la recette de decouverte. Toutes les regles
ci-dessous ont ete verifiees sur une base ERP Divalto reelle (X.13). Elles restent
des **conventions dominantes**, pas des lois : en cas de doute, **decouvrir** via
`INFORMATION_SCHEMA` plutot qu'affirmer.

## 1. MAJUSCULES = nom du dictionnaire (pas le NomOdbc)

Le nom SQL physique d'une table (et de ses colonnes) est le **nom du DICTIONNAIRE**,
ecrit en **MAJUSCULES**. Ce n'est **pas** :

- le `NomOdbc` local (le poste peut afficher un alias different) ;
- le libelle fonctionnel affiche a l'ecran ;
- une casse « jolie » (PascalCase / minuscules).

Exemple generique : une entite metier « Article » se requete `SELECT ... FROM ARTICLE`,
pas `FROM Article` ni `FROM article`. Le libelle ecran (« Article ») ou un `NomOdbc`
local n'est **pas** le nom SQL.

> Ne jamais deduire le nom SQL du libelle ni du NomOdbc. Si le nom exact n'est pas
> connu avec certitude -> decouverte (section 5).

## 2. Collation binaire = sensible a la casse ET aux accents

La base est generalement en collation **binaire** (observe : `Latin1_General_BIN`).
Consequence : **sensible a la casse et aux accents**. Un seul caractere de casse ou
un accent qui differe fait echouer la comparaison ou renvoyer 0 ligne.

```sql
-- Echoue / 0 ligne (casse) :
SELECT * FROM article;                 -- table introuvable
SELECT * FROM ARTICLE WHERE lib LIKE '%mvt%';   -- colonne 'lib' introuvable, ou 0 ligne
-- Passe :
SELECT * FROM ARTICLE WHERE LIB LIKE '%MVT%';
```

Nuance verifiee : le **serveur** peut etre en collation insensible (ex. `French_CI_AS`)
alors que la **base**, elle, est binaire. C'est la collation de **la base** qui
s'applique aux identifiants et aux comparaisons -> ne jamais se fier a la collation
serveur.

## 3. Schema `dbo`

Le metier Divalto vit sous le schema **`dbo`**. Quelques tables techniques/systeme
peuvent vivre sous un autre schema (ex. un schema d'outillage), mais pour le metier :
`dbo`.

## 4. La regle MAJUSCULES n'est pas absolue

Sur une base reelle, la quasi-totalite des tables et colonnes metier sont en
MAJUSCULES, mais **quelques exceptions** existent : objets **techniques / systeme**
(diagrammes, tables de framework) ou certaines **vues**. La regle vaut pour le
**metier sous `dbo`**. Devant un nom qui ne « rentre » pas -> decouvrir, ne pas forcer
la casse a l'aveugle.

## 5. Recette de decouverte (`INFORMATION_SCHEMA`)

`INFORMATION_SCHEMA` permet de retrouver le **nom et la casse reels** avant d'ecrire la
requete metier. Les vues `INFORMATION_SCHEMA` se requetent sans se soucier de la casse
de la table cible (on filtre sur `TABLE_NAME`, insensible a la recherche).

```sql
-- Le nom/casse reels d'une table (recherche large, insensible)
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME LIKE '%<fragment_maj>%';

-- Les colonnes reelles (nom, type, casse) d'une table
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = '<TABLE_MAJ>'
ORDER BY ORDINAL_POSITION;

-- Verifier la collation reelle de la base (diagnostic casse)
SELECT DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS collation_base;
```

Regle : **decouvrir d'abord, requeter ensuite**. Un `0 ligne` ou un « Nom d'objet non
valide » est, dans l'immense majorite des cas, un piege de casse/nom -> passer par
`INFORMATION_SCHEMA` avant de conclure a une absence de donnee.

## 6. Portee d'une table de parametrage (renvoi)

Le piege « 0 ligne pour ce dossier » sur une table de parametrage `Tnnn` releve d'un
autre mecanisme (commune vs par-dossier via `T000` / `TABTYP`) -> voir le SKILL.md
(helper `check_table_scope`) et `understanding-integrator-workspace/sql-resolution.md`.
