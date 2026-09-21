---
name: pushing-retex-to-github
description: >
  Pousse automatiquement les entrees R-NNN d'un fichier RETEX-skills.md vers un depot
  GitHub sous forme d'issues. Parse les entrees, deduit les labels (categorie + severite),
  formate le corps de l'issue, et utilise `gh issue create` (GitHub CLI). Idempotent via
  un cache local de tracking (.retex-pushed.json) : ne recree pas une issue deja poussee,
  commente l'issue existante si le contenu de l'entree a change. Mode degrade si `gh`
  n'est pas installe ou non authentifie : log sans bloquer. A utiliser pour synchroniser
  son journal RETEX local avec un canal centralise (ex : repo divalto/divalto-ia-devkit).
  Le skill est invoque (a) automatiquement par le hook `push_retex_to_github.py` apres
  chaque edition de RETEX-skills.md, ou (b) manuellement pour pousser explicitement /
  re-synchroniser / faire un backfill.
---

# pushing-retex-to-github

## Contenu

- [Utilisation rapide](#utilisation-rapide)
- [Configuration initiale](#configuration-initiale)
- [Comment ca marche](#comment-ca-marche)
- [Scripts disponibles](#scripts-disponibles)
- [Mode degrade](#mode-degrade)
- [References](#references)

---

## Utilisation rapide

### Premiere fois -- configurer le repo cible

```powershell
py plugin/skills/pushing-retex-to-github/scripts/init_config.py `
    --retex-file "retex/RETEX-skills.md" `
    --repo "divalto/divalto-ia-devkit"
```

Cree `retex/.retex-github.json` (config) et `retex/.retex-pushed.json` (tracking avec
toutes les entrees existantes marquees comme "deja poussees" -- pas de backfill).

### Pousser les nouvelles entrees a la main

```powershell
py plugin/skills/pushing-retex-to-github/scripts/push_new_entries.py `
    --retex-file "retex/RETEX-skills.md"
```

Detecte les R-NNN absents du tracking, cree une issue GitHub par entree, met a jour le
tracking. Sortie JSON sur stdout : `{"pushed": [...], "skipped": [...], "errors": [...]}`.

> **Toujours passer `--retex-file` explicitement** vers le RETEX du workspace courant. Sur
> un poste multi-projets, un glob large risque de selectionner le mauvais `RETEX-skills.md`.

### Pousser seulement certaines entrees (`--ids`)

```powershell
py plugin/skills/pushing-retex-to-github/scripts/push_new_entries.py `
    --retex-file "retex/RETEX-skills.md" --ids "R-021,R-022"
```

Restreint le push aux seuls IDs listes. Utile quand le collaborateur demande « pousse R-021 »
alors que d'autres entrees non trackees existent : **sans** filtre, elles partiraient toutes.
Les entrees hors filtre apparaissent en `skipped` (reason `hors-filtre-ids`) et restent **non
trackees** -- elles partiront a un prochain appel sans `--ids`. (Accepte `R-021,R-022`, `21 22`, etc.)

### Backfill (pousser TOUTES les entrees existantes)

```powershell
py plugin/skills/pushing-retex-to-github/scripts/push_new_entries.py `
    --retex-file "retex/RETEX-skills.md" --backfill --yes-i-want-to-push-everything
```

> CHECKPOINT -- Ne lancer `--backfill` qu'apres validation explicite du collaborateur.
> Risque de pollution massive du repo si lance par erreur sur un fichier RETEX historique.

---

## Configuration initiale

### Prerequis cote partenaire

1. **Installer GitHub CLI** : voir [reference/setup-gh-cli.md](reference/setup-gh-cli.md)
2. **S'authentifier** : `gh auth login` (via navigateur ou token)
3. **Avoir un acces write** au repo cible (ex `divalto/divalto-ia-devkit`)

### Fichiers de configuration

| Fichier | Role | Versionne ? |
|---------|------|-------------|
| `retex/.retex-github.json` | Repo cible, options de labels | NON (gitignore) |
| `retex/.retex-pushed.json` | Tracking des R-NNN deja pousses (R-NNN -> issue#, hash contenu) | NON (gitignore) |
| `retex/.retex-push.log` | Log d'execution (succes / erreurs / renumerotations) | NON (gitignore) |
| `retex/.retex-push.lock` | Verrou : un seul push a la fois. Cree et supprime par le push ; repris automatiquement au-dela de 5 min (process tue) | NON (gitignore) |

> **Resolution en cascade** (push) : `--config` explicite -> `.retex-github.json` **local**
> (a cote du RETEX) -> `~/.claude/.retex-github.json` **global** (partage entre workspaces,
> cree via `init_config.py --global`). Le **tracking `.retex-pushed.json` reste TOUJOURS
> local** : la numerotation R-NNN est propre a chaque workspace ; un tracking partage
> creerait des collisions d'ID. Le local surcharge toujours le global.

### Format de .retex-github.json

```json
{
  "repo": "divalto/divalto-ia-devkit",
  "labels_default": ["retex"],
  "labels_categorie": {
    "BUG-SKILL": "bug-skill",
    "BUG-DOC":   "bug-doc",
    "SUGGESTION": "suggestion",
    "ENV":        "env",
    "CLAUDE-TOOL": "claude-tool"
  },
  "labels_severite": {
    "CRITIQUE": "severite:critique",
    "HAUTE":    "severite:haute",
    "MOYENNE":  "severite:moyenne",
    "BASSE":    "severite:basse",
    "INFO":     "severite:info"
  }
}
```

---

## Comment ca marche

### Detection automatique (via hook)

Quand le hook `plugin/hooks/push_retex_to_github.py` est enregistre (PostToolUse sur
Edit/Write), chaque modification de `RETEX-skills.md` declenche en arriere-plan :

```
Edit RETEX-skills.md
   v
Hook PostToolUse (non bloquant)
   v
py push_new_entries.py --retex-file <path>
   v
Parse les R-NNN
   v
Pour chaque R-NNN absent du tracking ou avec hash modifie :
   - Nouveau -> gh issue create
   - Modifie -> gh issue comment (sur l'issue deja liee)
   v
Update retex/.retex-pushed.json
   v
Log dans retex/.retex-push.log
```

### Mapping RETEX -> Issue GitHub

| Champ RETEX | Destination GitHub |
|-------------|-------------------|
| `### R-NNN -- date -- titre` | Title : `[R-NNN] titre` |
| `Categorie` | Label : `bug-skill` / `bug-doc` / `suggestion` / `env` / `claude-tool` |
| `Severite` | Label : `severite:critique` / `haute` / `moyenne` / `basse` / `info` |
| `Skill(s)` | Mentionne dans le body, premier champ |
| `Resultat`, `Description`, `Reproduction`, `Contournement`, `Suggestion` | Sections du body |

Voir [reference/issue-format.md](reference/issue-format.md) pour le template exact.

### Idempotence

`retex/.retex-pushed.json` enregistre pour chaque R-NNN :
- Numero de l'issue GitHub creee
- Hash SHA-1 du contenu de l'entree

Sur un nouveau push :
- R-NNN absent du tracking -> `gh issue create`
- R-NNN present + hash inchange -> skip
- R-NNN present + hash modifie -> `gh issue comment` sur l'issue existante avec la nouvelle version

Le hash ne porte que les **8 champs** de l'entree (`Skill(s)`, `Categorie`, `Severite`,
`Resultat`, `Description`, `Reproduction`, `Contournement`, `Suggestion`). L'**ID, la date
et le titre en sont exclus** : on peut donc corriger un titre ou une date sans declencher
un faux commentaire sur l'issue.

### Un seul push a la fois

Le hook lance un push **detache** a chaque ecriture du `RETEX-skills.md`. Ecrire une entree
en deux editions successives lancait donc deux pushes simultanes, qui lisaient le meme
tracking vide et creaient **chacun leur issue**.

Le push prend desormais un verrou (`.retex-push.lock`) avant de lire le tracking. Un second
push concurrent abandonne sans rien faire -- ses entrees partent avec le premier, ou au
prochain appel. Un verrou plus vieux que 5 minutes est considere abandonne et repris, pour
qu'un process tue ne bloque pas tous les pushes suivants.

### Unicite des R-NNN, garantie avant l'envoi

La regle « chaque entree porte un identifiant unique » est enoncee dans le `RETEX-skills.md`
livre, mais rien ne la faisait respecter. Or deux entrees sous un meme numero se partagent
**une seule case de tracking** : chacune y trouve le hash de l'autre, conclut « modifiee »
et commente l'issue de l'autre -- a chaque passage, sans jamais converger.

Le push detecte donc les numeros en double **avant tout appel GitHub** et donne un numero
libre aux entrees en trop, en reecrivant le `RETEX-skills.md` (ecriture atomique, jamais en
`--dry-run`). Ce qui part vers GitHub a donc toujours un numero unique.

**Ce que la reecriture ne touche pas.** Le fichier est le journal du collaborateur :
la seule chose qui change est l'identifiant de l'en-tete. L'encodage, les fins de
ligne et jusqu'a la derniere ligne vide sont rendus a l'identique -- verifie au
niveau octet par `tests/test_unicite_et_parsing.py`, qui compare le fichier avant et
apres et n'accepte qu'une seule difference.

**Qui garde le numero**, du plus sur au plus degrade :

1. une entree est deja suivie avec un numero d'issue -> on lit sur GitHub **tous les hash
   que l'issue connait** : celui de son corps d'abord, puis ceux de ses commentaires de
   mise a jour, du plus recent au plus ancien. La premiere correspondance garde le numero ;
2. lecture impossible, ou aucun hash connu ne correspond -> l'entree dont le hash est celui
   du tracking ;
3. aucune n'est poussee -> la premiere du fichier ; le choix est alors sans consequence.

> **Pourquoi les commentaires comptent.** Le corps d'une issue est un instantane fige a sa
> creation : une mise a jour n'ajoute qu'un commentaire, le corps ne bouge jamais. Ne lire
> que le corps faisait donc echouer l'arbitrage des qu'une entree avait ete modifiee une
> fois -- il se repliait alors **en silence** sur le tracking, c'est-a-dire sur la seule
> source que le ping-pong corrompt. Le corps garde la priorite : sur une issue abimee, ses
> commentaires portent les deux contenus, et c'est le corps qui dit ce que l'issue EST.

Les renumerotations apparaissent dans la sortie JSON (`renumerotations`) **et** dans le log :
le collaborateur a pu citer l'ancien numero ailleurs.

---

## Scripts disponibles

| Script | Role |
|--------|------|
| `init_config.py` | Initialise `.retex-github.json` + `.retex-pushed.json` (marque les entrees existantes comme deja poussees) |
| `parse_retex_entries.py` | Parse RETEX-skills.md -> liste de dicts `{id, date, titre, skills, categorie, severite, resultat, description, reproduction, contournement, suggestion, hash}` |
| `push_entry.py` | Pousse UNE entree (cree issue ou commente issue existante). Utilise `gh`. |
| `push_new_entries.py` | Wrapper : parse, filtre les nouveaux/modifies, appelle push_entry pour chacun, met a jour le tracking |

Tous les scripts utilisent `argparse`, sortent JSON sur stdout, et respectent les exit
codes : `0` succes, `1` erreur applicative, `2` erreur d'usage.

---

## Mode degrade

### gh non installe

```
Detect: `gh --version` echoue
Action: log "gh CLI absent. Voir reference/setup-gh-cli.md" dans .retex-push.log
        exit 0 (non bloquant), le hook ne fige pas l'edition de RETEX-skills.md
```

### gh non authentifie

```
Detect: `gh auth status` retourne exit != 0
Action: log "gh non authentifie. Lancer `gh auth login`" dans .retex-push.log
        exit 0 (non bloquant)
```

### Repo inaccessible

```
Detect: `gh issue create` echoue avec 403 / 404
Action: log l'erreur, marquer l'entree comme "pending" dans tracking
        Au prochain push, retry automatique
```

### Conflit de tracking

```
Detect: .retex-pushed.json contient R-NNN -> issue 42, mais l'issue 42 a ete fermee/supprimee
Action: re-create + warning dans log
```

---

## Symptomes courants (diagnostic)

Le push tourne en arriere-plan via le hook : s'il echoue, **rien ne le signale a l'ecran**
(le hook est non bloquant par conception). Pour diagnostiquer quand des RETEX
**n'apparaissent pas** en issues :

| Symptome | Verifier | Cause / action |
|----------|----------|----------------|
| RETEX ecrit mais rien sur GitHub | Le hook a-t-il affiche "push non configure" ? Sinon, `.retex-github.json` existe-t-il (local ou `~/.claude/`) ? | Si config absente, le hook **previent desormais** (message non bloquant, pre-check synchrone) -> lancer `init_config.py`. Les RETEX ne sont **pas perdus** (ils restent dans `RETEX-skills.md`). |
| Configure mais d'anciennes entrees ne partent pas | `.retex-pushed.json` les marque-t-il deja ? | `init_config.py` marque l'existant comme "deja pousse" -> pour les entrees ecrites **avant** la config : `--backfill --yes-i-want-to-push-everything`. |
| Echec silencieux du hook | `retex/.retex-push.log` | Le log enregistre chaque tentative (succes / abort / erreur gh / `WARN parsing`). Source de verite du hook. |
| `gh` "label not found" | La note `(...)` de Categorie contenait-elle une virgule ? | Corrige (la note est retiree avant de deriver les labels). Sinon : `gh label create <nom>`. |
| En-tete `### R-NNN` ignore | `.retex-push.log` ligne `WARN parsing` | Un en-tete sans date `-- AAAA-MM-JJ --` est signale et **non** pousse -> corriger le format. |
| Entree `Categorie=OK` jamais poussee | La categorie de l'entree est-elle `OK` ? | **Normal, pas une erreur** : une entree `OK` n'est pas poussee (skip `categorie-ok-non-poussable`) -- elle ne doit pas devenir une issue. |
| Issue creee mais **sans aucun label** | Le compte a-t-il le droit `triage`/`push` sur le repo ? | Un compte en lecture seule voit ses labels **ignores silencieusement** par GitHub. `push_entry.py` le signale (`warning` + champ `labels` reel). Categorie/severite restent lisibles dans le corps de l'issue. |

> Lancer le script **a la main** (`push_new_entries.py --retex-file …`) affiche le diagnostic
> directement ; le hook, lui, reste silencieux (par conception).

---

## References

- [reference/setup-gh-cli.md](reference/setup-gh-cli.md) -- Installation et authentification de GitHub CLI cote partenaire
- [reference/issue-format.md](reference/issue-format.md) -- Template exact du corps d'issue et conventions de titre / labels
