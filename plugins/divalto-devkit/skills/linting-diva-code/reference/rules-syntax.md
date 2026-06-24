# Regles Syntaxe (S01-S10) et Langage inexistant (L01-L04)

## Syntaxe

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| S01 | error | Concatenation avec `+` au lieu de `&` | Regex: `+` entre expressions string |
| S02 | warning | `VRAI`/`FAUX` au lieu de `True`/`False` | Keyword match |
| S03 | error | Variable declaree apres `BeginP`/`BeginF` | Detection de bloc : var entre Begin et End |
| S04 | error | `Function` sans `FReturn` | Parse blocs Function, verifier FReturn |
| S06 | error | Code DIVA dans un `.dhsf` (hors blocs `[diva]` / `[diva_base]`) | Type de fichier + pattern code |
| S07 | error | Code DIVA dans un `.dhsq` | Type de fichier + pattern code |
| S08 | *V2* | `Zoom.Valretour` utilise sans initialisation | Analyse de flux semantique |
| S09 | *V2* | `public` sur une procedure surchargee (Erreur 210) | Necessite de savoir si la proc surcharge le standard (semantique) -- cf. SC-030 |
| S10 | error | `OverWrittenBy` pointant un `.dhsp` (source) au lieu d'un `.dhop` (compile) | Regex sur la ligne `OverWrittenBy` ; signale si la cible finit par `.dhsp` |

## Langage inexistant

| Code | Severite | Description | Detection |
|------|----------|-------------|-----------|
| L01 | error | `ForEach` (n'existe pas en DIVA) | Keyword: `\bForEach\b` |
| L02 | error | `Try`/`Catch`/`Finally` (pas d'exceptions en DIVA) | Keyword: `\bTry\b`, `\bCatch\b` |
| L03 | error | `Class` (pas d'OOP en DIVA) | Keyword: `\bClass\b` suivi d'un nom |
| L04 | error | Threads (n'existent pas en DIVA) | Keyword: `\bThread\b`, `\bCreateThread\b` |

## Contexte DIVA

- **Concatenation string** : operateur `&` (pas `+` qui est addition numerique). S01 ignore desormais un `+` a l'interieur d'un litteral (ex `Modify('+','%2B',...)`).
- **Booleens** : `True`/`False` (pas `VRAI`/`FAUX` qui n'existent pas)
- **Boucles** : `Loop`/`EndLoop`, `For`/`Next`, `Repeat`/`Until`, `Do`/`While`/`Wend`
- **Separateurs** : `|` separe deux instructions sur une meme ligne logique -- ce n'est NI un commentaire NI un OU ; le commentaire est `;`
- **Pas de** : ForEach, Try/Catch, Class, Thread
- **Surcharge / `OverWrittenBy`** (S10) : la directive doit referencer l'objet **compile** qui surcharge, dont l'extension depend du type de fichier source : `.dhsp` -> `.dhop`, `.dhsq` -> `.dhoq`, `.dhsd` -> `.dhod`. Les jointures `.dhsj` font exception (elles restent en `.dhsj`). S10 est donc **scopee aux `.dhsp`** : detecter un `.dhsp` la ou l'on attend un `.dhop`. Une regle generique « doit finir en `.dhop` » produirait des faux positifs sur tous les `.dhsq` (qui utilisent legitimement `.dhoq`).

> **S05 retiree (2026-06-16)** : un commentaire de fermeture `EndP`/`EndF` n'est pas une convention DIVA -- regle supprimee (faux positifs sur le code legacy non commente, sans signal utile).
