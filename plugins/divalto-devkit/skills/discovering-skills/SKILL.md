---
name: discovering-skills
description: >
  Aide le collaborateur a decouvrir les skills DIVA disponibles et a comprendre
  leur portee. Fournit une vue panoramique (synthese des 31 skills classes par
  workflow : analyser / creer / modifier / manipuler fichiers / ISAM / valider /
  tester-documenter / reference), le detail d'un skill precis (description, quand
  l'utiliser, scripts, references, skills lies, prerequis, nombre de checkpoints),
  la recherche par mot-cle dans les descriptions et metadonnees, et le filtrage
  par workflow ou par verbe. A utiliser quand le collaborateur demande "que
  peux-tu faire ?", "liste les skills disponibles", "explique-moi le skill X",
  "quel skill pour faire Y ?", "montre les skills de creation / validation /
  analyse", ou toute formulation equivalente visant a explorer la boite a outils
  avant de lancer une tache.
---

# Discovering Skills

## Contenu

- Utilisation
- Modes du script query_catalog.py
- Exemples de reponses
- Catalog source de verite

---

## Utilisation

Ce skill est une **table des matieres interactive** des skills DIVA installes.
Il s'appuie sur un `catalog.json` embarque (regenere a chaque build de distribution).

**Regle** : ne pas lire directement le catalog.json dans le contexte Claude. Utiliser
`query_catalog.py` qui extrait uniquement le sous-ensemble pertinent.

Avant de lancer la commande, **reformuler la demande** pour choisir le mode :

| Demande type | Mode a utiliser |
|--------------|-----------------|
| "Que peux-tu faire ?", "Panorama", "Liste des skills" | `overview` |
| "Explique-moi <nom>", "Que fait <nom> ?" | `detail <nom>` |
| "Quel skill pour <action libre>", "Comment faire <X>" | `search <mots-cles>` |
| "Skills pour creer / analyser / valider / ..." | `workflow <id>` |
| "Tous les skills qui generent / lisent / ecrivent" | `verb <verbe>` |

---

## Modes du script query_catalog.py

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py <mode> [arguments]
```

### 1. overview

Panorama complet : chaque workflow avec la liste de ses skills (nom + summary court).
C'est la reponse type pour "que peux-tu faire ?".

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py overview
```

### 2. detail <nom>

Fiche complete d'un skill : description, quand l'utiliser, workflow, orchestrateur,
nombre de checkpoints, scripts, references, skills lies, prerequis.

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py detail creating-diva-entity
```

### 3. search <mots-cles>

Recherche insensible a la casse dans le nom, description, summary, scripts, skills lies.
Utile quand la demande est formulee en langage libre ("je veux ecrire un fichier ISAM").

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py search ISAM
py .claude/skills/discovering-skills/scripts/query_catalog.py search "masque ecran"
```

### 4. workflow <id>

Liste les skills d'un workflow. Ids disponibles : `analyze`, `create`, `modify`, `files`,
`isam`, `validate`, `test_doc`, `reference`.

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py workflow create
```

### 5. verb <verbe>

Liste les skills d'un verbe (1er segment du nom). Exemples : `generating`, `reading`,
`writing`, `managing`, `allocating`, `analyzing`.

```bash
py .claude/skills/discovering-skills/scripts/query_catalog.py verb generating
```

### Option --json

Tous les modes acceptent `--json` pour sortir au format machine (debug, chainage).
Par defaut la sortie est un texte markdown lisible.

---

## Exemples de reponses

### "que peux-tu faire ?"

Invoquer `overview`, puis resumer au collaborateur :

> Tu disposes de 31 skills DIVA organises en 8 workflows. Points d'entree principaux :
> creer une entite metier (`creating-diva-entity`), analyser une demande
> (`analyzing-diva-request`), modifier une entite (`modifying-diva-entity`),
> documenter un module (`documenting-erp`). [puis liste par workflow]

### "que fait creating-diva-entity ?"

Invoquer `detail creating-diva-entity`, puis presenter :

> `creating-diva-entity` est l'orchestrateur de creation d'entite metier.
> 11 checkpoints annonces : calcul des noms, generation des 3 fichiers source,
> validation croisee, dictionnaire, compilation, ISAM, menu. Coordonne 13 autres
> skills. Deux scripts : `generate_alias.py`, `cross_validate.py`. 8 fichiers de
> reference. Prerequis : Jinja2, diva-mcp (optionnel), xwin7.exe.

### "quel skill pour ajouter un champ ?"

Invoquer `search "ajout champ"` ou `search modifier`, puis proposer :

> Pour ajouter un champ a une entite existante : `modifying-diva-entity`
> (orchestrateur, 4 checkpoints). Met a jour le dictionnaire (.dhsd) avec
> recalcul des positions, le masque ecran (.dhsf), recompile et synchronise SQL.

---

## Catalog source de verite

Le catalog est genere par `scripts/build_catalog.py` a la racine du workspace
(cote architecte) et copie dans `reference/catalog.json` a chaque build de
distribution.

**Chez le collaborateur** : le catalog est fige au moment du build. Pour le
regenerer il faut re-installer une nouvelle version des skills via le zip.

**Champs par skill** :

| Champ | Signification |
|-------|---------------|
| `name` | Slug du skill |
| `description` | Description complete (frontmatter) |
| `summary` | Premiere phrase utile (1 ligne) |
| `when_to_use` | Phrase "A utiliser..." (sinon description) |
| `workflow` | Id du workflow (create, analyze, ...) |
| `verb` | 1er segment du nom |
| `is_orchestrator` | Le skill coordonne d'autres skills |
| `checkpoint_count` | Nombre de checkpoints annonces |
| `scripts` | Liste des scripts Python (hors `_*`) |
| `references` | Liste des fichiers reference/*.md |
| `related_skills` | Skills cites en backticks dans le body |
| `prerequisites` | Prerequis externes detectes (Jinja2, DhxIsam64, xwin7, ...) |

Le champ `related_skills` signifie "skills mentionnes", pas "skills appeles" :
pour un orchestrateur ce sont les skills coordonnes, pour un skill simple ce
sont des skills complementaires cites en reference.
