---
name: generating-zoom-sql
description: >
  Genere un fichier Zoom SQL (.dhsp) complet avec les 27 procedures obligatoires
  du cycle de vie ecran CRUD (creation, modification, suppression, consultation).
  Inclut les appels framework (Select, PreInsert, PostInsert, etc.), la construction
  de conditions de selection, la gestion des reservations, et les hooks de personnalisation.
  Ecrit en ISO-8859-1+CRLF. A utiliser pour creer l'interface utilisateur d'une entite
  metier (troisieme fichier du pattern 3 fichiers).
---

# Generating Zoom SQL

## Contenu

- Utilisation rapide
- Workflow complet
- Validation
- Scripts disponibles
- References

---

## Utilisation rapide

```
py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
    --params --domaine Retail --entite FamRglt --table RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement" \
    --output "output/rttzfamrglt_sql.dhsp"
```

---

## Workflow complet

### 1. Generer le fichier .dhsp

Mode autonome (calcul des tokens integre) :

```
py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
    --params --domaine {DOMAINE} --entite {ENTITE} --table {TABLE_SQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}" \
    --output "{fichier_zoom}"
```

Mode tokens JSON (si les tokens sont deja calcules) :

```
py .claude/skills/generating-zoom-sql/scripts/generate_zoom.py \
    --file tokens.json --output "{fichier_zoom}"
```

### 2. Valider le fichier genere

```
py .claude/skills/generating-zoom-sql/scripts/validate_zoom.py \
    --path "{fichier_zoom}" --tokens tokens.json
```

### 3. Corriger si erreurs

- **Z01 (procedures manquantes)** : le template inclut les 27 — si absentes, le template est corrompu
- **Z03 (prefixe domaine)** : verifier que le bon domaine est passe en parametre
- **M04 (majuser=true)** : le template l'inclut dans ZoomAvantRewrite
- **ENC (encodage)** : utiliser le skill `writing-diva-files` pour convertir le fichier

### 4. Verifier l'encodage

Utiliser le skill `writing-diva-files` pour verifier l'encodage du fichier genere.

---

## Validation

Le script `validate_zoom.py` verifie 11 categories de regles :

| Regle | Severite | Quoi |
|-------|----------|------|
| Z01 | error | 27 procedures obligatoires presentes |
| Z02 | warning | `preturn` apres `Zoom.OK = 'I'/'S'/'C'` |
| Z03 | error | Pas de melange de prefixes domaine |
| Z08 | error | Module ficsql present |
| Z10 | warning | Gestion du prefixe `-` dans Scevaleur |
| OWB | warning | OverWrittenBy present et coherent |
| M04 | error | `majuser=true` dans PreUpdate |
| S08 | warning | Zoom.Valretour initialise |
| ENC | error | Encodage ISO-8859-1 + CRLF |
| NAMING_CONV | warning | 4e lettre du nom = `z` (convention zoom) |
| NAMING | warning | Nommage coherent avec tokens |

Avec `--tokens`, des verifications croisees supplementaires sont effectuees (Z03, OWB, NAMING).

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/generate_zoom.py` | Genere le fichier .dhsp | `--params` (autonome) ou JSON tokens (stdin/fichier) + --output | JSON rapport + fichier .dhsp |
| `scripts/validate_zoom.py` | Valide un .dhsp existant | --path fichier [+ --tokens JSON] | JSON rapport (errors/warnings) |
| `scripts/templates/zoom_sql.dhsp.j2` | Template Jinja2 | (utilise par generate_zoom.py) | — |
| `scripts/_naming.py` | Calcul des tokens de nommage (vendored) | (utilise par generate_zoom.py en mode --params) | — |

---

## References

- **Les 27 procedures avec patterns** : Voir [reference/zoom-procedures.md](reference/zoom-procedures.md)
- **Regles Z01-Z12 avec exemples** : Voir [reference/zoom-anti-patterns.md](reference/zoom-anti-patterns.md)
- **Patterns observes dans le corpus (advisory, snapshot de fraicheur inconnue)** : Voir [reference/corpus-patterns.md](reference/corpus-patterns.md) — taux de presence des 27 procedures, extensions recurrentes, ecart sur le nom `Construire_Condition_Selection`. **Croiser avec le filesystem X.13 avant decision.**
- **Coherence avec le masque .dhsf (normes graphiques)** : Voir [reference/normes-graphiques.md](reference/normes-graphiques.md) -- ce skill genere le `.dhsp` du zoom ; le `.dhsf` associe (produit par `manipulating-dhsf-screens`) doit exposer les champs audit du dictionnaire dans l'onglet Identifiants selon l'ordre canonique. Les 2 fichiers doivent etre coherents (regle E16-E17 verifiee par `linting-diva-code`).
