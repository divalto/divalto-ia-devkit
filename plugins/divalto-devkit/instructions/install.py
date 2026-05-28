"""
Bootstrap d'un workspace pour le plugin divalto-devkit.

Le plugin lui-meme (skills, hooks, commandes, agents) est installe par la
marketplace Claude Code et reside dans le cache (`~/.claude/plugins/cache/`).
Ce script ne touche donc PAS a `.claude/skills/` ni a `.claude/hooks/`.

Son role : initialiser les artefacts cote workspace (a la racine) qui
accompagnent l'usage du plugin :
  - CLAUDE.md (creation si absent, injection des regles)
  - 4PRINCIPLES.md (reference pour les 4 principes de generation)
  - CATALOG.md (catalogue des skills, ecrasable)
  - RETEX-skills.md (template de retour d'experience, non ecrase si present)

Usage:
    py install.py [--oui] [--path CHEMIN] [--create-claude-md | --skip-claude-md]

Options:
    --oui                Passer les confirmations (pour usage scripte)
    --path CHEMIN        Chemin du workspace cible (bypass du prompt interactif)
    --create-claude-md   Creer CLAUDE.md sans demander s'il est absent (bypass du prompt)
    --skip-claude-md     Refuser la creation de CLAUDE.md sans demander (bypass du prompt)

Les options --path / --create-claude-md / --skip-claude-md evitent d'utiliser stdin,
ce qui contourne le piege du BOM UTF-16 introduit par PowerShell quand le script est
appele avec une redirection ou un pipe depuis l'outil PowerShell de Claude Code.
"""

import argparse
import shutil
import sys
from pathlib import Path

MARKER_START = "<!-- diva-skills:rules -->"
MARKER_END = "<!-- /diva-skills:rules -->"

RULE_BLOCK = f"""\
{MARKER_START}
## Regles DIVA Skills

**Ne jamais appeler directement un script interne d'un skill SANS avoir d'abord invoque le Skill correspondant via l'outil `Skill` dans la session courante.**

Une fois le skill invoque via `Skill("<nom>")`, la doc retournee peut instruire l'execution
de scripts internes -- c'est le pattern de **progressive disclosure** (le SKILL.md est une
table des matieres, les scripts sont les outils detailles). Ce qui reste interdit, c'est
l'appel "a froid" : executer un script `scripts/*.py` d'un skill (ou lire son SKILL.md
directement) sans passer par l'outil `Skill` au prealable -- on court-circuite alors la
boucle de retraction et l'orchestration du skill.

| Interdit | Correct |
|----------|---------|
| Lancer `py .../skills/<X>/scripts/<Y>.py` sans `Skill("<X>")` prealable dans la session | `Skill("<X>")` puis suivre la doc retournee (qui peut elle-meme inviter a executer un script) |

**Collaboration humain/Claude : ne JAMAIS enchainer deux etapes significatives sans validation.**
A chaque etape qui produit ou modifie un fichier, ou qui prend une decision metier, suivre ce cycle :

1. **Executer** : lancer l'action (script, generation, modification)
2. **Verifier** : lancer les controles automatiques (linter, validation, cross-check)
3. **Expliquer** : decrire ce qui a ete fait, les fichiers touches, les choix effectues et pourquoi
4. **Attendre** : demander explicitement la validation du collaborateur avant de passer a l'etape suivante

Les skills d'orchestration contiennent des blocs `> CHECKPOINT` qui marquent les points d'arret obligatoires.
Ne jamais sauter un checkpoint. Ne jamais presumer que le silence vaut approbation.

**Remplissage du RETEX AU FUR ET A MESURE -- regle imperative.**

Le fichier `RETEX-skills.md` a la racine du workspace doit etre alimente **immediatement**,
pas en fin de session. A chacun des declencheurs suivants, ecrire une nouvelle entree :

1. **Fin d'une invocation de skill** (creating-diva-entity, compiling-diva-projects, etc.) :
   ecrire une entree "OK" si tout s'est bien passe, "KO" sinon. Meme si tout fonctionne.
2. **Friction ou erreur detectee** : script qui echoue, doc contradictoire, parametre mal
   documente, comportement inattendu -- ecrire l'entree immediatement, avant de chercher
   un contournement.
3. **Checkpoint franchi avec une decision metier** : si le collaborateur fait un choix
   non trivial (nom d'entite, domaine, surcharge d'une convention), ecrire une entree
   de type SUGGESTION pour tracer le raisonnement.
4. **Idee d'amelioration qui surgit** : meme sans bug, tout ce qui pourrait rendre un
   skill plus simple ou plus fiable.

**Interdictions :**
- Ne pas attendre la fin de la session / la fin d'une longue tache.
- Ne pas batcher plusieurs sujets dans une seule entree : **une entree = un sujet**.
- Ne pas demander l'autorisation avant d'ecrire dans `RETEX-skills.md` : le faire
  systematiquement, c'est de l'hygiene, pas une modification du code du collaborateur.

**Format de l'entree** (copier le bloc tel quel) :

```
### R-NNN -- YYYY-MM-DD -- [Titre court]

- **Skill(s)** : [noms des skills utilises]
- **Categorie** : [BUG-SKILL / BUG-DOC / ENV / CLAUDE-TOOL / SUGGESTION]
- **Severite** : [CRITIQUE / HAUTE / MOYENNE / BASSE]
- **Resultat** : [OK / KO + description courte]
- **Description** : [ce qui s'est passe]
- **Reproduction** : [commande ou etape pour reproduire]
- **Contournement** : [solution temporaire trouvee, ou "Aucun"]
- **Suggestion** : [amelioration souhaitee]
```

Incrementer R-NNN depuis le dernier ID present dans le fichier (ou R-001 si vide).

**Qualite de la generation DIVA.**

Source canonique des 4 principes : `4PRINCIPLES.md` a la racine de votre workspace (EN, generique).
Au-dela du processus (cycle executer-verifier-expliquer-attendre), 4 regles encadrent ce que Claude produit :

1. **Penser avant de generer** : si un parametre est ambigu (Nature du champ, dossier cible, surcharge existante), demander plutot que choisir silencieusement. Les choix silencieux creent des entites qu'il faudra jeter.
2. **Minimum viable** : ne generer que ce qui est demande. Cote DIVA : pas de `OverWrittenBy` spontane, pas de `U-Filler` non requis, pas de procedure vide "au cas ou".
3. **Modifications chirurgicales** : sur un fichier existant (.dhsd, .dhsf, .dhsp, votre CLAUDE.md), toucher uniquement les lignes liees a la demande. Ne pas reformater, ne pas reorganiser, ne pas renumeroter. Le code mort adjacent est signale, pas corrige sans demande.
4. **Critere de succes d'abord** : avant de lancer la generation, Claude enonce ce qui vaudra "fait" (lint OK, compil 0 erreur, synchro SQL OK, test ERP OK si applicable). La boucle `generer -> valider -> corriger` cible ce critere.

Si Claude devie de l'une de ces regles, signalez-le : une entree RETEX avec categorie `BUG-SKILL` ou `SUGGESTION` permet de reajuster les skills.
{MARKER_END}
"""


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def _strip_bom(s: str) -> str:
    """Retire un BOM UTF-16/UTF-8 (U+FEFF) eventuellement colle en tete par PowerShell.

    PowerShell encode stdin en UTF-16 LE avec BOM quand on pipe une chaine via
    `"..." | py install.py`. Le BOM (U+FEFF) se colle alors devant la 1ere ligne
    lue par `input()`. Sans nettoyage, un chemin du type "C:/..." est interprete
    comme un chemin relatif et concatene avec cwd, produisant un chemin invalide.
    """
    return s.lstrip("﻿")


def prompt_install_path(cli_path: str | None = None) -> Path:
    """Determine le chemin du workspace cible.

    Si --path est fourni, l'utilise directement (bypass du prompt interactif,
    evite le piege du BOM PowerShell). Sinon, demande a l'utilisateur via input().
    """
    if cli_path:
        return Path(_strip_bom(cli_path.strip())).resolve()
    default = Path.cwd()
    reponse = _strip_bom(input(f"Chemin du workspace [{default}] : ").strip())
    if not reponse:
        return default
    return Path(reponse).resolve()


def validate_target(target: Path) -> None:
    """Verifie que le workspace cible existe."""
    if not target.is_dir():
        print(f"ERREUR : le chemin n'existe pas : {target}", file=sys.stderr)
        sys.exit(1)


def check_claude_md(target: Path, force_create: bool = False, force_skip: bool = False) -> Path:
    """Verifie que CLAUDE.md existe ; propose de le creer si absent.

    Si force_create=True (--create-claude-md), cree sans demander.
    Si force_skip=True (--skip-claude-md), refuse sans demander -> exit 1.
    Sinon, demande a l'utilisateur via input().
    """
    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        return claude_md
    print(f"CLAUDE.md introuvable dans {target}")
    if force_skip:
        print("Bootstrap annule (--skip-claude-md).", file=sys.stderr)
        sys.exit(1)
    if force_create:
        claude_md.write_text("", encoding="utf-8")
        print(f"CLAUDE.md cree : {claude_md}")
        return claude_md
    reponse = _strip_bom(input("Creer un CLAUDE.md vide ? [O/n] : ").strip().lower())
    if reponse in ("", "o", "oui", "y", "yes"):
        claude_md.write_text("", encoding="utf-8")
        print(f"CLAUDE.md cree : {claude_md}")
        return claude_md
    print("Bootstrap annule.", file=sys.stderr)
    sys.exit(1)


def confirm(message: str = "Continuer ?") -> bool:
    """Demande confirmation a l'utilisateur."""
    reponse = _strip_bom(input(f"{message} [O/n] : ").strip().lower())
    return reponse in ("", "o", "oui", "y", "yes")


def show_summary(target: Path) -> None:
    """Affiche le resume des actions a effectuer."""
    print()
    print("=== Resume du bootstrap ===")
    print()
    print(f"  Workspace cible : {target}")
    print()
    print("  Actions :")
    print(f"    - CLAUDE.md          : injection du bloc de regles (idempotent)")
    print(f"    - 4PRINCIPLES.md     : copie a la racine (non ecrase si present)")
    print(f"    - CATALOG.md         : copie a la racine (ecrase)")
    print(f"    - RETEX-skills.md    : copie a la racine (non ecrase si present)")
    print()


# ---------------------------------------------------------------------------
# Etapes de bootstrap
# ---------------------------------------------------------------------------

def copy_4principles(target: Path) -> None:
    """Copie 4PRINCIPLES.md a la racine du workspace (non ecrasant)."""
    source = Path(__file__).resolve().parent / "4PRINCIPLES.md"
    dest = target / "4PRINCIPLES.md"
    if not source.exists():
        print(f"ATTENTION : 4PRINCIPLES.md absent de la source ({source}), ignore.", file=sys.stderr)
        return
    if dest.exists():
        print(f"4PRINCIPLES.md deja present a {dest} (non ecrase)")
        return
    shutil.copy2(source, dest)
    print(f"4PRINCIPLES.md installe : {dest}")


def copy_catalog_md(target: Path) -> Path | None:
    """Copie CATALOG.md a la racine du workspace (ecrasant).

    Retourne le chemin final, ou None si la source est absente.
    """
    source = Path(__file__).resolve().parent / "CATALOG.md"
    dest = target / "CATALOG.md"
    if not source.exists():
        print(f"ATTENTION : CATALOG.md absent de la source ({source}), ignore.", file=sys.stderr)
        return None
    shutil.copy2(source, dest)
    print(f"CATALOG.md installe : {dest}")
    return dest


def copy_retex(target: Path) -> None:
    """Copie le template RETEX a la racine du workspace (non ecrasant).

    Source : RETEX-collaborateur.md (a cote du script).
    Destination : RETEX-skills.md (nom standard cote workspace).
    """
    source = Path(__file__).resolve().parent / "RETEX-collaborateur.md"
    dest = target / "RETEX-skills.md"
    if not source.exists():
        print(f"ATTENTION : RETEX-collaborateur.md absent de la source ({source}), ignore.", file=sys.stderr)
        return
    if dest.exists():
        print(f"RETEX-skills.md deja present a {dest} (non ecrase)")
        return
    shutil.copy2(source, dest)
    print(f"RETEX-skills.md installe : {dest}")


def patch_claude_md(claude_md: Path) -> None:
    """Injecte le bloc de regles dans CLAUDE.md (idempotent via marqueurs)."""
    existing = claude_md.read_text(encoding="utf-8")

    if MARKER_START in existing:
        start = existing.index(MARKER_START)
        end = existing.index(MARKER_END) + len(MARKER_END)
        tail = existing[end:].lstrip("\r\n")
        separator = "\n" if tail else ""
        updated = existing[:start] + RULE_BLOCK + separator + tail
        claude_md.write_text(updated, encoding="utf-8")
        print(f"Regles mises a jour dans {claude_md}")
        return

    with claude_md.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n" + RULE_BLOCK)
    print(f"Regles ajoutees dans {claude_md}")


def show_onboarding(target: Path, catalog_path: Path | None) -> None:
    """Affiche le message de bienvenue pointant vers les skills."""
    print()
    print("=== Pour commencer ===")
    print()
    if catalog_path and catalog_path.exists():
        print(f"1. Ouvrir {catalog_path.name} a la racine du workspace pour voir le")
        print("   catalogue complet des skills disponibles, classes par workflow.")
    print("2. Demander a Claude dans une session :")
    print('   - "Que peux-tu faire ?" -> panorama des skills')
    print('   - "Explique-moi <nom-du-skill>" -> fiche detaillee')
    print('   - "Quel skill pour <besoin> ?" -> recherche par mot-cle')
    print("   (Claude invoquera automatiquement le skill `discovering-skills`.)")
    print()


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap d'un workspace pour le plugin divalto-devkit"
    )
    parser.add_argument("--oui", action="store_true", help="Passer les confirmations")
    parser.add_argument(
        "--path",
        default=None,
        help="Chemin du workspace cible (bypass du prompt interactif, evite le piege BOM PowerShell)",
    )
    claude_md_group = parser.add_mutually_exclusive_group()
    claude_md_group.add_argument(
        "--create-claude-md",
        action="store_true",
        help="Creer CLAUDE.md sans demander s'il est absent",
    )
    claude_md_group.add_argument(
        "--skip-claude-md",
        action="store_true",
        help="Refuser la creation de CLAUDE.md sans demander (annule le bootstrap si absent)",
    )
    args = parser.parse_args()

    print("=== Bootstrap workspace divalto-devkit ===")
    print()

    target = prompt_install_path(args.path)
    validate_target(target)
    claude_md = check_claude_md(
        target,
        force_create=args.create_claude_md,
        force_skip=args.skip_claude_md,
    )

    show_summary(target)

    if not args.oui:
        if not confirm():
            print("Bootstrap annule.")
            sys.exit(0)

    copy_4principles(target)
    catalog_path = copy_catalog_md(target)
    copy_retex(target)
    patch_claude_md(claude_md)

    print()
    print("Bootstrap termine.")
    show_onboarding(target, catalog_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBootstrap annule.", file=sys.stderr)
        sys.exit(1)
