# Strategie de cross-check par categorie

Comment chaque detecteur confronte le livrable UC-200 aux sources de verite.

## Sommaire

- [Sources de verite par categorie](#sources-de-verite-par-categorie)
- [E1 : regex sur les YAML d'entite](#e1--regex-sur-les-yaml-dentite)
- [E2 : evaluation LLM par paires narratif/contexte](#e2--evaluation-llm-par-paires-narratifcontexte)
- [E3 : diff structurel sources vs livrable](#e3--diff-structurel-sources-vs-livrable)
- [E4 : confrontation au referentiel DIVA](#e4--confrontation-au-referentiel-diva)
- [Ordre d'execution et parallelisme](#ordre-dexecution-et-parallelisme)

---

## Sources de verite par categorie

| Categorie | Source confrontee | Mode de confrontation |
|-----------|-------------------|------------------------|
| E1 | Livrable lui-meme (auto-verification) | Regex sur les YAML d'entite |
| E2 | Sources X.13 autour des citations | Extraction contexte 20 lignes + jugement LLM |
| E3 | Dictionnaires `.dhsd`, masques `.dhsf`, schema SQL | Re-parsing complet + diff structurel |
| E4 | Referentiel `docs/` du workspace | Corpus cible (voir docs-corpus.md) + heuristiques regex |

Principe commun : **chaque detection doit etre ancree**. Un item remonte porte systematiquement :

- `yaml_path` -- ou l'affirmation vit dans le livrable (ex: `business.role` sur `entity/CLI.yaml`)
- `source_ref` -- ou la verite vit (ex: `Gttcli.dhsd:87`, ou `docs/DICTIONNAIRE-DHSD.md:section 3`, ou `<aucune>` pour E1)
- `challenge` -- phrase courte qui contraste les deux

---

## E1 : regex sur les YAML d'entite

### Inputs

- IR du livrable (sortie de `ingest_deliverable.py`)

### Algorithme

Pour chaque entite :
1. Pour chaque champ texte dans `business.*`, `schema.*`, `technical.*` :
   1. Si champ vide : ignorer
   2. Si champ contient une citation `fichier:ligne` valide (regex) : OK
   3. Si champ est couvert par un item de `meta.a_verifier` (correspondance sur le nom du champ) : OK
   4. Sinon : remonter en E1 erreur
2. Le `meta.a_verifier` couvre un champ si la mention du champ apparait litteralement dans le texte de l'item (matching insensible a la casse sur le nom YAML sans le prefixe).

### Regex de citation

```
([A-Za-z0-9_./\\-]+\.(dhsp|dhsq|dhsd|dhsf|dhop|sql|dll|py|js)):(\d+)
```

Note : les citations vers `docs/*.md` sont aussi acceptees (via extension `.md`), meme si moins frequentes dans un livrable UC-200.

### Limites

- Ne detecte pas les citations fantomes (citation syntaxiquement correcte mais pointant sur un fichier inexistant). Cas couvert par E2 (si LLM detecte l'incoherence) ou par un pre-check optionnel dans `ingest_deliverable.py`.

---

## E2 : evaluation LLM par paires narratif/contexte

### Inputs

- IR du livrable
- Chemin `{CHEMIN_ERP_STANDARD}`
- Parametre `--context-lines` (defaut 20)

### Algorithme

Etape A (deterministe, `prepare_misalign_batch.py`) :
1. Pour chaque affirmation sourcee (champ avec au moins une citation `fichier:ligne` valide) :
   1. Resoudre le chemin absolu vers `{CHEMIN_ERP_STANDARD}/<relatif>.<ext>`
   2. Si le fichier n'existe pas : marquer l'entree comme `context_error: "source_not_found"`, continuer (l'item sera reporte en E2 avec severite `info` -- pas une erreur E1 puisque le format etait correct)
   3. Sinon extraire les 20 lignes centrees sur la ligne citee
2. Produire un batch JSON : une entree par paire {narratif, citation, context_source}.

Etape B (LLM, orchestree par Claude depuis le SKILL.md) :
Pour chaque entite (batch groupe par entite) :
1. Pour chaque paire `{narratif, context_source}` de l'entite :
   1. Evaluer strictement sur la base du `context_source` fourni
   2. Renvoyer : `align: oui|non|douteux`, `explication` (1-2 phrases), `extrait_contradictoire` (si `non`)
2. Agreger les reponses dans `.detect_e2.json`.

### Regles de jugement

- **Paraphrase large mais fidele** : `oui` -- ex: "Le client est une entite centrale" pour un code qui dit `Description = "Fichier central clients"` -> `oui`, ajout d'information minime et neutre
- **Ajout d'information non presente** : `non` -- ex: narratif qui cite un processus metier absent du code
- **Inversion logique** : `non` -- ex: narratif qui dit "actif si Bloque = 0" pour un code qui rejette `Bloque = 0`
- **Contexte trop court** : `douteux` -- le code cite ne suffit pas a trancher (< 5 lignes significatives)
- **Contexte ambigu** : `douteux` -- le code est interpretable de plusieurs facons

### Limites

- Couplage a la qualite du LLM : regressions possibles selon le modele.
- Pas de cache persistant entre deux executions : chaque passe re-evalue toutes les paires. Acceptable tant que le volume reste < 500 paires par module.
- **Hors scope** : detecter qu'une citation pointe un fichier qui existe mais un numero de ligne absurde (ex: ligne 999 d'un fichier de 300 lignes). Le script renverra un contexte vide ou tronque, Claude remontera `douteux`.

---

## E3 : diff structurel sources vs livrable

### Inputs

- IR du livrable
- Chemin `{CHEMIN_ERP_STANDARD}`
- Chemin `{CHEMIN_SCHEMA_SQL}`

### Algorithme

Pour chaque entite :
1. **Champs** : re-parser le dictionnaire `.dhsd` de l'entite via `_dhsd_parser.py`. Extraire la liste des champs `{nom, nature, position, taille}`. Diff avec `entity.technical.fields[]`.
2. **Indexes** : meme `.dhsd`, section `[INDEX]`. Extraire `{nom, champs}`. Diff avec `entity.technical.indexes[]`.
3. **Masques** : `_dhsf_parser.py` sur les `.dhsf` references dans l'entite. Extraire zooms `f8`, onglets. Diff avec `entity.schema.zooms[]` (si present dans le schema).
4. **Relations FK** : lecture du schema SQL JSON. Extraire les FK pour la table primaire de l'entite. Diff avec `relation/*.yaml` dont `source == entity`.

Pour chaque element present en source mais pas en livrable :
- Chercher une justification dans `meta.a_verifier` (matching sur le nom de l'element)
- Si trouve : ignorer (le producteur a reconnu l'incertitude)
- Sinon : remonter en E3 erreur

### Regles de matching

- Comparaison insensible a la casse sur les noms de champ
- Tolerance sur les prefixes : `CLI.DateDernierAchat` en source matche `DateDernierAchat` en livrable (le prefixe d'entite est implicite cote livrable)
- Les champs du socle audit canonique (`Ce1`, `Dos`, `UserCr`, `UserMo`, `UserCrDh`, `UserMoDh`, `Filler`, `U-field`) ne sont pas reportes si absents : ils sont typiquement resumes dans `technical.audit_fields` plutot qu'enumeres dans `technical.fields`. Si `audit_fields: true` dans le livrable, on considere ces champs couverts.

### Limites

- **Faux positifs possibles** sur les champs heritages ou les champs `Filler` ajoutes ad hoc. Couvert par la regle d'exclusion des champs audit canoniques.
- **Surcharge par OverWrittenBy** : si un module surcharge une structure, le parseur de base voit les deux declarations. Regle : la plus recente (derniere declaration avec `OverWrittenBy`) prime. Cas rare sur `.dhsd`, plus frequent sur `.dhsq`/`.dhsp`.

---

## E4 : confrontation au referentiel DIVA

### Inputs

- IR du livrable
- Racine `docs/` du workspace (`{RACINE_DOCS}`)

### Algorithme

Etape 1 : charger le corpus cible (voir [docs-corpus.md](docs-corpus.md)). Liste fixe de fichiers et de sections avec heuristiques associees.

Etape 2 : pour chaque entite, appliquer les heuristiques :

| Heuristique | Verification | Source referentiel |
|-------------|--------------|---------------------|
| Nature d'un champ coherente avec son suffixe | Le suffixe du nom YAML declare doit cadrer avec la Nature declaree | `docs/DICTIONNAIRE-DHSD.md` (table des suffixes) |
| Prefixe d'entite coherent avec son domaine | Le prefixe du fichier source (Gtt*, Gfc*, Gab*) doit cadrer avec le domaine declare | `docs/MODULES-ERP.md` (section 4) |
| Pattern 3 fichiers respecte | Si `.dhop` cite, verifier le naming `Gttmchk*.dhop` ou equivalent | `docs/ARCHITECTURE-ENTITE.md` |
| Anti-patterns connus | Chercher les patterns listes `Z01`-`Z20` dans le livrable | `docs/ANTI-PATTERNS.md` |

Etape 3 : si la racine `docs/` est absente (`--docs-root skip`), ecrire un `.detect_e4.json` avec `items: []` + `warning_global: "docs-root skip"` et continuer.

### Regles strictes

- **Jamais de modification de `docs/`** : seulement lecture + signalement
- **Toujours severite `warning`** : le referentiel peut etre obsolete, un ecart n'est pas automatiquement une erreur
- **Citation des deux cotes** dans le rapport : extrait livrable + extrait referentiel (`fichier:ligne` ou `fichier:section`)

### Limites

- Le corpus est **fige** : les heuristiques sont codees en dur dans le script. Enrichissement manuel requis a chaque ajout de regle dans le referentiel.
- **Dependance au format** des fichiers `docs/` : si le format d'une table de Natures change, l'heuristique peut casser silencieusement. Prevoir des tests de non-regression sur le corpus (couverts par `evals.json`).

---

## Ordre d'execution et parallelisme

Sequence dans le SKILL.md : E1 -> E3 -> E4 -> E2 (etapes 2 a 6).

Rationale :
- E1, E3, E4 sont deterministes et peu couteux -> les passer en premier
- E2 est LLM-driven et le plus couteux -> en dernier
- Si le livrable est massivement non source (scenario 3 UC-201), E1 remonte beaucoup d'erreurs et E2 a peu de citations a evaluer : bon ordre

Parallelisation possible entre E1 / E3 / E4 (detecteurs independants), mais hors scope v1 (sequence simple, plus facile a debuguer).
