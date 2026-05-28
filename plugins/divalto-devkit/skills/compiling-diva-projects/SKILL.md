---
name: compiling-diva-projects
description: >
  Compile un projet Divalto avec xwin7.exe (buildall ou build incremental), parse le rapport
  de compilation, et presente les erreurs avec leur contexte (fichier source, ligne).
  A utiliser apres avoir cree ou modifie des fichiers source DIVA pour verifier la compilation.
---

# compiling-diva-projects

## Contenu

- Utilisation rapide
- Workflow complet (3 etapes)
- Parsing du rapport
- Scripts disponibles
- References

---

## Utilisation rapide

### Validation rapide : standalone (~42s)

Generer un mini-projet standalone et compiler :

```bash
# 1. Generer le harness (cree .dhpt + .dhps dans le repertoire de sortie)
py .claude/skills/compiling-diva-projects/scripts/generate_harness.py \
    --source "chemin/mon_fichier.dhsp" --output-dir "{REPERTOIRE_SORTIE}" \
    --with-zdiva --with-communs

# 2. Compiler (chemin retourne par generate_harness.py dans compile_script)
powershell -ExecutionPolicy Bypass -File "{REPERTOIRE_SORTIE}/scripts/harness_compile.ps1"

# 3. Parser le rapport
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "{log_file retourne par generate_harness.py}"
```

**C'est le mode par defaut** pour valider un .dhsp en developpement iteratif (42s incompressibles, overhead demarrage xwin7).

### Validation d'integration : incremental ERP (~4.5 min)

Pour verifier qu'une modification ne casse pas les dependances ERP :

```powershell
C:\divalto\sys\xwin7.exe -action build `
    -project "{CHEMIN_PROJET}/divalto.dhpt" `
    -profile "développement" `
    -output "C:\...\Log\Compilation.txt" -outputall
```

**Prerequis** : les objets compiles doivent etre a jour (compilation ERP reussie prealable). Ne jamais tuer un processus xwin7 (corruption des objets → recompilation complete >45 min).

**Demander confirmation** avant de lancer cette compilation (duree ~4.5 min minimum).

### Parametres obligatoires

- `-user` : **regle de fallback stricte** (verifiee 2026-04-17). (1) `-user XX` explicite = prioritaire. (2) `-user` omis + `X_USER.strip() != ''` = xwin7 lit la variable. (3) `-user` omis + `X_USER` vide/absente = **crash xwin7 ExitCode -805306369** avec corruption des objets compiles (recuperation : buildall complet >45min). `generate_harness.py` applique un fallback securisant sur `USERNAME` Windows si `X_USER` est vide.
- Script .ps1 en **ISO-8859-1** si le nom de profil contient un accent (`développement`)

### Parser le rapport

```bash
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "C:/chemin/Log/Compilation.txt"
```

---

## Workflow complet

### Etape 1 -- Verifier les prerequis

Avant compilation :
- `C:\divalto\sys\xwin7.exe` accessible
- Fichier .dhpt valide (voir managing-diva-projects)
- Tous les .dhps references existent
- Tous les fichiers source en ISO-8859-1 + CRLF (P01, P02)
- Nom de profil avec accent correct

> **Working directory obligatoire** : tout appel xwin7 doit etre lance
> depuis `C:\divalto\sys` (`Set-Location "C:\divalto\sys"` en PowerShell). Cette
> regle est partagee avec `syncing-diva-sql` (synchroauto). Un cwd different
> peut produire des comportements subtils (resolution de chemins relatifs,
> profils, includes). `generate_harness.py` positionne automatiquement le cwd.
>
> **AccessViolation cosmetique en sortie** : xwin7 peut emettre une
> `AccessViolationException` a la fermeture (exit code 3) **sans** invalider la
> compilation. Le rapport reste fiable -- s'appuyer sur `Erreur(s)=0` du resume,
> pas sur l'exit code seul. `parse_compilation.py` filtre deja ce cas.

### Etape 2 -- Choisir le perimetre et confirmer

| Approche | Mode | Duree | Usage |
|----------|------|-------|-------|
| Standalone (harness) | buildall | **42s** | Validation syntaxique rapide (defaut) |
| Incremental ERP | build | **~4.5 min** | Validation d'integration |
| Complet ERP | buildall | **>45 min** | Premiere compilation ou corruption |

**Strategie recommandee** :
1. **Standalone** pour la boucle de dev rapide (generer le harness, compiler, corriger, repeter)
2. **Incremental ERP** pour valider l'integration avant commit (demander confirmation)
3. **Complet ERP** uniquement si necessaire (demander confirmation + indiquer >45 min)

### Etape 3 -- Compiler

> **Regle critique pour profils accentues** : si le nom du profil contient un accent (typique : `développement` avec `e` accent aigu), passer l'argument litteralement depuis une session PowerShell echoue silencieusement (encodage perdu lors du passage a xwin7). **Obligation** : passer par `scripts/compile_project.py` (recommande) ou ecrire manuellement un `.ps1` en ISO-8859-1 + CRLF. Cf. `reference/xwin7-syntax.md` section "Encodage du script PowerShell" pour le detail.
>
> Recette express avec `compile_project.py` :
> ```bash
> py .claude/skills/compiling-diva-projects/scripts/compile_project.py \\
>     --project "<chemin .dhpt>" \\
>     --profile "développement" \\
>     --log-path "<chemin log.txt>"
> ```
> Le script genere le `.ps1` ISO-8859-1, l'execute, capture stdout/stderr, et retourne un JSON `{ps1_script, log_file, exit_code, success, summary, ...}`.

**Cas standard -- compilation complete** (projet sans environnement) :
```powershell
C:\divalto\sys\xwin7.exe -action buildall `
    -project $Projet -profile $Profil `
    -output $LogFile -outputall | Out-Null
```

**Cas standard -- compilation incrementale** :
```powershell
C:\divalto\sys\xwin7.exe -action build `
    -project $Projet -profile $Profil `
    -output $LogFile -outputall | Out-Null
```

**Note** : `-user` est recommande mais pas toujours obligatoire. `generate_harness.py` accepte `--user` pour override explicite.

**Cas avec sous-projet** (compile uniquement les fichiers du sous-projet) :

> **Piege [communs]** : `-sousproject` ne recompile PAS les fichiers des groupes `[communs]` du .dhpt parent (ex: `gtpmficsql.dhsp`, `gttcficsql.dhsp`). Si ces fichiers ont ete modifies, lancer un `build` sur le projet principal ou les ajouter temporairement dans `[fichiers]` du sous-projet.

> **Piege changement dictionnaire -> buildall obligatoire (R-010)** : apres
> toute modification de structure dans un `.dhsd` (taille d'une table, ajout/
> suppression de champ, changement de positions), un `-action build` sur
> sous-projet NE recompile PAS le masque `.dhsf` si celui-ci n'a pas change.
> Le masque garde l'ancienne taille en cache et le runtime echoue avec
> `"enregistrement deja alloue avec la taille X par le module Y"`. Solution :
> utiliser `-action buildall -sousproject "<dhps>"` pour forcer la
> recompilation complete du sous-projet.
```powershell
C:\divalto\sys\xwin7.exe -action build `
    -project $Projet -sousproject $SousProjet `
    -profile $Profil -output $LogFile -outputall | Out-Null
```

**Cas avec un seul source** (validation chirurgicale d'un fichier modifie) :

> **Couplage obligatoire `-source` + `-sousproject`** : sur un projet parent
> multi-sous-projets, `-source` seul echoue avec
> `"Nom du sous-projet non renseigne"`. Toujours passer **les deux**.
>
> **Basename uniquement** : pour `-source`, passer le **nom du fichier
> sans chemin** (ex `gtezracechien_sql.dhsf`). Un chemin absolu echoue avec
> `"Source ... inexistant dans le sous projet"`. Le fichier doit etre declare
> dans `[fichiers]` ou `[includes]` du `.dhps` cible.
>
> Iteration de masque : ~8s vs ~22s pour `-action buildall -sousproject`.

```powershell
C:\divalto\sys\xwin7.exe -action build `
    -project $Projet -sousproject $SousProjet -source $FichierSourceBasename `
    -profile $Profil -output $LogFile -outputall | Out-Null
```

**Cas avec environnement** (deux commandes separees) :
```powershell
C:\divalto\sys\xwin7.exe -select_environment $Environnement -outputall | Out-Null
C:\divalto\sys\xwin7.exe -action buildall `
    -project $Projet -profile $Profil `
    -output $LogFile -outputall | Out-Null
```

**Utilisateur** : `-user` est optionnel si `X_USER.strip() != ''`. Sinon **obligatoire** (sous peine de crash xwin7 -- voir section plus haut). `generate_harness.py` fait automatiquement le fallback sur `USERNAME` si `X_USER` vide.

**Important** : `-select_environment` uniquement si le .dhpt est lie a un environnement. L'inclure sur un projet autonome provoque une erreur.

### Etape 4 -- Analyser le rapport

```bash
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "chemin/rapport.txt"
```

Si `success: true` → compilation reussie, possibilite de lancer la synchro SQL.
Si `success: false` → corriger les erreurs et recompiler.

---

## Parsing du rapport

### Ligne de resume

```
Erreur(s)=0   Warning(s)=0   Diva=42   Masques=5   Dictionnaires=3   Sql=8   Objets proteges=0
Duree=0:01:23
```

| Champ | Signification |
|-------|---------------|
| `Erreur(s)=` | Nombre d'erreurs (0 = succes) |
| `Warning(s)=` | Nombre de warnings |
| `Diva=` | Sources DIVA compiles |
| `Masques=` | Masques ecran compiles |
| `Dictionnaires=` | Dictionnaires compiles |
| `Sql=` | RecordSql compiles |
| `Objets proteges=` | Objets proteges compiles |
| `Duree=` | Temps total H:M:S |

### Erreurs avec contexte

Les erreurs apparaissent dans le rapport avec la ligne precedente contenant le nom du fichier source. Le script `parse_compilation.py` extrait automatiquement :
- Le message d'erreur
- Le contexte (ligne precedente)
- Le fichier source (si identifiable)

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `generate_harness.py` | Genere un harness standalone | --source ou --sources --output-dir [--with-zdiva] [--with-communs] [--user] | JSON (chemins generes + log_file unique) |
| `compile_project.py` | Compile un projet reel (.dhpt) via xwin7 avec gestion automatique du piege d'encodage profil accentue (R-005). Genere un .ps1 ISO-8859-1, l'execute, capture stdout/stderr, parse la ligne de resume du log. | --project --profile --log-path [--action build\|buildall] [--user] [--sousproject] [--source] [--xwin7-path] [--ps1-dir] [--no-execute] | JSON (ps1_script, log_file, exit_code, success, summary, ...) |
| `parse_compilation.py` | Parse rapport build/buildall | --path fichier.txt [--check-outputs] [--errors-only] | JSON (success, summary, errors, warnings) |

**generate_harness.py** :
- `--source` : chemin d'un fichier .dhsp ou .dhsq (retro-compatible)
- `--sources` : chemins de plusieurs fichiers .dhsp/.dhsq (compilation en une passe)
- `--with-zdiva` : inclure zdiva.dhsp dans les includes
- `--with-communs` : inclure les communs framework (a5pm000, a5pmtab, gtpm000)
- Le log de compilation est unique par run (`harness_YYYYMMDD_HHMMSS.txt`)
- Exit codes : 0 = succes, 1 = erreur utilisateur, 2 = erreur interne

**compile_project.py** :
- Cas d'usage : compiler un projet **reel** (.dhpt) -- typiquement un projet de surcharge integrateur. Pas pour les harnesses standalone (utiliser `generate_harness.py` pour ca).
- **Critique** : adresse le piege d'encodage R-005 -- passer `-profile "developpement"` (accent) directement depuis PowerShell echoue. Ce script genere automatiquement un `.ps1` en ISO-8859-1 + CRLF qui contient le profil litteral, puis l'execute via `powershell -File`. xwin7 recoit alors l'octet `0xe9` natif et matche correctement.
- `--project` : chemin absolu du `.dhpt`
- `--profile` : nom du profil (peut contenir accent)
- `--log-path` : chemin du log que xwin7 doit produire
- `--action` : `build` (defaut, incremental) ou `buildall` (complet)
- `--sousproject`, `--source` : couplage `-sousproject`/`-source` pour compilation chirurgicale
- `--user` : fallback `--user XX > X_USER > USERNAME` (idem `generate_harness.py`)
- `--no-execute` : genere uniquement le .ps1 (debug, exit 3)
- Exit codes : 0 = compilation reussie, 1 = erreurs ou input invalide, 2 = erreur interne, 3 = no-execute

**parse_compilation.py** :
- `--errors-only` : ne retourne que les erreurs (pas les warnings)
- `--check-outputs` : liste de fichiers compiles attendus (.dhop, .dhoq). Verifie existence ET taille >= 2048B (1024B = stub echec)
- Detecte les abandons de compilation ("Construction du projet arrêtée")
- Log vide = erreur (xwin7 ecrit toujours un resume quand il termine normalement)
- Exit codes : 0 = compilation reussie, 1 = erreurs trouvees, 2 = rapport illisible

---

## References

- [Syntaxe xwin7.exe](reference/xwin7-syntax.md) -- parametres, actions, encodage PS1
- [Erreurs courantes](reference/compilation-errors.md) -- format rapport, erreurs/solutions, prerequis
