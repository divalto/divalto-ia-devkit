# Surcharge -- OverWrittenBy / OverWrite

## Contenu

- Principe
- Hierarchie de surcharge
- Surcharge RecordSql
- Regles
- Advisory -- analyse d'impact avant surcharge (via diva-mcp)

---


Mecanisme de verticalisation : un module utilisateur surcharge les fonctions du module standard sans modifier le code original.

## Principe

```
; Module original (fichier standard)
OverWrittenBy 'MONMODULEU.dhop'   ; Convention : suffixe 'U'

; Module de surcharge (fichier utilisateur)
OverWrite 'MONMODULE.dhop'

; Appeler la version originale depuis la surcharge
Standard.MaFonction(params)    ; Prefixe Standard.
```

## Hierarchie de surcharge

Convention de nommage multi-niveaux :

| Niveau | Fichier | Suffixe |
|--------|---------|---------|
| Standard | `monmodule.dhop` | _(aucun)_ |
| Surcharge niveau 1 | `monmoduleu.dhop` | `u` |
| Surcharge niveau 2 | `monmoduleuu.dhop` | `uu` |

Chaque niveau fait `OverWrite` du niveau precedent et peut appeler `Standard.Fonction()` pour invoquer l'implementation originale.

## Surcharge RecordSql

```xml
; Dans le .dhsq d'origine
<RecordSql Name=MaVue ... OverWrittenBy="monfichierU.dhoq">
```

Convention de nommage : `gtrsart.dhoq` → `gtrsartu.dhoq` → `gtrsartuu.dhoq`

La surcharge RecordSql peut ajouter :
- Champs SELECT supplementaires
- JOINs additionnels
- Criteres WHERE
- Ordres de tri

## Regles

- **Ne jamais modifier le module standard** -- toujours surcharger
- Le fichier surcharge doit etre dans le meme sous-projet (ou un sous-projet de surcharge dedie)
- `Standard.` est le seul moyen d'appeler la version originale depuis la surcharge
- Convention stricte sur le nommage : suffixe `U` (puis `UU`) en majuscule dans le `OverWrittenBy`, minuscule dans le nom de fichier

---

## Advisory -- analyse d'impact avant surcharge (via diva-mcp)

> **Snapshot X.12, non bloquant**. Toujours croiser avec X.13 avant decision -- le graphe est une aide a la decouverte, pas une validation. Ne jamais utiliser ces resultats comme garde-fou.

Avant de surcharger un module (zoom, mchk, recordsql), il est utile d'identifier **qui depend deja** des exports publics du module. Le graphe `diva-mcp` permet des explorations rapides.

### Reutilisateurs d'une procedure / fonction publique

Typiquement utile pour mchk (`Get_TABLE_Record`, `Check_TABLE`, `Initialize_*_New` sont tres reutilises).

```cypher
// Nombre de reutilisateurs d'une procedure/fonction publique (hors programme d'origine)
MATCH (proc)
WHERE (proc:Procedure OR proc:Function)
  AND toLower(proc.name) = toLower($nom_procedure)
  AND toLower(proc.decla_type) = 'public'
OPTIONAL MATCH (caller)-[:CALLS]->(proc)
WHERE caller.program <> proc.program
WITH proc, count(DISTINCT caller) AS nb_callers_externes,
     collect(DISTINCT caller.program)[..15] AS sample_programs
RETURN proc.program AS module_source, proc.name AS procedure,
       nb_callers_externes, sample_programs
ORDER BY nb_callers_externes DESC;
```

### RecordSql surcharges deja existants dans le standard

Utile pour eviter de surcharger un RecordSql qui l'est deja, ou pour s'inspirer d'une surcharge existante.

```cypher
// Lister les RecordSql ayant deja une surcharge dans le standard X.12
// (property OverWrittenBy exposee dans le DObj du fichier .dhsq)
MATCH (p:Program)-[:CONTAINS]->(rs:RecordSQL)
WHERE rs.name IS NOT NULL
RETURN p.name AS fichier, rs.name AS recordsql_name LIMIT 50;

// Pour un RecordSql donne, quels programmes l'utilisent (via USES_QUERY)
MATCH (rs:RecordSQL {name: $nom_vue})-[:USES_QUERY]->(q:QueryFile)
OPTIONAL MATCH (prog:Program)-[:CONTAINS]->(rs2:RecordSQL {name: $nom_vue})
RETURN DISTINCT prog.name AS program, q.name AS query_file LIMIT 30;
```

### Impact "en amont" d'une surcharge de zoom

Les procedures `Zoom*` (ZoomDebut, ZoomCreation, ...) ne sont typiquement pas appelees par du code applicatif mais par le framework via hook. En revanche, les **constantes de zoom** (numeros) et les **libelles exposes** sont tres consommes.

```cypher
// Constantes publiques declarees dans un zoom
MATCH (p:Program {name: $nom_zoom_programme})-[:CONTAINS]->(c:Const)
WHERE toLower(c.decla_type) = 'public'
RETURN c.name, c.value, c.line ORDER BY c.line;

// Defines declarees dans le mchk associe au zoom
MATCH (p:Program {name: $nom_mchk_programme})-[:CONTAINS]->(d:Define)
RETURN d.name, d.line ORDER BY d.line;
```

### Bonnes pratiques advisory

- Lancer ces requetes **avant** de decider de la portee de la surcharge (standard, standard + uU, ou uniquement uU).
- Reflechir a la compatibilite ascendante : une surcharge qui change la signature d'une fonction publique peut casser tous les reutilisateurs identifies.
- **Ne pas bloquer sur ces chiffres** -- croiser avec la version X.13 courante si la surcharge vise le code actuel (grep dans le filesystem standard, inspection SQL).
