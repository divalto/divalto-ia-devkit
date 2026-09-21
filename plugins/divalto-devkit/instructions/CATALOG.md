# Catalog des skills DIVA

**40 skills** organises en **9 workflows**.
Genere le 2026-08-21 (resync).

Pour explorer un skill de maniere interactive, demander a Claude dans une session :
> "Que peux-tu faire ?", "Explique-moi <nom-du-skill>", "Quel skill pour <besoin> ?"

Claude invoquera le skill `discovering-skills` qui s'appuie sur ce meme catalog.

---

## Sommaire par workflow

- [Analyser une demande avant de coder](#analyser-une-demande-avant-de-coder) (7 skills)
- [Creer une entite metier](#creer-une-entite-metier) (6 skills)
- [Modifier une entite existante](#modifier-une-entite-existante) (1 skill)
- [Manipuler les fichiers DIVA texte](#manipuler-les-fichiers-diva-texte) (4 skills)
- [Lire et ecrire les fichiers ISAM](#lire-et-ecrire-les-fichiers-isam) (7 skills)
- [Valider, compiler, synchroniser](#valider-compiler-synchroniser) (3 skills)
- [Tester dans l'ERP et documenter](#tester-dans-l-erp-et-documenter) (3 skills)
- [Migrer un pack ERP / arbitrer un downgrade](#migrer-un-pack-erp-arbitrer-un-downgrade) (2 skills)
- [Reference, consultation et protocoles de session](#reference-consultation-et-protocoles-de-session) (7 skills)
- [Index alphabetique](#index-alphabetique)

---

## Analyser une demande avant de coder <a id="analyser-une-demande-avant-de-coder"></a>

_Parser une user story, interroger le graphe, verifier dans les sources X.13 et produire un rapport pre-action._

### `parsing-diva-request`

Structure une demande DIVA en texte libre (user story + criteres d'acceptation, ou ticket myService d'anomalie) en JSON canonique : type de demande, titre, resume, acteurs, donnees manipulees, domaine ERP pressenti, keywords techniques et metier, CA detectes, message d'erreur.

- **Scripts** : `parse_request.py`

### `querying-diva-graph`

Interroge le graphe Neo4j diva-mcp (snapshot X.12 advisory) pour explorer le standard ERP Divalto.

- **Scripts** : `query_neo4j.py`
- **Prerequis** : diva-mcp (Neo4j advisory X.12)
- **Lies** : `searching-erp-sources`

### `searching-erp-sources`

Verifie l'existence des candidats Neo4j (candidates_x12.json) dans le code source X.13 standard ({CHEMIN_ERP_STANDARD}) et extrait le contexte precis (fichier:ligne, procedure englobante, snippet 10-30 lignes).

- **Scripts** : `extract_context.py`, `verify_x13.py`
- **Prerequis** : diva-mcp (Neo4j advisory X.12)

### `building-preaction-report`

Assemble un rapport d'analyse pre-action a partir des 3 JSON intermediaires (request, candidates_x12, evidence_x13).

- **Scripts** : `build_facts.py`, `build_report.py`, `content_types.py`, `facts_schema.py`
- **Prerequis** : Jinja2 (templates)

### `rendering-preaction-livrable`

Rend le livrable final d'une analyse pre-action a partir d'un facts.json.

- **Scripts** : `render_livrable.py`
- **Prerequis** : Jinja2 (templates)

### `analyzing-diva-request` -- orchestrateur (5 checkpoints)

Orchestre l'analyse pre-action d'une demande DIVA (user story + criteres d'acceptation, ou ticket myService d'anomalie) en mode collaboratif.

- **Prerequis** : Jinja2 (templates), diva-mcp (Neo4j advisory X.12)
- **Lies** : `building-preaction-report`, `parsing-diva-request`, `querying-diva-graph`, `rendering-preaction-livrable`, `searching-erp-sources`

### `assisting-functional-question`

Assiste un collaborateur qui pose une question fonctionnelle conversationnelle sur le standard ERP Divalto (formulations du type "ne comprends pas pourquoi X ne marche pas", "il manque une info pour que Y fonctionne", "quand l'option Z est activee, W n'apparait plus").

- **Scripts** : `translate_keywords.py`
- **Prerequis** : diva-mcp (Neo4j advisory X.12)
- **Lies** : `analyzing-diva-request`, `creating-diva-entity`, `documenting-erp`

---

## Creer une entite metier <a id="creer-une-entite-metier"></a>

_Generer les 3 fichiers source d'une entite (.dhsq, objet metier, zoom SQL) et orchestrer la creation de bout en bout._

### `naming-diva-entities`

A partir du triplet (domaine, entite, table SQL), calcule l'ensemble complet des noms de fichiers, instances, variables, constantes et tokens de substitution necessaires a la generation d'une entite metier DIVA.

- **Scripts** : `compute_names.py`, `validate_names.py`

### `generating-recordsql`

Genere un fichier source RecordSql (.dhsq) complet et valide pour une entite metier DIVA, a partir d'un template Jinja2 et des tokens de nommage.

- **Scripts** : `generate_rsql.py`, `validate_rsql.py`
- **Prerequis** : Jinja2 (templates)
- **Lies** : `writing-diva-files`

### `generating-objet-metier`

Genere un fichier Module Check (.dhsp) complet pour une entite metier DIVA, a partir d'un template Jinja2 et des tokens de nommage.

- **Scripts** : `generate_mchk.py`, `validate_mchk.py`
- **Prerequis** : Jinja2 (templates)
- **Lies** : `binding-zoom-to-field`, `writing-diva-files`

### `generating-zoom-sql`

Genere un fichier Zoom SQL (.dhsp) complet avec les 27 procedures obligatoires du cycle de vie ecran CRUD (creation, modification, suppression, consultation).

- **Scripts** : `generate_zoom.py`, `validate_zoom.py`
- **Prerequis** : Jinja2 (templates)
- **Lies** : `linting-diva-code`, `manipulating-dhsf-screens`, `writing-diva-files`

### `creating-diva-entity` -- orchestrateur (11 checkpoints)

Orchestre la creation de bout en bout d'une entite metier DIVA en mode collaboratif.

- **Scripts** : `cross_validate.py`, `generate_alias.py`
- **Prerequis** : Jinja2 (templates), diva-mcp (Neo4j advisory X.12), xwin7.exe (compilateur Divalto)
- **Lies** : `allocating-menu-enrno`, `compiling-diva-projects`, `generating-objet-metier`, `generating-recordsql`, `generating-zoom-sql` (+8)

### `binding-zoom-to-field`

Ajoute un binding "FK par zoom standard" a une entite metier DIVA existante (post-creation).

- **Scripts** : `dhsp_add_fk.py`
- **Prerequis** : Playwright MCP (navigateur)
- **Lies** : `compiling-diva-projects`, `creating-diva-entity`, `testing-erp`

---

## Modifier une entite existante <a id="modifier-une-entite-existante"></a>

_Ajouter, modifier ou supprimer un champ d'une table existante avec propagation dictionnaire -> masque -> SQL._

### `modifying-diva-entity` -- orchestrateur (4 checkpoints)

Modifie une entite metier DIVA existante : ajout de champ(s), modification de Nature/type, suppression de champ.

- **Scripts** : `modify_dhsd_table.py`
- **Lies** : `binding-zoom-to-field`, `compiling-diva-projects`, `managing-diva-dictionaries`, `manipulating-dhsf-screens`, `syncing-diva-sql` (+1)

---

## Manipuler les fichiers DIVA texte <a id="manipuler-les-fichiers-diva-texte"></a>

_Ecrire en ISO-8859-1+CRLF, manipuler les masques ecran, les dictionnaires et les projets._

### `writing-diva-files`

Ecrit et modifie les fichiers texte Divalto (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps) en garantissant l'encodage ISO-8859-1 et les fins de ligne CRLF.

- **Scripts** : `add_zoom_constant.py`, `convert_file.py`, `patch_file.py`, `verify_encoding.py`, `write_file.py`

### `manipulating-dhsf-screens`

Parse, genere et modifie les masques ecran Divalto (.dhsf).

- **Scripts** : `dhsf_add_fk.py`, `dhsf_modify.py`, `dhsf_parser.py`, `dhsf_template.py`, `is_dhsf_filename.py`, `surcharge_mask.py`
- **Prerequis** : xwin7.exe (compilateur Divalto)
- **Lies** : `binding-zoom-to-field`, `creating-diva-entity`, `writing-diva-files`

### `managing-diva-dictionaries`

Ajoute une table complete dans un dictionnaire Divalto (.dhsd) en generant les 5 zones obligatoires : [CHAMP] (declaration des champs), [TABLE] (structure avec positions calculees), [BASE] (fichier physique), [INDEX] (index avec positions cumulees), et [INDEXL] (mapping).

- **Scripts** : `compare_dhsd_versions.py`, `generate_dhsd_block.py`, `generate_surcharge_field.py`, `insert_dhsd_blocks.py`, `modify_field_nature.py`, `nature_to_size.py`, `suggest_nature.py`, `validate_dhsd.py`
- **Lies** : `binding-zoom-to-field`, `creating-diva-entity`

### `managing-diva-projects`

Cree et modifie les fichiers projet Divalto : .dhpt (projet principal) et .dhps (sous-projet).

- **Scripts** : `add_to_project.py`, `cleanup_communs_from_subproject.py`, `create_subproject.py`, `validate_project.py`
- **Prerequis** : xwin7.exe (compilateur Divalto)

---

## Lire et ecrire les fichiers ISAM <a id="lire-et-ecrire-les-fichiers-isam"></a>

_Acceder aux fichiers binaires proprietaires (.dhfi), multichoix, styles, allouer des numeros de zoom et d'EnrNo._

### `reading-isam-files`

Lit des enregistrements dans les fichiers binaires ISAM Divalto (.dhfi) via DhxIsam64.dll (ctypes).

- **Scripts** : `read_isam.py`, `validate_structure.py`
- **Prerequis** : DhxIsam64.dll (API ISAM Divalto)
- **Lies** : `allocating-menu-enrno`, `reading-multichoix`

### `writing-isam-files`

Ecrit, modifie et supprime des enregistrements dans les fichiers binaires ISAM Divalto (.dhfi) via DhxIsam64.dll (ctypes).

- **Scripts** : `validate_structure.py`, `write_isam.py`
- **Prerequis** : DhxIsam64.dll (API ISAM Divalto), Playwright MCP (navigateur), SQL Server (base Divalto), xwin7.exe (compilateur Divalto)
- **Lies** : `allocating-menu-enrno`

### `reading-fstyle`

Lit les feuilles de style ISAM Divalto (`fstyle.dhfi` et 3 variantes WPF / impression / web dans `C:\divalto\sys\`).

- **Scripts** : `read_fstyle.py`
- **Prerequis** : DhxIsam64.dll (API ISAM Divalto)
- **Lies** : `documenting-erp`, `reading-multichoix`

### `reading-multichoix`

Lit le dictionnaire des multichoix Divalto (fichier `gtfdmc.dhfi` d'un module ERP).

- **Scripts** : `read_multichoix.py`
- **Lies** : `documenting-erp`, `reading-isam-files`

### `managing-diva-error-messages`

Lit, compare ou gere les messages d'erreur applicatifs DIVA (fichiers XXferr : gtferr/ccferr... standard, ou <prefixe>ferr specifique partenaire).

- **Scripts** : `manage_error_messages.py`
- **Prerequis** : DhxIsam64.dll (API ISAM Divalto, via reading-isam-files)
- **Lies** : `generating-objet-metier`, `migrating-erp-downgrade`, `reading-isam-files`, `understanding-integrator-workspace`, `writing-isam-files`

### `allocating-zoom-numbers`

Trouve un numero de zoom libre pour une plage donnee (ou un domaine ERP) en cross-checkant trois sources : `a5tczoom.dhsp` (constantes), `a5f.dhfi` local (enregistrements M4), `a5f.dhfi` de versionx9 (optionnel).

- **Scripts** : `find_free_zoom.py`

### `allocating-menu-enrno`

Trouve un EnrNo libre dans le fichier menu `g3f.dhfi` d'un domaine ERP, selon la plage demandee (`standard` < 100000 reserve ERP, `custom` >= 100000 recommande pour creations utilisateur).

- **Scripts** : `find_free_enrno.py`
- **Lies** : `creating-diva-entity`, `modifying-diva-entity`, `reading-isam-files`

---

## Valider, compiler, synchroniser <a id="valider-compiler-synchroniser"></a>

_Linter le code, compiler avec xwin7, synchroniser la base SQL._

### `linting-diva-code`

Analyse les fichiers source DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhsi, .dhse, .dhpt, .dhps, .sql) et produit un rapport d'erreurs classees par severite, en verifiant la conformite aux ~100 anti-patterns connus (dont regles dictionnaire D04/D10/D11, masque E12-E19 incluant normes graphiques), aux regles de syntaxe DIVA, et aux 11 controles qualite CI (shift-left des moulinettes nightly)

- **Scripts** : `dhsf_info.py`, `lint_diva.py`

### `compiling-diva-projects`

Compile un projet Divalto avec xwin7.exe (buildall ou build incremental), parse le rapport de compilation, et presente les erreurs avec leur contexte (fichier source, ligne)

- **Scripts** : `compile_project.py`, `generate_harness.py`, `parse_compilation.py`
- **Prerequis** : xwin7.exe (compilateur Divalto)

### `syncing-diva-sql`

Synchronise la base SQL Server a partir des dictionnaires compiles via xwin7 synchroauto.

- **Scripts** : `parse_synchro.py`
- **Prerequis** : SQL Server (base Divalto), xwin7.exe (compilateur Divalto)

---

## Tester dans l'ERP et documenter <a id="tester-dans-l-erp-et-documenter"></a>

_Verifier le resultat dans l'ERP via navigateur, generer la documentation technique et la relire._

### `testing-erp`

Interagit avec l'ERP Divalto via navigateur (Playwright MCP) pour verifier le resultat de modifications : connexion, navigation dans le menu, ouverture de zoom, consultation du zoom des zooms, verification post-compilation

- **Prerequis** : Playwright MCP (navigateur)
- **Lies** : `compiling-diva-projects`, `syncing-diva-sql`

### `documenting-erp`

Genere la documentation technique d'un module ou d'une entite de l'ERP Divalto sous forme de contenu structure YAML, independant de la forme du livrable final.

- **Scripts** : `assemble_model.py`, `extract_codified_values.py`, `extract_entity.py`, `extract_module.py`, `extract_narrative.py`, `extract_relations.py`, `merge_narrative.py`, `render_markdown.py`, `render_pdf.py`, `validate_model.py`
- **Prerequis** : DhxIsam64.dll (API ISAM Divalto), SQL Server (base Divalto)
- **Lies** : `reading-multichoix`

### `reviewing-erp-doc`

Relit la documentation technique produite par documenting-erp et la challenge contre les sources X.13 et le referentiel DIVA.

- **Scripts** : `build_review.py`, `detect_doc_contradictions.py`, `detect_omissions.py`, `detect_unsourced.py`, `ingest_deliverable.py`, `prepare_misalign_batch.py`
- **Lies** : `documenting-erp`

---

## Migrer un pack ERP / arbitrer un downgrade <a id="migrer-un-pack-erp-arbitrer-un-downgrade"></a>

_Migrer le specifique d'un client entre versions ERP (rebase sur un SP / version X.N) : ordre de compilation, arbitrage des sources downgrade, verification de l'integrite des surcharges, conversion des fonctions de lecture (seek/Lectab -> objet metier)._

### `converting-diva-lectab`

Convertit en masse les lectures DIVA seek_xxx/Lectab vers l'API objet metier (Give_/Find_/Load_) lors d'une migration, en validant chaque cible contre l'objet metier du pack Std de destination.

- **Scripts** : `convert_lectures.py`
- **Prerequis** : pack Std de la version cible (argument --std), sources .dhsp a convertir (argument --src)
- **Lies** : `compiling-diva-projects`, `linting-diva-code`, `migrating-erp-downgrade`

### `migrating-erp-downgrade`

Guide la migration du specifique d'un client entre versions ERP Divalto et l'arbitrage d'un downgrade (ordre de compilation, arbitrage des sources, integrite des surcharges overWrite).

- **Scripts** : `check_overwrite_order.py`
- **Prerequis** : xwin7.exe (compilateur Divalto), acces aux objets compiles du projet (objets/) pour le verificateur overWrite
- **Lies** : `compiling-diva-projects`, `managing-diva-dictionaries`, `managing-diva-projects`

---

## Reference, consultation et protocoles de session <a id="reference-consultation-et-protocoles-de-session"></a>

### `coding-a5pmtab-screens`

Ecrans specifiques a tableaux A5PMTAB : callbacks `DefProcInterro_*` / `DefProcSaisie_*`,
invocation par `Creer_Parametre` + `AP_Interroger_Tableaux` / `AP_Saisir_Tableaux`, options
HMP, ecrans multi-tableaux et tableaux imbriques.

**A consulter IMPERATIVEMENT avant d'ecrire ou de modifier la signature d'une callback** :
les ecarts de declaration **compilent** et cassent a l'execution sans aucun message --
tableau fige, selection de ligne perdue, boucle infinie.

Deux faits qui coutent des heures quand on les ignore : la valeur de retour d'une callback
(**`0` = « je gere, ne fais rien »**, `1` = « laisse A5PMTAB faire »), et le fait que
**l'option `Fperso` decide** de la forme des callbacks appelees -- le suffixe se declarant
dans `Nom=`.

- **References** : `callbacks-catalogue.md`, `invocation.md`, `pieges-execution.md`, `keywords-verifies.json`
- **Lies** : `coding-diva-advanced`, `manipulating-dhsf-screens`, `generating-zoom-sql`
- **Incomplet, et le declarant** : voir `differe_declare` dans son releve

_Consulter les patterns avances du langage DIVA (REST, JSON, .NET, mtab, tunnels, Harmony) et appliquer les protocoles de session integrateur (identification du workspace, resolution des chemins harmony, classification standard/specifique)._

### `coding-diva-advanced`

Reference des patterns avances du langage DIVA : HTTP/REST, JSON/XML, integration .NET, surcharge (OverWrite), module table (mtab), RecordSql avance (Reader, Collate, Paging), tunnels inter-modules (Ping/Pong), evenements Harmony.

### `understanding-integrator-workspace`

Protocole de session pour un workspace integrateur : identifie le fichier implicite, resout les chemins harmony, lit les profils du .dhpt et classifie standard/specifique.

- **Scripts** : `check_workspace_coherence.py`, `find_canonical_file.py`, `parse_implicit.py`
- **Lies** : `reading-isam-files`, `writing-diva-files`

### `configuring-diva-mcp`

Configure les credentials du serveur MCP diva-mcp pour le partenaire integrateur.

- **Scripts** : `locate_mcp_json.py`, `write_credentials.py`

### `pushing-retex-to-github`

Pousse automatiquement les entrees R-NNN d'un fichier RETEX-skills.md vers un depot GitHub sous forme d'issues.

- **Scripts** : `init_config.py`, `parse_retex_entries.py`, `push_entry.py`, `push_new_entries.py`

### `querying-client-sql`

Conventions d'ecriture SQL cote base client Divalto + helper check_table_scope (portee commune/999 vs par-dossier via T000/TABTYP).

- **Scripts** : `check_table_scope.py`
- **Prerequis** : understanding-integrator-workspace (resolution de connexion), sqlcmd (optionnel, pour --execute)
- **Lies** : `querying-diva-graph`, `syncing-diva-sql`, `understanding-integrator-workspace`

---

## Index alphabetique <a id="index-alphabetique"></a>

| Skill | Workflow | Summary |
|-------|----------|---------|
| `allocating-menu-enrno` | Lire et ecrire les fichiers ISAM | Trouve un EnrNo libre dans le fichier menu `g3f.dhfi` d'un domaine ERP, selon la plage demandee (`standard` < 100000 reserve ERP, `custom` >= 100000 recommande pour creations utilisateur). |
| `allocating-zoom-numbers` | Lire et ecrire les fichiers ISAM | Trouve un numero de zoom libre pour une plage donnee (ou un domaine ERP) en cross-checkant trois sources : `a5tczoom.dhsp` (constantes), `a5f.dhfi` local (enregistrements M4), `a5f.dhfi` de versionx9 (optionnel). |
| `analyzing-diva-request` | Analyser une demande avant de coder | Orchestre l'analyse pre-action d'une demande DIVA (user story + criteres d'acceptation, ou ticket myService d'anomalie) en mode collaboratif. |
| `assisting-functional-question` | Analyser une demande avant de coder | Assiste un collaborateur qui pose une question fonctionnelle conversationnelle sur le standard ERP Divalto (formulations du type "ne comprends pas pourquoi X ne marche pas", "il manque une info pour que Y fonctionne", "quand l'option Z est activee, W n'apparait plus"). |
| `binding-zoom-to-field` | Creer une entite metier | Ajoute un binding "FK par zoom standard" a une entite metier DIVA existante (post-creation). |
| `building-preaction-report` | Analyser une demande avant de coder | Assemble un rapport d'analyse pre-action a partir des 3 JSON intermediaires (request, candidates_x12, evidence_x13). |
| `coding-a5pmtab-screens` | Reference, consultation et protocoles de session | Ecrans specifiques a tableaux A5PMTAB : callbacks, invocation, options HMP, ecrans multi-tableaux. Les ecarts de declaration compilent et cassent a l'execution sans message. |
| `coding-diva-advanced` | Reference, consultation et protocoles de session | Reference des patterns avances du langage DIVA : HTTP/REST, JSON/XML, integration .NET, surcharge (OverWrite), module table (mtab), RecordSql avance (Reader, Collate, Paging), tunnels inter-modules (Ping/Pong), evenements Harmony. |
| `compiling-diva-projects` | Valider, compiler, synchroniser | Compile un projet Divalto avec xwin7.exe (buildall ou build incremental), parse le rapport de compilation, et presente les erreurs avec leur contexte (fichier source, ligne) |
| `configuring-diva-mcp` | Reference, consultation et protocoles de session | Configure les credentials du serveur MCP diva-mcp pour le partenaire integrateur. |
| `converting-diva-lectab` | Migrer un pack ERP / arbitrer un downgrade | Convertit en masse les lectures DIVA seek_xxx/Lectab vers l'API objet metier (Give_/Find_/Load_) lors d'une migration, en validant chaque cible contre l'objet metier du pack Std de destination. |
| `creating-diva-entity` | Creer une entite metier | Orchestre la creation de bout en bout d'une entite metier DIVA en mode collaboratif. |
| `discovering-skills` | unknown | Aide le collaborateur a decouvrir les skills DIVA disponibles et a comprendre leur portee. |
| `documenting-erp` | Tester dans l'ERP et documenter | Genere la documentation technique d'un module ou d'une entite de l'ERP Divalto sous forme de contenu structure YAML, independant de la forme du livrable final. |
| `generating-objet-metier` | Creer une entite metier | Genere un fichier Module Check (.dhsp) complet pour une entite metier DIVA, a partir d'un template Jinja2 et des tokens de nommage. |
| `generating-recordsql` | Creer une entite metier | Genere un fichier source RecordSql (.dhsq) complet et valide pour une entite metier DIVA, a partir d'un template Jinja2 et des tokens de nommage. |
| `generating-zoom-sql` | Creer une entite metier | Genere un fichier Zoom SQL (.dhsp) complet avec les 27 procedures obligatoires du cycle de vie ecran CRUD (creation, modification, suppression, consultation). |
| `linting-diva-code` | Valider, compiler, synchroniser | Analyse les fichiers source DIVA (.dhsp, .dhsq, .dhsd, .dhsf, .dhsi, .dhse, .dhpt, .dhps, .sql) et produit un rapport d'erreurs classees par severite, en verifiant la conformite aux ~100 anti-patterns connus (dont regles dictionnaire D04/D10/D11, masque E12-E19 incluant normes graphiques), aux regles de syntaxe DIVA, et aux 11 controles qualite CI (shift-left des moulinettes nightly) |
| `managing-diva-dictionaries` | Manipuler les fichiers DIVA texte | Ajoute une table complete dans un dictionnaire Divalto (.dhsd) en generant les 5 zones obligatoires : [CHAMP] (declaration des champs), [TABLE] (structure avec positions calculees), [BASE] (fichier physique), [INDEX] (index avec positions cumulees), et [INDEXL] (mapping). |
| `managing-diva-error-messages` | Lire et ecrire les fichiers ISAM | Lit, compare ou gere les messages d'erreur applicatifs DIVA (fichiers XXferr : gtferr/ccferr... standard, ou <prefixe>ferr specifique partenaire). |
| `managing-diva-projects` | Manipuler les fichiers DIVA texte | Cree et modifie les fichiers projet Divalto : .dhpt (projet principal) et .dhps (sous-projet). |
| `manipulating-dhsf-screens` | Manipuler les fichiers DIVA texte | Parse, genere et modifie les masques ecran Divalto (.dhsf). |
| `migrating-erp-downgrade` | Migrer un pack ERP / arbitrer un downgrade | Guide la migration du specifique d'un client entre versions ERP Divalto et l'arbitrage d'un downgrade (ordre de compilation, arbitrage des sources, integrite des surcharges overWrite). |
| `modifying-diva-entity` | Modifier une entite existante | Modifie une entite metier DIVA existante : ajout de champ(s), modification de Nature/type, suppression de champ. |
| `naming-diva-entities` | Creer une entite metier | A partir du triplet (domaine, entite, table SQL), calcule l'ensemble complet des noms de fichiers, instances, variables, constantes et tokens de substitution necessaires a la generation d'une entite metier DIVA. |
| `parsing-diva-request` | Analyser une demande avant de coder | Structure une demande DIVA en texte libre (user story + criteres d'acceptation, ou ticket myService d'anomalie) en JSON canonique : type de demande, titre, resume, acteurs, donnees manipulees, domaine ERP pressenti, keywords techniques et metier, CA detectes, message d'erreur. |
| `pushing-retex-to-github` | Reference, consultation et protocoles de session | Pousse automatiquement les entrees R-NNN d'un fichier RETEX-skills.md vers un depot GitHub sous forme d'issues. |
| `querying-client-sql` | Reference, consultation et protocoles de session | Conventions d'ecriture SQL cote base client Divalto + helper check_table_scope (portee commune/999 vs par-dossier via T000/TABTYP). |
| `querying-diva-graph` | Analyser une demande avant de coder | Interroge le graphe Neo4j diva-mcp (snapshot X.12 advisory) pour explorer le standard ERP Divalto. |
| `reading-fstyle` | Lire et ecrire les fichiers ISAM | Lit les feuilles de style ISAM Divalto (`fstyle.dhfi` et 3 variantes WPF / impression / web dans `C:\divalto\sys\`). |
| `reading-isam-files` | Lire et ecrire les fichiers ISAM | Lit des enregistrements dans les fichiers binaires ISAM Divalto (.dhfi) via DhxIsam64.dll (ctypes). |
| `reading-multichoix` | Lire et ecrire les fichiers ISAM | Lit le dictionnaire des multichoix Divalto (fichier `gtfdmc.dhfi` d'un module ERP). |
| `rendering-preaction-livrable` | Analyser une demande avant de coder | Rend le livrable final d'une analyse pre-action a partir d'un facts.json. |
| `reviewing-erp-doc` | Tester dans l'ERP et documenter | Relit la documentation technique produite par documenting-erp et la challenge contre les sources X.13 et le referentiel DIVA. |
| `searching-erp-sources` | Analyser une demande avant de coder | Verifie l'existence des candidats Neo4j (candidates_x12.json) dans le code source X.13 standard ({CHEMIN_ERP_STANDARD}) et extrait le contexte precis (fichier:ligne, procedure englobante, snippet 10-30 lignes). |
| `syncing-diva-sql` | Valider, compiler, synchroniser | Synchronise la base SQL Server a partir des dictionnaires compiles via xwin7 synchroauto. |
| `testing-erp` | Tester dans l'ERP et documenter | Interagit avec l'ERP Divalto via navigateur (Playwright MCP) pour verifier le resultat de modifications : connexion, navigation dans le menu, ouverture de zoom, consultation du zoom des zooms, verification post-compilation |
| `understanding-integrator-workspace` | Reference, consultation et protocoles de session | Protocole de session pour un workspace integrateur : identifie le fichier implicite, resout les chemins harmony, lit les profils du .dhpt et classifie standard/specifique. |
| `writing-diva-files` | Manipuler les fichiers DIVA texte | Ecrit et modifie les fichiers texte Divalto (.dhsp, .dhsq, .dhsd, .dhsf, .dhpt, .dhps) en garantissant l'encodage ISO-8859-1 et les fins de ligne CRLF. |
| `writing-isam-files` | Lire et ecrire les fichiers ISAM | Ecrit, modifie et supprime des enregistrements dans les fichiers binaires ISAM Divalto (.dhfi) via DhxIsam64.dll (ctypes). |
