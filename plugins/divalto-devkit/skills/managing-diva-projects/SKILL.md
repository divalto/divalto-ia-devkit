---
name: managing-diva-projects
description: >
  Cree et modifie les fichiers projet Divalto : .dhpt (projet principal) et .dhps (sous-projet).
  Genere un .dhps avec toutes les sections obligatoires ([general], [communs], [fichiers],
  [includes], [autres]), l'ajoute dans [sousprojets] du .dhpt parent, et valide la structure
  complete contre les regles PROJ01-PROJ17. A utiliser pour declarer un nouveau sous-projet
  (nouvelle entite a compiler) ou modifier les fichiers/includes d'un .dhps existant.
---

# managing-diva-projects

## Contenu

- Utilisation rapide
- Workflow complet (3 etapes)
- Validation (PROJ01-PROJ17)
- Scripts disponibles
- References

---

## Utilisation rapide

### Creer un sous-projet

```json
{
    "name": "gt_zoom article",
    "util": "SC",
    "communs": ["gt_base", "gt_dictionnaires", "gt_sql"],
    "fichiers": ["gtez099_sql.dhsf", "gtpp099.dhsp", "gtpz099.dhsp", "gttq099.dhsq"],
    "includes": ["a5pcbaslic.dhsp", "a5tcchk000.dhsp", "gtpc000.dhsp", "gttcficsql.dhsp"]
}
```

```bash
echo '<json ci-dessus>' | py .claude/skills/managing-diva-projects/scripts/create_subproject.py \
    --stdin --output "gt_zoom article.dhps"
```

Le script ajoute automatiquement `zdiva.dhsp` dans [includes] s'il est absent.

### Ajouter dans le projet parent

```bash
py .claude/skills/managing-diva-projects/scripts/add_to_project.py \
    --dhpt "divalto achat-vente.dhpt" --dhps "gt_zoom article.dhps"
```

### Valider

```bash
py .claude/skills/managing-diva-projects/scripts/validate_project.py \
    --path "gt_zoom article.dhps" --dhpt "divalto achat-vente.dhpt"
```

---

## Workflow complet

### Etape 1 -- Preparer les parametres

Collecter :
- **name** : nom du sous-projet (convention `<prefixe>_<type> <entite>` ; suffixe `u` si surcharge -- ex: `gt_zoom articleu`)
- **util** : initiales utilisateur
- **communs** : groupes du .dhpt parent a inclure (dictionnaires, bases, sql)
- **fichiers** : fichiers sources propres (.dhsf, .dhsp, .dhsq)
- **includes** : dependances de compilation (.dhsp framework)
- **standard vs surcharge** : voir bloc ci-dessous

**Prefixes domaine** :

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

**Types courants** : `zoom`, `table`, `base`, `outil`, `impression`, `administration`, `rf`, `search`.

### Standard vs surcharge

Un projet de surcharge (`.dhpt` avec en-tete `xwin-s-projet`) heberge des `.dhps` qui surchargent les sous-projets du standard livre. Les regles different :

| Aspect | .dhps standard | .dhps de surcharge |
|--------|----------------|--------------------|
| Nom | `gt_zoom article.dhps` | `gt_zoom articleu.dhps` (suffixe `u`) |
| En-tete | `xwin-sprojet 2.0` | `xwin-s-sprojet 2.0` |
| .dhpt parent | `xwin-projet 2.0` | `xwin-s-projet 2.0` |
| Dans [sousprojets] du .dhpt | Oui (PROJ08) | **Non** (PROJ17) -- auto-detectee via `cheminbases` |

`create_subproject.py` bascule en mode surcharge via :
- `--surcharge` (flag explicite)
- `--parent-dhpt <projet.dhpt>` (auto-detection : si en-tete `xwin-s-projet`, mode surcharge)

`add_to_project.py` refuse l'ajout d'une `.dhps` de surcharge dans `[sousprojets]` (garde-fou PROJ17).

Voir [reference/dhps-structure.md](reference/dhps-structure.md) section "En-tete" pour les regles xwin7 exactes.

### Etape 2 -- Generer et inserer

1. Generer le .dhps avec `create_subproject.py` (ecrit directement en
   ISO-8859-1 + CRLF, pas de conversion ulterieure necessaire)
2. Ajouter dans [sousprojets] du .dhpt parent avec `add_to_project.py`
   (lecture/ecriture binaire, preserve ISO-8859-1 + CRLF + accents)

**Note** : `add_to_project.py --dhps` accepte un chemin relatif ou absolu ;
seul le nom simple (basename) est ecrit dans `[sousprojets]` car c'est ce
qu'attend `xwin7 -sousproject`.

### Etape 3 -- Valider

```bash
py .claude/skills/managing-diva-projects/scripts/validate_project.py \
    --path "mon_sous_projet.dhps" --dhpt "parent.dhpt"
```

Verifications effectuees :
- En-tete correct (`xwin-sprojet`/`xwin-s-sprojet` pour .dhps, `xwin-projet`/`xwin-s-projet` pour .dhpt)
- Sections obligatoires presentes
- Syntaxe `fic=` correcte ([fichiers] avec `," "`, [includes] sans)
- `zdiva.dhsp` present dans [includes]
- Encodage ISO-8859-1 et CRLF
- Reference dans [sousprojets] du parent (si `--dhpt` fourni)
- Aucune `.dhps` de surcharge (`<base>u.dhps`) dans [sousprojets] (PROJ17)

Si erreurs : corriger et re-valider.

---

## Validation

### Anti-patterns verifies (PROJ01-PROJ17)

| Code | Severite | Regle |
|------|----------|-------|
| PROJ01 | error | Encodage UTF-8 interdit (ISO-8859-1 requis) |
| PROJ02 | error | Fins de ligne LF interdites (CRLF requis) |
| PROJ03 | *consigne, non verifiee* | Ne pas utiliser Edit/Write de Claude Code sur fichiers accentues -- le hook `protect_encoding.py` l'applique, pas le validateur |
| PROJ04 | error | **.dhps** : en-tete invalide -- attendu `xwin-sprojet` (ou `xwin-s-sprojet` pour une surcharge). Le type controle vient de l'**extension**, pas de l'en-tete |
| PROJ05 | error | **.dhpt** : en-tete invalide -- attendu `xwin-projet` (ou `xwin-s-projet` pour une surcharge). Un code par extension : PROJ04 pour le `.dhps`, PROJ05 pour le `.dhpt` |
| PROJ06 | error | `fic="nom"," "` interdit dans [includes] |
| PROJ07 | error | `fic="nom"` sans `," "` interdit dans [fichiers] |
| PROJ08 | error | .dhps **standard** non reference dans [sousprojets] du .dhpt parent (**exemptee pour une .dhps de surcharge** `xwin-s-sprojet` -- cf. PROJ17) |
| PROJ09 | `info` **hors defaut** | `zdiva.dhsp` absent de [includes] -- **convention**, `--with-rules PROJ09`. Le standard livre ne le fait **jamais** (0/2304 `.dhps`), un specifique le fait a 80-98 % |
| PROJ10 | warning | Groupes communs manquants dans [communs] |
| PROJ11 | *non implementee* | Melange de prefixes domaine -- annoncee, codee nulle part (ni ici, ni chez le linter) |
| PROJ12 | error | Section [autres] absente en fin de .dhps |
| PROJ13 | error | Sections obligatoires absentes dans .dhpt |
| PROJ14 | error | Accent manquant dans `developpement` (profil) |
| PROJ15 | error | Accent manquant dans `developpement_x13.txt` (implicites) |
| PROJ16 | warning | Pas de verification d'encodage finale |
| PROJ17 | error | `.dhps` de surcharge (`<base>u.dhps`) listee dans [sousprojets] |

Detail complet : [reference/project-anti-patterns.md](reference/project-anti-patterns.md) (PROJ01-PROJ17)

### Difference critique : [fichiers] vs [includes]

| Section | Syntaxe | Erreur si inverse |
|---------|---------|-------------------|
| `[fichiers]` | `fic="nom"," "` | PROJ07 |
| `[includes]` | `fic="nom"` | PROJ06 |

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `create_subproject.py` | Genere un .dhps complet | JSON (--stdin) | Fichier .dhps (--output) ou stdout |
| `add_to_project.py` | Ajoute un .dhps dans [sousprojets] d'un .dhpt | --dhpt + --dhps | JSON resultat + .dhpt modifie |
| `validate_project.py` | Valide structure .dhpt ou .dhps (PROJ01-PROJ17). Le type controle vient de l'**extension** ; l'en-tete est ce qu'on lui compare (PROJ04/PROJ05) | --path [--dhpt] [--with-rules PROJ09] | JSON (valid, type, type_annonce_par_entete, errors, warnings) |
| `cleanup_communs_from_subproject.py` | Retire des entrees temporaires de `[fichiers]` (cleanup post-compilation) | --path .dhps --remove FICHIER (repetable) | JSON (removed, kept, backup) + .dhps modifie (+ .bak) |

> **Workaround [communs]** : pour le pattern "pousser temporairement
> un `.dhsd` ou `.dhsp` de `[communs]` du `.dhpt` parent vers `[fichiers]` du
> `.dhps` avant `xwin7 -sousproject`", voir `compiling-diva-projects` section
> "Piege [communs]". Une fois la compilation OK, lancer
> `cleanup_communs_from_subproject.py` pour retirer ces entrees temporaires
> (CP6bis de `creating-diva-entity`).

**Convention** : tous les scripts utilisent `py` comme lanceur, sortie JSON sur stdout, erreurs sur stderr. Exit code 0 = succes, 1 = erreur.

> **Regles hors jeu par defaut** -- audit de **convention** : le constat n'est ni une
> erreur de compilation ni un dysfonctionnement, et ne rend pas le fichier invalide.
> Aujourd'hui : **`PROJ09`** (`zdiva.dhsp` dans `[includes]` -- le standard livre ne le fait
> **jamais**, 0/2304 `.dhps` ; un specifique le fait a 80-98 %). Activation :
> `--with-rules PROJ09`.
>
> **`--with-rules` AJOUTE au jeu normal**, il ne filtre pas -- a ne pas confondre avec le
> `--rules` de `linting-diva-code`, qui n'execute QUE les regles nommees. Un validateur
> structurel prive de ses controles de structure n'aurait aucun sens : deux sens
> differents, deux noms d'option differents.

---

## Tests

Les regles d'en-tete et de convention ont une suite executable, sans poste Divalto :

```
py .claude/skills/managing-diva-projects/tests/run_all.py
```

A lancer apres toute modification de `scripts/validate_project.py`. Chaque cas rejoue un
defaut reel : PROJ04/PROJ05 etaient **inatteignables** (le type etait deduit de l'en-tete meme
qu'elles validaient, donc un melange en-tete/extension repondait `valid: true`), et PROJ09
etait une `error` « obligatoire » sur une simple convention. Detail :
[tests/README.md](tests/README.md).

---

## References

- [Structure .dhpt](reference/dhpt-structure.md) -- sections, proprietes, arborescence
- [Structure .dhps](reference/dhps-structure.md) -- sections, difference [fichiers]/[includes], conventions nommage
- [Anti-patterns PROJ01-PROJ17](reference/project-anti-patterns.md) -- detail, exemples, corrections
