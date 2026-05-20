---
name: documenting-erp
description: >
  Genere la documentation technique d'un module ou d'une entite de l'ERP Divalto
  sous forme de contenu structure YAML, independant de la forme du livrable final.
  Orchestre un pipeline `sources -> extraction -> assemblage -> rendu` : extrait
  depuis dictionnaires .dhsd, schema SQL et code X.13, enrichit avec un narratif
  metier, assemble selon un modele a 3 couches de lecture (metier / schema /
  technique) et rend via les renderers du skill -- Markdown et PDF aujourd'hui,
  autres formats (Confluence, MkDocs, pandoc, site statique...) via renderers
  additionnels ajoutes au skill (jamais via scripts ad-hoc externes).
  A utiliser quand un developpeur doit rediger ou actualiser la documentation
  technique d'un module ERP (DAV, COMPTA, GS...), produire la matiere avant un
  livrable Confluence/PDF, ou re-generer la doc pour detecter les derives entre
  une version ERP anterieure et l'actuelle.
---

# documenting-erp

Production de documentation technique ERP Divalto : pipeline source -> modele de contenu -> renderers. Livrable orthogonal a `docs/` (technique DIVA) : cible l'ERP fonctionnel (modules, entites, processus metier).

## Pour quoi

Reproduire et moderniser le role des anciens docs Word "Divalto X.xx Technique Base" (devenus obsoletes) avec trois ameliorations majeures :
1. **Generation automatique** depuis les sources vivantes (dicos, SQL, code) au lieu de saisie manuelle
2. **Trois couches de lecture** (consultants / dev clients / dev internes) portees par la meme instance de contenu
3. **Fond decouple de la forme** : YAML structure -> **plusieurs renderers autonomes** fournis par le skill (Markdown + PDF aujourd'hui, Confluence/MkDocs/pandoc/site statique a venir). Jamais de renderer ad-hoc externe au skill : le skill est autonome pour produire ses livrables.

## Quand l'utiliser

- Rediger ou actualiser la doc technique d'un module ERP (DAV, COMPTA, GS, CRM, Immo, ...)
- Documenter une nouvelle entite metier ou une entite refondue
- Preparer la matiere structuree avant un livrable Confluence, PDF ou site statique
- Re-generer periodiquement pour detecter les derives vs la version precedente

## Modele de contenu

6 types documentaires. Chaque instance est un fichier YAML valide contre le schema correspondant dans `schemas/`. Details et sous-schemas dans [reference/content-model.md](reference/content-model.md).

| Type      | Role                                                      | Schema                  |
|-----------|-----------------------------------------------------------|-------------------------|
| module    | Grand domaine fonctionnel (DAV, COMPTA, GS...)            | schemas/module.yaml     |
| entity    | Objet metier persistant (CLI, FOU, ART, C3...) -- cœur    | schemas/entity.yaml     |
| relation  | Lien inter-entites (FK, zoom, composition)                | schemas/relation.yaml   |
| process   | Processus metier transverse (ex: Order-to-Cash)           | schemas/process.yaml    |
| program   | Ecran / zoom / moulinette / batch                         | schemas/program.yaml    |
| glossary  | Terme metier -> code technique                            | schemas/glossary.yaml   |

## Trois couches de lecture

Chaque type de contenu declare ses couches via `rendering_layers:`. Un renderer choisit quelle couche afficher. Details et regles de routage dans [reference/layering.md](reference/layering.md).

| Couche     | Audience                         | Contenu rendu                         |
|------------|----------------------------------|---------------------------------------|
| business   | Consultants, chefs de projet     | Role, processus, vocabulaire          |
| schema     | Dev clients / integrateurs       | Relations, cardinalites, contrats     |
| technical  | Dev Divalto internes             | Champs, Natures, indexes, programmes  |

## Pipeline

```
Sources X.13                  Scripts                       Artefacts
────────────                  ───────                       ─────────
.dhsd (dictionnaires)         extract_entity.py             entity/*.yaml
schema SQL (JSON)             extract_module.py             module/*.yaml
code source .dhsp/.dhsq       extract_relations.py          relation/*.yaml
masques .dhsf                       |                             |
graphe Neo4j X.12 (advisory)        V                             V
                              assemble_model.py --->  {out}/doc-erp/{module}/
                                    |
                                    V
                              render_markdown.py  --->  {out}/doc-erp/{module}.md
```

Details du pipeline et des sources dans [reference/pipeline.md](reference/pipeline.md).

## Workflow orchestre

Skill LLM-driven en **production autonome** : Claude execute le pipeline de
bout en bout, sans pause. Le retour humain se fait **uniquement post-livraison**
(revue du livrable + corrections ciblees re-injectees en re-generation).

Deux seuls points d'interaction humaine :
- **CP1 initial** : cadrage des parametres (module, chemins) -- indispensable
  pour cibler la production
- **CP-Final** : presentation du livrable + liste des items [A VERIFIER]

**Checklist de progression** (copier au debut) :
- [ ] CP1 : Parametres collectes (module, entites, chemins, **formats de livrable**)
- [ ] Etape 2 : Extraction automatique (autonome)
- [ ] Etape 3 : Enrichissement narratif (autonome, sourcé X.13)
- [ ] Etape 4 : Assemblage (autonome)
- [ ] Etape 4 bis : Interpretation metier des CE (autonome, LLM-driven)
- [ ] Etape 4 ter : Validation schemas + regle de citation CE (autonome)
- [ ] Etape 5 : Rendu via les renderers du skill (autonome) -- Markdown + PDF aujourd'hui, autres formats a venir
- [ ] CP-Final : Livrable presente au collaborateur + items [A VERIFIER]

### Etape 1 -- Collecter les parametres (CP1)

Demander au collaborateur :
1. Module cible (ex: `DAV`, `COMPTA`)
2. Entites prioritaires (liste ou `all` pour tout le module)
3. Chemins `{CHEMIN_ERP_STANDARD}` (lecture seule) et `{REPERTOIRE_SORTIE}`
4. Objectif : doc complete ou re-generation incrementale ?
5. **Formats de livrable** parmi les renderers fournis par le skill (defaut : `markdown` + `pdf`, audiences `externe` + `interne`). Autres formats a venir au meme endroit (Confluence, MkDocs, pandoc, site statique...) -- **jamais de renderer ad-hoc externe** : un renderer insuffisant produit un livrable qualitativement degrade (cf RETEX 2026-04-23).

> **CHECKPOINT CP1 -- Parametres**
> Presenter : module cible, liste entites, chemins resolus, objectif.
> Critere : pas de chemin absolu en dur, pas d'entite ambigue.
> Attendre validation avant de lancer la production.
>
> **C'est le seul checkpoint humain AVANT la livraison**. Une fois CP1
> valide, Claude execute les Etapes 2 a 5 en une passe autonome.

### Etape 2 -- Extraction automatique

**Etape 2.0 -- Pre-enrichir les valeurs codifiees** (une seule fois par module, en amont) :

`extract_codified_values.py` s'appuie sur le skill `reading-multichoix` (via la
copie vendoree `_read_multichoix.py`) pour lire le fichier ISAM `<prefix>fdmc.dhfi`
et typer chaque choix (Type 1 liste fixe, Type 3 lookup dynamique
enreg/donnee/prefixe/ideb/ifin, Type 4 identifiant externe IdFic/LstPolice/...). Il
signale les libelles opaques `tbl*` (bitmaps) et `#<nom>` (i18n) que le renderer
externe remplace par `_(icone)_` / `_(libelle traduit)_`. Prerequis : DLL
`C:\divalto\sys\DhxIsam64.dll` accessible.

```bash
py scripts/extract_codified_values.py \
   --dhfi {CHEMIN_FICHIERS}/gtfdmc.dhfi \
   --partial-json {CHEMIN_FICHIERS}/gtfdmc.json \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/_codified_values.json
```

Le `--partial-json` est optionnel (il apporte la Color, absente du `.dhfi`).

**Multi-`.dhfi` (resolution cross-modules)** : certains champs pointent vers des
choix d'un autre module (ex: `NATURE` sur CLI DAV est dans `rtfdmc.dhfi` Retail).
Passer plusieurs `--dhfi` (et `--partial-json`) resout ces cas ; **premier gagne**
sur les doublons, placer le `.dhfi` principal en premier :

```bash
py scripts/extract_codified_values.py \
   --dhfi {CHEMIN_FICHIERS}/gtfdmc.dhfi \
   --dhfi {CHEMIN_FICHIERS}/rtfdmc.dhfi \
   --dhfi {CHEMIN_FICHIERS}/wmfdmc.dhfi \
   --partial-json {CHEMIN_FICHIERS}/gtfdmc.json \
   --partial-json {CHEMIN_FICHIERS}/wmfdmc.json \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/_codified_values.json
```

Sur DAV avec 3 `.dhfi` : **1025 choix_ids / 3413 values**, 932 Type 1 / 33 Type 3 /
60 Type 4. Le summary expose `by_type`, `tbl_references`, `translation_references`,
`extern_ids`, `choix_by_dhfi_source`. Le JSON est passe a `extract_narrative.py`
via `--choix-json` ; `codified_fields[*].choix_type / values / lookup / extern_id`
sont utilises par le renderer pour un rendu adapte par Type.

**Par entite -- chaine complete en deux commandes** (Claude les enchaine sans pause) :

```bash
# 2a. Structure SQL de l'entite (partial : champs + indexes)
py scripts/extract_entity.py \
   --entity CLI --module DAV --base GTFPCF \
   --dict {CHEMIN_FICHIERS}/gtfdd.dhsd \
   --sql-schema {CHEMIN_SCHEMA_SQL}/columns/CLI.json \
   --sql-indexes {CHEMIN_SCHEMA_SQL}/indexes/CLI.json \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.partial.yaml

# 2b. Narratif sourcé X.13 (libellés DIVA, FK 3 canaux, CE analysis, codified fields)
py scripts/extract_narrative.py \
   --entity CLI --module DAV --base GTFPCF \
   --dict {CHEMIN_FICHIERS}/gtfdd.dhsd \
   --main-screen {CHEMIN_FICHIERS}/gtez021_sql.dhsf \
   --main-module {CHEMIN_FICHIERS}/gttz021_sql.dhsp \
   --module-check {CHEMIN_FICHIERS}/gttmchkcli.dhsp \
   --choix-json {REPERTOIRE_SORTIE}/doc-erp/DAV/_codified_values.json \
   --sql-columns {CHEMIN_SCHEMA_SQL}/columns/CLI.json \
   --sql-indexes-json {CHEMIN_SCHEMA_SQL}/indexes/CLI.json \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.narrative.yaml
```

**Les 7 sources X.13 sont toutes necessaires pour une extraction one-shot complete** :

| Source | Alimente |
|--------|----------|
| `--dict` (dictionnaire `.dhsd`) | Libelles des champs via `[CHAMP]` globaux, libelles des tables cibles FK via `[TABLE]` top-level |
| `--main-screen` (masque `.dhsf`) | 3 canaux FK (f8+table_associee, diva_apres, donnee=), codified fields (`choix=`), pages/onglets |
| `--main-module` (module zoom `.dhsp`) | Modules references, records, header description |
| `--module-check` (objet metier `.dhsp`) | Check_Field procs (confirme FK), Find_<Table> (revele table cible), FieldNames_Min (PK metier), constantes C_*, Authorize_* |
| `--choix-json` (`gtfdmc.json`) | Valeurs concretes des listes codifiees (partiel -- les 30+ restantes sont dans `gtfdmc.dhfi` ISAM) |
| `--sql-columns` | Liste complete des 200+ colonnes SQL, enrichies avec libelles DIVA au merge |
| `--sql-indexes-json` | Detection de l'usage reel des Ce1..CeA (co-colonnes : STAT_* -> stat, TIERSGRP -> groupement) |

**Si une source manque** : l'extraction reussit mais perd en precision (ex: sans `--module-check`, les FK sont detectees uniquement via f8 masque et les vraies tables cibles T014/T048/C3 sont remplacees par le nom du champ source). **Toujours fournir les 7 sources pour une passe one-shot.**

Naming convention DAV (a adapter par module) :
- Module Check : `gttmchk<ent>.dhsp` (ex: `gttmchkcli.dhsp`, `gttmchkfou.dhsp`)
- Masque zoom principal : `gtez<NNN>_sql.dhsf` (ex: `gtez021_sql.dhsf` pour CLI)
- Module zoom : `gttz<NNN>_sql.dhsp`

Le JSON `{CHEMIN_SCHEMA_SQL}` est un export du schema SQL Server produit en amont
(ex: script de dump qui interroge `information_schema.columns` et `sys.indexes`).
Format attendu : `{table, database, refreshed, column_count, columns[{name,type,length,nullable,ordinal}]}`
pour columns, `{table, indexes[{name,columns[],unique,primary}]}` pour indexes.

Pour le module (parametres fournis par le collaborateur au CP1) :
```bash
py scripts/extract_module.py --module DAV --prefix GTF --label "Achat-Vente" \
   --bases "GTFDOS,GTFPCF,GTFAT,..." --entities "CLI,FOU,ART,..." \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/module.partial.yaml
```

Reference locale pour les prefixes/bases des 15+ modules ERP standards :
[reference/modules-erp-summary.md](reference/modules-erp-summary.md).

Relations (si Neo4j dispo) :
```bash
py scripts/extract_relations.py --entity CLI --source neo4j \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/relation/CLI.partial.yaml
```

Les fichiers `.partial.yaml` contiennent ce que les scripts ont pu extraire mecaniquement. Les sections `business.*` et `meta.a_verifier` sont enrichies a l'etape 3 (pas de checkpoint intermediaire, Claude enchaine).

### Etape 3 -- Enrichissement narratif metier (autonome)

**Claude produit le narratif en autonomie, sans question au collaborateur.**
Le retour humain se fait uniquement post-livraison (CP-Final).

Sources de verite **exclusivement** (par ordre de priorite) :

1. **Sources X.13 vivantes** (`{CHEMIN_ERP_STANDARD}`) :
   - Commentaires d'en-tete des masques `.dhsf` (titre, description d'onglet)
   - Commentaires et procedures des modules `.dhsp`/`.dhsq` de l'entite
   - Module Check (`.dhop`/`.dhsp` mchk) pour les regles metier appliquees
   - Menu et navigation ERP (zoom, titre, regroupement)
2. **Fragments locaux** (`<skill>/reference/*.md`) : transposition ciblee de
   la documentation workspace (modules, prefixes, conventions).

**Interdit** comme source narrative :
- `archive/*` (matiere digeree non canonique)
- `raw/*` (brouillons workspace)
- Inventions / interpolations du LLM non tracables a une source

**Regle de citation stricte** :
Chaque affirmation narrative du livrable doit etre :
- soit tracee a une source X.13 avec reference `fichier:ligne`
- soit marquee `[A VERIFIER]` dans `meta.a_verifier` de l'entite concernee

Aucune invention tacite. Aucune formulation "probablement", "semble",
"possiblement" sans marquage `[A VERIFIER]` explicite.

Pour chaque entite, Claude :
1. Ouvre les sources X.13 associees (dict, masques principaux, modules Check).
2. Extrait le role metier, processus, regles observees, avec citations
   `fichier:ligne`.
3. Remplit `business.role`, `business.criticality`, `business.processes`,
   `business.business_rules`, `business.examples`.
4. Liste exhaustivement dans `meta.a_verifier` les elements non sourcables
   (criticite metier appreciative, exemples typiques non documentes dans
   le code, regles tacites, etc.).
5. Passe a l'etape 4 sans pause.

### Etape 4 -- Assemblage (autonome)

```bash
# 4a. Fusion partial + narrative (par entite)
py scripts/merge_narrative.py \
   --entity-partial {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.partial.yaml \
   --narrative {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.narrative.yaml \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/entity/CLI.yaml

# 4b. Assemblage module (resolution heuristiques + traitement [A VERIFIER])
py scripts/assemble_model.py --module DAV \
   --input {REPERTOIRE_SORTIE}/doc-erp/DAV/ \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV/
```

Le script `merge_narrative.py` fusionne partial + narrative en un `<entity>.yaml` consolide. Le script `assemble_model.py` traite ensuite les relations heuristiques (resolution via confirmed_relations, reclassement `DOS`/`ETB` en `type=partitioning`, suppression des heuristiques non confirmees tracees dans `meta._dropped_heuristic_relations`).

### Etape 4 bis -- Interpretation metier des CE (autonome, LLM-driven)

Apres assemblage et avant validation, Claude lit chaque `<ENT>.yaml` et redige
la `description_metier` de chaque CE actif (Ce1..CeA) a partir des signaux X.13
extraits par les scripts. Cette etape est **LLM-driven** : pas de script, Claude
edite directement le YAML in-place.

**Pourquoi cette etape existe** : l'heuristique `role_infere` (champ conserve
comme signal diagnostic) produit des descriptions generiques pour les entites
dont la structure differe de CLI (ex: ART, SOC, VRP). Le role metier *specifique*
de chaque CE se lit en croisant : le commentaire `[CHAMP]` du .dhsd, les
constantes `C_*Ce<n>*` du Module Check, la regle d'activation (Condition ou valeur
fixe), les co-colonnes des indexes, et le role metier global de l'entite.

**Procedure a suivre par Claude pour chaque `<ENT>.yaml`** :

Boucler sur `technical.ce_analysis.fields[]` et, pour chaque CE :

1. **Si `status == "reserve"`** : rien a faire (le script a deja ecrit
   `description_metier = "Reserve pour extension future..."`).
2. **Si `status == "actif"` et `description_metier` existe deja et
   `description_metier_signature` est inchange** : conserver tel quel
   (idempotence CA13).
3. **Si `status == "actif"` et besoin de rediger** :
   - Lire les signaux disponibles pour le CE :
     - `dhsd_comment` + `dhsd_source` : commentaire du champ Ce<n> dans le .dhsd
     - `mchk_constants[]` : constantes C_*Ce<n>* du Module Check (name, value,
       comment, source)
     - `activation_rule` : expression de Condition (ex: `Ean <> ' '`)
     - `fixed_value` : valeur litterale assignee (ex: `'3'`)
     - `values_observed_in_mchk`, `co_cols`, `indexes` : indices supplementaires
     - Nom et role metier de l'entite (ex: ART = article, CLI = client)
   - **Rediger 1-3 phrases metier** expliquant le role du CE : quel aspect
     metier il exprime, dans quel contexte il est active, et si pertinent ce
     que signifient ses valeurs.
   - **Citer au moins UNE source X.13** parmi les signaux : soit `dhsd_source`,
     soit un `mchk_constants[].source`. Format libre, plusieurs citations
     separees par `, `. Stocker dans `description_metier_source`.
   - Si aucun signal ne permet une description sourcee, laisser
     `description_metier: null` et ajouter un item dans `meta.a_verifier`
     du type `"CE actif <ENT>.Ce<n> : role metier non sourcable depuis X.13"`.

**Regle de citation stricte (CA4)** : toute `description_metier` non vide DOIT
contenir une reference `fichier:ligne` dans `description_metier_source`. Pas
d'invention. Pas de formulation "probablement/semble/possiblement" sans
`[A VERIFIER]` explicite. Le script `validate_model.py` (etape 4 ter) refuse
sinon.

**Calibration** : le niveau de specificite metier attendu est celui du tableau
CE de CLI (reference validee). Un "drapeau derive (voir regle d'activation)"
generique n'est PAS acceptable pour une entite non-CLI.

**Exemple bien formule** (ART.CE9, actif si `Ephemerefl = 2`) :
> "Drapeau article ephemere : actif quand l'article est marque comme a cycle
> de vie limite (`Ephemerefl = 2`), co-indexe dans `INDEX_A_MINI` pour
> accelerer les filtrages de catalogue." _(src: `gttmchkart.dhsp:XXX`)_

**Contre-exemple a eviter** (ART.CE9) :
> "Probablement un drapeau lie a l'ephemerite, semble-t-il utilise dans des
> traitements de catalogue."
> **Pourquoi c'est mauvais** : "probablement" et "semble-t-il" sans
> `[A VERIFIER]`, aucune citation, repete l'heuristique sans ajouter de sens
> metier. Correction : soit sourcer proprement, soit marquer `[A VERIFIER]`
> et ne pas rediger.

### Etape 4 ter -- Validation schemas (autonome)

```bash
py scripts/validate_model.py --model {REPERTOIRE_SORTIE}/doc-erp/DAV/ --schemas schemas/
```

Le script `validate_model.py` verifie la conformite aux schemas ET applique la
regle de citation stricte sur les CE : toute `description_metier` d'un CE actif
doit avoir une citation `fichier:ligne` dans `description_metier_source`, sinon
erreur.

Si `validate_model.py` renvoie des erreurs (non-warnings), Claude corrige
en re-editant les YAML et re-execute la validation, jusqu'a exit 0.
Les warnings (relations vers entites externes non documentees dans le
module courant) sont acceptes et reportes dans le livrable final.

### Etape 5 -- Rendu (renderers fournis par le skill)

Le skill fournit **plusieurs renderers autonomes** consommant le meme modele YAML.
PDF n'est **pas** le format final unique : c'est un format parmi plusieurs. D'autres
renderers (Confluence, MkDocs, pandoc, site statique...) viendront s'ajouter sur le
meme principe. Regle d'autonomie : **tout format de livrable necessaire doit etre
produit par un renderer du skill**. Ne jamais court-circuiter avec un script externe
ad-hoc -- un renderer ad-hoc perd la typographie, les tableaux, les diagrammes
Mermaid et les refs inline, ce qui fait regresser silencieusement le livrable
(cf RETEX 2026-04-23 ou un md_to_pdf ad-hoc reportlab a produit un PDF 40x plus
petit que la reference Chrome headless, contenu textuel identique mais rendu
visuel appauvri).

Renderers disponibles aujourd'hui :

| Renderer            | Script                  | Sortie         | Prerequis                       |
|---------------------|-------------------------|----------------|---------------------------------|
| Markdown            | `render_markdown.py`    | `.md`          | PyYAML                          |
| PDF (Chrome headless) | `render_pdf.py`       | `.pdf`         | `markdown` + Chrome ou Edge     |

Chaque renderer produit une sortie par audience (`externe` ou `interne`). En
audience `interne`, les chemins de sortie sont automatiquement suffixes `.interne`.

Au CP1, le collaborateur a precise les formats attendus (defaut : `markdown` +
`pdf`, audiences `externe` + `interne`). Claude execute ci-dessous les commandes
correspondantes.

#### 5a -- Markdown (externe + interne)

```bash
py scripts/render_markdown.py \
   --input {REPERTOIRE_SORTIE}/doc-erp/DAV/ \
   --layer all \
   --audience externe \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV.md

py scripts/render_markdown.py \
   --input {REPERTOIRE_SORTIE}/doc-erp/DAV/ \
   --layer all \
   --audience interne \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV.md
# -> genere DAV.interne.md (suffixe applique automatiquement par le script)
```

Option `--layer` : `business`, `schema`, `technical`, ou `all` (sections empilees avec ancres).

Audiences :
- `externe` (defaut) : livrable autonome destine au public large (clients,
  Confluence publique). Aucune ref `fichier:ligne` visible.
- `interne` : meme contenu + refs inline + annexe "Sources consultees" pour audit
  equipe Divalto. Fichier suffixe `.interne.md`.

#### 5b -- PDF (externe + interne, via Chrome headless)

**Toujours utiliser `render_pdf.py` du skill** pour produire les PDFs. Ne jamais
utiliser un autre script de rendu PDF : le resultat qualitatif chute drastiquement.

```bash
py scripts/render_pdf.py \
   --input {REPERTOIRE_SORTIE}/doc-erp/DAV.md \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV-externe.pdf \
   --title "Module DAV -- audience externe"

py scripts/render_pdf.py \
   --input {REPERTOIRE_SORTIE}/doc-erp/DAV.interne.md \
   --output {REPERTOIRE_SORTIE}/doc-erp/DAV-interne.pdf \
   --title "Module DAV -- audience interne"
```

Chaine interne : Markdown -> HTML (lib `markdown` + extensions tables/fenced_code/toc)
-> PDF (Chrome/Edge headless avec CSS A4 dedie : typographie serif, code monospace,
tableaux stylees, blockquotes colores, numerotation de pages).

Prerequis : Chrome ou Edge installes (recherches dans PATH puis dans les emplacements
Windows classiques). Variable `DOCERP_BROWSER` pour forcer un autre browser.

#### 5c -- Autres renderers (a venir)

Les futurs renderers (Confluence, MkDocs, pandoc, site statique) seront ajoutes
ici sous la meme regle d'autonomie : **fournis par le skill, consomment le YAML
canonique, ne court-circuitent pas**. A chaque nouveau renderer, mettre a jour
le tableau ci-dessus + la checklist de progression + la ligne correspondante
dans la section Scripts.

> **CHECKPOINT CP-Final -- Livrable presente au collaborateur**
> Presenter :
> - Fichiers produits (YAML canoniques + .md + .pdf si demande)
> - Taille du livrable, nb de pages, nb d'entites documentees
> - **Liste exhaustive des items [A VERIFIER]** (c'est le principal point
>   d'interface post-livraison : le collaborateur confirme ou corrige)
> - Statistiques : nb affirmations sourcees vs nb items [A VERIFIER]
> Critere : rendu s'ouvre proprement, chaque couche a du contenu, toute
> affirmation est tracee (source X.13 ou [A VERIFIER]).
>
> Le collaborateur lit le livrable, annote les corrections ciblees, Claude
> les re-injecte en re-generation partielle (pas de re-run complet si
> evitable).

## Scripts

Details d'usage dans chaque script (`--help`). Resume :

| Script                    | Role                                                  |
|---------------------------|-------------------------------------------------------|
| extract_module.py         | Extrait identite + bases + entites d'un module        |
| extract_entity.py         | Extrait champs + indexes d'une entite                 |
| extract_relations.py      | Detecte FK et zooms d'une entite                      |
| assemble_model.py         | Fusionne les .partial.yaml en modele complet          |
| validate_model.py         | Valide les YAML contre les schemas                    |
| render_markdown.py        | Produit un .md depuis le modele (3 couches possibles) |
| render_pdf.py             | Convertit un .md en PDF via Chrome/Edge headless      |

## Dependances

- Python 3.14+ (launcher `py`)
- PyYAML : `py -m pip install pyyaml`
- markdown (pour render_pdf) : `py -m pip install markdown`
- Chrome ou Edge installes (render_pdf uniquement, recherche PATH + emplacements Windows classiques)

## Convention de chemins

| Placeholder              | Usage                                              |
|--------------------------|----------------------------------------------------|
| `{CHEMIN_ERP_STANDARD}`  | Racine X.13 en lecture seule                       |
| `{CHEMIN_FICHIERS}`      | Repertoire dicos .dhsd                             |
| `{CHEMIN_SCHEMA_SQL}`    | Repertoire contenant l'export JSON du schema SQL   |
| `{REPERTOIRE_SORTIE}`    | Racine de sortie pour les YAML et le markdown      |

Pas de chemin absolu en dur dans les scripts ni dans les instructions.
Aucune reference a `archive/` ou `raw/` : le skill doit rester portable et
autonome chez tout collaborateur (cf. `.claude/skills/README.md` sections
Autonomie documentaire et Autonomie vis-a-vis du repertoire prive
workspace).

## Principes

1. **Penser avant de generer** : collecter les parametres a CP1, clarifier toute ambiguite avant extraction.
2. **Minimum viable** : produire ce qui est demande, pas plus. Un module a la fois.
3. **Modifications chirurgicales** : sur un modele existant, re-extraire uniquement les entites touchees.
4. **Critere de succes** : 0 erreur de validation, 3 couches couvertes, rendu Markdown qui s'ouvre proprement.
