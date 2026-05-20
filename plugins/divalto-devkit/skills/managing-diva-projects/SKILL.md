---
name: managing-diva-projects
description: >
  Cree et modifie les fichiers projet Divalto : .dhpt (projet principal) et .dhps (sous-projet).
  Genere un .dhps avec toutes les sections obligatoires ([general], [communs], [fichiers],
  [includes], [autres]), l'ajoute dans [sousprojets] du .dhpt parent, et valide la structure
  complete contre les regles P01-P16. A utiliser pour declarer un nouveau sous-projet
  (nouvelle entite a compiler) ou modifier les fichiers/includes d'un .dhps existant.
---

# managing-diva-projects

## Contenu

- Utilisation rapide
- Workflow complet (3 etapes)
- Validation (P01-P16)
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
- **name** : nom du sous-projet (convention `<prefixe>_<type> <entite>`)
- **util** : initiales utilisateur
- **communs** : groupes du .dhpt parent a inclure (dictionnaires, bases, sql)
- **fichiers** : fichiers sources propres (.dhsf, .dhsp, .dhsq)
- **includes** : dependances de compilation (.dhsp framework)

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

**Check SVN pre-modification** (optionnel) : avant de modifier un fichier projet .dhpt/.dhps existant, verifier les modifs locales non committees et l'activite recente pour detecter un refactor en cours.

```bash
py .claude/skills/managing-diva-projects/scripts/check_svn_recent.py     --path "{DHPT_PATH}" --limit 5 --days 30
```

Si `warning != null` ou `local_changes.has_changes=true`, signaler au collaborateur avant de poursuivre. Degradation gracieuse si SVN indispo. Voir [reference/svn-policy.md](reference/svn-policy.md).

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
- En-tete correct (`xwin-sprojet` pour .dhps, `xwin-projet` pour .dhpt)
- Sections obligatoires presentes
- Syntaxe `fic=` correcte ([fichiers] avec `," "`, [includes] sans)
- `zdiva.dhsp` present dans [includes]
- Encodage ISO-8859-1 et CRLF
- Reference dans [sousprojets] du parent (si `--dhpt` fourni)

Si erreurs : corriger et re-valider.

---

## Validation

### Anti-patterns verifies (P01-P16)

| Code | Severite | Regle |
|------|----------|-------|
| P01 | error | Encodage UTF-8 interdit (ISO-8859-1 requis) |
| P02 | error | Fins de ligne LF interdites (CRLF requis) |
| P03 | error | Ne pas utiliser Edit/Write de Claude Code sur fichiers avec accents |
| P04 | error | En-tete `xwin-projet` interdit dans .dhps |
| P05 | error | En-tete `xwin-sprojet` interdit dans .dhpt |
| P06 | error | `fic="nom"," "` interdit dans [includes] |
| P07 | error | `fic="nom"` sans `," "` interdit dans [fichiers] |
| P08 | error | .dhps non reference dans [sousprojets] du .dhpt parent |
| P09 | error | `zdiva.dhsp` absent de [includes] |
| P10 | warning | Groupes communs manquants dans [communs] |
| P11 | warning | Melange de prefixes domaine |
| P12 | error | Section [autres] absente en fin de .dhps |
| P13 | error | Sections obligatoires absentes dans .dhpt |
| P14 | error | Accent manquant dans `developpement` (profil) |
| P15 | error | Accent manquant dans `developpement_x13.txt` (implicites) |
| P16 | warning | Pas de verification d'encodage finale |

Detail complet : [reference/project-anti-patterns.md](reference/project-anti-patterns.md)

### Difference critique : [fichiers] vs [includes]

| Section | Syntaxe | Erreur si inverse |
|---------|---------|-------------------|
| `[fichiers]` | `fic="nom"," "` | P07 |
| `[includes]` | `fic="nom"` | P06 |

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `create_subproject.py` | Genere un .dhps complet | JSON (--stdin) | Fichier .dhps (--output) ou stdout |
| `add_to_project.py` | Ajoute un .dhps dans [sousprojets] d'un .dhpt | --dhpt + --dhps | JSON resultat + .dhpt modifie |
| `validate_project.py` | Valide structure .dhpt ou .dhps (P01-P16) | --path [--dhpt] | JSON (valid, errors, warnings) |
| `cleanup_communs_from_subproject.py` | Retire des entrees temporaires de `[fichiers]` (cleanup post-compilation) | --path .dhps --remove FICHIER (repetable) | JSON (removed, kept, backup) + .dhps modifie (+ .bak) |

> **Workaround [communs]** : pour le pattern "pousser temporairement
> un `.dhsd` ou `.dhsp` de `[communs]` du `.dhpt` parent vers `[fichiers]` du
> `.dhps` avant `xwin7 -sousproject`", voir `compiling-diva-projects` section
> "Piege [communs]". Une fois la compilation OK, lancer
> `cleanup_communs_from_subproject.py` pour retirer ces entrees temporaires
> (CP6bis de `creating-diva-entity`).

**Convention** : tous les scripts utilisent `py` comme lanceur, sortie JSON sur stdout, erreurs sur stderr. Exit code 0 = succes, 1 = erreur.

---

## References

- [Structure .dhpt](reference/dhpt-structure.md) -- sections, proprietes, arborescence
- [Structure .dhps](reference/dhps-structure.md) -- sections, difference [fichiers]/[includes], conventions nommage
- [Anti-patterns P01-P16](reference/project-anti-patterns.md) -- detail, exemples, corrections
