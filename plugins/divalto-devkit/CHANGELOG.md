# Changelog

Toutes les modifications notables du plugin `divalto-devkit` sont documentees dans ce fichier.

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet adhere au [Semantic Versioning](https://semver.org/lang/fr/).

## [0.1.1] - 2026-09-18

Ce cycle integre **179 retours d'experience** remontes par les integrateurs : deux
nouveaux skills, une nouvelle page de reference sur le langage Diva, et une cinquantaine
de regles corrigees, completees ou retirees. **177 sont clos.** Deux restent ouverts et
seront traites au prochain cycle : la recuperation d'une colonne issue d'une table
jointe dans le record de travail d'un explorateur, et la comparaison de deux masques
surcharges entre deux versions d'ERP.

### Added

#### Skill `coding-a5pmtab-screens` (nouveau)
- Ecrans specifiques a tableaux A5PMTAB : catalogue des callbacks `DefProcInterro_*` /
  `DefProcSaisie_*` avec, pour chacun, quand il est appele et ce qu'on peut y faire.
- Sequence d'invocation complete (`Creer_Parametre` + `AP_Interroger_Tableaux` /
  `AP_Saisir_Tableaux`), options HMP, ecrans multi-tableaux et tableaux imbriques.
- Les pieges qui ne se voient qu'a l'execution : **un ecart de signature de callback
  COMPILE** et casse ensuite sans aucun message -- tableau fige, selection de ligne
  perdue, boucle infinie.

#### Skill `querying-client-sql` (nouveau)
- Quatre conventions qui expliquent l'essentiel des erreurs constatees : un nom de table
  en MAJUSCULES est un nom de **dictionnaire** et pas forcement le nom ODBC ; la
  collation est **binaire**, donc la casse et les accents comptent ; le schema est `dbo` ;
  la structure reelle se decouvre via `INFORMATION_SCHEMA`.
- Script `check_table_scope.py` : dit si une table de parametrage est commune a tous les
  dossiers ou propre a un dossier. **La reponse conditionne tout filtrage** -- filtrer
  une table commune sur un dossier metier renvoie zero ligne et laisse croire, a tort, a
  une absence de parametrage.

#### Skill `coding-diva-advanced` (nouvelle page de reference du langage)
- `reference/syntaxe-de-base.md` : les faux amis du langage avec, chaque fois, la forme
  reelle a ecrire -- `ElseIf` -> `Elsif`, `Pos` -> `String`, `Len` -> `Length`, `Str$` ->
  `Str`, `SplitCount` / `SplitItem` -> `SplitList` puis `ListCount` / `ListIndex`.
  `Round` n'est pas une fonction, c'est une instruction de mode.
- Matrice complete des 4 boucles (terminateur, sortie, continue). Le booleen Diva a
  **trois** etats, et `NON` vaut `1`, jamais `0`.
- `Oui` et `Non` sont des constantes declarees **par programme** : les ecrire dans votre
  module donne « Mot inconnu » tant qu'il ne les declare pas. Et « Mot inconnu » ne veut
  presque jamais dire « absent de cette version » -- les fonctions natives appartiennent
  au **langage**, pas au pack ERP.
- La declaration `Module` n'est pas transitive, et les deux blocs d'un masque de
  surcharge (`[diva]` et `[diva_base]`) ont des declarations independantes.
- Couvre aussi la surcharge et la visibilite, le RecordSql avance et les tunnels
  inter-modules. Chaque affirmation porte sa source et son niveau de preuve.

#### Skill `migrating-erp-downgrade`
- `reference/montee-version-surcharge.md` : les deux actions xwin7 qui reportent une
  surcharge sur un nouveau standard, avec leurs parametres et trois points qui
  surprennent -- le compte rendu ne va pas sur la sortie demandee mais dans le **journal
  de mise a niveau de l'installation** ; le **code de sortie n'est pas fiable** ; il faut
  **un passage par projet**, un `.dhpt` ne couvrant qu'une partie des masques.

#### Skill `manipulating-dhsf-screens`
- Trois pages neuves : `composant-grille-wpf.md`, `composant-rich-edit.md`,
  `volets-ywpf.md`.
- Masquage d'une colonne de tableau, et template de zoom enrichi pour les zooms metier a
  nombreux champs.

#### Skill `querying-diva-graph`
- `reference/mcp-query-pitfalls.md` : trois pieges d'interrogation du graphe, dont les
  corps de fonctions annonces « programme protege » alors que les sources equivalentes
  sont livrees.
- Detection de la version ERP a utiliser pour interroger le graphe, confirmee en debut de
  session plutot que choisie silencieusement.

#### Skills `reading-isam-files` / `writing-isam-files`
- Champs binaires : ce qui est exprimable et comment l'ecrire.
- Cible overlay et surcharge des fichiers `*u`.

#### Autres ajouts
- `managing-diva-dictionaries` : ajout d'un champ sur une table existante, avec recalcul
  automatique des positions -- tables et index.
- `syncing-diva-sql` : etape de **pre-vol** avant application, pour voir ce qui va
  changer avant que ca change.
- `understanding-integrator-workspace` : le mecanisme des **tables communes** est
  documente -- une table declaree commune a toutes ses lignes sur le dossier commun.
- `linting-diva-code` : nouvelles regles de lint, dont les demandes qui revenaient le
  plus souvent.

### Changed

- `compiling-diva-projects` : analyse du rapport fiabilisee (compilation complete ou
  incrementale, interrompue, erreurs sur plusieurs lignes) ; le chemin d'installation de
  xwin7 n'est plus suppose, il est derive de l'option qui le designe -- pour les postes
  ou Divalto n'est pas sur `C:`.
- `managing-diva-dictionaries` : les tailles reelles declarees sont respectees, et le
  routage se fait vers la **surcharge** plutot que vers une modification du standard.
- `writing-isam-files` : structures de lecture completees, lecture par cle et parcours
  sequentiel plus robustes. A l'ecriture, l'identite du developpeur est desormais
  **exigee** plutot que supposee -- une valeur par defaut se retrouvait dans les donnees.
- `understanding-integrator-workspace` : un poste sans cle de registre Divalto n'est pas
  un cas exotique, c'est frequent sur les portables et les installations hors installeur.
  La resolution des chemins repart alors de l'arborescence reelle, **avec confirmation**,
  au lieu d'echouer.
- `writing-diva-files` : modification de fichier plus robuste, et role du garde-fou
  d'encodage clarifie -- ce qu'il bloque, ce qu'il ne bloque pas, et pourquoi.
- `building-preaction-report` / `rendering-preaction-livrable` : orchestrateur d'analyse
  pre-action plus robuste, et le livrable porte les **libelles reels** des elements
  selectionnes la ou il affichait des identifiants techniques.
- `assisting-functional-question` : `reference/lexique-metier-technique.md` enrichi, avec
  un avertissement utile -- les codes `Ce<n>` sont polysemiques d'une table a l'autre, et
  un multichoix peut etre lie a un autre champ que celui qu'on suppose.
- `testing-erp` : prerequis pour tester dans l'ERP (acces web, configuration serveur)
  clarifies. Plusieurs demandes de ce lot relevaient de l'installation plutot que du
  devkit : elles sont fermees en le disant, avec ce qui reste couvert de notre cote.
- `pushing-retex-to-github` : vous n'avez rien a envoyer manuellement. Vos retours
  remontent automatiquement en issues sur le depot du devkit, pousses par ce skill.

### Fixed

- `manipulating-dhsf-screens` : trois composants que le devkit documentait mais que son
  propre analyseur ignorait -- **cadre**, **bitmap constante**, **bitmap variable** --
  sont desormais reconnus. Un masque qui en contenait etait analyse sans les voir.
- `manipulating-dhsf-screens` : regles de syntaxe masque -- `[param_case]` n'est valide
  qu'en case a cocher ; la valeur non-cochee est `1`, jamais `0` ; la page Identifiants
  n'a de sens que si la table porte le socle d'audit ; un champ reference doit exister
  dans la table.
- `syncing-diva-sql` : erreur de documentation qui coutait du temps -- le rapport produit
  par l'option de sortie contient les logs d'etapes et le total d'erreurs, **PAS le
  DDL**. Le DDL applique se trouve dans le script SQL genere, accessible par une autre
  option.
- `managing-diva-dictionaries` : la capacite d'un container ne se lit pas sur sa ligne de
  placement mais dans la **declaration globale**. Une lecture au mauvais endroit
  comparait des zeros et concluait « aucun changement » sur n'importe quel fichier.
- `querying-diva-graph` : un nom d'outil faux figurait dans la documentation de trois
  skills -- suivre la doc menait a un appel qui n'existe pas.
- `compiling-diva-projects` : les noms de profil accentues sont transmis dans l'encodage
  attendu par xwin7, ce qui evite un echec sans message clair.
- `writing-diva-files` : encodage des scripts PowerShell generes -- PowerShell 5.1 lit un
  `.ps1` sans BOM comme de l'ANSI, ce qui corrompt les chemins accentues.
- `pushing-retex-to-github` : encodage du push corrige, les accents ne partent plus en
  caracteres illisibles dans les issues.

### Removed

- `linting-diva-code` : les regles qui produisaient des faux positifs de masse sont
  retirees ou corrigees -- dont une qui ne produisait **que** des faux positifs, et une
  autre qui se declenchait sur les en-tetes de surcharge. Plusieurs milliers
  d'avertissements sans objet ont disparu. **Une regle qui crie sur le standard livre est
  fausse par construction** : le standard est la reference, pas le suspect.

## [0.1.0] - 2026-05-28

> Publiee sous le numero `0.0.2` dans une version anterieure de ce fichier. Renumerotee
> en `0.1.0` pour refleter l'ampleur reelle du lot (trois nouveaux skills) et rester
> coherente avec `plugin.json`.

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

- `plugin.json` : version `0.0.1` -> `0.1.0`.
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
