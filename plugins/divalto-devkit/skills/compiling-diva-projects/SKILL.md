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
- Workflow complet (4 etapes)
- Quitus (compilation de livraison)
- Parsing du rapport
- Scripts disponibles
- References

---

## Utilisation rapide

### Arbre de decision -- ou compiler un source ?

**Regle : compiler dans la structure REELLE du projet, pas dans un mini-projet fabrique.**
Le `.dhpt`, ses profils et le sous-projet d'un source sont ceux identifies par
**`understanding-integrator-workspace`** (decouverte du workspace : implicite actif +
enumeration des `.dhpt` + coherence) -- on ne les devine pas.

1. **Le source appartient deja a un `.dhpt`** (cas normal -- source du standard livre, ou
   specifique deja cable dans un `.dhps`) -> compiler via le **vrai `.dhpt`**, perimetre
   restreint (rapide, pas de buildall complet) :
   ```bash
   # chirurgical -- un seul source (~8s) : -source + -sousproject OBLIGATOIREMENT couples
   py .claude/skills/compiling-diva-projects/scripts/compile_project.py \
       --project "<projet.dhpt>" --sousproject "<sousprojet.dhps>" \
       --source "<fichier.dhsf>" --profile "<profil>" --log-path "<log.txt>"
   # ou tout un sous-projet
   py .claude/skills/compiling-diva-projects/scripts/compile_project.py \
       --project "<projet.dhpt>" --sousproject "<sousprojet.dhps>" \
       --profile "<profil>" --log-path "<log.txt>"
   ```

2. **Le source est NOUVEAU** (cree, pas encore declare dans un `.dhps`) :
   - **Interactif** -> demander a l'utilisateur dans quel sous-projet le cabler, puis cas 1.
   - **Autonome / goal** (pas d'interlocuteur) -> **dernier recours** : harness standalone
     qui **emprunte** la config d'un vrai `.dhpt` (ci-dessous).

> **Le harness ne compile que des sources programme** (`.dhsp` / `.dhsq`). Un masque `.dhsf`,
> un dictionnaire `.dhsd` ou un include `.dhsi` n'a pas de sens compile hors de son contexte
> (un masque depend de son dictionnaire) : pour ceux-la, passer par le **vrai `.dhpt`** (cas 1),
> meme sur un fichier neuf -- au besoin en le cablant d'abord dans un `.dhps`.

> Le harness n'est **jamais** le premier choix : il ne compile qu'un source **isole** de son
> contexte. S'il a besoin d'un module `[communs]`, il **n'est pas isolable** -> revenir au cas 1.

### Dernier recours -- harness standalone (`--from-dhpt`)

Uniquement quand le source n'appartient a aucun `.dhps` **et** qu'on ne peut pas demander
ou le cabler. Le harness **ne code aucune valeur poste en dur** : profil, implicite (search
path), util, cheminbases sont **empruntes** a un `.dhpt` modele du workspace (celui identifie
par `understanding-integrator-workspace`). Un harness a la config inventee compile contre un
environnement fantome (implicite inexistant -> resolution des includes cassee, faux verdicts).

```bash
# 1. Generer le harness en EMPRUNTANT la config d'un .dhpt reel du workspace
py .claude/skills/compiling-diva-projects/scripts/generate_harness.py \
    --from-dhpt "<projet_reel.dhpt>" --source "chemin/mon_fichier.dhsp" \
    --output-dir "{REPERTOIRE_SORTIE}"
#   -> JSON : { dhpt, borrowed_profile, next, ... }  (borrowed_profile = profil emprunte)

# 2. Compiler via le profil EMPRUNTE retourne (champ borrowed_profile)
py .claude/skills/compiling-diva-projects/scripts/compile_project.py \
    --project "{REPERTOIRE_SORTIE}/projet/harness.dhpt" \
    --profile "<borrowed_profile>" --log-path "{REPERTOIRE_SORTIE}/log/harness.txt" \
    --action buildall

# 3. Parser le rapport (compile_project le fait deja ; utile en analyse separee)
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "{log_file}"
```

Si le `.dhpt` modele declare **plusieurs** profils, preciser lequel emprunter avec
`--profile "<nom>"` (sinon `generate_harness.py` echoue en listant les profils).

> **Dependance locale non precompilee (#28).** Si le source appelle un `.dhop` **local** non
> precompile dans l'ERP (un autre `.dhsp` du meme lot, pas un objet standard), compiler le
> `.dhsp` **seul** echoue. Passer **toutes** les sources interdependantes ensemble :
> `--sources A.dhsp B.dhsp ...` -- le harness les compile en une passe.

> **Sous-projet `.dhps` orphelin (#216).** Cas particulier du point 2 : une `.dhps` **existe
> sur disque** mais **aucun `.dhpt`** ne la reference (`grep -l "<base>.dhps" projets/*.dhpt`
> -> vide). `-sousproject` echoue alors ("inexistant"). Reconstruire un harness qui **reprend
> le bloc `[fichiers]`** de cette `.dhps` : `generate_harness.py --from-dhpt "<un .dhpt du
> workspace>" --output-dir "<sortie>" --sources <les .dhsp/.dhsq du bloc [fichiers]>`.
> Si le bloc contient aussi des masques ou des dictionnaires, ils ne sont **pas** compilables
> par le harness : se rabattre sur un `buildall` global du `.dhpt` (cf. #308).

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

- `-user` : **regle de fallback stricte** (verifiee 2026-04-17). (1) `-user XX` explicite = prioritaire. (2) `-user` omis + `X_USER.strip() != ''` = xwin7 lit la variable. (3) `-user` omis + `X_USER` vide/absente = **crash xwin7 ExitCode -805306369** avec corruption des objets compiles (recuperation : buildall complet >45min). `compile_project.py` resout l'utilisateur dans l'ordre `--user > util= du .dhpt > X_USER > USERNAME` (#235) et applique un fallback securisant sur `USERNAME` Windows en dernier ressort.
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
- Tous les fichiers source en ISO-8859-1 + CRLF (PROJ01, PROJ02)
- Nom de profil avec accent correct

> **Découvrir le projet et le profil d'abord** : privilégier un `.dhpt` **existant** (le harness standalone est un dernier recours). Un `.dhpt` définit ses **propres** profils nommés — ne pas présumer « développement ». Lister/valider avant de compiler :
> ```
> py .claude/skills/compiling-diva-projects/scripts/compile_project.py --project "<dhpt>" --list-profiles
> ```
> `compile_project.py` **valide** le profil contre le `.dhpt` et **échoue tôt** (avant xwin7) s'il est absent, en listant les profils disponibles — évite l'échec tardif « Profil X inexistant ».

> **Working directory obligatoire** : tout appel xwin7 doit etre lance **depuis le dossier
> de `xwin7.exe`** (souvent `C:\divalto\sys`, mais **pas toujours** -- #301). Cette
> regle est partagee avec `syncing-diva-sql` (synchroauto). Un cwd different
> peut produire des comportements subtils (resolution de chemins relatifs,
> profils, includes). `compile_project.py` positionne automatiquement le cwd (via `Set-Location`, derive de `--xwin7-path`, #301).
>
> **AccessViolation cosmetique en sortie** : xwin7 peut emettre une
> `AccessViolationException` a la fermeture (exit code 3) **sans** invalider la
> compilation. Le rapport reste fiable -- s'appuyer sur le **verdict** de
> `parse_compilation.py`, pas sur l'exit code seul. Ce cas y est deja filtre.

### Etape 2 -- Choisir le perimetre et confirmer

| Approche | Mode | Duree | Usage |
|----------|------|-------|-------|
| Vrai `.dhpt` -- source / sous-projet | build | **~8-22s** | **Voie normale** : valider un source dans son projet reel |
| Vrai `.dhpt` -- incremental complet | build | **~4.5 min** | Valider l'integration (toutes dependances ERP) |
| Vrai `.dhpt` -- buildall complet | buildall | **>45 min** | Premiere compilation ou corruption |
| Harness standalone (`--from-dhpt`) | buildall | **~42s** | **Dernier recours** : source neuf hors `.dhps` (cf. arbre) |

**Strategie recommandee** :
1. **Vrai `.dhpt` + `-sousproject`/`-source`** pour la boucle de dev rapide (chirurgical, dans le contexte reel)
2. **Incremental complet** pour valider l'integration avant commit (demander confirmation)
3. **Buildall complet** uniquement si necessaire (demander confirmation + indiquer >45 min)
4. **Harness** seulement si le source n'appartient a aucun `.dhps` **et** qu'on ne peut pas demander (cf. arbre de decision en tete)

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

**Note** : `-user` est recommande mais pas toujours obligatoire. `compile_project.py` le resout automatiquement (`--user > util= du .dhpt > X_USER > USERNAME`, #235) ; passer `--user` pour forcer explicitement.

**Cas avec sous-projet** (compile uniquement les fichiers du sous-projet) :

> **Piege [communs]** : `-sousproject` ne recompile PAS les fichiers des groupes `[communs]` du .dhpt parent (ex: `gtpmficsql.dhsp`, `gttcficsql.dhsp`). Si ces fichiers ont ete modifies, lancer un `build` sur le projet principal ou les ajouter temporairement dans `[fichiers]` du sous-projet.

> **Piege surcharge -- viser le nom STANDARD, pas le nom `u` (#224/#308).** Une `.dhps` de
> surcharge (`<base>u.dhps`) n'est **jamais** ciblable directement par `-sousproject` : la
> regle **PROJ17** (managing-diva-projects) l'exclut de `[sousprojets]`, et xwin7 repond
> `Sous projet <base>u.dhps inexistant dans le projet`. Pour la compiler en cible, passer le
> **nom STANDARD sans `u`** : `-sousproject "<base>.dhps"` -- xwin7 resout le sous-projet
> standard et **applique la surcharge automatiquement**. **Verifie sur un vrai projet** :
> un `buildall` cible sur le nom standard a compile les fichiers **de la surcharge**
> (`<base>u.dhsf` et les sources du `<base>u.dhps`), lus depuis la zone specifique, objets
> ecrits dans `repobjetsurcharge`, `Erreur(s)=0`.
>
> **Corollaire #308** : s'il n'existe **aucun** sous-projet standard a cibler (surcharge sans
> contrepartie standard dans `[sousprojets]`), `-sousproject` est **inoperant pour les deux
> noms** -> se rabattre sur `buildall` global (le cout cache de PROJ17), ou sur un harness
> `--from-dhpt` si `buildall` est lui-meme bloque (cf. #200).

> **Piege changement dictionnaire -> buildall obligatoire** : apres
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
>
> **Build global bloque par des fichiers tiers casses (#200).** Si un `buildall` du `.dhpt`
> parent echoue sur des fichiers **hors de ta modif** (source standard absente, erreur de
> syntaxe dans un module tiers...), il n'invalide **pas** ta modif. Valider **uniquement**
> ton fichier en chirurgical `-sousproject <dhps> -source <basename>` ; si le sous-projet
> lui-meme est inatteignable (surcharge sans cible standard, cf. #308), passer par un
> harness `--from-dhpt`. Ne pas conclure « ma modif casse le build » sur un echec tiers.

```powershell
C:\divalto\sys\xwin7.exe -action build `
    -project $Projet -sousproject $SousProjet -source $FichierSourceBasename `
    -profile $Profil -output $LogFile -outputall | Out-Null
```

**Utilisateur** : `compile_project.py` résout l'utilisateur dans l'ordre **`--user` > `util=` du `.dhpt` > `X_USER` > `USERNAME`** (#235) — il lit désormais le champ `util="..."` déclaré dans le `.dhpt` (avant de tomber sur le `USERNAME` Windows, source fréquente de compils sous le mauvais utilisateur Harmony), et **avertit** si `--user` contredit ce `util=`. Sans user résolu, xwin7 peut crasher (ExitCode -805306369).

> **Discipline d'environnement (crucial — #161/#345/#196).** La compilation résout les **sources** via l'**environnement / implicite actif** du poste, **pas** via `--project` seul. Un environnement qui ne correspond pas au projet compile silencieusement des **objets faux** (sources d'une autre branche — #345) ou échoue sur « fichier/module absent » alors que le fichier **existe** (#161). **Avant de compiler**, valider que l'environnement/implicite actif correspond au workspace du `.dhpt` : c'est le rôle du skill **`understanding-integrator-workspace`** (identification du fichier implicite + contrôle de cohérence implicite ↔ `.dhpt`, de façon générique). Ce skill **ne charge pas** l'environnement (c'est l'outillage du poste) — xwin7 doit tourner **dans l'environnement déjà chargé**, sinon il peut se bloquer sur un dialogue de démarrage et produire des erreurs « Module absent » en cascade (#196 ; ces fausses erreurs sont bloquées depuis, cf. le verdict « faux positif mauvais implicite »).

### Etape 4 -- Analyser le rapport

```bash
py .claude/skills/compiling-diva-projects/scripts/parse_compilation.py \
    --path "chemin/rapport.txt"
```

Si `success: true` → compilation reussie, possibilite de lancer la synchro SQL.
Si `success: false` → corriger les erreurs et recompiler.

---

## Quitus (compilation de livraison)

> Distinct de la **boucle de compilation de dev** (sections ci-dessus). Le **quitus**
> est une passe de **livraison / pre-prod** : il (re)compile l'ensemble des `.dhpt`
> puis lance un **controle de coherence**.

> **Disponibilite** : `quitus.bat` / `quitus.dhop` ne fait **PAS partie du package
> Divalto de base** -- c'est un outil des **PowerTools**, telecharge separement. Un
> partenaire peut donc **ne pas l'avoir** : verifier sa presence avant de s'appuyer
> dessus (a defaut, le controle de coherence se fait autrement / manuellement).

`quitus.bat` (PowerTools) orchestre :
1. la compilation de **tous les `.dhpt`** du perimetre ;
2. si 0 erreur, l'ouverture de l'ERP via `xrtdiva.exe quitus.dhop`, qui **controle la
   coherence objets <-> sources** (via horodatages) -- il detecte notamment le piege
   **recompilation d'un standard APRES une surcharge** (la surcharge devient obsolete).

**Caracteristiques** :
- **Interactif** : `quitus.bat` lit des choix `set /p` (R/C/A) -> **non pilotable en
  mode non-interactif**. Ne pas tenter de l'automatiser aveuglement.
- **Resultats** : lire les fichiers **`quitus*.txt`** produits (le rapport n'est pas
  sur stdout).

> **Piege -- automatiser un `.bat` interactif par pipe stdin** : `echo R | quitus*.bat`
> peut **boucler a l'infini**. Un `pause` lit la **console (CON)**, pas le pipe ; une
> boucle `set /p` rappelee apres `pause` ne consomme donc jamais le pipe (EOF) ->
> recursion jusqu'au stack overflow cmd. Si vous devez piper, fournir **deux** entrees
> (`(echo R & echo A)`) pour que le second `set /p` declenche la sortie ; mieux : si
> vous **possedez** le `.bat`, remplacer `pause` par `timeout /T 0 /NOBREAK >nul` ou
> court-circuiter l'interactivite par une variable d'environnement.

La **preparation de la livraison** elle-meme (mise en pack, reset de repertoires,
filtrage des surcharges, zip...) depend du processus **propre a chaque projet /
integrateur** et n'est pas couverte ici.

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

> **Deux formats réels** : le `buildall` complet produit ce résumé français `Erreur(s)=…`. Le **`build` incrémental** ne le produit **pas** — il n'a que l'en-tête **`[TOTAL_ERRORS]N`** (+ lignes `[INFO]`/`[WARNING]`/`[ERROR]`). `parse_compilation.py` traite `[TOTAL_ERRORS]` comme résumé de **1re classe**.

> **Verdict = succès SEULEMENT si TOUT** : un résumé dit **0 erreur** (`[TOTAL_ERRORS]0` ou `Erreur(s)=0`), **ET** aucune ligne `[ERROR]`, **ET** aucune erreur **hors compilation** (`N ERREUR(S) autre(s)` / `absent ou inaccessible. Code=` → souvent un **mauvais implicite actif**, #310), **ET** **pas d'interruption/abandon** (`Compilation interrompue` / `Construction du projet arrêtée` / `Fin anormale` → `build_incomplet:true`, #236). Un build **interrompu** affiche `Erreur(s) 0` mais les objets **ne sont pas à jour** → **jamais un succès**.

> **« Le projet est à jour, aucune compilation à effectuer »** : ce **n'est pas un échec** en soi (build incrémental sans rien à recompiler). **MAIS** s'il s'accompagne de `N ERREUR(S) autre(s)` / `absent … Code=0x14` (sources non résolues → **mauvais implicite**), c'est un **faux positif** que `parse_compilation.py` bloque désormais (`success:false`, cf. #310). Un « à jour » **propre** reste `success:true, up_to_date:true`.

### Erreurs avec contexte

Les erreurs apparaissent dans le rapport avec la ligne precedente contenant le nom du fichier source. Le script `parse_compilation.py` extrait automatiquement :
- Le message d'erreur
- Le contexte (ligne precedente)
- Le fichier source (si identifiable)

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `generate_harness.py` | Genere un harness standalone (dernier recours) qui **emprunte** sa config a un `.dhpt` reel | --from-dhpt --source\|--sources --output-dir [--profile] [--with-zdiva] | JSON (dhpt, dhps, **borrowed_profile**, next, ...) |
| `compile_project.py` | Compile un projet reel (.dhpt) via xwin7 (gere le piege d'encodage du profil accentue). **Valide le profil** contre le .dhpt, **delegue le verdict** a `parse_compilation.py` (regle unique : `[TOTAL_ERRORS]` en 1re classe, refus du succes sur `[ERROR]` / erreurs hors-compilation / interruption). | --project [--profile --log-path] [--list-profiles] [--action build\|buildall] [--user] [--sousproject] [--source] [--xwin7-path] [--ps1-dir] [--no-execute] | JSON (ps1_script, log_file, exit_code, success, up_to_date, summary, ...) |
| `parse_compilation.py` | Parse rapport build/buildall | --path fichier.txt [--check-outputs] [--errors-only] [--dhsf-base-dir] | JSON (success, summary, errors, warnings) |

**generate_harness.py** (dernier recours -- cf. arbre de decision) :
- `--from-dhpt` **(obligatoire)** : `.dhpt` reel du workspace dont on **emprunte** la config (profil, implicite, util, progexec, cheminbases). Aucune valeur poste en dur. Typiquement celui identifie par `understanding-integrator-workspace`.
- `--profile` : nom du profil a emprunter si `--from-dhpt` en declare **plusieurs** (sinon echec listant les profils). Un seul profil -> emprunte d'office.
- `--source` / `--sources` : un ou plusieurs fichiers .dhsp/.dhsq a compiler isolement.
- `--with-zdiva` : inclure zdiva.dhsp dans les includes.
- **Ne compile pas** : retourne `borrowed_profile` (a repasser a `compile_project.py --profile`) et `next` (commande prete). Pas de `[communs]` (source isole ; un source qui en a besoin n'est pas isolable -> vrai `.dhpt`).
- Exit codes : 0 = succes, 1 = erreur utilisateur (source/`.dhpt` introuvable, profil ambigu/absent, implicite manquant), 2 = erreur interne

**compile_project.py** :
- Cas d'usage : compiler un projet **reel** (.dhpt) -- typiquement un projet de surcharge integrateur. Pas pour les harnesses standalone (utiliser `generate_harness.py` pour ca).
- **Critique** : adresse le piege d'encodage -- passer `-profile "developpement"` (accent) directement depuis PowerShell echoue. Ce script genere automatiquement un `.ps1` en ISO-8859-1 + CRLF qui contient le profil litteral, puis l'execute via l'operateur d'appel `powershell -NoProfile -Command "& '<ps1>'"` (**pas** `-ExecutionPolicy Bypass -File`, bloque/signale par GPO ou EDR sur poste verrouille -- **#217**). xwin7 recoit alors l'octet `0xe9` natif et matche correctement.
- `--project` : chemin absolu du `.dhpt`
- `--profile` : nom du profil (peut contenir accent)
- `--log-path` : chemin du log que xwin7 doit produire
- `--action` : `build` (defaut, incremental) ou `buildall` (complet)
- `--sousproject`, `--source` : couplage `-sousproject`/`-source` pour compilation chirurgicale
- `--user` : resolution `--user XX > util= du .dhpt > X_USER > USERNAME` (#235)
- `--list-profiles` : liste les profils declares dans le `.dhpt` (lecture seule) puis sort — a faire avant de choisir `--profile`
- `--no-execute` : genere uniquement le .ps1 (debug, exit 3)
- **Verdict délégué à `parse_compilation.py`** (source UNIQUE) : après attente du log (race #16), applique la même règle de verdict que le parser — `[TOTAL_ERRORS]` en 1re classe, **refus du succès** sur `[ERROR]` / erreurs hors-compilation (#310 « mauvais implicite ») / interruption-abandon (#236 → `build_incomplet`). **Ne fait plus le faux positif** sur un « à jour » accompagné de `N ERREUR(S) autre(s)`. Sortie forcée UTF-8.
- Exit codes : 0 = compilation reussie, 1 = erreurs ou input invalide, 2 = erreur interne, 3 = no-execute

**parse_compilation.py** :
- `--errors-only` : ne retourne que les erreurs (pas les warnings)
- `--check-outputs` : liste de fichiers compiles attendus (.dhop, .dhoq). Verifie existence ET taille >= 2048B (1024B = stub echec)
- **Verdict robuste** : `[TOTAL_ERRORS]` en résumé de **1re classe** (format `build` incrémental) ; refuse le succès si `[ERROR]`, erreurs hors-compilation (`N ERREUR(S) autre(s)` / `absent … Code=`, **#310**) ou interruption/abandon (`Compilation interrompue` / `Construction du projet arrêtée` / `Fin anormale`, **#236** → `build_incomplet:true`). Champs de sortie additionnels : `build_incomplet`, `other_errors`, `up_to_date`, `log_vide` (log vraiment vide -- **seul** etat ou `--check-outputs` peut rattraper le verdict), `summary_absent` (aucun resume reconnu ; `summary.errors` vaut alors `-1` = compteur **inconnu**, a ne jamais interpreter comme un etat).
- `--dhsf-base-dir <dir>` : sur une erreur **« Objet en dehors de la clip grille »** (masque),
  parse le `.dhsf` cible et **tranche la cause** que le message xwin7 ne dit pas : saturation
  **X** (`max_X > nb_col*4`) ou **Y** (`max_Y > nb_lig*14`), avec la page et un conseil.
  Sans l'option, l'erreur est signalee mais la cause reste `unknown`.
- Log vide = echec (xwin7 ecrit toujours un resume quand il termine normalement)
- Sortie **UTF-8** (les accents des messages `[ERROR]`/`[WARNING]` ne cassent plus un `json.loads(utf-8)` appelant)
- Exit codes : 0 = compilation reussie, 1 = erreurs / build incomplet, 2 = rapport illisible

---

## Tests

Les 3 scripts ont une suite de tests **executable**, sans xwin7 ni poste Divalto
(fixtures de logs reels, `.dhpt` modeles fabriques en temporaire, `--no-execute`) :

```
py .claude/skills/compiling-diva-projects/tests/run_all.py
```

A lancer apres toute modification d'un script du skill. Detail des suites et des
fixtures : [tests/README.md](tests/README.md).

---

## References

- [Syntaxe xwin7.exe](reference/xwin7-syntax.md) -- parametres, actions, encodage PS1
- [Erreurs courantes](reference/compilation-errors.md) -- format rapport, erreurs/solutions, prerequis
