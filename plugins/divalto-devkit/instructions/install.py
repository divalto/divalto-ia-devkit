"""
Installe les skills DIVA dans un workspace Claude Code.

Usage:
    py install.py [--oui]

Etapes :
  1. Propose un chemin d'installation (defaut : repertoire courant)
  2. Supprime l'ancienne version des skills si elle existe
  3. Copie les skills dans <chemin>/.claude/skills/
  4. Injecte les regles DIVA dans <chemin>/CLAUDE.md

Options:
    --oui   Passer les confirmations (pour usage scripte)
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

MARKER_START = "<!-- diva-skills:rules -->"
MARKER_END = "<!-- /diva-skills:rules -->"

WORKSPACE_PREFIX = "workspace-"

HOOKS_CONFIG = {
    "PreToolUse": [
        {
            "matcher": "Edit|Write",
            "hooks": [
                {
                    "type": "command",
                    "command": "py .claude/hooks/protect_skills.py",
                },
                {
                    "type": "command",
                    "command": "py .claude/hooks/protect_encoding.py",
                }
            ],
        }
    ]
}

RULE_BLOCK = f"""\
{MARKER_START}
## Regles DIVA Skills

**Ne jamais appeler directement un script dans `.claude/skills/*/scripts/`.**
Toujours passer par l'outil `Skill` avec le nom du skill concerne.
Les scripts sont des composants internes : les appeler directement court-circuite
la boucle de retraction, la progressive disclosure, et l'orchestration du skill.

| Interdit | Correct |
|----------|---------|
| `py .claude/skills/.../scripts/generate.py ...` | `Skill("generating-recordsql", ...)` |

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

def find_source_skills() -> Path:
    """Localise le repertoire skills source (relatif au script)."""
    source = Path(__file__).resolve().parent / ".claude" / "skills"
    if not source.is_dir():
        print(f"ERREUR : repertoire skills source introuvable : {source}", file=sys.stderr)
        sys.exit(1)
    # Verifier qu'il contient au moins un skill (sous-dossier avec SKILL.md)
    skills = [d for d in source.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
    if not skills:
        print(f"ERREUR : aucun skill trouve dans {source}", file=sys.stderr)
        sys.exit(1)
    return source


def count_skills(skills_dir: Path) -> int:
    """Compte les skills (sous-dossiers contenant SKILL.md)."""
    return sum(1 for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists())


def prompt_install_path() -> Path:
    """Demande le chemin d'installation a l'utilisateur."""
    default = Path.cwd()
    reponse = input(f"Chemin d'installation [{default}] : ").strip()
    if not reponse:
        return default
    return Path(reponse).resolve()


def validate_target(target: Path) -> None:
    """Verifie que le chemin cible et .claude/ existent."""
    if not target.is_dir():
        print(f"ERREUR : le chemin n'existe pas : {target}", file=sys.stderr)
        sys.exit(1)
    claude_dir = target / ".claude"
    if not claude_dir.is_dir():
        print(f"ERREUR : le repertoire .claude/ n'existe pas dans {target}", file=sys.stderr)
        print("Claude Code cree ce repertoire au premier lancement.", file=sys.stderr)
        print("Ouvrez d'abord le workspace avec Claude Code, puis relancez l'installation.", file=sys.stderr)
        sys.exit(1)


def check_claude_md(target: Path) -> Path:
    """Verifie que CLAUDE.md existe ; propose de le creer si absent."""
    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        return claude_md
    print(f"CLAUDE.md introuvable dans {target}")
    reponse = input("Creer un CLAUDE.md vide ? [O/n] : ").strip().lower()
    if reponse in ("", "o", "oui", "y", "yes"):
        claude_md.write_text("", encoding="utf-8")
        print(f"CLAUDE.md cree : {claude_md}")
        return claude_md
    print("Installation annulee.", file=sys.stderr)
    sys.exit(1)


def confirm(message: str = "Continuer ?") -> bool:
    """Demande confirmation a l'utilisateur."""
    reponse = input(f"{message} [O/n] : ").strip().lower()
    return reponse in ("", "o", "oui", "y", "yes")


def show_summary(source: Path, target: Path, old_exists: bool) -> None:
    """Affiche le resume de l'installation."""
    nb_source = count_skills(source)
    print()
    print("=== Resume de l'installation ===")
    print()
    print(f"  Source : {source} ({nb_source} skills)")
    print(f"  Cible  : {target / '.claude' / 'skills'}")
    if old_exists:
        nb_old = count_skills(target / ".claude" / "skills")
        print(f"  Action : SUPPRESSION de l'ancienne version ({nb_old} skills) puis reinstallation")
    else:
        print("  Action : Premiere installation (skills/ sera cree)")
    print(f"  Hook   : protection en lecture seule des skills (.claude/hooks/)")
    print()


def remove_old_skills(target_skills: Path) -> None:
    """Supprime l'ancien repertoire skills/."""
    try:
        shutil.rmtree(target_skills)
        print("Ancien repertoire skills/ supprime.")
    except OSError as e:
        print(f"ERREUR lors de la suppression de {target_skills} : {e}", file=sys.stderr)
        print("Fermez Claude Code et tout editeur ayant des fichiers ouverts, puis reessayez.", file=sys.stderr)
        sys.exit(2)


def install_skills(source: Path, target: Path) -> None:
    """Copie les skills depuis la source vers la cible.

    Refus automatique des skills prefixes `workspace-` (workspace-only). Si le zip
    en contenait un, on avorte : cela signale un bug dans build_zip.py cote
    emetteur. Ne jamais installer un workspace-* chez un collaborateur.
    """
    target_skills = target / ".claude" / "skills"

    forbidden = [d.name for d in source.iterdir() if d.is_dir() and d.name.startswith(WORKSPACE_PREFIX)]
    if forbidden:
        print(
            f"ERREUR CRITIQUE : zip corrompu, skills workspace-* detectes : {forbidden}",
            file=sys.stderr,
        )
        print(
            "Ces skills ne doivent jamais etre distribues. Signaler au producteur du zip.",
            file=sys.stderr,
        )
        sys.exit(2)

    if target_skills.exists():
        remove_old_skills(target_skills)
    try:
        shutil.copytree(source, target_skills)
    except OSError as e:
        print(f"ERREUR lors de la copie : {e}", file=sys.stderr)
        sys.exit(2)
    nb = count_skills(target_skills)
    print(f"{nb} skills installes dans {target_skills}")


def install_hook(source: Path, target: Path) -> None:
    """Copie les hooks de protection dans le workspace cible."""
    target_hooks = target / ".claude" / "hooks"
    target_hooks.mkdir(parents=True, exist_ok=True)

    hooks = ["protect_skills.py", "protect_encoding.py"]
    for hook_name in hooks:
        source_hook = source.parent / "hooks" / hook_name
        if not source_hook.exists():
            print(f"ATTENTION : hook {hook_name} introuvable dans la source, ignore.",
                  file=sys.stderr)
            continue
        target_file = target_hooks / hook_name
        shutil.copy2(source_hook, target_file)
        print(f"Hook installe : {target_file}")


def patch_settings_json(target: Path) -> None:
    """Injecte la configuration hooks dans .claude/settings.json (idempotent)."""
    settings_path = target / ".claude" / "settings.json"

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            settings = {}
    else:
        settings = {}

    settings["hooks"] = HOOKS_CONFIG
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Configuration hooks injectee dans {settings_path}")


def copy_4principles(target: Path) -> None:
    """Copie 4PRINCIPLES.md a la racine du workspace cible (si absent)."""
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
    """Copie CATALOG.md a la racine du workspace cible (ecrase si present).

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


def show_onboarding(target: Path, catalog_path: Path | None) -> None:
    """Affiche le message de bienvenue pointant vers les skills installes."""
    print()
    print("=== Pour commencer ===")
    print()
    if catalog_path and catalog_path.exists():
        print(f"1. Ouvrir {catalog_path.name} a la racine du workspace pour voir le")
        print("   catalog complet des skills disponibles, classes par workflow.")
    print("2. Demander a Claude dans une session :")
    print('   - "Que peux-tu faire ?" -> panorama des skills')
    print('   - "Explique-moi <nom-du-skill>" -> fiche detaillee')
    print('   - "Quel skill pour <besoin> ?" -> recherche par mot-cle')
    print("   (Claude invoquera automatiquement le skill `discovering-skills`.)")
    print()


def patch_claude_md(claude_md: Path) -> None:
    """Injecte le bloc de regles dans CLAUDE.md (idempotent)."""
    existing = claude_md.read_text(encoding="utf-8")

    # Si l'ancien marqueur existe, le remplacer
    if MARKER_START in existing:
        # Extraire et remplacer le bloc entre les marqueurs
        start = existing.index(MARKER_START)
        end = existing.index(MARKER_END) + len(MARKER_END)
        updated = existing[:start] + RULE_BLOCK + existing[end:]
        claude_md.write_text(updated, encoding="utf-8")
        print(f"Regles mises a jour dans {claude_md}")
        return

    # Sinon, ajouter a la fin
    with claude_md.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n" + RULE_BLOCK)
    print(f"Regles ajoutees dans {claude_md}")


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Installe les skills DIVA dans un workspace Claude Code")
    parser.add_argument("--oui", action="store_true", help="Passer les confirmations")
    args = parser.parse_args()

    print("=== Installation DIVA Skills ===")
    print()

    source = find_source_skills()
    target = prompt_install_path()
    validate_target(target)
    claude_md = check_claude_md(target)

    old_exists = (target / ".claude" / "skills").is_dir()
    show_summary(source, target, old_exists)

    if not args.oui:
        if not confirm():
            print("Installation annulee.")
            sys.exit(0)

    install_skills(source, target)
    install_hook(source, target)
    patch_settings_json(target)
    copy_4principles(target)
    catalog_path = copy_catalog_md(target)
    patch_claude_md(claude_md)

    # Installer RETEX-skills.md a la racine du workspace (si absent)
    retex_target = target / "RETEX-skills.md"
    retex_source = Path(__file__).resolve().parent / "RETEX-collaborateur.md"
    if not retex_source.exists():
        # Chercher dans le meme repertoire que l'archive extraite
        retex_source = Path(__file__).resolve().parent / "RETEX-collaborateur.md"
    if retex_source.exists() and not retex_target.exists():
        import shutil
        shutil.copy2(retex_source, retex_target)
        print(f"RETEX-skills.md installe dans {retex_target}")
    elif retex_target.exists():
        print(f"RETEX-skills.md deja present (non ecrase)")

    print()
    print("Installation terminee. Ouvrez le workspace avec Claude Code.")
    show_onboarding(target, catalog_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInstallation annulee.", file=sys.stderr)
        sys.exit(1)
