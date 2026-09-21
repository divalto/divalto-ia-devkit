# Pièges d'interrogation du graphe MCP (diva-mcp)

Les outils du serveur `diva-mcp` (`get_schema`, `get_table_schema`, `query_cypher`…)
ont quelques comportements qui induisent en erreur si on ne les connaît pas. Ce skill
ne peut pas corriger le serveur : il documente les **contournements**. Les cas ci-dessous
ont été **vérifiés contre le snapshot X.12 le 2026-08-20**.

---

## 1. `get_schema` sous-déclare les propriétés de Function / Procedure / Const / Variable / Record

**Symptôme.** `get_schema` renvoie `props: []` pour les nœuds les plus utiles du graphe :
`Function`, `Procedure`, `Const`, `Variable`, `Record`. Lu littéralement, on croirait
qu'on ne peut ni filtrer ni projeter sur ces nœuds — ce qui condamnerait l'écriture de
Cypher utile.

**Réalité.** Ces nœuds portent en fait **17 propriétés** :
`uid, name, program, obj_type, scope_type, scope_name, decla_type, line, end_line,
lines_length, decl_idx, color, out_type, has_prototype, has_body, params, body`.
La plus précieuse est **`body`** (le code source de la routine) : elle permet de lire une
ouverture **sans accéder au disque**.

**Cause.** ArcadeDB stocke ces nœuds sous le supertype **`DObj`** : `get_schema` déclare
les propriétés sous `DObj` (où elles apparaissent bien : `body`, `name`, `program`, `uid`…),
pas sous les sous-types logiques `Function` / `Procedure` / … qui remontent `[]`.

**Contournement.** Avant d'écrire une requête utile, faire une **requête de découverte** :

```
MATCH (n:Function) WITH n LIMIT 1 RETURN keys(n)
```

(ou lire les props sous `DObj` dans la sortie de `get_schema`). Ne jamais se fier au
`props: []` d'un sous-type. `Program`, `DocPage`, `DbTable`, `DbField`, `NativeKeyword`
remontent, eux, leurs propriétés correctement.

---

## 2. `body` = « Programme protégé, non livré. » sur les programmes protégés (`xxpm*` / `xxpp*`)

**Symptôme.** Pour les routines des **programmes protégés** du standard (préfixes `xxpm*` /
`xxpp*`, p. ex. `gtpm*`, `gtpp*`), la propriété `body` ne contient pas de code mais la
chaîne littérale `Programme protégé, non livré.`. La structure reste exploitable (noms de
routines, `line` / `lines_length`, tables accédées, graphe d'appels) — seul le corps est vide.

**À l'inverse**, les modules d'**ouvertures** `xxtt*` / `xxtm*` sont livrés intégralement
(code réel, commentaires inclus).

**Pourquoi c'est LA clé de lecture du graphe pour un intégrateur.** Cette asymétrie dit
**où l'on peut lire et où l'on peut surcharger** : analyser un besoin passe par les
**ouvertures `xxtt` / `xxtm`**, pas par la lecture des `xxpp` / `xxpm`. Un `body` vide sur
un `xxpp*` n'est **pas** une lacune d'indexation — inutile d'aller chercher les sources sur
le disque ou en SVN (le standard livré n'inclut pas les `xxpp*`).

**Pour les `xxpp*` / `xxpm*`**, exploiter ce qui reste : liste des routines, `lines_length`
comme proxy de complexité, tables accédées, appels croisés.

Vérifié : `gtpm000.soc_bp_valider_auto_horsstock` → `Programme protégé, non livré.` ;
`gttt542.ent_bl_creation_ap` → code réel.

**Mesuré en masse sur X.13 le 2026-08-28** — l'asymétrie n'a rien d'anecdotique :

| Famille | Routines | Corps = le marqueur |
|---|---|---|
| `..pp<nnn>..` | 11 169 | **11 169 (100 %)** |
| `..tt<nnn>..` | 6 447 | **40 (0,6 %)** |

> **Attention à `has_body`.** La propriété vaut `true` **même quand le corps est le
> marqueur** : elle ne distingue donc pas « livré » de « protégé ». Le seul test fiable est
> le contenu — `body STARTS WITH 'Programme prot'`. Une première mesure fondée sur
> `has_body` concluait à tort que les `xxpp*` étaient livrés.

Corollaire côté écriture : un `xxpp*` n'est pas seulement illisible, il est **non
surchargeable** (`Erreur 106`). Voir
[overwrite-pattern.md](../../coding-diva-advanced/reference/overwrite-pattern.md), section
`PP` / `TT`.

---

## 3. `get_table_schema` n'expose pas le NomOdbc local (`[PROPLOC]`)

**Symptôme.** `get_table_schema` renvoie pour chaque champ : `field` (mnémonique DIVA),
`nature` (type) et `label` (libellé français). Pour un champ **générique** `CEx`
(« Code enregistrement 1..20 »), ce libellé n'est que **« Code enregistrement N »** —
inexploitable sémantiquement. Le **NomOdbc local** du bloc `[PROPLOC]` (p. ex. `CE4` =
`IndicateurLettrage`, `CE5` = `IndicateurPointage`) **n'est pas renvoyé** par l'outil.

**Contournement.** Pour connaître le sens réel d'un `CEx` (ou de tout champ générique),
consulter le **`[PROPLOC]` du dico** (colonne « Nom ODBC local » dans l'IDE xwin) **ou** le
module check `cctmchk*` (le code fait foi). Ne pas conclure du seul `get_table_schema`.

> Le dico lui-même est **fiable** (le NomOdbc local y est correct) — c'est l'outil MCP qui
> ne le surface pas. Vérifié : `get_table_schema('C8')` → `CE1..CEK` = « Code enregistrement
> N », aucun NomOdbc. À l'inverse, se méfier de toute affirmation « le dico est faux » : sur
> C8, dico (`CE4=Lettrage`, `CE5=Pointage`) et code concordent.

---

## 4. Aucune propriété ne donne la **signature** d'une routine — `params` est toujours vide

**Symptôme.** Pour écrire une surcharge ou un appel, on cherche la liste des paramètres
formels d'une routine — surtout quand son corps n'est pas livré. Le réflexe est d'interroger
une propriété du nœud. **Il n'y en a aucune qui réponde.**

- La propriété `args` **n'existe pas** sur `Function` / `Procedure` (les 17 propriétés
  réelles sont listées en section 1 ; `params` en fait partie, `args` non).
- La propriété `params`, elle, existe — **et vaut `[]` partout**. Mesuré le 2026-08-28 sur
  X.13 : **195 665 `Function` + `Procedure`, dont `params = '[]'` pour 195 665**. Aucune
  exception, aucun `null`.

Autrement dit : une requête du type `MATCH (n:Function) WHERE n.name = '…' RETURN n.args`
rend `null`, et sa variante avec `n.params` rend `[]`. Ni l'une ni l'autre ne donne la
signature.

**Contournement — passer par un appelant livré.** Le corps d'un `xxpp*` / `xxpm*` est
remplacé par le marqueur (section 2), mais le **site d'appel** dans du code livré, lui, est
lisible et montre les arguments réels :

```cypher
MATCH (c)-[:CALLS]->(f)
WHERE (f:Function OR f:Procedure) AND toLower(f.name) = '<la_routine_protegee>'
  AND NOT c.body STARTS WITH 'Programme prot'
RETURN toLower(c.program) AS appelant, c.name AS depuis, c.body AS corps
LIMIT 3
```

Vérifié : `Piece_Imprimer` est protégée, mais elle est appelée depuis
`gttt545.Integration_BL_Ap` — un `xxtt*`, donc livré, dont le corps montre l'appel complet.
La convergence avec la section 2 n'est pas un hasard : **ce sont les ouvertures `xxtt*` qui
appellent les programmes protégés**, donc ce sont elles qui exposent leurs signatures.

À défaut d'appelant livré, il reste le nombre de paramètres attendu par le compilateur, que
l'on ne découvre qu'en compilant — c'est précisément ce que ce contournement évite.

---

## En résumé

| Outil | Piège | Réflexe |
|-------|-------|---------|
| `get_schema` | `props: []` sur Function/Procedure/Const/Variable/Record | requête de découverte `RETURN keys(n)` ; `body` existe (17 props) |
| `query_cypher` (`body`) | `xxpm*` / `xxpp*` → « Programme protégé, non livré. » | lire/analyser via les ouvertures `xxtt*` / `xxtm*` |
| `query_cypher` (signature) | `args` n'existe pas ; `params` vaut `[]` sur **195 665/195 665** | remonter à un **appelant livré** via `[:CALLS]` et lire son corps |
| `get_table_schema` | pas de NomOdbc local ; `CEx` = « Code enregistrement N » | croiser le `[PROPLOC]` (IDE) ou le module check `cctmchk*` |
