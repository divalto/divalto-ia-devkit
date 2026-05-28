---
description: Bootstrap du workspace courant pour le plugin divalto-devkit (CLAUDE.md, 4PRINCIPLES, CATALOG, RETEX)
allowed-tools:
  - Bash
---

Initialise le workspace courant pour le plugin **divalto-devkit**.

Le script installe a la racine du workspace :

- `CLAUDE.md` -- cree si absent, bloc de regles injecte de maniere idempotente
- `4PRINCIPLES.md` -- non ecrase si present
- `CATALOG.md` -- ecrase
- `RETEX-skills.md` -- non ecrase si present

Le plugin lui-meme (skills, hooks, commandes) reste dans le cache Claude Code
et n'est pas touche par ce script.

## Execution

Lance la commande suivante depuis le repertoire de travail courant (qui sera
utilise comme workspace cible) :

```bash
printf '\n\n' | py "${CLAUDE_PLUGIN_ROOT}/instructions/install.py" --oui
```

Le `printf '\n\n'` fournit les reponses par defaut :

- chemin du workspace = repertoire courant
- creation d'un `CLAUDE.md` vide si absent = oui

Le flag `--oui` passe la confirmation finale.

## Apres execution

Resume a l'utilisateur :

1. les fichiers crees ou mis a jour a la racine du workspace
2. l'invitation a ouvrir `CATALOG.md` pour decouvrir les skills disponibles
3. la possibilite de demander a Claude "Que peux-tu faire ?" pour declencher
   le skill `discovering-skills`
