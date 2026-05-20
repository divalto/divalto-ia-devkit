---
name: linting-diva-code
description: >
  Analyse les fichiers source DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps) et produit
  un rapport d'erreurs classees par severite, en verifiant la conformite aux ~80 anti-patterns
  connus et aux regles de syntaxe DIVA. A utiliser pour controler la qualite du code avant
  compilation ou apres generation.
---

# Linting DIVA Code

## Contenu

- Utilisation rapide
- Regles implementees (V1)
- Regles reportees (V2)
- Interpretation du rapport
- References

---

## Utilisation rapide

```
py .claude/skills/linting-diva-code/scripts/lint_diva.py --path "chemin/fichier.dhsp"
```

Sortie JSON : `{file, type, errors[], warnings[], summary: {total, errors, warnings}}`

Chaque element de `errors[]` / `warnings[]` :
```json
{
  "rule": "S01",
  "severity": "error",
  "line": 42,
  "message": "Concatenation avec + au lieu de &",
  "context": "  s = a + b"
}
```

### Options

| Option | Description |
|--------|-------------|
| `--path` | Chemin du fichier a analyser (obligatoire) |
| `--rules` | Filtrer par codes de regles (ex: `S01,S02,Z02`) |
| `--severity` | Filtrer par severite (`error`, `warning`, `all`) |
| `--format` | Format de sortie (`json`, `text`) — defaut: `json` |

---

## Regles implementees (V1)

### Par type de fichier

| Type | Categories | Regles |
|------|-----------|--------|
| `.dhsp` | S, L, Z, M, F, R | S01-S05, L01-L04, Z02-Z03, Z08, Z11-Z12, M01-M05, F02-F04, R07 |
| `.dhsq` | S, R | S07, R01-R05 |
| `.dhsd` | D | D01-D11 |
| `.dhsf` | S, E | S06, E01, E08-E10 |
| `.dhpt` | P | P01-P02, P04-P05, P13-P15 |
| `.dhps` | P | P01-P02, P04, P06-P07, P09, P12 |

### Par severite

**Errors** (bug garanti ou corruption) : S01, S03-S04, S06-S07, L01-L04, P01-P02, P04-P07, D01-D02, D05-D09, E10

**Warnings** (best practice manquante) : S02, S05, Z02-Z03, Z08, Z11-Z12, M01-M05, R01-R05, R07, P09, P11-P15, D03-D04, D10-D11, E01, E08-E09, F02-F04

---

## Regles reportees (V2)

Necessitent analyse semantique ou cross-file : S08, Z01, Z04-Z07, Z09-Z10, R06, P03, P08, P10, P16, E02-E07, E11, F01

---

## Interpretation du rapport

- **0 erreurs, 0 warnings** : fichier conforme
- **Erreurs** : a corriger avant compilation — bugs garantis
- **Warnings** : best practices — corriger idealement, mais pas bloquant

### Boucle de retroaction

```
Generer (script) → Valider (lint_diva.py) → Corriger (LLM) → Re-valider
```

---

## References

- **Regles syntaxe + langage** : Voir [reference/rules-syntax.md](reference/rules-syntax.md)
- **Regles architecture zoom + mchk** : Voir [reference/rules-architecture.md](reference/rules-architecture.md)
- **Regles RecordSql** : Voir [reference/rules-recordsql.md](reference/rules-recordsql.md)
- **Regles projet + dict + masque** : Voir [reference/rules-project.md](reference/rules-project.md)
