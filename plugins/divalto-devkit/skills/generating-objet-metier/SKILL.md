---
name: generating-objet-metier
description: >
  Genere un fichier Module Check (.dhsp) complet pour une entite metier DIVA,
  a partir d'un template Jinja2 et des tokens de nommage. Contient l'en-tete,
  les includes/modules, Init_Module, les ~52 fonctions du pattern standard
  (proprietes, champs, recherche, controle, init, pre/post, autorisations, reservation).
  Ecrit le fichier en ISO-8859-1+CRLF. A utiliser pour creer la couche objet
  metier d'une entite (deuxieme fichier du pattern 3 fichiers).
---

# Generating Objet Metier

## Contenu

- Utilisation rapide
- Workflow complet
- Validation
- Scripts disponibles
- References

---

## Utilisation rapide

```
py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
    --params --domaine Retail --entite FamRglt --table RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement" \
    --output "output/rttmchkrtlfamrglt.dhsp"
```

---

## Workflow complet

### 1. Generer le fichier .dhsp

Mode autonome (calcul des tokens integre) :

```
py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
    --params --domaine {DOMAINE} --entite {ENTITE} --table {TABLE_SQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}" \
    --output "{fichier_mchk}"
```

Mode tokens JSON (si les tokens sont deja calcules) :

```
py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
    --file tokens.json --output "{fichier_mchk}"
```

Mode avec foreign keys (parametre `--fk`, repetable) :

```
py .claude/skills/generating-objet-metier/scripts/generate_mchk.py \
    --params --domaine Dav --entite RacChien --table RaceChien \
    --champ-cle RacCod --description "Race de chien" --champ-libelle Lib \
    --fk RacPays:T013:9053 --fk RacDev:T007 \
    --output "gttmchkracechien.dhsp"
```

Format `--fk CHAMP:TARGET[:ZOOM]` :
- `CHAMP` : nom du champ source (ex `RacPays`)
- `TARGET` : entite cible (ex `T013`, `CLI`, `ART`). Derive automatiquement le module `Gttmchk<target>.dhop`, les fonctions `Find_<target>` et `Get_<target>_Lib`
- `ZOOM` (optionnel) : numero zoom a5tczoom.dhsp (advisory, pas utilise dans le .dhsp mais transmis au `.dhsf`)

Genere :
- L'import `Module "Gttmchk<target>.dhop"` dans la section modules
- Les procedures `Check_<SRC>_Field_<CHAMP>` (validation + Find_<target>) et `Check_<SRC>_Field_<CHAMP>_Lib` (validation + Get_<target>_Lib) en fin de fichier

Exemptions : les cibles comptables (`C3`, `C4`, `C5`, `C6`, `C7`, `C8`, `C9`) n'ont pas de module unique dedie (framework CC indirect) -- l'import Module est omis, seules les procedures sont generees.

Cf. le skill [`binding-zoom-to-field`](../binding-zoom-to-field/SKILL.md) et son `reference/fk-pattern.md` (pattern 3 couches + mapping cible -> module + taxonomie suffixes).

### 2. Valider le fichier genere

```
py .claude/skills/generating-objet-metier/scripts/validate_mchk.py \
    --path "{fichier_mchk}" --tokens tokens.json
```

### 3. Corriger si erreurs

- **M01 (Init_Module absent)** : erreur critique, le template l'inclut automatiquement — si absent, le template est corrompu
- **M02 (INIT non initialise)** : le template l'inclut automatiquement
- **M03 (Stack/UnStack OutputMode)** : le template l'inclut dans PostFetch
- **M04 (OverWrittenBy)** : le template l'inclut automatiquement
- **M05 (encodage)** : le script ecrit en ISO-8859-1+CRLF — si erreur, utiliser le skill `writing-diva-files` pour convertir le fichier

### 4. Verifier l'encodage

Utiliser le skill `writing-diva-files` pour verifier l'encodage du fichier genere.

---

## Validation

Le script `validate_mchk.py` verifie 7 categories de regles :

| Regle | Severite | Quoi |
|-------|----------|------|
| M01 | error | `Init_Module` avec `Get_CheckObject_Data` |
| M02 | error | Record `_INIT` initialise |
| M03 | warning | `Stack/UnStack_OutputMode` dans PostFetch |
| M04 | warning | `OverWrittenBy` present et coherent |
| M05 | error | Encodage ISO-8859-1 + CRLF |
| STRUCT | error | 22 fonctions obligatoires presentes |
| NAMING | warning | Nommage coherent avec les tokens |

Avec `--tokens`, des verifications croisees supplementaires sont effectuees (M04, NAMING).

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/generate_mchk.py` | Genere le fichier .dhsp | `--params` (autonome) ou JSON tokens (stdin/fichier) + --output | JSON rapport + fichier .dhsp |
| `scripts/validate_mchk.py` | Valide un .dhsp existant | --path fichier [+ --tokens JSON] | JSON rapport (errors/warnings) |
| `scripts/templates/mchk.dhsp.j2` | Template Jinja2 | (utilise par generate_mchk.py) | — |
| `scripts/_naming.py` | Calcul des tokens de nommage (vendored) | (utilise par generate_mchk.py en mode --params) | — |

---

## References

### Interne au skill

- **Structure complete d'un Module Check** : [reference/mchk-structure.md](reference/mchk-structure.md)
- **Regles M01-M05 avec exemples** : [reference/mchk-anti-patterns.md](reference/mchk-anti-patterns.md)
- **Patterns observes dans le corpus (advisory, snapshot de fraicheur inconnue)** : [reference/corpus-patterns.md](reference/corpus-patterns.md) — taux de presence des 22 fonctions canoniques, distribution nb_fn par mchk, confirmation alignement template. **Croiser avec le filesystem X.13 avant decision.**

