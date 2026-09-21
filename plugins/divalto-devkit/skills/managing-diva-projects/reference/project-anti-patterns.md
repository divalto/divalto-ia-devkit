# Anti-patterns projet (PROJ01-PROJ17)

## Contenu

- Table de reference rapide
- Detail par anti-pattern
- Validation croisee

---


## Table de reference rapide

| Code | Severite | Anti-pattern | Correction | Regle linter |
|------|----------|-------------|------------|--------------|
| PROJ01 | error | Encodage UTF-8 dans .dhpt/.dhps | Encoder en ISO-8859-1 | `P01` |
| PROJ02 | error | Fins de ligne LF au lieu de CRLF | Utiliser CRLF (`\r\n`) | `P02` |
| PROJ03 | *consigne, non verifiee* | Edit/Write de Claude Code sur fichiers avec accents | Utiliser Bash (head/tail) ou reconvertir (iconv + sed) | `P03` |
| PROJ04 | error | **.dhps** : en-tete invalide | Utiliser `xwin-sprojet 2.0` (standard) ou `xwin-s-sprojet 2.0` (surcharge) | `P04` |
| PROJ05 | error | **.dhpt** : en-tete invalide | Utiliser `xwin-projet 2.0` (standard) ou `xwin-s-projet 2.0` (surcharge) | `P05` |
| PROJ06 | error | Syntaxe `fic="nom"," "` dans [includes] | Utiliser `fic="nom"` sans virgule | `P06` |
| PROJ07 | error | Syntaxe `fic="nom"` sans `," "` dans [fichiers] | Utiliser `fic="nom"," "` | `P07` |
| PROJ08 | error | .dhps non reference dans [sousprojets] du .dhpt | Ajouter `fic="nom.dhps"," "` dans [sousprojets] | `P08` |
| PROJ09 | `info` **hors defaut** | `zdiva.dhsp` absent de [includes] -- **convention de projet** | Si la convention du projet est de l'inclure : `fic="zdiva.dhsp"`. Activation : `--with-rules PROJ09` | `P09` |
| PROJ10 | warning | Groupes communs manquants dans [communs] du .dhps | Ajouter les `incl=` necessaires | `P10` |
| PROJ11 | *non implementee* | Melange de prefixes domaine dans un projet | Respecter le prefixe domaine | `P11` |
| PROJ12 | error | .dhps sans section [autres] en fin | Toujours ajouter `[autres]` | `P12` |
| PROJ13 | error | .dhpt sans [projetsfusion], [fabricationmere] ou [autres] | Toujours inclure les 3 sections | `P13` |
| PROJ14 | error | `developpement` sans accent dans nom de profil | Ecrire `\xe9` (ISO-8859-1) pour l'accent | `P14` |
| PROJ15 | error | `developpement_x13.txt` sans accent dans implicites | Ecrire `\xe9` dans le nom de fichier | `P15` |
| PROJ16 | warning | Pas de verification d'encodage finale | Verifier avec `file --mime-encoding` | `P16` |
| PROJ17 | error | `.dhps` de surcharge (**en-tete `xwin-s-sprojet`**) listee dans `[sousprojets]` | Retirer la ligne -- xwin7 auto-detecte la surcharge via `cheminbases`. Detection par l'**en-tete**, jamais par le suffixe `u` du nom | -- |

> **La colonne « Regle linter ».** Un producteur et `lint_diva.py` verifient parfois
> la meme chose et le disent avec deux codes : cette colonne fait le lien. C'est ici
> la paire la plus alignee du plugin -- **seize sur dix-sept**, libelle pour libelle.
> Seule `PROJ17` n'a pas de vis-a-vis : le linter s'arrete a `P16`.
>
> **Trois de ces seize meritent une precision.**
> Le linter marque `P08`, `P10` et `P16` en *V2* : il les declare et ne les execute
> pas. Ce producteur, lui, les verifie. Le renvoi dit donc ou le numero existe, pas
> qu'il soit actif des deux cotes.
>
> **Et deux lignes de cette table ne sont pas des verifications.** `PROJ03` est une
> consigne a l'operateur : ne pas editer un fichier accentue avec Edit/Write. Ce qui
> la fait respecter est le hook `protect_encoding.py`, pas le validateur -- la
> chercher dans une sortie JSON serait vain. `PROJ11` (melange de prefixes domaine)
> est annoncee et codee nulle part : ni ici, ni chez le linter, dont la table la
> presente pourtant comme un `warning` actif.

---

## Detail par anti-pattern

### PROJ01 -- Encodage UTF-8

**Probleme** : les accents sont corrompus (`\xc3\xa9` au lieu de `\xe9`), le compilateur Divalto echoue.

**Verification** :
```bash
file --mime-encoding fichier.dhps
# Attendu : iso-8859-1, unknown-8bit, ou us-ascii
# Erreur : utf-8
```

### PROJ02 -- Fins de ligne LF

**Probleme** : tous les fichiers texte Divalto utilisent CRLF. LF seul corrompt la structure.

**Verification** :
```bash
file fichier.dhps
# Doit contenir "CRLF" ou "with CR"
```

### PROJ03 -- Edit/Write de Claude Code

**Probleme** : les outils Edit et Write de Claude Code convertissent automatiquement en UTF-8 avec LF, corrompant les accents et les fins de ligne.

**Solution** : utiliser le skill `writing-diva-files` (methodes Bash avec head/tail, ou reconversion iconv + sed).

### PROJ04 -- En-tete projet dans un sous-projet

**Probleme** : un .dhps doit utiliser `xwin-sprojet` (standard) ou `xwin-s-sprojet` (surcharge), pas `xwin-projet`.

```
# MAUVAIS (dans un .dhps)
xwin-projet        2.0

# BON (sous-projet standard)
xwin-sprojet       2.0

# BON (sous-projet de surcharge -- nom <base>u.dhps)
xwin-s-sprojet     2.0
```

Confondre les deux variantes (`xwin-sprojet` vs `xwin-s-sprojet`) provoque l'erreur xwin7 "n'est pas une surcharge de sous projet".

### PROJ05 -- En-tete sous-projet dans un projet

**Probleme** : un .dhpt doit utiliser `xwin-projet` (standard) ou `xwin-s-projet` (surcharge), pas `xwin-sprojet`.

```
# BON (projet standard)
xwin-projet        2.0

# BON (projet de surcharge)
xwin-s-projet      2.0
```

### PROJ06 -- Virgule dans [includes]

**Probleme** : la section `[includes]` n'accepte PAS la virgule-espace.

```ini
# MAUVAIS
[includes]
fic="zdiva.dhsp"," "

# BON
[includes]
fic="zdiva.dhsp"
```

### PROJ07 -- Pas de virgule dans [fichiers]

**Probleme** : la section `[fichiers]` EXIGE la virgule-espace.

```ini
# MAUVAIS
[fichiers]
fic="monprog.dhsp"

# BON
[fichiers]
fic="monprog.dhsp"," "
```

### PROJ08 -- Sous-projet non reference

**Probleme** : un .dhps non declare dans `[sousprojets]` du .dhpt parent ne sera pas compile.

**Exemption surcharge** : la regle **ne s'applique PAS** a une `.dhps` de surcharge (en-tete `xwin-s-sprojet`, nom `<base>u.dhps`). Une surcharge ne doit **jamais** figurer dans `[sousprojets]` (cf. PROJ17 -- xwin7 l'auto-detecte via `cheminbases`) ; l'exiger contredirait PROJ17. `validate_project.py --dhpt` detecte la surcharge par l'en-tete et **saute PROJ08** dans ce cas (issues #306 / #340).

### PROJ09 -- zdiva.dhsp manquant (CONVENTION, hors jeu par defaut)

**Ce n'est pas un defaut** : c'est une convention de projet. Mesure sur sources reelles --
le **standard X.13 livre ne met JAMAIS `zdiva.dhsp`** dans les `[includes]` de ses
sous-projets (**0 sur 2304** `.dhps`), alors qu'un specifique partenaire le fait a
**80-98 %**. En `error` et active par defaut, la regle rendait `valid: false` sur 100 %
des sous-projets du standard -- que l'on valide couramment comme **modele de reference**.

Elle est donc **hors du jeu par defaut**, en severite `info`, et s'active explicitement
si la convention du projet est bien d'inclure `zdiva.dhsp` :

```
py .claude/skills/managing-diva-projects/scripts/validate_project.py --path mon_sousprojet.dhps --with-rules PROJ09
```

```ini
[includes]
fic="zdiva.dhsp"
```

> **`--with-rules` AJOUTE, il ne filtre pas.** A ne pas confondre avec le `--rules` de
> `linting-diva-code`, qui **filtre** (n'execute que les regles nommees). Ici les
> controles de structure restent tous actifs : un validateur qui en serait prive
> n'aurait aucun sens. Deux sens differents, deux noms d'option differents.

### PROJ10 -- Groupes communs manquants

**Probleme** : les definitions partagees (dictionnaires, bases) sont inaccessibles. Verifier que les groupes necessaires du .dhpt parent sont inclus dans `[communs]`.

### PROJ11 -- Melange de prefixes

**Probleme** : un sous-projet `rt_` ne devrait pas inclure des groupes `gt_` sauf si transverse. Respecter la coherence de prefixe domaine.

### PROJ12 -- Section [autres] absente (.dhps)

**Probleme** : `[autres]` est obligatoire en fin de .dhps, meme vide.

### PROJ13 -- Sections obligatoires absentes (.dhpt)

**Probleme** : `[projetsfusion]`, `[fabricationmere]` et `[autres]` sont obligatoires dans un .dhpt, meme vides.

### PROJ14 -- Accent manquant dans nom de profil

**Probleme** : le profil standard est `développement` avec accent aigu ISO-8859-1 (`\xe9`). Sans accent, la comparaison echoue.

### PROJ15 -- Accent manquant dans nom implicites

**Probleme** : le fichier implicite standard est `développement_x13.txt`. Meme regle que PROJ14.

### PROJ16 -- Pas de verification d'encodage

**Bonne pratique** : toujours verifier avec `file --mime-encoding` apres creation/modification. Le resultat ne doit JAMAIS etre `utf-8`.

### PROJ17 -- .dhps de surcharge listee dans [sousprojets]

**Probleme** : xwin7 auto-detecte les `.dhps` de surcharge (`<base>u.dhps`) via `cheminbases`. Si la `.dhps` de surcharge est listee dans `[sousprojets]` du `.dhpt` parent, xwin7 leve "Le fichier <x>u.dhps est une surcharge. Il ne peut etre charge directement".

```
# .dhpt de surcharge -- MAUVAIS
[sousprojets]
fic="gt_zoom articleu.dhps"," "    <- PROJ17 : surcharge listee, retirer
fic="autre.dhps"," "                <- OK : .dhps standard, garder

# .dhpt de surcharge -- BON
[sousprojets]
fic="autre.dhps"," "
# gt_zoom articleu.dhps est auto-detectee, pas besoin de la lister
```

> **Detection par l'EN-TETE, jamais par le nom.** Le suffixe `u` est une convention
> de nommage, pas un marqueur : sur un corpus reel de **2513 entrees `[sousprojets]`**,
> le test `nom.endswith("u")` produisait **31 faux positifs et zero vrai positif** -- il
> flaguait tout mot finissant par la lettre `u` : `gt_menu.dhps`, `a5_menu.dhps`,
> `rc_cpt_bordereau.dhps`, `pp_zoom individu.dhps`, `...lieu.dhps`, `...fou.dhps`,
> `...visu.dhps`. Dont **30 noms figurant dans des `.dhpt` du standard livre**.
>
> `validate_project.py` lit donc la premiere ligne de la `.dhps` referencee et ne
> conclut que sur `xwin-s-sprojet`. Si le fichier est introuvable a cote du `.dhpt`,
> **il se tait** : on ne peut pas savoir. Meme regle dans `add_to_project.py`, qui
> **refusait l'ajout** de ces 31 noms -- un refus d'ecriture bloque le travail, la ou
> un faux constat ne fait que fatiguer ; quand le fichier n'existe pas encore, il
> ajoute et signale l'incertitude dans son JSON (`warning`).

**Convention de detection** : nom de fichier dont le radical (avant `.dhps`) se termine par `u`. Le script `add_to_project.py` refuse cet ajout par defaut.

> **Corollaire a la compilation (#308)** : puisque la surcharge n'est **pas** dans `[sousprojets]`, elle n'est **pas ciblable** par `-sousproject "<base>u.dhps"` (xwin7 : « inexistant dans le projet »). Pour la compiler en cible, viser le **nom STANDARD sans `u`** (`-sousproject "<base>.dhps"`, xwin7 applique la surcharge auto) ; a defaut de sous-projet standard, `buildall` global. Detail : skill **compiling-diva-projects** (#224/#308).

---

## Validation croisee

| Verification | Fichier | Sections impliquees |
|-------------|---------|---------------------|
| En-tete correct | .dhpt -> PROJ05, .dhps -> PROJ04 (**un code par extension**) | Ligne 1 |
| Syntaxe fic | [fichiers] -> PROJ07, [includes] -> PROJ06 | Lignes fic= |
| zdiva.dhsp present | .dhps [includes] -> PROJ09 (**hors defaut**, `--with-rules PROJ09`) | [includes] |
| Sections obligatoires | .dhpt -> PROJ13, .dhps -> PROJ12 | Toutes |
| Encodage ISO-8859-1 | Tous -> PROJ01, PROJ02, PROJ16 | Fichier entier |
| Reference dans parent | .dhps -> PROJ08 | [sousprojets] du .dhpt |
| Surcharge non listee | .dhpt -> PROJ17 | [sousprojets] du .dhpt |
