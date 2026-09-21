# Regles Projet (P01-P16), Dictionnaire (D01-D11), Masque (E01-E15)

## Projet (.dhpt, .dhps)

| Code | Severite | Type | Description |
|------|----------|------|-------------|
| P01 | error | .dhpt/.dhps | Encodage UTF-8 au lieu de ISO-8859-1 |
| P02 | error | .dhpt/.dhps | Fins de ligne LF au lieu de CRLF |
| P03 | *V2* | — | Utilisation Edit/Write sur fichier Divalto |
| P04 | error | **.dhps** | En-tete invalide : attendu `xwin-sprojet`, ou `xwin-s-sprojet` pour un sous-projet de **surcharge** -- legitime, cf. `managing-diva-projects` P08/P17 (#293/#307) |
| P05 | error | **.dhpt** | En-tete invalide : attendu `xwin-projet`, ou `xwin-s-projet` pour un projet de **surcharge**. **Un code par extension** : P04 controle le `.dhps`, P05 le `.dhpt`. Auparavant P04 etait dispatche sur les deux ET P05 testait une sous-chaine, si bien qu'un `.dhpt` mal en-tete remontait **les deux codes** pour un seul defaut, tandis que `xwin-s-sprojet` echappait a P05 (la sous-chaine `xwin-sprojet` n'y figure pas) |
| P06 | error | .dhps | Syntaxe `fic="x"," "` dans `[includes]` (doit etre sans `," "`) |
| P07 | error | .dhps | Syntaxe `fic="x"` dans `[fichiers]` (manque `," "`) |
| P08 | *V2* | — | Sous-projet non reference dans .dhpt parent |
| P09 | `info` **hors defaut** | .dhps | `zdiva.dhsp` manquant dans `[includes]` -- **convention**, `--rules P09`. Le standard livre ne le fait **jamais** (0/2304 `.dhps`), un specifique partenaire mesure le fait a 80-98 % : active par defaut, la regle remonte 100 % des sous-projets du standard -- or les linter comme **modele de reference** est un usage courant. |
| P10 | *V2* | — | Groupes communs dict/rsql manquants |
| P11 | *V2* | — | Prefixes domaine mixtes dans les fichiers |
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
