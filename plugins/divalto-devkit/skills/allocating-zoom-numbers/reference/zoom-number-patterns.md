# Registre des patterns d'usage d'un numero de zoom

> Reference **vivante** du skill `allocating-zoom-numbers`. Sert a la **phase 2**
> (recherche large dans les sources specifiques) : chaque occurrence d'un numero
> candidat est etiquetee selon ce registre, puis remontee **pour jugement humain**
> (jamais de decision automatique).

## Principe

On ne peut pas enumerer une fois pour toutes « ce qui est / n'est pas un numero
de zoom » dans le code. Ce registre **demarre avec les patterns surs** et
**grandit au fil des RETEX** : une occurrence etiquetee `non_reconnu` qui se revele
etre un vrai usage de zoom devient un **nouveau pattern** documente ici, avec son
RETEX d'origine. Inversement, un contexte qui genere des faux positifs est note en
« contextes a ignorer ».

La source de verite du code est `scripts/find_free_zoom.py` -> liste
`ZOOM_USAGE_PATTERNS`. **Ce document et cette liste evoluent ensemble.**

## Niveaux de confiance

| Confiance | Sens |
|-----------|------|
| `fort` | Contexte sans ambiguite : c'est un usage de zoom. |
| `faible` | Contexte possible mais ambigu : a juger (peut etre un prix, un ID...). |
| `inconnu` (`non_reconnu`) | Aucun pattern connu ne matche : signal d'apprentissage. |

## Patterns connus (seed initial -- R-012 / #29)

| id | Extensions | Confiance | Ce qui est detecte | Exemple | RETEX |
|----|-----------|-----------|--------------------|---------|-------|
| `zoom_call` | `.dhsp` | fort | Appel `Zoom_Call(` / `Tnt_Zoom_Call(` contenant le numero | `Tnt_Zoom_Call(9022)` | R-012 (#29) |
| `touche_masque` | `.dhsf` | fort | Binding de touche de masque `[touches]` : `fN=<num>`, `ctrl_fN=<num>`, `shift_fN=<num>` | `f8=9022` | R-012 (#29) |
| `affectation` | `.dhsp`, `.dhsf` | faible | Affectation `= <num>` (constante `C_ZOOM_...` ou autre) | `C_ZOOM_FOO_9022 = 9022` | R-012 (#29) |

> Limite connue du seed : un appel via **constante** (`Zoom_Call(C_ZOOM_FOO_9022)`)
> n'expose pas le numero litteral sur la ligne d'appel ; c'est la **declaration**
> `C_ZOOM_FOO_9022 = 9022` (etiquetee `affectation`) qui revele le numero. Suffisant
> pour signaler le candidat comme utilise.

## Contextes a ignorer (faux positifs connus)

Decouverts lors de la verification live sur sources reelles (`Specifs\sss`,
2026-06-18, R-012 / #29). Ces contextes font apparaitre un numero qui coincide
avec une plage de zoom mais **ne sont pas une allocation d'un numero precis** :

| Contexte | Exemple | Pourquoi l'ignorer |
|----------|---------|--------------------|
| Garde de plage F8 | `Case vsw = K_F8 or Harmony.DataArret in(9000..9999,11000..65000)` | Les nombres sont des **bornes de plage** du dispatch generique « est-ce un numero de zoom ? », pas un numero alloue. Inoffensif en pratique : un candidat 90000+ ne tombe pas dans ces bornes. |
| Code de log / anomalie | `R3_Log_Ano(9000," ",...)` | `9000` est un **code de log**, pas un zoom. |
| Comparateur | `case vsw >= 9000` | Comparaison, pas affectation. Depuis 2026-06-18, le pattern `affectation` exclut `>= <= == != :=` via lookbehind -> ces lignes retombent en `non_reconnu` (surfacees, jugees). |

> Ces contextes restent **surfaces pour jugement** (jamais ecartes en dur). Ils
> sont notes ici pour aider l'analyse, et parce qu'en usage reel (candidats 90000+)
> ils ne se declenchent quasiment pas.

## Comment etendre (procedure RETEX)

1. Une occurrence `non_reconnu` (ou un faux positif) est remontee par un RETEX.
2. Verifier dans la source reelle s'il s'agit d'un vrai usage de zoom.
3. Si oui : ajouter une entree a `ZOOM_USAGE_PATTERNS` (`scripts/find_free_zoom.py`)
   **et** une ligne dans la table « Patterns connus » ci-dessus, avec le RETEX source.
4. Si c'est un faux positif recurrent : le documenter dans « Contextes a ignorer »
   (et, si pertinent, affiner la regex du pattern fautif).
5. Garder `{N}` comme placeholder du numero candidat dans les regex (substitue a
   l'execution, deja echappe).
