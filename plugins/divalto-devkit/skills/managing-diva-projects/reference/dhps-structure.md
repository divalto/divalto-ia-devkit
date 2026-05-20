# Structure d'un fichier .dhps (sous-projet)

## Contenu

- En-tete
- Sections (dans l'ordre)
- Exemple complet
- Conventions de nommage

---


## En-tete

```
xwin-sprojet       2.0
```

Exactement `xwin-sprojet` suivi d'espaces puis `2.0`. Ne JAMAIS utiliser `xwin-projet` (anti-pattern P04).

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
- **Syntaxe : `fic="nom"," "`** -- AVEC `," "` (P07 si absent)
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
- **Syntaxe : `fic="nom"`** -- SANS `," "` (P06 si present)
- `zdiva.dhsp` TOUJOURS present (P09 si absent)
- Inclure les .dhsp de framework necessaires

### Difference critique [fichiers] vs [includes]

| Section | Syntaxe | Role | Erreur si inverse |
|---------|---------|------|-------------------|
| `[fichiers]` | `fic="nom"," "` | Fichiers sources propres | P07 |
| `[includes]` | `fic="nom"` | Dependances compilation | P06 |

C'est la difference syntaxique la plus critique. Se tromper provoque des erreurs de compilation.

### [autres] (OBLIGATOIRE, peut etre vide)

```ini
[autres]
```

Fichiers divers. **Toujours present**, meme vide (P12 si absent).

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
