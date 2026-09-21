---
name: querying-client-sql
description: A utiliser des que Claude doit ecrire, debugger ou faire executer une requete SQL sur la base d'un CLIENT Divalto (interroger une table, comprendre un resultat vide, verifier un schema) | Donne les conventions d'ecriture SQL cote client -- tables et colonnes en MAJUSCULES (= nom du dictionnaire, distinct du NomOdbc local), collation binaire sensible a la casse et aux accents, schema dbo, decouverte des noms/casse reels via INFORMATION_SCHEMA -- plus un helper deterministe check_table_scope (lit T000/TABTYP) pour savoir si une table de parametrage est commune a tous les dossiers (dossier 999) ou propre a un dossier. La resolution de la connexion reste du ressort de understanding-integrator-workspace.
---

# querying-client-sql -- interroger la base SQL d'un client Divalto

Ecrire, debugger ou faire executer une requete SQL contre la base de donnees d'un client Divalto **sans se tromper de nom, de casse ou de portee**.

## Quand l'utiliser

- Ecrire une requete SQL sur une table du client (lecture, controle, diagnostic).
- Comprendre un resultat **vide** ou un « Nom d'objet non valide » -- souvent un piege de **casse** ou de **portee**, pas une vraie absence.
- Verifier le **schema reel** d'une table (colonnes, types, casse).

**Ne pas utiliser** pour :
- **Resoudre la connexion** (quelle base, quel serveur, quelles credentials, joignabilite) -> c'est `understanding-integrator-workspace` (`sql-resolution.md`, R-7 a R-12). Ce skill suppose la connexion **deja resolue**.
- Interroger le **graphe diva-mcp** (structure du standard) -> `querying-diva-graph`.
- Ecrire du RecordSql / SQL *genere* dans le code DIVA -> `generating-recordsql` / `linting-diva-code`.

## Prerequis : connexion resolue

La resolution de la connexion (serveur, base, authentification, joignabilite) est **hors perimetre** : voir `understanding-integrator-workspace`. En reprendre les parametres **et la posture de delegation R-12** : on ne lance pas `sqlcmd` a l'aveugle contre une base client -- privilegier une verification indirecte, fournir la requete au collaborateur, ou n'executer qu'avec son **accord explicite** (lecture seule).

## Les 4 conventions d'or (base client Divalto)

1. **MAJUSCULES.** Les noms de tables et de colonnes s'ecrivent en **MAJUSCULES** -- c'est le **nom du DICTIONNAIRE**, pas forcement le `NomOdbc` local ni le libelle affiche. Ex. une entite « Article » se requete `ARTICLE`, pas `Article`. **Regle transverse** (rappelee dans la note globale du README partenaire).
2. **Collation sensible.** La base est generalement en collation **binaire** (ex. `Latin1_General_BIN`) -> **sensible a la casse ET aux accents**. `FROM article` ou `LIKE '%Mvt%'` echouent la ou `ARTICLE` / `LIKE '%MVT%'` passent. Ne jamais compter sur une comparaison insensible.
3. **Table = nom du dictionnaire, != NomOdbc.** Le nom SQL physique est celui du dictionnaire (MAJUSCULES), qui **differe** du `NomOdbc` local que le poste peut afficher. En cas de doute -> decouverte (ci-dessous), jamais deviner.
4. **Schema `dbo`.** Le metier Divalto vit sous le schema **`dbo`**.

> **La regle MAJUSCULES n'est pas absolue.** Quelques objets techniques/systeme ou vues peuvent deroger. Elle vaut pour le metier sous `dbo` -> **en cas de doute, decouvrir** plutot qu'affirmer.

## Recette de decouverte (avant d'ecrire la requete finale)

Retrouver le **nom et la casse reels** via `INFORMATION_SCHEMA` avant de figer la requete metier :

```sql
-- Nom/casse reels d'une table (recherche large)
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME LIKE '%ART%';

-- Colonnes reelles d'une table
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'ARTICLE'
ORDER BY ORDINAL_POSITION;
```

Detail (collation, `dbo`, pieges de casse, exceptions) : [reference/sql-client-conventions.md](reference/sql-client-conventions.md).

## Helper : portee d'une table de parametrage (`check_table_scope`)

Une table de parametrage `Tnnn` du standard peut etre **commune a tous les dossiers** ou **propre a un dossier** -- l'info est portee par `T000` / `TABTYP` (mecanisme detaille dans `understanding-integrator-workspace/sql-resolution.md`). **Avant de conclure qu'une table `T*` est "vide" pour un dossier**, verifier sa portee :

```
py scripts/check_table_scope.py --table T021 [--tabtyp 2] [--dossier 998] \
    [--server <srv> --database <db> -E --execute]
```

- **Sans `--execute`** : le script **construit la requete** `SELECT TABTYP_0021 FROM T000` a faire executer (delegation -- regle `R-12` du skill `understanding-integrator-workspace`) ; si `--tabtyp` est fourni, il l'**interprete** directement.
- **Avec `--execute`** (+ `--server --database -E`) : il lit `T000` en **lecture seule**, en **auth Windows uniquement**, et interprete. Une base en **auth SQL** passe par le mode delegation -- aucun mot de passe en clair sur la ligne de commande.

Sortie JSON : `{table, colonne, tabtyp, scope, dossier_a_requeter, requete}`. `TABTYP=2` -> **commune** (dossier `999`) ; `=1` -> **par-dossier**.

## Hygiene

- **Lecture seule par defaut.** Aucune ecriture sur une base client sans demande explicite.
- **Delegation** (regle `R-12` du skill `understanding-integrator-workspace`). Ne pas attaquer une base client a l'aveugle.
- **Credentials jamais en clair** dans un skill, un log ou une trace (voir la regle `R-11` du skill `understanding-integrator-workspace`).

## Voir aussi

- `understanding-integrator-workspace` -- resolution de connexion (R-7 a R-12) et mecanisme `T000` / `TABTYP` (`sql-resolution.md`).
- `querying-diva-graph` -- interroger la structure du **standard** (graphe diva-mcp), pas la base client.
- `syncing-diva-sql` -- synchronisation du schema SQL depuis le dictionnaire (offline).
