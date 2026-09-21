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

> **Deux methodes.** La methode **marketplace** (recommandee) installe le plugin `divalto-devkit`
> via l'interface de Claude Code. La methode **archive** (`install.py`, plus bas) reste disponible
> pour un deploiement manuel ou scripte.

### Methode 1 -- Marketplace (recommandee)

1. Ouvrir l'**interface graphique Plugins** de Claude Code.
2. **Add marketplace** -> coller l'URL du depot : `https://github.com/divalto/divalto-ia-devkit`
3. Installer le plugin **`divalto-devkit`** depuis la liste.
4. Initialiser le workspace avec la commande slash **`/divalto-devkit-init`** : elle execute `install.py`
   (injection du bloc de regles dans `CLAUDE.md`, depot de `4PRINCIPLES.md`, `CATALOG.md`, `RETEX-skills.md`
   a la racine du workspace).

> **Important** : la commande **`/plugin marketplace add <url>` n'est PAS disponible en mode conversation**
> -- elle renvoie « isn't available in this environment ». L'ajout d'une marketplace se fait **uniquement via
> l'interface graphique** Plugins decrite ci-dessus.

### Methode 2 -- Archive (`install.py`)

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
    └── skills/                (skills du devkit -- catalogue complet : skill discovering-skills)
```

> **Creer vos propres skills locaux.** Les skills ci-dessus sont distribues en **lecture seule** (le hook `protect_skills.py` bloque tout `Edit`/`Write` sous `.claude/skills/`). Pour ajouter **vos propres** skills, editables et non geres par le devkit, **prefixez leur nom par `workspace-`** (ex. `workspace-mon-outil`) : le hook les laisse passer.

---

## Skills disponibles

Le **catalogue complet et toujours a jour** est expose par le skill **`discovering-skills`** :
vue panoramique par workflow (analyse / creation / modification / fichiers / ISAM / validation /
test-doc / reference), detail d'un skill, recherche par mot-cle. Invoquez-le simplement --
par ex. « quels skills DIVA ? », « quel skill pour faire Y ? », « explique-moi <skill> ».
Reference statique equivalente : `CATALOG.md` (depose a la racine du workspace a l'installation).

### Analyse pre-action

Quand vous recevez une user story ou un ticket myService et ne savez pas par ou commencer, invoquez `analyzing-diva-request` en collant le texte de la demande.

Le rapport contient : exemples de code similaires (`fichier:ligne` verifiable), fonctions DIVA utiles, etude d'impact, propositions d'action, pistes complementaires, points d'attention.

---

## Mode de collaboration

Les skills fonctionnent en **mode collaboratif** : Claude ne fait jamais tout d'un trait.
A chaque etape significative, Claude :

1. **Execute** l'action (generation, modification, compilation...)
2. **Verifie** le resultat avec ses controles automatiques
3. **Explique** ce qu'il a fait, ses choix, et les resultats
4. **Attend votre validation** avant de passer a l'etape suivante

Concretement, pour une creation d'entite (skill `creating-diva-entity`), Claude s'arrete a
**chaque etape significative** -- nommage, generation des sources, coherence inter-fichiers,
dictionnaire, integration ERP, compilation, synchro SQL, menu... -- pour expliquer et attendre
votre feu vert.

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

- a la fin de chaque invocation d'un skill **`divalto-devkit`** (entree "OK" si tout s'est bien passe, "KO" sinon) -- **pas** les skills d'autres plugins ;
- des qu'une friction est rencontree (script qui echoue, doc ambigue, comportement inattendu) ;
- a chaque checkpoint ou vous avez pris une decision metier non triviale ;
- a chaque fois qu'une idee d'amelioration emerge.

Chaque entree porte un identifiant unique (R-001, R-002...), une categorie
(`BUG-SKILL`, `BUG-DOC`, `ENV`, `CLAUDE-TOOL`, `SUGGESTION`) et une severite.
Si Claude oublie, rappelez-lui : "ajoute l'entree RETEX". Il ne doit pas demander
l'autorisation pour ecrire dans `RETEX-skills.md`.

**Vous n'avez rien a envoyer.** Les entrees sont poussees automatiquement en issues sur
le depot du devkit par le skill `pushing-retex-to-github` : c'est le canal de remontee,
et il ne demande aucun geste manuel.

Votre retour d'experience permet d'identifier les frictions, corriger les bugs,
et ameliorer les templates de generation.

La version des skills installes est indiquee dans le champ `Version skills` du RETEX.
Cela permet de savoir rapidement si un probleme signale a deja ete corrige.

---

## Mettre a jour le plugin

Les skills evoluent : corrections, nouvelles pages, nouveaux skills. La mise a jour se fait
normalement par l'interface marketplace de Claude Code.

> **Pourquoi cette section existe** : l'interface marketplace n'est pas toujours accessible
> depuis une session conversationnelle. La procedure manuelle ci-dessous est le **repli**.

### Procedure manuelle

```
# 1. Recuperer la derniere version du marketplace
cd <votre-clone-du-marketplace>
git pull

# 2. Reinstaller les skills et les regles
py plugins/divalto-devkit/instructions/install.py
```

`install.py` reecrit le bloc `diva-skills:rules` de votre `CLAUDE.md` **entre ses marqueurs**
(`<!-- diva-skills:rules -->` ... `<!-- /diva-skills:rules -->`) : ce que vous avez ecrit
ailleurs dans le fichier n'est pas touche.

### Verifier ce qu'on a reellement

```
py plugins/divalto-devkit/skills/discovering-skills/scripts/query_catalog.py overview
```

La premiere ligne annonce le nombre de skills installes -- « Panorama des skills DIVA
(N skills, M workflows) » -- et la suite les liste par workflow. Comparez ce compte a ce que
la version annonce : **un ecart signifie que la mise a jour n'a pas ete complete.**

> **Les corrections de regles n'arrivent que par la mise a jour.** Le bloc
> `diva-skills:rules` de votre `CLAUDE.md` est ecrit **a l'installation** : tant que vous ne
> relancez pas `install.py`, vous travaillez avec les regles de la version que vous aviez.
> C'est la raison la plus frequente d'un comportement corrige "qui persiste".

---

## Mode de fonctionnement des scripts

Chaque skill embarque ses propres scripts Python (aucune dependance externe entre skills).
Les scripts acceptent des parametres en ligne de commande et produisent du JSON en sortie.

> **Important** : dans Claude Code, toujours invoquer les skills via l'outil `Skill`.
> Ne pas appeler les scripts directement -- c'est reserve aux tests CLI hors Claude.

### Comment fonctionne un skill (a lire si « le skill ne fait que m'afficher sa doc »)

Invoquer un skill **charge ses instructions** dans le contexte de Claude. Un skill
**n'est pas** une fonction qui « prend des arguments et renvoie la sortie d'un
script » : c'est un **mode d'emploi** que **Claude lit, puis execute lui-meme** (il
lance les scripts Python via le terminal, en suivant ces instructions).

- **Ce qui est normal** : Claude commence par charger les instructions du skill --
  puis il **doit enchainer** sur l'action (generation, lint, compilation...).
- **Si Claude s'arrete a la doc** sans rien executer : dites-lui simplement
  « **execute, ne te contente pas d'afficher le README** ». Et notez-le en RETEX
  (categorie `CLAUDE-TOOL`) -- surtout si ca se reproduit, car un echec **reel** de
  chargement du skill releverait d'un bug Claude Code a remonter.
- **Vous, vous decrivez la tache** -- pas besoin de « passer des arguments » :
  « genere le RecordSql de l'entite X », « compile le projet », « lis le fichier
  ISAM Y ». Claude choisit le bon skill et lance ses scripts.

L'appel direct `py .claude/skills/<skill>/scripts/<script>.py` reste reserve au
**depannage / test CLI hors Claude** (exemple ci-dessous).

Exemple de test CLI hors Claude (skill `generating-recordsql`) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine Retail --entite FamRglt --table RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement" \
    --output "output/rtlrsfamrglt.dhsq"
```
