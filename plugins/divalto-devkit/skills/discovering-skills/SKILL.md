---
name: discovering-skills
description: >
  Point d'entree du devkit DIVA. Aide le collaborateur a decouvrir les skills
  disponibles et leur portee : vue panoramique par workflow (analyse / creation
  / modification / fichiers / ISAM / validation / test-doc / reference), detail
  d'un skill precis, recherche par mot-cle, filtrage par workflow ou verbe. A
  utiliser quand le collaborateur demande "que peux-tu faire ?", "liste des
  skills", "explique-moi <X>", "quel skill pour faire Y ?". Porte aussi la
  **discipline d'invocation** du devkit DIVA : (1) la documentation des skills
  (`reference/*.md`) est la source autoritaire pour toute question de
  convention/regle/nommage/structure -- le filesystem n'est jamais source
  primaire ; (2) les skills DIVA sont prioritaires sur toute commande
  improvisee -- si un skill couvre l'operation, l'invoquer plutot que
  reproduire son resultat via `find` / `grep` / `cat`.
---

# Discovering Skills

## Contenu

- Utilisation
- Discipline d'invocation
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

## Discipline d'invocation

Ces deux regles encadrent l'usage de l'ensemble du devkit DIVA. Elles s'appliquent independamment des regles internes a chaque skill (P-A/P-B de `understanding-integrator-workspace`, 4PRINCIPLES, anti-patterns metier, etc.). Le `discovering-skills` est le **point d'entree** annonce du devkit -- il porte ces regles parce qu'elles concernent la **discipline d'invocation des skills**, pas un skill particulier.

### Regle 1 -- Documentation skill = source autoritaire pour les conventions

**Pour toute question de convention, regle, nommage, structure dans le perimetre DIVA, la source autoritaire est la documentation des skills (`reference/*.md`). Le filesystem n'est jamais source primaire -- au plus un cross-check de confirmation apres lecture de la doc.**

Ordre correct quand le collaborateur pose une question de convention/structure :

1. **`discovering-skills detail <skill-pertinent>`** -- identifier le skill qui couvre le sujet
2. **Lecture des references du skill** (`reference/*.md` listees dans le SKILL.md)
3. **Reponse appuyee sur la doc** -- avec citation des fichiers references
4. **(Optionnel) cross-check filesystem** pour confirmer un point particulier

Ordre erronne (a eviter) :

1. ~~`find` / `grep` / `ls` dans le filesystem pour deduire la convention~~ -> donne une reponse moins fiable
2. ~~Inference par symetrie/observation~~ -> peut etre un cas particulier, une coutume locale, ou une erreur historique
3. Reponse formulee sans appui sur la doc

**Pourquoi cette regle** : la doc skill est ecrite et revue. Le filesystem est un instantane de l'etat reel d'un workspace -- il peut contenir des conventions specifiques au partenaire, des erreurs heritees, des exceptions ponctuelles. Confondre les deux mene a des reponses qui semblent justes mais qui ne sont pas la regle generale.

**Exception unique** : quand un skill annonce explicitement que la verite vit dans un fichier source (ex: `a5tczoom.dhsp` comme catalogue de constantes pour `allocating-zoom-numbers`, ou `gtfdd.dhsd` pour le dictionnaire), c'est ce fichier qui est consulte -- mais via le skill qui le rend autoritaire, pas via un `cat` direct.

### Regle 2 -- Skills DIVA prioritaires sur toute commande improvisee

**Si un skill DIVA couvre l'operation demandee, l'invoquer -- pas de raccourci `find` / `grep` / `cat` qui simulerait l'operation. Les skills ne sont pas des suggestions optionnelles, ils sont la maniere canonique d'operer sur l'ERP DIVA.**

Examples concrets :

| Tache demandee | Raccourci tentant (a eviter) | Skill a invoquer |
|----------------|------------------------------|------------------|
| Trouver la version standard d'un `.dhsd` | `find /Developpements/Standard -name gtfdd.dhsd` | `understanding-integrator-workspace` (R-13) |
| Lister les zooms standards | `grep "C_ZOOM_" a5tczoom.dhsp` | `allocating-zoom-numbers` |
| Verifier l'encodage d'un `.dhsp` | `file <chemin>` | `writing-diva-files` (verification + correction) |
| Generer un fichier `.dhsq` | Copier-coller un template d'un autre RecordSql | `generating-recordsql` |
| Lire un fichier ISAM | `head -c 1000 fichier.dhfi \| od` | `reading-isam-files` |
| Modifier un masque `.dhsf` | Editer le bloc INI a la main | `manipulating-dhsf-screens` |

**Pourquoi cette regle** : les skills encapsulent (a) les conventions de la plateforme, (b) les protocoles de validation (`check_*`, `validate_*`), (c) les pieges connus catalogues par RETEX. Court-circuiter un skill par une commande improvisee = reproduire des operations sans les garde-fous. Le resultat peut sembler equivalent mais perd la coherence et la tracabilite.

**Quand cette regle ne s'applique pas** :

- Question hors perimetre DIVA (ex: question sur Git, Docker, Python pur).
- Operation explicitement non couverte par un skill et signalee comme telle (perimetre hors-scope documente dans le SKILL.md correspondant).
- Reflexe d'observation rapide sur le workspace (un `ls` pour voir le contenu d'un dossier) qui n'engage pas une operation metier.

Dans le doute : passer par `discovering-skills search <mots-cles>` pour verifier qu'aucun skill ne couvre la tache avant de la faire a la main.

### Application a Claude

Ces deux regles concernent **le comportement de Claude lors d'une session sur un workspace DIVA**. Elles ne demandent rien au collaborateur. Concretement :

- Avant toute reponse a une question de convention/structure : Claude consulte la doc du skill pertinent.
- Avant toute commande improvisee dans le perimetre DIVA : Claude verifie qu'un skill ne la couvre pas.
- En cas de doute : `discovering-skills` est le point d'entree pour la verification.

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
