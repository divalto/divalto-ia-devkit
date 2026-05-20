# Regles Projet (P01-P16), Dictionnaire (D01-D11), Masque (E01-E15)

## Projet (.dhpt, .dhps)

| Code | Severite | Type | Description |
|------|----------|------|-------------|
| P01 | error | .dhpt/.dhps | Encodage UTF-8 au lieu de ISO-8859-1 |
| P02 | error | .dhpt/.dhps | Fins de ligne LF au lieu de CRLF |
| P03 | *V2* | — | Utilisation Edit/Write sur fichier Divalto |
| P04 | error | .dhps | En-tete `xwin-projet` au lieu de `xwin-sprojet` |
| P05 | error | .dhpt | En-tete `xwin-sprojet` au lieu de `xwin-projet` |
| P06 | error | .dhps | Syntaxe `fic="x"," "` dans `[includes]` (doit etre sans `," "`) |
| P07 | error | .dhps | Syntaxe `fic="x"` dans `[fichiers]` (manque `," "`) |
| P08 | *V2* | — | Sous-projet non reference dans .dhpt parent |
| P09 | warning | .dhps | `zdiva.dhsp` manquant dans `[includes]` |
| P10 | *V2* | — | Groupes communs dict/rsql manquants |
| P11 | warning | .dhps | Prefixes domaine mixtes dans les fichiers |
| P12 | warning | .dhps | Section `[autres]` manquante |
| P13 | warning | .dhpt | Sections obligatoires manquantes |
| P14 | warning | .dhpt | `developpement` sans accent dans profil |
| P15 | warning | .dhpt | `developpement_x13.txt` sans accent |
| P16 | *V2* | — | Verification encodage non faite |

## Dictionnaire (.dhsd)

| Code | Severite | Description |
|------|----------|-------------|
| D01 | error | Chevauchement de champs (positions qui se superposent) |
| D02 | error | Trou entre les champs (position suivante != position + taille) |
| D03 | warning | Champ `U<TABLE>` manquant (reserve distributeur) |
| D04 | warning | Champ utilise dans [CHAMPS] sans declaration [CHAMP] |
| D05 | error | Encodage UTF-8 au lieu de ISO-8859-1 |
| D06 | error | Fins de ligne LF au lieu de CRLF |
| D07 | error | Tag `[/CHAMPS]` fermant manquant |
| D08 | error | Tag `[/TABLES]` fermant manquant |
| D09 | error | Tag `[/INDEX]` fermant manquant |
| D10 | warning | Valeur CE incorrecte dans CLE d'index |
| D11 | warning | Base non prefixee selon le dictionnaire |

## Masque (.dhsf)

| Code | Severite | Description |
|------|----------|-------------|
| E01 | warning | Element graphique sans bloc `[presentation]` |
| E02-E07 | *V2* | Coherence champs/colonnes (analyse semantique) |
| E08 | warning | `[diva_base][/diva]` manquant en fin de fichier |
| E09 | warning | IDs dupliques dans le masque |
| E10 | error | Encodage UTF-8 au lieu de ISO-8859-1 |
| E11 | *V2* | Generation .dhsf from scratch |
| E12 | warning | Code DIVA excessif dans [diva] (> 200 lignes) |
| E13 | info | Enregistrement declare mais non reference |
| E14 | info | Melange WPF/classique detecte |
| E15 | info | Page vide hors convention zoom |
