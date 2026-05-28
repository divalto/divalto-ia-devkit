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

### Backfill (pousser TOUTES les entrees existantes)

```powershell
py plugin/skills/pushing-retex-to-github/scripts/push_new_entries.py `
    --retex-file "retex/RETEX-skills.md" --backfill
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
| `retex/.retex-push.log` | Log d'execution (succes / erreurs) | NON (gitignore) |

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

## References

- [reference/setup-gh-cli.md](reference/setup-gh-cli.md) -- Installation et authentification de GitHub CLI cote partenaire
- [reference/issue-format.md](reference/issue-format.md) -- Template exact du corps d'issue et conventions de titre / labels
