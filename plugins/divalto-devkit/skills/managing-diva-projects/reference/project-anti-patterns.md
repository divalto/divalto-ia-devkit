# Anti-patterns projet (P01-P17)

## Contenu

- Table de reference rapide
- Detail par anti-pattern
- Validation croisee

---


## Table de reference rapide

| Code | Severite | Anti-pattern | Correction |
|------|----------|-------------|------------|
| P01 | error | Encodage UTF-8 dans .dhpt/.dhps | Encoder en ISO-8859-1 |
| P02 | error | Fins de ligne LF au lieu de CRLF | Utiliser CRLF (`\r\n`) |
| P03 | error | Edit/Write de Claude Code sur fichiers avec accents | Utiliser Bash (head/tail) ou reconvertir (iconv + sed) |
| P04 | error | En-tete `xwin-projet` dans un .dhps | Utiliser `xwin-sprojet 2.0` (standard) ou `xwin-s-sprojet 2.0` (surcharge) |
| P05 | error | En-tete `xwin-sprojet` dans un .dhpt | Utiliser `xwin-projet 2.0` (standard) ou `xwin-s-projet 2.0` (surcharge) |
| P06 | error | Syntaxe `fic="nom"," "` dans [includes] | Utiliser `fic="nom"` sans virgule |
| P07 | error | Syntaxe `fic="nom"` sans `," "` dans [fichiers] | Utiliser `fic="nom"," "` |
| P08 | error | .dhps non reference dans [sousprojets] du .dhpt | Ajouter `fic="nom.dhps"," "` dans [sousprojets] |
| P09 | error | `zdiva.dhsp` absent de [includes] | Toujours inclure `fic="zdiva.dhsp"` |
| P10 | warning | Groupes communs manquants dans [communs] du .dhps | Ajouter les `incl=` necessaires |
| P11 | warning | Melange de prefixes domaine dans un projet | Respecter le prefixe domaine |
| P12 | error | .dhps sans section [autres] en fin | Toujours ajouter `[autres]` |
| P13 | error | .dhpt sans [projetsfusion], [fabricationmere] ou [autres] | Toujours inclure les 3 sections |
| P14 | error | `developpement` sans accent dans nom de profil | Ecrire `\xe9` (ISO-8859-1) pour l'accent |
| P15 | error | `developpement_x13.txt` sans accent dans implicites | Ecrire `\xe9` dans le nom de fichier |
| P16 | warning | Pas de verification d'encodage finale | Verifier avec `file --mime-encoding` |
| P17 | error | `.dhps` de surcharge (`<base>u.dhps`) listee dans `[sousprojets]` | Retirer la ligne -- xwin7 auto-detecte la surcharge via `cheminbases` |

---

## Detail par anti-pattern

### P01 -- Encodage UTF-8

**Probleme** : les accents sont corrompus (`\xc3\xa9` au lieu de `\xe9`), le compilateur Divalto echoue.

**Verification** :
```bash
file --mime-encoding fichier.dhps
# Attendu : iso-8859-1, unknown-8bit, ou us-ascii
# Erreur : utf-8
```

### P02 -- Fins de ligne LF

**Probleme** : tous les fichiers texte Divalto utilisent CRLF. LF seul corrompt la structure.

**Verification** :
```bash
file fichier.dhps
# Doit contenir "CRLF" ou "with CR"
```

### P03 -- Edit/Write de Claude Code

**Probleme** : les outils Edit et Write de Claude Code convertissent automatiquement en UTF-8 avec LF, corrompant les accents et les fins de ligne.

**Solution** : utiliser le skill `writing-diva-files` (methodes Bash avec head/tail, ou reconversion iconv + sed).

### P04 -- En-tete projet dans un sous-projet

**Probleme** : un .dhps doit utiliser `xwin-sprojet` (standard) ou `xwin-s-sprojet` (surcharge), pas `xwin-projet`.

```
# MAUVAIS (dans un .dhps)
xwin-projet        2.0

# BON (sous-projet standard)
xwin-sprojet       2.0

# BON (sous-projet de surcharge -- nom <base>u.dhps)
xwin-s-sprojet     2.0
```

Confondre les deux variantes (`xwin-sprojet` vs `xwin-s-sprojet`) provoque l'erreur xwin7 "n'est pas une surcharge de sous projet" (cf. R-006).

### P05 -- En-tete sous-projet dans un projet

**Probleme** : un .dhpt doit utiliser `xwin-projet` (standard) ou `xwin-s-projet` (surcharge), pas `xwin-sprojet`.

```
# BON (projet standard)
xwin-projet        2.0

# BON (projet de surcharge)
xwin-s-projet      2.0
```

### P06 -- Virgule dans [includes]

**Probleme** : la section `[includes]` n'accepte PAS la virgule-espace.

```ini
# MAUVAIS
[includes]
fic="zdiva.dhsp"," "

# BON
[includes]
fic="zdiva.dhsp"
```

### P07 -- Pas de virgule dans [fichiers]

**Probleme** : la section `[fichiers]` EXIGE la virgule-espace.

```ini
# MAUVAIS
[fichiers]
fic="monprog.dhsp"

# BON
[fichiers]
fic="monprog.dhsp"," "
```

### P08 -- Sous-projet non reference

**Probleme** : un .dhps non declare dans `[sousprojets]` du .dhpt parent ne sera pas compile.

### P09 -- zdiva.dhsp manquant

**Probleme** : les fonctions de base DIVA sont indisponibles a la compilation.

```ini
[includes]
fic="zdiva.dhsp"
```

### P10 -- Groupes communs manquants

**Probleme** : les definitions partagees (dictionnaires, bases) sont inaccessibles. Verifier que les groupes necessaires du .dhpt parent sont inclus dans `[communs]`.

### P11 -- Melange de prefixes

**Probleme** : un sous-projet `rt_` ne devrait pas inclure des groupes `gt_` sauf si transverse. Respecter la coherence de prefixe domaine.

### P12 -- Section [autres] absente (.dhps)

**Probleme** : `[autres]` est obligatoire en fin de .dhps, meme vide.

### P13 -- Sections obligatoires absentes (.dhpt)

**Probleme** : `[projetsfusion]`, `[fabricationmere]` et `[autres]` sont obligatoires dans un .dhpt, meme vides.

### P14 -- Accent manquant dans nom de profil

**Probleme** : le profil standard est `développement` avec accent aigu ISO-8859-1 (`\xe9`). Sans accent, la comparaison echoue.

### P15 -- Accent manquant dans nom implicites

**Probleme** : le fichier implicite standard est `développement_x13.txt`. Meme regle que P14.

### P16 -- Pas de verification d'encodage

**Bonne pratique** : toujours verifier avec `file --mime-encoding` apres creation/modification. Le resultat ne doit JAMAIS etre `utf-8`.

### P17 -- .dhps de surcharge listee dans [sousprojets]

**Probleme** : xwin7 auto-detecte les `.dhps` de surcharge (`<base>u.dhps`) via `cheminbases`. Si la `.dhps` de surcharge est listee dans `[sousprojets]` du `.dhpt` parent, xwin7 leve "Le fichier <x>u.dhps est une surcharge. Il ne peut etre charge directement" (cf. R-007).

```
# .dhpt de surcharge -- MAUVAIS
[sousprojets]
fic="gt_zoom articleu.dhps"," "    <- P17 : surcharge listee, retirer
fic="autre.dhps"," "                <- OK : .dhps standard, garder

# .dhpt de surcharge -- BON
[sousprojets]
fic="autre.dhps"," "
# gt_zoom articleu.dhps est auto-detectee, pas besoin de la lister
```

**Convention de detection** : nom de fichier dont le radical (avant `.dhps`) se termine par `u`. Le script `add_to_project.py` refuse cet ajout par defaut.

---

## Validation croisee

| Verification | Fichier | Sections impliquees |
|-------------|---------|---------------------|
| En-tete correct | .dhpt -> P05, .dhps -> P04 | Ligne 1 |
| Syntaxe fic | [fichiers] -> P07, [includes] -> P06 | Lignes fic= |
| zdiva.dhsp present | .dhps [includes] -> P09 | [includes] |
| Sections obligatoires | .dhpt -> P13, .dhps -> P12 | Toutes |
| Encodage ISO-8859-1 | Tous -> P01, P02, P16 | Fichier entier |
| Reference dans parent | .dhps -> P08 | [sousprojets] du .dhpt |
| Surcharge non listee | .dhpt -> P17 | [sousprojets] du .dhpt |
