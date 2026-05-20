# Skills DIVA -- Guide d'installation

Skills Claude Code pour la generation et validation de code DIVA (ERP Divalto Infinity X.13).

---

## Pour Claude Code

Si tu lis ce fichier, commence par verifier si l'installation a deja ete effectuee :
verifie si le marqueur `diva-skills:no-direct-script-call` est present dans
`~/.claude/CLAUDE.md`. S'il est absent, execute `py install.py` maintenant
avant toute autre action.

---

## Prerequis

| Outil | Version | Obligatoire | Installation |
|-------|---------|-------------|--------------|
| [Claude Code](https://claude.ai/code) | Derniere version | Oui | Voir site officiel |
| Python (launcher `py`) | 3.14+ | Oui | https://www.python.org/downloads/ |
| Jinja2 | 3.1+ | Oui | `py -m pip install Jinja2` |
| MCP `diva-mcp` (Neo4j X.12 advisory) | -- | **Non** | Config `.mcp.json` -- token fourni par Stephane sur demande. Sans ce MCP, le skill `analyzing-diva-request` bascule automatiquement en mode "verification X.13 directe" |
| MCP Playwright | Derniere | Si `testing-erp` utilise | `npx @playwright/mcp@latest` |

> **Important** : utiliser le launcher `py` (pas `python` ni `python3`).

---

## Prerequis

| Condition | Detail |
|-----------|--------|
| `.claude/` | Doit exister dans le workspace cible (cree par Claude Code au premier lancement) |
| `CLAUDE.md` | Doit exister a la racine du workspace cible (le script propose de le creer si absent) |

## Installation

1. Decompresser l'archive dans un dossier temporaire
2. Ouvrir un terminal dans le dossier decompresse
3. Executer `py install.py`
4. Le script propose le repertoire courant comme chemin d'installation -- taper un autre chemin si necessaire
5. Confirmer l'installation

Le script :
- Supprime automatiquement l'ancienne version des skills si elle existe
- Copie les skills dans `<chemin>/.claude/skills/`
- Installe un hook de protection empechant Claude de modifier les skills
- Depose `4PRINCIPLES.md` a la racine du workspace (reference canonique des 4 regles de qualite, non ecrase s'il existe deja)
- Injecte les regles DIVA dans `<chemin>/CLAUDE.md`

> **Option** : `py install.py --oui` pour passer les confirmations (usage scripte).

Structure attendue apres installation :

```
votre-workspace/
├── CLAUDE.md
└── .claude/
    ├── settings.json          (hooks de protection)
    ├── hooks/
    │   └── protect_skills.py  (bloque Edit/Write sur skills/)
    └── skills/
        ├── naming-diva-entities/
        ├── generating-recordsql/
        ├── generating-objet-metier/
        ├── generating-zoom-sql/
        ├── creating-diva-entity/
        ├── modifying-diva-entity/
        ├── writing-diva-files/
        ├── writing-isam-files/
        ├── reading-isam-files/
        ├── linting-diva-code/
        ├── managing-diva-dictionaries/
        ├── managing-diva-projects/
        ├── compiling-diva-projects/
        ├── syncing-diva-sql/
        ├── manipulating-dhsf-screens/
        ├── testing-erp/
        ├── coding-diva-advanced/
        ├── parsing-diva-request/
        ├── querying-diva-graph/
        ├── searching-erp-sources/
        ├── building-preaction-report/
        └── analyzing-diva-request/
```

---

## Skills disponibles

### Pipeline de creation d'entite

| Skill | Role |
|-------|------|
| `creating-diva-entity` | **Point d'entree principal** : cree une entite metier complete (RecordSql + Module Check + Zoom SQL + alias) en une seule operation |
| `naming-diva-entities` | Calcule les tokens de nommage (prefixes, noms de fichiers, instances) pour un domaine/entite/table |
| `generating-recordsql` | Genere le fichier RecordSql (.dhsq) -- couche d'acces SQL |
| `generating-objet-metier` | Genere le Module Check (.dhsp) -- couche objet metier |
| `generating-zoom-sql` | Genere le Zoom SQL (.dhsp) -- interface utilisateur CRUD |

### Validation et qualite

| Skill | Role |
|-------|------|
| `linting-diva-code` | Analyse un fichier DIVA et detecte les anti-patterns (~80 regles) |
| `writing-diva-files` | Verifie et corrige l'encodage des fichiers (ISO-8859-1 + CRLF) |

### Gestion de projet

| Skill | Role |
|-------|------|
| `managing-diva-dictionaries` | Ajoute une table dans un dictionnaire .dhsd (5 zones obligatoires) |
| `managing-diva-projects` | Cree ou modifie les fichiers projet .dhpt et .dhps |
| `compiling-diva-projects` | Lance la compilation xwin7 et interprete le rapport d'erreurs |
| `syncing-diva-sql` | Synchronise la base SQL Server apres compilation |
| `manipulating-dhsf-screens` | Parse, genere et modifie les masques ecran .dhsf (zoom, CRUD, simple) |

### Reference

| Skill | Role |
|-------|------|
| `coding-diva-advanced` | Reference des patterns avances : HTTP/REST, JSON/XML, .NET, surcharge, tunnels |

### Analyse pre-action (UC-100 -- nouveau)

Quand vous recevez une user story ou un ticket myService et ne savez pas par ou commencer, invoquez `analyzing-diva-request` en collant le texte de la demande.

| Skill | Role |
|-------|------|
| `analyzing-diva-request` | **Point d'entree principal** : orchestre l'analyse pre-action en 5 checkpoints -- produit un rapport markdown d'orientation (`output/UC100-<slug>-<date>.md`) |
| `parsing-diva-request` | Phase 1 : structure la demande en JSON canonique (type, acteurs, donnees, domaine pressenti, keywords) |
| `querying-diva-graph` | Phase 2 : interroge le graphe Neo4j `diva-mcp` (advisory X.12) si disponible. Optionnel -- degradation automatique en mode direct si MCP absent |
| `searching-erp-sources` | Phase 3 : verifie dans le code X.13 local (`{CHEMIN_ERP_STANDARD}`) et extrait les snippets -- source de verite |
| `building-preaction-report` | Phase 4 : assemble le rapport final (markdown 7 sections + JSON de metriques) |

Le rapport contient : exemples de code similaires (`fichier:ligne` verifiable), fonctions DIVA utiles, etude d'impact, propositions d'action, pistes complementaires, points d'attention.

---

## Mode de collaboration

Les skills fonctionnent en **mode collaboratif** : Claude ne fait jamais tout d'un trait.
A chaque etape significative, Claude :

1. **Execute** l'action (generation, modification, compilation...)
2. **Verifie** le resultat avec ses controles automatiques
3. **Explique** ce qu'il a fait, ses choix, et les resultats
4. **Attend votre validation** avant de passer a l'etape suivante

Concretement, pour une creation d'entite (skill `creating-diva-entity`), il y a **10 points d'arret** :
nommage, generation des sources, coherence inter-fichiers, dictionnaire, integration ERP,
compilation, sous-projet, synchro SQL, zoom des zooms, menu domaine.

Vous gardez le controle a chaque etape. Si quelque chose ne convient pas,
dites-le a Claude -- il corrigera et re-presentera le checkpoint.

**Avant chaque etape significative**, Claude doit aussi :

- **Enoncer ses hypotheses** quand un parametre est ambigu (plutot que choisir silencieusement)
- **Enoncer le critere de succes** attendu (lint OK, compil 0 erreur, synchro OK)
- **Rester chirurgical** sur l'existant : ne modifier que ce qui est demande, ne pas reformater

Ces 4 regles -- hypotheses explicites, minimum DIVA viable, modifications chirurgicales, critere de succes --
sont rappelees dans votre `CLAUDE.md` apres installation. Si Claude devie de l'une d'elles, dites-le lui :
c'est aussi une entree RETEX (`BUG-SKILL` ou `SUGGESTION`).

---

## Utilisation typique

Pour creer une nouvelle entite metier DIVA, invoquer le skill `creating-diva-entity` en precisant :

- **Domaine** : ex. `Retail`, `Production`, `Comptabilite`
- **Entite** : nom en PascalCase, ex. `FamRglt`
- **Table SQL** : ex. `RtlFamRglt`
- **Champ cle** : ex. `RgltFam`
- **Description** : ex. `Famille de reglement`

Le skill orchestre la generation etape par etape, avec validation a chaque checkpoint.

---

## Retour d'experience (RETEX)

Un fichier `RETEX-collaborateur.md` est fourni avec cette distribution.
C'est un **journal structure** de votre experience avec les skills.

Le fichier `RETEX-skills.md` est installe automatiquement a la racine de votre workspace.

**Claude remplit le RETEX au fur et a mesure**, pas en fin de session. Les declencheurs
sont definis dans votre `CLAUDE.md` (bloc `diva-skills:rules`). En pratique, vous devez
voir une nouvelle entree apparaitre dans `RETEX-skills.md` :

- a la fin de chaque invocation de skill (entree "OK" si tout s'est bien passe, "KO" sinon) ;
- des qu'une friction est rencontree (script qui echoue, doc ambigue, comportement inattendu) ;
- a chaque checkpoint ou vous avez pris une decision metier non triviale ;
- a chaque fois qu'une idee d'amelioration emerge.

Chaque entree porte un identifiant unique (R-001, R-002...), une categorie
(`BUG-SKILL`, `BUG-DOC`, `ENV`, `CLAUDE-TOOL`, `SUGGESTION`) et une severite.
Si Claude oublie, rappelez-lui : "ajoute l'entree RETEX". Il ne doit pas demander
l'autorisation pour ecrire dans `RETEX-skills.md`.

Periodiquement, **envoyez ce fichier a Stephane Castelain** pour enrichir les skills.
Votre retour d'experience permet d'identifier les frictions, corriger les bugs,
et ameliorer les templates de generation.

La version des skills installes est indiquee dans le champ `Version skills` du RETEX.
Cela permet de savoir rapidement si un probleme signale a deja ete corrige.

---

## Mode de fonctionnement des scripts

Chaque skill embarque ses propres scripts Python (aucune dependance externe entre skills).
Les scripts acceptent des parametres en ligne de commande et produisent du JSON en sortie.

> **Important** : dans Claude Code, toujours invoquer les skills via l'outil `Skill`.
> Ne pas appeler les scripts directement -- c'est reserve aux tests CLI hors Claude.

Exemple de test CLI hors Claude (skill `generating-recordsql`) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine Retail --entite FamRglt --table RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement" \
    --output "output/rtlrsfamrglt.dhsq"
```
