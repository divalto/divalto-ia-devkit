# x13-impact-patterns.md

## Contenu

- Limitation de l'analyse statique DIVA
- Patterns d'appel
- Patterns de dependance structurelle
- Ordre de priorite dans le rapport
- Ajouter un pattern

---


Regex de reference pour detecter l'impact (callers, dependances) dans les sources DIVA X.13.

## Limitation de l'analyse statique DIVA

DIVA est resolu a la compilation, pas dynamiquement. L'analyse statique textuelle capture la majorite des appels mais manque :
- Les appels dynamiques via `Execute "X"` dont `X` est une variable
- Les tunnels Harmony inter-modules (`Ping`/`Pong`)
- Les hooks resolus par nom par le framework

Pour le MVP, on se contente des patterns textuels. Les cas avances sont inscrits au BACKLOG.

## Patterns d'appel

### Appel procedure directe

```regex
\bCall\s+<nom>\b
```

Exemples matches :
- `Call Construire_ConditionSelection`
- `Call Check_FamRgltRtl_Field_Libelle`
- `	Call	Update_Famille_Rglt(RtlFamRglt)`

### Execution dynamique

```regex
\bExecute\s+["']<nom>["']
```

Exemples :
- `Execute "Open_File"`
- `Execute 'Close_Zoom'`

Pour le MVP, on ne resout pas les `Execute variable` (variable Execute X_name).

### Appel methode sur instance

```regex
\b<instance>\.<nom>\b
```

Exemples (plus risque de faux positifs) :
- `FamRgltRtl.Orderby.Par_Code()`
- `MZ.Dos.Init()`

Le script `verify_x13.py` combine les patterns `Call` + `Execute` + appel fonction `X(`:

```python
call_pat = re.compile(
    rf'\b(?:Call|Execute)\s+[\'"]?{re.escape(fn_name)}[\'"]?|'
    rf'\b{re.escape(fn_name)}\s*\(',
    re.IGNORECASE,
)
```

Cela capture les 3 formes d'appel. Les faux positifs sont acceptables (le rapport final cite le `fichier:ligne` et le developpeur juge la pertinence).

## Patterns de dependance structurelle

### Declaration de module

```regex
^\s*Module\s+['"]<nom>\.(dhop|dhoq)['"]
```

Exemple : `Module 'rttmchkrtlfamrglt.dhop'`. Indique une dependance directe.

### Include de fichier

```regex
^\s*Include\s+['"]<nom>\.dh\w+['"]
```

Exemple : `Include 'GTTCZ00.dhsp'`.

### Version de fichier ISAM

```regex
^\s*HFileVersion\s+\S+\s+<table>\b
```

Exemple : `HFileVersion RTLFDD.dhsd RTFTAB`. Indique que le program accede a la table `RTFTAB` via le dictionnaire `RTLFDD`.

### Surcharge declaree

```regex
^\s*OverWrittenBy\s+['"]<nom>\.(dhop|dhoq)['"]
```

Exemple : `OverWrittenBy 'RTUZFAMRGLT_SQL.dhop'`. Indique que ce fichier peut etre surcharge.

## Ordre de priorite dans le rapport

Pour la section 4 "Etude d'impact" de `docs/ANALYSE-PRE-ACTION.md` :

1. **Appelants directs** (`Call`, `Execute`) -- cascade probable
2. **Dependances structurelles** (`Module`, `HFileVersion`) -- cascade certaine en cas de modification d'interface
3. **Surcharges declarees** (`OverWrittenBy`) -- point d'attention major

Le script `verify_x13.py` remonte les 3 dans `impact.callers`. Le LLM orchestrateur (phase 4) les regroupe selon ces categories dans le rapport final.

## Ajouter un pattern

Procedure :
1. Ajouter la regex dans `verify_x13.py` (fonction `verify`)
2. Documenter ici avec exemple
3. Ajouter un scenario dans `evals.json`
