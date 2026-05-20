# Pipeline -- documenting-erp

Source -> extraction -> assemblage -> rendu. Ce document precise chaque etape et les sources mobilisees.

## Contenu

- Schema general du pipeline
- Sources par categorie
- Extraction : responsabilite de chaque script
- Assemblage et fusion narratif
- Validation
- Rendu

## Schema general

```
┌─ Sources ERP X.13 (verite vivante) ─────────────────────────┐
│                                                             │
│  .dhsd (dictionnaires)         │ {CHEMIN_FICHIERS}/*.dhsd   │
│  masques .dhsf                 │ {CHEMIN_ERP_STANDARD}/...  │
│  modules .dhsp/.dhsq           │ {CHEMIN_ERP_STANDARD}/...  │
│  base SQL Server (export JSON) │ {CHEMIN_SCHEMA_SQL}/...    │
│  graphe Neo4j (advisory X.12)  │ MCP diva-mcp               │
│                                                             │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─ Extraction (scripts) ──────────────────────────────────────┐
│  extract_entity.py --entity CLI → CLI.partial.yaml          │
│  extract_module.py --module DAV → module.partial.yaml       │
│  extract_relations.py --entity CLI → CLI.relations.yaml     │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─ Enrichissement narratif (humain + Claude) ─────────────────┐
│  Sources autorisees : code X.13 + fragments reference/ +    │
│  connaissance collaborateur (jamais matiere digeree externe)│
│  Renseigne : business.role, business.rules, business.examples│
│  Marque : meta.a_verifier pour tout non-source              │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─ Assemblage (script) ───────────────────────────────────────┐
│  assemble_model.py  → entity/CLI.yaml (final)               │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─ Validation (script) ───────────────────────────────────────┐
│  validate_model.py  → exit 0 ou liste d'erreurs             │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─ Rendu (script) ────────────────────────────────────────────┐
│  render_markdown.py --layer business|schema|technical|all   │
│  render_pdf.py (Chrome headless, optionnel)                 │
│     → DAV.md / DAV.pdf                                      │
└─────────────────────────────────────────────────────────────┘
```

## Sources par categorie

### Structures de donnees

| Source                                          | Contenu extrait                 | Script             |
|-------------------------------------------------|---------------------------------|--------------------|
| `{CHEMIN_FICHIERS}/*.dhsd`                      | Champs + Natures + indexes      | extract_entity.py  |
| `{CHEMIN_SCHEMA_SQL}/columns/{ENTITY}.json`     | Type SQL, nullable, ordinal     | extract_entity.py  |
| `{CHEMIN_SCHEMA_SQL}/indexes/{ENTITY}.json`     | Indexes SQL                     | extract_entity.py  |
| `reference/modules-erp-summary.md`              | Liste des modules + prefixes    | Claude (lecture CP1)|

Le JSON `{CHEMIN_SCHEMA_SQL}` est un export prealable du schema SQL
Server (script de dump interrogeant `information_schema.columns` et
`sys.indexes`). Format attendu documente dans le SKILL.md.

### Relations et navigation

| Source                                         | Contenu extrait                 | Script                |
|------------------------------------------------|---------------------------------|-----------------------|
| Graphe Neo4j diva-mcp (advisory X.12)          | FK, liens programmes-entites    | extract_relations.py  |
| Code source `.dhsp`/`.dhsq` (X.13)             | Zooms f8, Record OverWrittenBy  | extract_relations.py  |
| Masques `.dhsf` (X.13)                         | f8=, table_associee, onglets    | Claude (lecture CP3)  |
| Heuristique sur noms de champs (DOS, ETB, CPT) | Relations probables a confirmer | extract_relations.py  |

### Narratif et metier

| Source                                         | Contenu extrait                 | Qui ?              |
|------------------------------------------------|---------------------------------|--------------------|
| Commentaires en-tete `.dhsf` et `.dhsp`        | Role fonctionnel, titre         | Claude (extraction)|
| Procedures Module Check (mchk)                 | Regles metier appliquees        | Claude (extraction)|
| Menu et navigation ERP                         | Place dans l'arborescence       | Claude (extraction)|
| Fragment `reference/modules-erp-summary.md`    | Mapping modules/prefixes/dicos  | Claude (lecture)   |
| Connaissance metier du collaborateur           | role, rules, examples concrets  | Collaborateur (CP3)|

**Sources interdites** : `archive/*`, `raw/*`, ou toute matiere digeree non
canonique. Un skill reste autonome chez tout collaborateur
(cf. `.claude/skills/README.md` sections Autonomie).

## Extraction

### extract_module.py

Entree : `--module DAV --prefix GTF --label "Achat-Vente" --bases ... --entities ...`
Les listes de bases et d'entites sont fournies explicitement par le
collaborateur au CP1 (ou par Claude apres consultation de
`reference/modules-erp-summary.md` pour les modules standards).
Sortie : YAML partiel conforme a `schemas/module.yaml` avec `code`, `label`,
`prefix`, `bases`, `entities`.

### extract_entity.py

Entree : `--entity CLI --module DAV --base GTFPCF --sql-schema {CHEMIN_SCHEMA_SQL}/columns/CLI.json`.
Sortie : YAML partiel avec `technical.primary_table`, `technical.fields[]`
(nom, sql_type, nullable, layer heuristique), `technical.indexes[]`,
`technical.audit_fields`, `technical.field_count`.

Note : `business.*` n'est PAS rempli par ce script (role de l'enrichissement CP3).

### extract_relations.py

Entree : `--entity CLI --source heuristic|neo4j|code`.
Sortie : YAML partiel de relations : liste de `{source_entity, target_entity, type, cardinality, source_field?}`.

- `heuristic` : scan des noms de champs avec table de conversion embarquee
- `neo4j` : graphe advisory X.12 via MCP diva-mcp (si dispo)
- `code` : scan des .dhsf/.dhsp X.13 pour `f8=` et `Record ... OverWrittenBy`

## Enrichissement narratif (CP3)

Etape manuelle assistee par Claude. Pattern :

1. Claude charge les `.partial.yaml` produits par les scripts.
2. Pour chaque entite, Claude ouvre les sources X.13 (masques, modules)
   associees et extrait role, regles, processus **avec citation fichier:ligne**.
3. Claude propose une redaction pour `business.role`, `business.criticality`,
   `business.processes`, `business.business_rules`, `business.examples`.
4. Collaborateur revise, valide, corrige avec sa connaissance metier.
5. Tout contenu non sourcable depuis X.13 et non valide par le collaborateur
   est marque `[A VERIFIER]` dans `meta.a_verifier`.

## Assemblage

`assemble_model.py` :
1. Charge tous les fichiers `*.partial.yaml` et `*.yaml` du repertoire d'entree
2. Fusionne par type et code (le non-partial ecrase les sections qu'il renseigne)
3. Injecte les relations dans la section `schema.relations` de chaque entite
4. Ecrit les fichiers finaux :

```
{REPERTOIRE_SORTIE}/doc-erp/{MODULE}/
├── module.yaml
├── entity/{CODE}.yaml
├── relation/{CODE}.yaml
├── process/{CODE}.yaml
├── program/{CODE}.yaml
└── glossary.yaml
```

## Validation

`validate_model.py` verifie :
- Parsing YAML sans erreur
- Presence des champs requis par schema
- Coherence inter-fichiers : les references pointent vers des codes existants
- Presence de rendering_layers valides

Sortie : JSON avec liste d'erreurs + exit code (0 si OK).

## Rendu

`render_markdown.py` :
1. Charge le modele (tous les YAML du repertoire)
2. Filtre selon `--layer` demandee (business | schema | technical | all)
3. Produit un markdown structure : TOC, entites triees, diagrammes Mermaid,
   liens internes, glossaire, items [A VERIFIER] en fin.

`render_pdf.py` (optionnel) :
Convertit le Markdown en PDF via Chrome/Edge headless + lib `markdown` +
CSS typographie A4. Preview : la forme cible (Confluence, MkDocs, pandoc)
reste a trancher cote collaborateur. Le modele YAML etant stable, ajouter
un nouveau renderer n'affecte pas l'amont.
