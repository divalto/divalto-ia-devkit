---
name: naming-diva-entities
description: >
  A partir du triplet (domaine, entite, table SQL), calcule l'ensemble complet des noms
  de fichiers, instances, variables, constantes et tokens de substitution necessaires a
  la generation d'une entite metier DIVA. Verifie la coherence (non-collision RecordSql/Record,
  prefixe domaine correct). A utiliser avant toute generation de code pour obtenir le jeu de tokens.
---

# Naming DIVA Entities

## Contenu

- Utilisation rapide
- Workflow complet
- Parametres d'entree
- Sortie : tokens JSON
- Gestion de la non-collision
- Scripts disponibles
- References

---

## Utilisation rapide

```
py .claude/skills/naming-diva-entities/scripts/compute_names.py \
    --domaine Retail --entite FamRglt --nomrecordsql RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement"
```

Sortie JSON : tous les tokens necessaires a la generation des fichiers d'une entite DIVA.

---

## Workflow complet

### 1. Calculer les tokens

```
py .claude/skills/naming-diva-entities/scripts/compute_names.py \
    --domaine {DOMAINE} --entite {ENTITE} --nomrecordsql {NOMRECORDSQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}"
```

### 2. Valider la coherence

Enchainer avec le validateur (pipe depuis stdout) :

```
py .claude/skills/naming-diva-entities/scripts/compute_names.py \
    --domaine {DOMAINE} --entite {ENTITE} --nomrecordsql {NOMRECORDSQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}" | \
    py .claude/skills/naming-diva-entities/scripts/validate_names.py --stdin
```

### 3. Corriger si erreurs

- **V01 (collision)** : relancer avec `--nom-vue` pour fournir un nom alternatif
- **V02-V04 (PascalCase)** : corriger les parametres d'entree
- **V05 (prefixe DB)** : verifier que la table appartient au domaine
- **V07 (base vide)** : verifier le nom de table
- **V08 (description vide)** : fournir une description

### 4. Utiliser les tokens

Le JSON de sortie est consomme par les skills de generation (RecordSql, objet metier, zoom).

---

## Parametres d'entree

| Parametre | Format | Obligatoire | Exemple |
|-----------|--------|-------------|---------|
| `--domaine` | Nom canonique (case-insensitive) | Oui | `Retail` |
| `--entite` | PascalCase | Oui | `FamRglt` |
| `--nomrecordsql` | Nom du RecordSQL | Oui | `LivreRS`, `RtlFamRglt` |
| `--champ-cle` | PascalCase | Oui | `RgltFam` |
| `--description` | Texte libre | Oui | `Famille de reglement` |
| `--nom-vue` | PascalCase (override) | Non | `FamRgltRetail` |

**Domaines supportes** : DAV, Retail, Production, Atelier, Comptabilite, Affaires, Reglements, Relation-Tiers, Paie, Point de vente, Qualite, Controle, Processus, Mobilite, GRM.

---

## Sortie : tokens JSON

Le script produit un JSON avec l'ensemble des tokens de nommage consommes par les templates de generation :

| Categorie | Tokens |
|-----------|--------|
| Metadonnees | `domaine`, `entite`, `table_sql`, `champ_cle`, `description`, `date` |
| Prefixes | `PREFIX_`, `prefix_module`, `prefix_module_u`, `prefix_db`, `domaine_2l`, `DICT` |
| Nommage | `NomVue`, `TableSQL`, `TABLE_MAJUSCULE`, `table_minuscule`, `entity`, `ENTITY`, `base`, `FichierDico` |
| Fichiers | `fichier_rsql`, `fichier_zoom`, `fichier_mchk`, `fichier_masque`, `fichier_masque_compile` + variantes surcharge/compile |
| Instances | `RS_instance`, `instance_sel`, `record_init`, `shared_record`, `ChkData`, `FieldNames_Min` |
| Define | `ChaineReservation`, `TitreVariable`, `PREFIXRES` |
| Modules | `module_mchk`, `module_ficsql`, `overwrittenby_zoom/mchk/rsql` |
| Options | `has_libelle` (booleen, defaut true -- false si `--no-libelle`) |
| Validation | `collision_detected` (booleen) |

---

## Gestion de la non-collision

DIVA est case-insensitive : si `NomVue` == `TableSQL` (case-insensitive), le compilateur echoue.

Le script detecte cette situation automatiquement (`collision_detected: true`). Si collision :

1. Relancer avec `--nom-vue` pour fournir un nom alternatif
2. Convention : tables a nom court → nom long descriptif (ex: `CLI` → `Client`)

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/compute_names.py` | Calcul de tous les tokens | CLI args | JSON (tokens) |
| `scripts/validate_names.py` | Validation de coherence | JSON stdin ou fichier | JSON (rapport) |

---

## References

### Interne au skill

- **Table des prefixes par domaine** : [reference/domain-prefixes.md](reference/domain-prefixes.md)
- **Formules de nommage avec exemples** : [reference/naming-formulas.md](reference/naming-formulas.md)
- **Regle de non-collision RecordSql / Record** : [reference/non-collision-rule.md](reference/non-collision-rule.md)

