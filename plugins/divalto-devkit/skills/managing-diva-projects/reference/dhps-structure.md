# Structure d'un fichier .dhps (sous-projet)

## Contenu

- En-tete
- Sections (dans l'ordre)
- Exemple complet
- Conventions de nommage

---


## En-tete

Deux variantes valides selon le contexte du projet :

| Cas | En-tete | Quand |
|-----|---------|-------|
| **Standard** | `xwin-sprojet       2.0` | .dhps d'un projet standard (nouveau sous-projet) |
| **Surcharge** | `xwin-s-sprojet     2.0` | .dhps qui surcharge un sous-projet du standard livre (nom `<base>u.dhps`) |

Anti-patterns associes :
- `xwin-projet` (ou `xwin-s-projet`) dans un .dhps -> PROJ04. Le type attendu vient de l'**extension** du fichier, pas de son en-tete
- `xwin-sprojet` dans une .dhps de surcharge -> xwin7 leve "n'est pas une surcharge de sous projet"

### Quand utiliser la variante surcharge

Une `.dhps` est une surcharge quand :
1. Son nom suit la convention `<base>u.dhps` (suffixe `u` avant l'extension)
2. Elle vit dans le repertoire `projets/` d'un **projet de surcharge** (`.dhpt` avec en-tete `xwin-s-projet`)
3. xwin7 l'auto-detecte via `cheminbases` -- elle surcharge `<base>.dhps` du standard livre

Le script `create_subproject.py` declenche automatiquement le mode surcharge si :
- Flag `--surcharge` explicite
- OU `--parent-dhpt <projet.dhpt>` ou le .dhpt parent a un en-tete `xwin-s-projet`

### Regle PROJ17 -- ne PAS lister une .dhps de surcharge dans [sousprojets]

xwin7 detecte automatiquement les surcharges. Si une `.dhps` de surcharge est listee dans `[sousprojets]` du `.dhpt` parent, xwin7 leve "Le fichier <x>u.dhps est une surcharge. Il ne peut etre charge directement".

Le script `add_to_project.py` refuse desormais l'ajout des `.dhps` de surcharge (PROJ17).

---

## Sections (dans l'ordre)

### [general] (OBLIGATOIRE)

```ini
[general]
date="20260204035419201299"
util="SC"
```

| Cle | Description | Exemple |
|-----|-------------|---------|
| date | Horodatage 20 caracteres : `YYYYMMDDHHMMSSmmm999` | `"20260204035419201299"` |
| util | Utilisateur createur | `"SC"` |

Proprietes optionnelles : `progexec`, `modeweb`, `typetransport`.

### [communs] (OPTIONNEL)

```ini
[communs]
incl="gt_base"," "
incl="gt_dictionnaires"," "
incl="gt_sql"," "
```

- Inclut des groupes definis dans le .dhpt parent
- Syntaxe : `incl="nom_groupe"," "`
- Les groupes referent des fichiers partages (dictionnaires, bases communes)

### [fichiers] (OBLIGATOIRE)

```ini
[fichiers]
fic="gtez099_sql.dhsf"," "
fic="gtpp099.dhsp"," "
fic="gtpz099.dhsp"," "
fic="gttq099.dhsq"," "
```

- Fichiers sources propres au sous-projet
- **Syntaxe : `fic="nom"," "`** -- AVEC `," "` (PROJ07 si absent)
- Types courants : .dhsf (masques), .dhsp (programmes), .dhsq (RecordSql), .dhsd (dictionnaires)
- Variante privee : `fic="nom","<priv>1"`

### [includes] (OBLIGATOIRE)

```ini
[includes]
fic="zdiva.dhsp"
fic="a5pcbaslic.dhsp"
fic="a5tcchk000.dhsp"
fic="gtpc000.dhsp"
fic="gttcficsql.dhsp"
```

- Dependances de compilation
- **Syntaxe : `fic="nom"`** -- SANS `," "` (PROJ06 si present)
- `zdiva.dhsp` : **convention de projet**, pas une obligation (PROJ09, hors jeu par defaut -- le standard livre ne le met jamais, 0/2304 `.dhps`)
- Inclure les .dhsp de framework necessaires

### Difference critique [fichiers] vs [includes]

| Section | Syntaxe | Role | Erreur si inverse |
|---------|---------|------|-------------------|
| `[fichiers]` | `fic="nom"," "` | Fichiers sources propres | PROJ07 |
| `[includes]` | `fic="nom"` | Dependances compilation | PROJ06 |

C'est la difference syntaxique la plus critique. Se tromper provoque des erreurs de compilation.

### [autres] (OBLIGATOIRE, peut etre vide)

```ini
[autres]
```

Fichiers divers. **Toujours present**, meme vide (PROJ12 si absent).

---

## Exemple complet

```ini
xwin-sprojet       2.0
[general]
date="20260409120000000099"
util="SC"
[communs]
incl="gt_base"," "
incl="gt_dictionnaires"," "
incl="gt_sql"," "
[fichiers]
fic="gtez099_sql.dhsf"," "
fic="gtpp099.dhsp"," "
fic="gtpz099.dhsp"," "
fic="gttq099.dhsq"," "
[includes]
fic="zdiva.dhsp"
fic="a5pcbaslic.dhsp"
fic="a5tcchk000.dhsp"
fic="gtpc000.dhsp"
fic="gttcficsql.dhsp"
[autres]

```

---

## Conventions de nommage

Format : `<prefixe>_<type> <entite>[_<suffixe>].dhps`

| Prefixe | Domaine |
|---------|---------|
| `gt_` | Commercial (DAV) |
| `gg_` | Production (GPAO) |
| `rt_` | Retail |
| `wm_` | WMS |
| `cc_` | Comptabilite |
| `gr_` | Relation tiers (CRM) |
| `ga_` | Affaires (GPA) |
| `pp_` | Paie |
| `tpv_` | Point de vente |
| `a5_` | Transverse/Outils |

Types courants : `zoom`, `table`, `base`, `outil`, `impression`, `administration`, `rf`, `search`.
