# Surcharge -- OverWrittenBy / OverWrite

## Contenu

- Principe
- Hierarchie de surcharge
- Declaration des procedures surchargees (sans Public/Private/Protected)
- Visibilite des declarations dans une surcharge (records, fichiers, RSQL, constantes)
- Pattern canonique de surcharge de procedure
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

## Declaration des procedures surchargees

Dans une `.dhsp` `OverWrite`, une procedure qui surcharge une procedure publique du standard **ne doit PAS porter de modificateur de visibilite** (`Public`, `Private`, `Protected`). La visibilite est heritee du module standard.

```diva
; MAUVAIS -- erreur compilateur xwin7 #210
;   "La fonction/procedure ZoomAbandon est une surcharge.
;    Elle ne peut etre PUBLIC"
Public Procedure ZoomAbandon
BeginP
    ...
EndP

; BON -- la visibilite est heritee du standard
Procedure ZoomAbandon
BeginP
    ...
EndP
```

Verifier la declaration du standard (`Public Procedure ZoomAbandon` dans le module original) confirme la visibilite, mais ne pas la repeter dans la surcharge.

## Visibilite des declarations dans une surcharge

Les `Record`, fichiers, `RecordSql` et constantes utilises par une procedure surchargee **ne sont PAS herites** du module standard. Ils doivent etre **redeclares localement** au fichier de surcharge.

```diva
; Fichier standard : gtuz021.dhsp
OverWrittenBy 'gtuz021u.dhop'
Public Record DDSYS.dhsd ZOOM

Public Procedure ZoomCreation
BeginP
    Zoom.Ok = 'O'
    ...
EndP

; -----------------------------------------------------
; Fichier de surcharge : gtuz021u.dhsp
OverWrite 'gtuz021.dhop'

Public Record DDSYS.dhsd ZOOM   ; <-- OBLIGATOIRE : redeclaration locale
                                ;     sinon erreur compilateur xwin7 #99
                                ;     "Mot inconnu : Zoom"

Procedure ZoomCreation          ; <-- sans Public (cf. section precedente)
BeginP
    Standard.ZoomCreation()
    if Zoom.Ok = 'O'
        ; specifique
    endif
EndP
```

Regle : seules les `Procedure` / `Function` sont surchargees au sens runtime. Tout symbole non-procedural (record, file, RecordSql, constante, define) utilise dans le corps doit etre redeclare en haut de la `.dhsp` de surcharge, **identique a la declaration du standard**.

## Pattern canonique de surcharge de procedure

Trois regles, dans l'ordre :

1. **Toujours appeler `Standard.<proc>()`** -- meme si le standard est vide aujourd'hui. L'omettre cree une dette de compatibilite ascendante invisible : ca casse au prochain upgrade de pack si Divalto enrichit la procedure (cleanup, journalisation, validation metier).
2. **`Standard.<proc>()` en PREMIER**, code specifique ensuite. Le specifique observe l'etat post-standard et peut decider de ne pas s'executer si le standard a deja tranche (ex: standard a deja mis `Zoom.Ok = 'I'` -> ne pas afficher de pop-up de confirmation).
3. **Structurer en "tester l'acceptation"** (`if <flag> = 'O'`) plutot qu'en "tester le refus avec preturn". Un seul `if`/`endif` imbrique, branchement unique, plus lisible.

```diva
; Pattern canonique
Procedure ZoomAbandon
BeginP

    Standard.ZoomAbandon()

    if Zoom.Ok = 'O'                       ; le standard accepte l'abandon
        if MessageBox(...) = IDNO          ; on demande confirmation specifique
            Zoom.Ok = 'I'                  ; on annule l'abandon
        endif
    endif

EndP
```

A comparer au pattern "tester l'echec" (fonctionnellement equivalent mais moins lisible) :

```diva
Procedure ZoomAbandon
BeginP

    Standard.ZoomAbandon()

    if Zoom.Ok = 'I'                       ; standard a refuse
        preturn                            ; sortie precoce 1
    endif

    if MessageBox(...) = IDNO
        Zoom.Ok = 'I'
        preturn                            ; sortie precoce 2
    endif

EndP
```

Deux `preturn`, deux branches de sortie = code moins maintenable.

**Le pattern s'applique a toutes les procedures surchargees**, pas seulement aux `Zoom*` : modules de pieces (`Pre/PostInsert`, `Pre/PostUpdate`, `Pre/PostDelete`), tarification, calcul, etc. L'ordre "Standard puis specifique" + test du flag d'acceptation est la convention solide.

> Note : la grille des flags de retour (`'O'`, `'N'`, `'I'`, `'C'`...) varie selon le hook. Voir [zoom-hooks-reference.md](zoom-hooks-reference.md) pour les codes par hook Zoom*.

## Surcharge RecordSql

```xml
; Dans le .dhsq d'origine
<RecordSql Name=MaVue ... OverWrittenBy="monfichierU.dhoq">
```

Convention de nommage : `gtrsart.dhoq` → `gtrsartu.dhoq` → `gtrsartuu.dhoq`

La surcharge RecordSql peut ajouter :
- Champs SELECT supplementaires
- JOINs additionnels (avec restrictions, cf. delta strict)
- Criteres WHERE / ORDERBY (avec restrictions)

**Important** : la surcharge `.dhsq` obeit a une grammaire "delta strict" -- toute redeclaration du standard est interdite et provoque des erreurs explicites au compile. Voir la doc dediee du skill `generating-recordsql` : [dhsq-overwrite-pattern.md](../../generating-recordsql/reference/dhsq-overwrite-pattern.md) pour les 9 interdits empiriques, le pattern delta correct, et la convention de rattachement via groupe `[communs]`.

## Regles

- **Ne jamais modifier le module standard** -- toujours surcharger
- Le fichier surcharge doit etre dans le meme sous-projet (ou un sous-projet de surcharge dedie)
- `Standard.` est le seul moyen d'appeler la version originale depuis la surcharge
- Convention stricte sur le nommage : suffixe `U` (puis `UU`) en majuscule dans le `OverWrittenBy`, minuscule dans le nom de fichier
- Pas de modificateur de visibilite sur la procedure surchargee (heritage)
- Redeclarer localement tout symbole non-procedural utilise (records, fichiers, RSQL, constantes)
- Appeler `Standard.<proc>()` systematiquement, en premier, et structurer le test sur le flag d'acceptation

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
