# Changelog

Toutes les modifications notables du plugin `divalto-devkit` sont documentees dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet adhere au [Semantic Versioning](https://semver.org/lang/fr/).

## [0.0.2] - 2026-05-28

### Added

#### Infrastructure MCP
- `.mcp.json` : declaration du serveur `diva-mcp` au niveau plugin.
- Hook `check_mcp_version.py` (SessionStart) : verifie la version du serveur MCP au demarrage de session.
- Skill `configuring-diva-mcp` : configure les credentials du serveur `diva-mcp` (scripts `locate_mcp_json.py`, `write_credentials.py`, reference `credentials-format.md`, evals).

#### Commande d'initialisation
- Commande slash `/divalto-devkit-init` : bootstrap d'un workspace integrateur Divalto.

#### Skill `understanding-integrator-workspace` (nouveau)
- Comprehension du workspace integrateur Harmony : classification des fichiers, resolution SQL, fichiers implicites, profils poste.
- References : `classification.md`, `harmony-paths.md`, `implicit-file.md`, `poste-memory-template.md`, `profile.md`, `sql-resolution.md`.
- Scripts : `_resolver.py`, `check_workspace_coherence.py`, `find_canonical_file.py`, `parse_implicit.py`.

#### Skill `pushing-retex-to-github` (nouveau)
- Pousse les entrees `RETEX-skills.md` vers GitHub Issues (deduplication, parsing, init config).
- Hook `push_retex_to_github.py` (Stop) : push automatique des nouvelles entrees RETEX en fin de session.
- Scripts : `init_config.py`, `parse_retex_entries.py`, `push_entry.py`, `push_new_entries.py`.
- References : `issue-format.md`, `setup-gh-cli.md`.

#### Skill `manipulating-dhsf-screens` (enrichissement majeur)
- Pattern OverWrite des masques (`.dhsf`) : reference `dhsf-overwrite-pattern.md` + script `surcharge_mask.py`.
- Structure complete `.dhsf` (`dhsf-structure.md`).
- References composants : `composant-bitmap-constante.md`, `composant-bitmap-variable.md`, `composant-cadre.md`, `composant-champ.md`, `composant-groupbox.md`, `composant-obj-texte.md`.
- Surcharge des feuilles de style (`surcharge-feuilles-style.md`).
- API `XMeSetAttribut` dynamique (`xmesetattribut-dynamique.md`).
- Case-sensitivity DIVA (`diva-case-sensitivity.md`).
- Script utilitaire `is_dhsf_filename.py`.

#### Skill `managing-diva-dictionaries` (surcharge)
- Pattern de surcharge de dictionnaire : `dhsd-surcharge-pattern.md`, `dhsd-surcharge-indexes.md`.
- Script `generate_surcharge_field.py` : generation d'un champ de surcharge.

#### Skill `generating-recordsql`
- Reference `dhsq-overwrite-pattern.md` : pattern OverWrite des RecordSql.

#### Skill `coding-diva-advanced`
- Reference `zoom-hooks-reference.md` : catalogue des hooks zoom DIVA.

#### Skill `compiling-diva-projects`
- Script `compile_project.py` : compilation pilotee (buildall / incremental) avec parsing du rapport.

### Changed

- `plugin.json` : version `0.0.1` -> `0.0.2`.
- `instructions/install.py` : mise a jour des etapes d'installation.
- `discovering-skills` : `SKILL.md` et `catalog.json` mis a jour avec les 3 nouveaux skills (`configuring-diva-mcp`, `pushing-retex-to-github`, `understanding-integrator-workspace`).
- `managing-diva-dictionaries` : `SKILL.md`, `evals.json`, references `dhsd-5-zones.md`, `dhsd-anti-patterns.md`, `nature-types.md` et `validate_dhsd.py` enrichis (prise en charge de la surcharge).
- `managing-diva-projects` : `SKILL.md`, references `dhps-structure.md`, `dhpt-structure.md`, `project-anti-patterns.md` et scripts `add_to_project.py`, `create_subproject.py`, `validate_project.py` revus.
- `manipulating-dhsf-screens/SKILL.md` : reorganisation et integration des nouveaux composants/patterns.
- `coding-diva-advanced/SKILL.md` et `reference/overwrite-pattern.md` : alignement avec les nouvelles references OverWrite (dhsf, dhsq).
- `compiling-diva-projects/SKILL.md` et `reference/xwin7-syntax.md` : alignement avec le nouveau script `compile_project.py`.
- `generating-recordsql/SKILL.md` : renvoi vers le nouveau pattern OverWrite.

## [0.0.1] - Initial

- Version initiale du plugin `divalto-devkit`.
