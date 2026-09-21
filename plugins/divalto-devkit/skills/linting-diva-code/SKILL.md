---
name: linting-diva-code
description: >
  Analyse les fichiers source DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhsi, .dhse, .dhpt, .dhps, .sql)
  et produit un rapport d'erreurs classees par severite, en verifiant la conformite aux 85
  anti-patterns connus (dont regles dictionnaire D04/D10/D11, masque E12-E19 incluant normes
  graphiques), aux regles de syntaxe DIVA, et aux 11 controles qualite CI (shift-left des
  moulinettes nightly). A utiliser pour controler la qualite du code avant compilation ou
  apres generation.
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

Sortie JSON : `{file, type, errors[], warnings[], infos[], summary: {total, errors, warnings, infos}}`

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
| `--rules` | Filtrer par codes de regles (ex: `S01,S02,Z02`) — **et seul moyen d'activer les regles hors defaut** |
| `--severity` | Filtrer par severite (`error`, `warning`, `info`, `all`) |
| `--format` | Format de sortie (`json`, `text`) — defaut: `json` |

> **Regles hors du jeu par defaut.** Certaines regles auditent une **convention maison**,
> pas un defaut : leur constat n'est ni une erreur de compilation ni un dysfonctionnement.
> Elles ne s'executent donc **que si on les demande** par `--rules`. Aujourd'hui :
> **`CI01`** (`SetModuleInfo` absent — l'information lue par `ModuleInfo`, dont Divalto se sert pour afficher les versions : systematique dans le
> standard, libre en specifique). A activer si la politique du projet est de tracer les
> releases : `--rules CI01`. Detail : [reference/rules-ci.md](reference/rules-ci.md).

---

## Regles implementees (V1)

### Par type de fichier

| Type | Categories | Regles |
|------|-----------|--------|
| `.dhsp` | S, L, Z, M, F, CI | S01-S04, S10-S12, L01-L04, Z02-Z03, Z08, Z11-Z12, Z15, M01-M05, F02-F04, CI02-CI04, CI10-CI11 |
| `.dhsq` | S, R, CI | S07, R01-R05, R08, CI05-CI06, CI08-CI09 |
| `.dhsd` | D, Z | D01-D14, Z14 |
| `.dhsf` | S, E, Z | S06, S12, E01, E08-E10, E12-E19, Z16 |
| `.dhsi` | _(aucune par defaut)_ | — |
| `.dhse` | _(aucune par defaut)_ | — |
| `.dhpt` | P | P01-P02, P05, P13-P15 |
| `.dhps` | P | P01-P02, P04, P06-P07, P12 |
| `.sql` | CI | CI07 |

### Par severite

**Errors** (bug garanti ou corruption) : S01, S03-S04, S06-S07, S10-S12, R08, L01-L04, P01-P02, P04-P07, D01-D02, D05-D09, E10, E16 (champ audit absent de l'onglet Identifiants), CI02, CI04, CI06, CI08

**Warnings** (best practice manquante) : S02, Z02-Z03, Z08, Z11-Z12, Z15, Z16 (suffixe FK fiable sans f8=<zoom> dans [touches] du masque), M01-M05, R01-R05, P12-P15, D03-D04, D10-D11, E01, E08-E09, E12, E17 (ordre onglet Identifiants non canonique), E19 (taille ecran hors normes), F02-F04, CI03, CI05, CI07, CI09-CI11

**Infos** (indication non bloquante) : E13-E15, E18 (espacement hors valeurs canoniques 5, 8, 10, 12, 14, 16, 18, 26 -- tolerance pratique constatee en X.13)

**Hors jeu par defaut** -- audit de **convention** : le constat n'est ni une erreur de compilation ni un dysfonctionnement. Activation explicite par `--rules <code>`.

| Regle | Severite | Convention auditee | Pourquoi hors defaut |
|-------|----------|--------------------|----------------------|
| `CI01` | `info` | `SetModuleInfo` present -- information lue a l'execution par `ModuleInfo` (`.dhsp`, `.dhsq`, `.dhsf`, `.dhsi`, `.dhse`) | Non obligatoire : aucun effet a la compilation, mais un module sans elle n'execution. Systematique dans le standard, **libre en specifique** -- ~860 constats sur un specifique mesure. |
| `P09` | `info` | `zdiva.dhsp` dans `[includes]` d'un `.dhps` | Le standard livre ne le fait **jamais** (0/2304), un specifique le fait a 80-98 %. Active par defaut, elle remonte 100 % des sous-projets du standard -- que l'on linte couramment comme **modele de reference**. |

---

## Regles reportees (V2)

Necessitent analyse semantique ou cross-file : S08, Z01, Z04-Z07, Z09-Z10, R06, R07, P03, P08, P10, P16, E02-E07, E11, F01

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

## Tests

Les corrections de **faux positifs** ont une suite executable (un faux positif systematique
fait ignorer le rapport entier) :

```
py .claude/skills/linting-diva-code/tests/run_all.py
```

Chaque cas garde une correction **et** la detection legitime qu'elle ne doit pas casser.
A lancer apres toute modification de `scripts/lint_diva.py`.

> `versions/v1/` est une **archive figee** (jeu de regles anterieur) : ne jamais l'editer.
> Le seul fichier vivant est `scripts/lint_diva.py`.

---

## References

- **Regles syntaxe + langage** : Voir [reference/rules-syntax.md](reference/rules-syntax.md)
- **Regles architecture zoom + mchk** : Voir [reference/rules-architecture.md](reference/rules-architecture.md)
- **Regles RecordSql** : Voir [reference/rules-recordsql.md](reference/rules-recordsql.md)
- **Regles projet + dict + masque** : Voir [reference/rules-project.md](reference/rules-project.md)
- **Regles CI (shift-left moulinettes)** : Voir [reference/rules-ci.md](reference/rules-ci.md)
- **Normes graphiques masques E16-E19** : Voir [reference/rules-dhsf-normes.md](reference/rules-dhsf-normes.md) (E16 champ audit absent de l'onglet Identifiants, E17 ordre non canonique, E18 espacements, E19 taille ecran)
