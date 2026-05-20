---
name: modifying-diva-entity
description: >
  Modifie une entite metier DIVA existante : ajout de champ(s), modification de
  Nature/type, suppression de champ. Met a jour le dictionnaire (.dhsd) avec
  recalcul automatique des positions, le masque ecran (.dhsf), recompile et
  synchronise SQL. Orchestration LLM avec 4 checkpoints de validation humaine.
  A utiliser quand le developpeur veut faire evoluer une table existante (ajouter,
  modifier ou supprimer un champ) avec propagation dictionnaire -> masque -> SQL.
---

# Modifying DIVA Entity

## Contenu

- Operations supportees
- Workflow complet (7 etapes, 4 checkpoints)
- Scripts disponibles
- References

---

## Operations supportees

| Operation | Description | Impact masque | Impact SQL |
|-----------|-------------|---------------|------------|
| **Ajout** | Ajouter un ou plusieurs champs a une table existante | Oui (add-field) | Oui (ADD COLUMN) |
| **Modification** | Changer la Nature/type d'un champ existant | Non | Oui (ALTER COLUMN) |
| **Suppression** | Retirer un champ d'une table | Oui (remove widget) | Oui (DROP COLUMN, perte de donnees) |
| **Ajout FK** | Brancher un zoom standard sur un champ existant (FK vers T013, T007, ART, CLI, ...) | Oui (f8, callback, bouton zoom) | Non |

---

## Prerequis

Skills necessaires sur le poste :
- `managing-diva-dictionaries` (validation post-modification)
- `manipulating-dhsf-screens` (mise a jour masque)
- `compiling-diva-projects` (recompilation)
- `syncing-diva-sql` (synchronisation SQL)

---

## Workflow complet

### Parametres a obtenir du collaborateur

| Parametre | Exemple | Requis |
|-----------|---------|--------|
| Operation | add / modify / remove / **add-fk** | Oui |
| Dictionnaire (.dhsd) | gtfdd.dhsd | Selon operation (non requis pour add-fk) |
| Table | Livre | Oui |
| Champ(s) | NbPages / RacPays | Oui |
| Nature (add/modify) | 11,0 | Selon operation |
| Apres (add) | Libelle | Optionnel |
| Cible FK (add-fk) | T013 / T007 / ART / CLI | Oui pour add-fk |
| Numero zoom (add-fk) | 9053 | Optionnel (advisory, pour le masque) |
| Chemin Module Check (add-fk) | gttmchk{entite}.dhsp | Oui pour add-fk |
| Chemin masque (add-fk) | gtez{entite}_sql.dhsf | Oui pour add-fk |

---

### Etape 1 : Etat actuel de la table

```bash
py .claude/skills/modifying-diva-entity/scripts/modify_dhsd_table.py \
    --action list-fields --dhsd "{DHSD_PATH}" --table "{TABLE}"
```

Presenter au collaborateur : champs, positions, tailles, Nature, index.

### Etape 2 : Analyse d'impact

Selon l'operation :

**Ajout** : calculer la taille du nouveau champ (`nature_to_size`), montrer quels champs seront decales, impact sur Filler/Taille.

**Modification** : calculer le delta de taille (ancienne Nature vs nouvelle), montrer la cascade de repositionnement. Si le champ est dans un index, signaler le recalcul des positions cumulees.

**Suppression** : avertir explicitement de la **perte de donnees irreversible** apres synchro SQL. Lister les index impactes.

**Check SVN pre-modification** (optionnel, S-16) : si un acces SVN lecture seule est disponible, verifier l'activite recente du dictionnaire pour detecter un refactor en cours qui pourrait entrer en collision.

```bash
py .claude/skills/modifying-diva-entity/scripts/check_svn_recent.py \
    --path "{DHSD_PATH}" --limit 5 --days 30
```

Si le JSON retourne `warning != null` (>= 2 commits recents), signaler au collaborateur et coordonner avec l'auteur avant de poursuivre. Si `svn_available=false`, continuer sans enrichissement (degradation gracieuse). Voir [reference/svn-policy.md](reference/svn-policy.md) pour la policy.

> **CHECKPOINT CP1 -- Intention et impact**
> Presenter :
> - L'operation demandee et le(s) champ(s) concerne(s)
> - L'etat actuel (positions, Taille)
> - L'impact prevu (champs decales, delta Taille, index impactes)
> - Pour suppression : avertissement perte de donnees
> Attendre validation avant de modifier le dictionnaire.

### Etape 3 : Modification du dictionnaire

**Ajout :**
```bash
py .claude/skills/modifying-diva-entity/scripts/modify_dhsd_table.py \
    --action add-field --dhsd "{DHSD_PATH}" --table "{TABLE}" \
    --name "{CHAMP}" --nature "{NATURE}" --after "{APRES}" --backup
```

**Modification :**
```bash
py .claude/skills/modifying-diva-entity/scripts/modify_dhsd_table.py \
    --action modify-field --dhsd "{DHSD_PATH}" --table "{TABLE}" \
    --name "{CHAMP}" --new-nature "{NATURE}" --backup
```

**Suppression :**
```bash
py .claude/skills/modifying-diva-entity/scripts/modify_dhsd_table.py \
    --action remove-field --dhsd "{DHSD_PATH}" --table "{TABLE}" \
    --name "{CHAMP}" --backup
```

### Etape 4 : Validation dictionnaire

```bash
py .claude/skills/managing-diva-dictionaries/scripts/validate_dhsd.py \
    --path "{DHSD_PATH}" --table "{TABLE}"
```

Doit retourner 0 erreurs. Puis re-lister les champs pour montrer l'etat final :

```bash
py .claude/skills/modifying-diva-entity/scripts/modify_dhsd_table.py \
    --action list-fields --dhsd "{DHSD_PATH}" --table "{TABLE}"
```

> **CHECKPOINT CP2 -- Dictionnaire modifie**
> Presenter :
> - Comparaison avant/apres (positions, Taille, Filler)
> - Resultat de validation D01-D11 (0 erreurs)
> - Fichier backup cree (.bak)
> Attendre validation avant de modifier le masque.

### Etape 5 : Mise a jour du masque (ajout et suppression uniquement)

**Ajout de champ :**
```bash
py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_modify.py \
    --path "{DHSF_PATH}" --action add-field --params '{
        "page_numero": {PAGE},
        "label": "{LABEL}",
        "vue": "{VUE}",
        "champ": "{CHAMP_LOWER}",
        "alias": "{ALIAS}"
    }'
```

**Suppression de champ :** pas de script `remove-field` dans `dhsf_modify.py`. Procedure manuelle :
1. Parser le masque : `py .../dhsf_parser.py --path "{DHSF_PATH}" --summary`
2. Localiser les widgets referençant le champ (chercher `donnee=...,{champ},...`)
3. Supprimer les blocs `[champ]` et `[obj_texte]` correspondants via `writing-diva-files`

**Modification de Nature :** aucun changement de masque necessaire (le binding `donnee=` ne reference pas la Nature). Passer directement a l'etape 6.

**Ajout FK (operation `add-fk`) :** delegue au skill `binding-zoom-to-field` (FK-05). Cette operation ne touche PAS au dictionnaire (etapes 3-4 sont skippees) ; seuls le Module Check (.dhsp) et le masque (.dhsf) sont modifies.

```bash
# Couche 1 : Module Check
py .claude/skills/binding-zoom-to-field/scripts/dhsp_add_fk.py \
    --path "{DHSP_MCHK_PATH}" \
    --src-table {TABLE_MAJUSCULE} \
    --fk {CHAMP}:{TARGET}[:{ZOOM}]

# Couches 2 + 3 : masque (structurel + callback [diva])
py .claude/skills/manipulating-dhsf-screens/scripts/dhsf_add_fk.py \
    --path "{DHSF_PATH}" \
    --src-table {TABLE_MAJUSCULE} \
    --fk {CHAMP}:{TARGET}[:{ZOOM}]
```

Le champ cible doit **deja exister** dans le dictionnaire et dans le masque (sinon utiliser `add` pour l'ajouter puis `add-fk`). Cf. [binding-zoom-to-field/SKILL.md](../binding-zoom-to-field/SKILL.md) pour les regles de detection (dict, NomVue, prefix) et les limitations V1 (cardinalite 1:1).

> **CHECKPOINT CP3 -- Masque mis a jour** _(skip si modification de Nature)_
> Presenter : champ(s) ajoute(s)/supprime(s), page, IDs alloues.
> Pour `add-fk` : presenter les imports Module ajoutes, les procedures `Check_*_Field_*` generees, les f8/diva_apres injectes dans le masque, le nom de la procedure `Champ_*_Ap` et son `<id>` sequentiel.
> Attendre validation avant de compiler.

### Etape 6 : Compilation

```bash
py .claude/skills/compiling-diva-projects/scripts/generate_harness.py \
    --sources "{FICHIERS_MODIFIES}" --with-zdiva --with-communs
```

Puis executer le script de compilation et parser le rapport.

### Etape 7 : Synchronisation SQL

Suivre le workflow `syncing-diva-sql` pour mettre a jour la structure SQL.

> **CHECKPOINT CP4 -- Compilation + synchro SQL**
> Presenter : resultat compilation (0 erreurs ou liste), resultat synchro.
> Workflow termine. Proposer au collaborateur de tester dans l'ERP.

---

## Scripts disponibles

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/modify_dhsd_table.py` | Modifie les tables d'un .dhsd | `--action` `--dhsd` `--table` [+ args action] | Voir ci-dessous |
| `scripts/_nature_to_size.py` | Module interne (vendoring) | Import uniquement | - |

### Actions de modify_dhsd_table.py

| Action | Parametres supplementaires | Sortie |
|--------|---------------------------|--------|
| `list-fields` | _(aucun)_ | `{fields[], taille, indexes[]}` |
| `add-field` | `--name` `--nature` [`--after`] [`--dry-run`] [`--backup`] | `{field, position, taille_before, taille_after, champ_created}` |
| `modify-field` | `--name` `--new-nature` [`--dry-run`] [`--backup`] | `{field, old_nature, new_nature, size_delta, taille_after}` |
| `remove-field` | `--name` [`--dry-run`] [`--backup`] | `{field, taille_before, taille_after, indexes_cleaned}` |

**Exit codes** : 0 = succes, 1 = erreur utilisateur (champ introuvable, Nature invalide, champ standard), 2 = erreur interne.

---

## References

### Interne au skill

- `reference/modification-checklist.md` : checklist avant/apres chaque operation

