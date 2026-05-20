# Regles Syntaxe (S01-S08) et Langage inexistant (L01-L04)

## Syntaxe

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| S01 | error | Concatenation avec `+` au lieu de `&` | Regex: `+` entre expressions string |
| S02 | warning | `VRAI`/`FAUX` au lieu de `True`/`False` | Keyword match |
| S03 | error | Variable declaree apres `BeginP`/`BeginF` | Detection de bloc : var entre Begin et End |
| S04 | error | `Function` sans `FReturn` | Parse blocs Function, verifier FReturn |
| S05 | warning | `EndP`/`EndF` sans commentaire de fermeture | Regex: `EndP\s*$` ou `EndF\s*$` |
| S06 | error | Code DIVA dans un `.dhsf` (hors `[diva]...[/diva]`) | Type de fichier + pattern code |
| S07 | error | Code DIVA dans un `.dhsq` | Type de fichier + pattern code |
| S08 | *V2* | `Zoom.Valretour` utilise sans initialisation | Analyse de flux semantique |

## Langage inexistant

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| L01 | error | `ForEach` (n'existe pas en DIVA) | Keyword: `\bForEach\b` |
| L02 | error | `Try`/`Catch`/`Finally` (pas d'exceptions en DIVA) | Keyword: `\bTry\b`, `\bCatch\b` |
| L03 | error | `Class` (pas d'OOP en DIVA) | Keyword: `\bClass\b` suivi d'un nom |
| L04 | error | Threads (n'existent pas en DIVA) | Keyword: `\bThread\b`, `\bCreateThread\b` |

## Contexte DIVA

- **Concatenation string** : operateur `&` (pas `+` qui est addition numerique)
- **Booleens** : `True`/`False` (pas `VRAI`/`FAUX` qui n'existent pas)
- **Boucles** : `Loop`/`EndLoop`, `For`/`Next`, `Repeat`/`Until`, `Do`/`While`/`Wend`
- **Pas de** : ForEach, Try/Catch, Class, Thread
