---
name: generating-recordsql
description: >
  Genere un fichier source RecordSql (.dhsq) complet et valide pour une entite metier DIVA,
  a partir d'un template Jinja2 et des tokens de nommage. Inclut le filtre multi-dossier
  obligatoire (Dos = MZ.Dos), les cases WHERE/ORDERBY standard, et la declaration OverWrittenBy.
  Ecrit le fichier en ISO-8859-1+CRLF. A utiliser pour creer la couche d'acces SQL declarative
  d'une entite.
---

# Generating RecordSql

## Contenu

- Utilisation rapide
- Multi-table (jointures G-021)
- Bibliotheque de squelettes (G-022)
- Workflow complet
- Validation
- Scripts disponibles
- References

---

## Utilisation rapide

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine Retail --entite FamRglt --table RtlFamRglt \
    --champ-cle RgltFam --description "Famille de reglement" \
    --output "output/rtlrsfamrglt.dhsq"
```

---

## Multi-table (jointures G-021)

Le template supporte les **jointures parametriques** : 65 % du corpus X.13 joint >= 2 tables.
Deux types supportes :

- **Jointure implicite** (FROM + WHERE, style natif DIVA -- dominante en X.13) :
  les tables sont listees dans FROM, la condition est dans WHERE.
- **LEFT JOIN** (SQL standard -- 161 cas en X.13).

Les jointures passent **obligatoirement par JSON** (pas de flag CLI dedie pour rester deterministe).
Ajouter dans le JSON de tokens :

```json
{
  "joined_tables": [
    {
      "table_sql": "TIA",
      "alias": "TIA",
      "join_type": "implicit",
      "join_condition": "TIA.Dos = MZ.Dos AND CLI.Ticod = TIA.Ticod",
      "columns_selected": ["TIA.TiaLib"]
    }
  ],
  "additional_cases": [
    {"name": "Equal_Ref", "field": "Ref", "type": "equal", "param": "char"},
    {"name": "Between_DateMaj", "field": "DateMaj", "type": "between", "param": "date"}
  ]
}
```

Types supportes : `implicit` | `left_join` pour jointures, `equal` | `like` | `between` pour cases,
`char` | `int` | `date` | `num` pour parametres.

---

## Bibliotheque de squelettes (G-022)

8 squelettes pre-configures couvrant les super-patterns X.12 (>900 RSQL du corpus) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine Reglements --entite DtrFa --table RCMDTRFA \
    --champ-cle NumDtr --description "Detail reglement fournisseur" \
    --skeleton zoom-reglement-19 \
    --output output/rcmrsdtrfa.dhsq
```

Le flag `--skeleton <nom>` charge un JSON de jointures canoniques (repertoire `reference/skeletons/`), substitue le placeholder `{MAIN}` par la table principale, puis merge dans les tokens. Liste complete : cf. [reference/skeletons-catalogue.md](reference/skeletons-catalogue.md).

## Jointures FK explicites (--fk)

Pour ajouter une jointure FK avec libelle, utiliser `--fk CHAMP:TARGET[:ZOOM]` (repetable) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine Retail --entite RaceChien --table RaceChien \
    --champ-cle Code --description "Race de chien" \
    --fk Pay:T013:9053 \
    --output output/rtlrsracechien.dhsq
```

Pour chaque `--fk` :
- Ajoute `LEFT JOIN <TARGET> ON <MAIN>.<CHAMP> = <TARGET>.<CHAMP> AND <MAIN>.Dos = <TARGET>.Dos` dans `<FROM>`
- Ajoute `<TARGET>.Lib AS <CHAMP>_Lib` dans `<SELECT>`

Le nom de colonne `<CHAMP>_Lib` est coherent avec le pattern callback genere par `manipulating-dhsf-screens/dhsf_add_fk.py`.

Note : ce skill genere un LEFT JOIN syntaxique avec condition `ON` explicite, **et non** la syntaxe `<LEFTJOIN ... Using ...>` du standard DAV. Approche pragmatique : evite la dependance au dico `gtfdd.dhsj` et au `Public Record GTFDD.dhsd T000`. Si le pattern `Using` est requis (cas DAV stricte), patcher le .dhsq manuellement.

Combinable avec `--skeleton` : les FK sont concatenees aux jointures du squelette.

---

## Workflow complet

### 1. Generer le fichier .dhsq

Mode autonome (calcul des tokens integre) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --params --domaine {DOMAINE} --entite {ENTITE} --table {TABLE_SQL} \
    --champ-cle {CHAMP_CLE} --description "{DESCRIPTION}" \
    --output "{fichier_rsql}"
```

Mode tokens JSON (si les tokens sont deja calcules) :

```
py .claude/skills/generating-recordsql/scripts/generate_rsql.py \
    --file tokens.json --output "{fichier_rsql}"
```

### 2. Valider le fichier genere

```
py .claude/skills/generating-recordsql/scripts/validate_rsql.py \
    --path "{fichier_rsql}" --tokens tokens.json
```

### 3. Corriger si erreurs

- **R01 (Dos = MZ.Dos absent)** : erreur critique, le template l'inclut automatiquement — si absent, le template est corrompu
- **R02 (OverWrittenBy absent)** : le template l'inclut automatiquement
- **R06 (encodage)** : le script ecrit en ISO-8859-1+CRLF — si erreur, utiliser le skill `writing-diva-files` pour convertir le fichier

### 4. Verifier l'encodage

Utiliser le skill `writing-diva-files` pour verifier l'encodage du fichier genere.

---

## Validation

Le script `validate_rsql.py` verifie 8 regles (R01-R06 anti-patterns DIVA, R07/R08 jointures G-021 -- detail dans [reference/recordsql-anti-patterns.md](reference/recordsql-anti-patterns.md)) :

| Regle | Severite | Quoi |
|-------|----------|------|
| R01 | error | Filtre multi-dossier `Dos = MZ.Dos` |
| R02 | warning | `OverWrittenBy` present |
| R03 | warning | Nom RecordSql coherent avec tokens |
| R04 | error | Sections `<SELECT>` et `<FROM>` presentes |
| R05 | warning | `DefaultDictionary` coherent |
| R06 | error | Encodage ISO-8859-1 + CRLF |
| R07 | warning | Chaque table implicite dans `<FROM>` apparait dans `<WHERE>` (jointures G-021) |
| R08 | warning | Syntaxe `LEFT JOIN <table> [alias] ON <condition>` bien formee |

Avec `--tokens`, des verifications croisees supplementaires sont effectuees (R03, R05).

---

## Scripts disponibles

| Script | Role | Entree | Sortie |
|--------|------|--------|--------|
| `scripts/generate_rsql.py` | Genere le fichier .dhsq | `--params` (autonome) ou JSON tokens (stdin/fichier) + optionnel `--skeleton` + --output | JSON rapport + fichier .dhsq |
| `scripts/validate_rsql.py` | Valide un .dhsq existant (R01-R08) | --path fichier [+ --tokens JSON] | JSON rapport (errors/warnings) |
| `scripts/templates/recordsql.dhsq.j2` | Template Jinja2 (multi-table) | (utilise par generate_rsql.py) | — |
| `scripts/_naming.py` | Calcul des tokens de nommage (vendored) | (utilise par generate_rsql.py en mode --params) | — |
| `reference/skeletons/*.skel.json` | Bibliotheque G-022 : 8 super-patterns pre-configures | (charge par generate_rsql.py via --skeleton) | — |

---

## References

- **Structure complete d'un RecordSql** : Voir [reference/recordsql-structure.md](reference/recordsql-structure.md)
- **Regles R01-R06 avec exemples** : Voir [reference/recordsql-anti-patterns.md](reference/recordsql-anti-patterns.md)
- **Surcharge .dhsq (delta strict, groupe `[communs]`)** : Voir [reference/dhsq-overwrite-pattern.md](reference/dhsq-overwrite-pattern.md) — entetes overwrite/overwrittenby, les 9 interdits empiriques, convention de rattachement
- **Callbacks, MandatoryColumns, jointures avancees** : Voir [reference/recordsql-api-reference.md](reference/recordsql-api-reference.md)
- **Patterns observes dans le corpus (advisory, snapshot de fraicheur inconnue)** : Voir [reference/corpus-patterns.md](reference/corpus-patterns.md) — signatures de jointure, super-patterns, angles morts du generateur. **Croiser avec le filesystem X.13 avant decision.**
- **Bibliotheque de squelettes G-022** : Voir [reference/skeletons-catalogue.md](reference/skeletons-catalogue.md) — 8 super-patterns pre-configures (fichiers .skel.json dans `reference/skeletons/`).
