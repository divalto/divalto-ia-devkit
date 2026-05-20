# scripts/ -- manipulating-dhsf-screens

## Contenu

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `dhsf_parser.py` | Parse un .dhsf en arbre structurel | `--path` | JSON stdout |
| `dhsf_template.py` | Genere un .dhsf depuis un template | `--template` + `--params` + `--output` | Fichier .dhsf |
| `dhsf_modify.py` | Modifications incrementales | `--path` + `--action` + `--params` | Fichier modifie + JSON stdout |

## Dependances

- `dhsf_modify.py` importe `dhsf_parser.py` (meme repertoire)
- Templates : fournis via `--template-dir` en CLI (3 squelettes .dhsf attendus)

## Usage

Toujours passer par le skill via l'outil `Skill("manipulating-dhsf-screens")`.
