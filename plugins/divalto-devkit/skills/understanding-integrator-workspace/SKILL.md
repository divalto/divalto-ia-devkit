---
name: understanding-integrator-workspace
description: >
  Quand utiliser : en debut de toute session sur un workspace integrateur Divalto
  (typiquement sous l'alias harmony /specifs/<workspace>/), avant toute lecture,
  copie ou generation de fichier. Particulierement critique sur un poste d'integrateur
  ou cohabitent systematiquement plusieurs versions de l'ERP, plusieurs bases de
  donnees clients et plusieurs projets d'integration -- ce sont precisement les
  contextes ou une copie ou lecture aveugle commence sur de mauvaises bases.

  Quoi faire : identifier le fichier implicite du workspace (search path declaratif),
  resoudre les chemins harmony (/specifs/, /sources/, /objets/, /fichiers/, /divalto/, ...)
  via divaltopath.cfg et fconfig, lire les profils typed du .dhpt, retrouver la
  connexion SQL (porte Harmony ODBC + porte ADO.NET), classifier les chemins standard
  / specifique avec validation utilisateur obligatoire. Evite les erreurs de version,
  les copies aveugles de fichiers compagnons et les generations contre une base mal
  identifiee.

  Discipline registre Windows : les acces au registre sont strictement limites
  a une liste blanche documentee (R-5 pour Divalto, R-10 pour DSN ODBC). Pas
  d'exploration libre, pas de `reg query /s`, pas de lecture de cles voisines
  "au cas ou". Le registre du poste integrateur contient de l'information
  sensible au-dela de Divalto -- voir principe transverse P-C.
---

# understanding-integrator-workspace

## Contenu

- Vocation
- Quand utiliser ce skill
- Principes transverses (P-A, P-B, P-C)
- Workflow -- protocole de session
- Workflow -- trouver la version canonique d'un fichier
- Workflow -- capture/relecture des conventions du poste (memoire de session)
- Table de synthese des regles (R-1 a R-16)
- References documentaires

## Vocation

Sur un poste d'integrateur Divalto, il y a **systematiquement** plusieurs versions de l'ERP installees cote a cote, plusieurs bases de donnees clients, plusieurs projets d'integration. Aller lire ou copier des fichiers de maniere aveugle sans savoir si c'est le bon est **le meilleur moyen de commencer sur de mauvaises bases** -- erreur de version, surcharge cassee, doublons, references croisees inconsistantes, fichiers compagnons sources d'une mauvaise version, etc.

Ce skill donne les **competences pour comprendre l'architecture d'un projet d'integration** afin de :

1. **Trouver les eventuelles erreurs de parametrage** -- coherence implicite ↔ profils du `.dhpt` ↔ `divaltopath.cfg` ↔ `fconfig` ↔ `divaltoserver.cfg` ↔ `connexions.xml` ↔ DSN ODBC ↔ registre Windows. Toutes ces couches doivent matcher ; une divergence est un bug latent qui se revelera tard et coutera cher a diagnostiquer.
2. **Eviter les erreurs au moment de generer du code** ou de **copier des fichiers compagnons** (`_base.dhsf` etc.) : utiliser systematiquement le search path declaratif du workspace, pas un `find` aveugle qui sortirait une version aleatoire parmi les multiples versions installees.
3. **Controler et challenger l'installation existante**, proposer mieux quand c'est pertinent.
4. **Poser les bonnes questions** quand l'environnement est ambigu, plutot que de presumer (P-A/P-B).

Le skill est **un outil de comprehension et de prudence**, pas seulement une boite a outils de resolution de chemins.

## Quand utiliser ce skill

Au plus tard **avant** :

- Toute creation de surcharge (`.dhsf`, `.dhsd`, `.dhsq`, `.dhsp`, `.dhpt`, `.dhps`) qui necessite un fichier compagnon `_base` ou une reference au standard
- Toute lecture d'un fichier "du standard" pour comprendre un pattern ou faire un cross-check
- Toute identification de la version ERP cible du workspace
- Toute operation de copie / reference entre la zone specifique et la zone standard
- Toute generation de fichier qui depend de chemins (cheminbases, repobjet, etc.)
- Tout audit de coherence sur un workspace existant

Si la session demarre sur une question qui ne touche pas la distinction standard/specifique (ex: explication d'un concept general), le protocole peut etre differe jusqu'au premier moment ou la distinction devient pertinente. Mais des qu'elle est pertinente : protocole obligatoire avant action.

## Principes transverses

Trois interdictions absolues qui encadrent toute application des regles. Aucune regle ne peut etre executee en violant ces principes -- ils priment sur toute heuristique, intuition, ou recoupement "evident".

### P-A -- Interdiction d'inventer

Si une heuristique ne trouve aucun candidat (fichier, chemin, profil, version, etc.), **ne jamais inventer un nom plausible**. La seule action acceptable est : signaler explicitement au collaborateur qu'aucun candidat n'a ete trouve, et lui demander de fournir la valeur.

| Anti-pattern interdit | Action correcte |
|----------------------|-----------------|
| "Je n'ai pas trouve `impltmp.txt`, je vais essayer un autre nom plausible" | "Aucun fichier implicite trouve. Peux-tu me donner le chemin absolu ?" |
| "Le `.dhpt` reference `impltmp.txt` introuvable -- je vais creer un fichier vide" | "Le `.dhpt` reference `impltmp.txt` introuvable. As-tu le chemin reel, ou faut-il le creer (avec quel contenu) ?" |
| "Pas de `divaltopath.cfg` -- je vais resoudre l'alias par heuristique" | "Sans `divaltopath.cfg`, je ne peux pas resoudre cet alias. Ou se trouve la table de resolution sur ce poste ?" |

### P-B -- Interdiction de presumer

Meme si une heuristique trouve UN candidat avec tous les signes de confiance (refere ET present, recoupement parfait, unique resultat), **ne jamais proceder a l'etape suivante sans confirmation explicite** du collaborateur. Le silence ne vaut pas approbation.

| Anti-pattern interdit | Action correcte |
|----------------------|-----------------|
| "J'ai trouve UN seul candidat coherent, je suppose que c'est le bon et je continue" | "J'ai trouve UN candidat : `<chemin>`. Est-ce bien le fichier a utiliser ?" |
| "Le collaborateur n'a rien dit depuis ma derniere demande, donc c'est OK" | Re-demander explicitement (silence != approbation). |

Les deux principes sont des corollaires de la meme regle racine : **ask, don't guess**. P-A couvre le cas "rien trouve" (tentation d'inventer), P-B couvre le cas "quelque chose trouve" (tentation de presumer). Les deux modes d'echec sont aussi dangereux l'un que l'autre.

### P-C -- Discipline registre Windows (liste blanche stricte)

Le registre Windows d'un poste integrateur contient de l'information sensible **au-dela de Divalto** : configurations d'autres applications (Office, IDE, navigateurs), credentials systeme, parametres utilisateur, historiques d'apps tierces, traces d'usage. Pour respecter la confidentialite du poste partenaire et rester focalise sur la mission du skill, **Claude lit UNIQUEMENT les cles / valeurs strictement necessaires aux regles documentees, jamais en exploration libre**.

#### Liste blanche -- seules lectures autorisees

| Regle | Cle autorisee | Valeurs autorisees |
|-------|---------------|--------------------|
| **R-5** (decouverte Divalto) | `HKLM\SOFTWARE\WOW6432Node\Divalto\divalto.ini\System` + fallback `HKLM\SOFTWARE\Divalto\divalto.ini\System` | `CheminUl1`, `CheminFpartd` -- rien d'autre sous ces cles |
| **R-10** (DSN ODBC) | `HKLM/HKCU \SOFTWARE\[WOW6432Node\]ODBC\ODBC.INI\<DSN>` (4 vues) pour un `<DSN>` precis identifie par R-9 | Champs de configuration ODBC standard : `Driver`, `Server`, `Database`, `Trusted_Connection`, `Encrypt`, `TrustServerCertificate`. Les autres valeurs sous la cle DSN ciblee sont tolerees si elles font partie de la chaine ODBC standard. |
| **R-10** (listing DSN, conditionnel) | `HKLM\SOFTWARE\[WOW6432Node\]ODBC\ODBC.INI\ODBC Data Sources` | Listing **uniquement si necessaire** pour resoudre un DSN ambigu -- pas par precaution |

#### Liste noire -- interdictions explicites

| Anti-pattern interdit | Pourquoi |
|----------------------|----------|
| `reg query HKLM\SOFTWARE` (ou tout chemin de premier niveau non-cible) | Enumeration globale -- expose tout le poste |
| `reg query <cle> /s` (recursion) | Aspire l'arbre entier d'une branche -- meme probleme |
| Lecture sous `HKLM\SOFTWARE\Microsoft\...`, `HKCU\SOFTWARE\Microsoft\...` | Donnees Microsoft Office, Windows, navigateurs : hors-perimetre absolu |
| Lecture sous des cles d'IDE, mailers, autres apps tierces | Idem -- jamais necessaire pour le skill |
| Decouverte par voisinage (lire les sous-cles d'une cle voisine "au cas ou") | Aucune valeur documentee ne necessite ca -- signal d'arret |
| "J'ai juste verifie ce qui existait" | Chaque lecture doit etre **justifiable par une regle precise du skill** |

| Anti-pattern interdit | Action correcte |
|----------------------|-----------------|
| "La cle R-5 est introuvable, je vais regarder les cles voisines pour voir ce qui existe" | "La cle R-5 est introuvable sous les deux paths documentes. P-A : demander au collaborateur ou se trouve l'installation Divalto." |
| "Je vais lister `HKLM\SOFTWARE` pour voir si Divalto est ailleurs" | NON. P-A : demander. |
| "Le DSN n'est pas dans les 4 vues attendues, je vais chercher dans les DSN.INI d'autres apps" | NON. P-A : demander. |

#### Principe d'arret

Si une operation registre n'est pas couverte par R-5 ou R-10, c'est qu'elle est **hors-perimetre** du skill. Le besoin d'explorer plus loin est le **signal d'arret** : appliquer **P-A** (demander au collaborateur l'info manquante) plutot que d'aller fouiller. La discipline est **non-negociable** -- elle prime sur tout reflexe d'enquete autonome.

#### Justification

- **Confidentialite du poste partenaire** : le registre peut contenir credentials d'autres clients, traces de sessions, donnees personnelles -- jamais utiles pour Divalto, toujours sensibles.
- **Focus du skill** : si l'info n'est pas dans une cle documentee, le skill n'est de toute facon pas en mesure de l'interpreter -- exploration = bruit.
- **Tracabilite / audit** : chaque lecture justifiable par une regle = audit possible des actions du skill, alignement avec la posture "minimum viable" de CLAUDE.md.

## Workflow -- protocole de session

Au lancement d'une session sur un workspace integrateur, executer ces etapes dans l'ordre **avant** toute operation qui depend de la distinction standard / specifique :

1. **R-1 -- Identifier le fichier implicite** : trouver le fichier implicite du workspace, **demander confirmation au collaborateur** meme si on pense l'avoir trouve. Voir [reference/implicit-file.md](reference/implicit-file.md).
2. **R-2 -- Parser le fichier implicite** ligne par ligne (search path ordonne). Voir [reference/implicit-file.md](reference/implicit-file.md).
3. **Pre-check workspace** : chercher les `.dhpt` de surcharge du workspace (`find <workspace> -iname "*.dhpt"` puis filtrer ceux dont l'en-tete est `xwin-s-projet`). Un workspace mature contient typiquement plusieurs `.dhpt` (un par domaine ERP : achat-vente, compta, paie...).
4. **R-15 -- Lire les profils des `.dhpt`** (conditionnel) : si le pre-check a trouve au moins un `.dhpt` de surcharge, extraire les 4 champs typés (`repobjet`, `repbrowse`, `repobjetsurcharge`, `repbrowsesurcharge`). Ces paths donnent le signal de classification le plus fort. Voir [reference/profile.md](reference/profile.md).
5. **R-14 -- Classifier les chemins de l'implicite** (STANDARD / SPECIFIQUE / RUNTIME / URL SQL) et **presenter la classification au collaborateur sous forme de tableau pour validation ligne par ligne**. Voir [reference/classification.md](reference/classification.md).
6. **Stocker la classification validee** comme reference de la session pour toutes les operations ulterieures.

Cas special -- workspace en cours d'initialisation : si l'etape 3 ne trouve aucun `.dhpt`, l'etape 4 est sautee. R-14 s'appuie alors uniquement sur l'alias `divalto` + heuristiques content-based + position + nommage.

## Workflow -- trouver la version canonique d'un fichier (R-13)

Cas d'usage central du skill. Procedure : identifier l'implicite (R-1), parser ses lignes ordonnees (R-2), resoudre chaque chemin filesystem (R-3 → R-4 → R-5), chercher le fichier par nom dans l'ordre, **premier hit gagne**. Si introuvable → **P-A** : ne JAMAIS aller chercher dans un dossier "Standard generique" hors search path (regression test a empecher).

R-13 s'applique au type **sources** (`.dhsf`, `.dhsp`, `.dhsd`, `.dhsq`). Pour les objets compiles (`.dhof`/`.dhoq`) ou le browse, le canal de resolution passe par les champs `repobjet*`/`repbrowse*` du profil du `.dhpt` (R-15).

→ Detail complet, procedure pas a pas, cas d'usage typiques, garde-fous, canal par type d'artefact : [reference/harmony-paths.md](reference/harmony-paths.md) section R-13.

## Workflow -- capture/relecture des conventions du poste (R-16)

Sur un poste integrateur mature, les conventions decouvertes par l'audit initial (R-1 a R-15) sont **stables dans le temps** mais **specifiques au poste** : implicite actif, mode `cheminbases`, casse des versions ERP, cles `[general]` obligatoires, profils actifs. Plutot que de re-poser ces questions au collaborateur a chaque session, **R-16** capture ces conventions dans la memoire de session Claude Code (`~/.claude/projects/<workspace>/memory/poste-conventions.md`) pour les relire au demarrage des sessions suivantes.

Procedure (resume) :

1. **A la 1ere session** sur un workspace nouveau, apres R-1 a R-15 : presenter les 5 conventions observees au collaborateur, demander confirmation, ecrire `poste-conventions.md` selon le template documente.
2. **A chaque session ulterieure** : relire `poste-conventions.md` en premier, presenter le resume au collaborateur, confirmer que les conventions tiennent toujours, demarrer la tache informe.

Garde-fous : P-B (jamais d'ecriture sans confirmation explicite), memoire locale au poste (non transposable cross-postes), pas de mecanisme automatique (bonne pratique, pas un hook).

→ Detail complet, template a 5 sections, procedure pas a pas, limites : [reference/poste-memory-template.md](reference/poste-memory-template.md).

## Table de synthese des regles

| R | Sujet | Reference |
|---|-------|-----------|
| R-1 | Identifier le fichier implicite du workspace | [implicit-file.md](reference/implicit-file.md) |
| R-2 | Analyser le fichier implicite ligne par ligne | [implicit-file.md](reference/implicit-file.md) |
| R-3 | Resoudre un chemin harmony via `divaltopath.cfg` | [harmony-paths.md](reference/harmony-paths.md) |
| R-4 | Resoudre un chemin harmony via `fconfig` cle E (fallback) | [harmony-paths.md](reference/harmony-paths.md) |
| R-5 | Decouvrir `<DIVA_ROOT>` et `fconfig` via le registre Windows | [harmony-paths.md](reference/harmony-paths.md) |
| R-6 | Grammaire et semantique du fichier implicite | [implicit-file.md](reference/implicit-file.md) |
| R-7 | Resoudre le chemin SQL via `divaltoserver.cfg` (porte Harmony) | [sql-resolution.md](reference/sql-resolution.md) |
| R-8 | Resoudre le chemin SQL via `fconfig` cle B (fallback Harmony) | [sql-resolution.md](reference/sql-resolution.md) |
| R-9 | Extraire le DSN ODBC depuis `fhsql.dhfi` cle C | [sql-resolution.md](reference/sql-resolution.md) |
| R-10 | Lire la configuration ODBC d'un DSN dans le registre | [sql-resolution.md](reference/sql-resolution.md) |
| R-11 | Porte ADO.NET : `impltmp.xml` → `connexions.xml` | [sql-resolution.md](reference/sql-resolution.md) |
| R-12 | Verifier la joignabilite SQL sans attaquer la base directement | [sql-resolution.md](reference/sql-resolution.md) |
| R-13 | Trouver la version canonique d'un fichier pour ce workspace | (workflow ci-dessus) + [harmony-paths.md](reference/harmony-paths.md) |
| R-14 | Classification standard/specifique avec validation utilisateur obligatoire | [classification.md](reference/classification.md) |
| R-15 | Lire le profil du `.dhpt` pour comprendre l'architecture typee | [profile.md](reference/profile.md) |
| R-16 | Capturer/relire les conventions du poste integrateur en memoire de session | [poste-memory-template.md](reference/poste-memory-template.md) |

## References documentaires

- [reference/implicit-file.md](reference/implicit-file.md) -- identification, parsing, grammaire et semantique du fichier implicite (R-1, R-2, R-6)
- [reference/harmony-paths.md](reference/harmony-paths.md) -- resolution des chemins harmony (R-3, R-4, R-5)
- [reference/sql-resolution.md](reference/sql-resolution.md) -- modele deux portes (Harmony ODBC + ADO.NET) et joignabilite SQL (R-7 a R-12)
- [reference/classification.md](reference/classification.md) -- classification standard/specifique avec validation utilisateur (R-14)
- [reference/profile.md](reference/profile.md) -- lecture du profil du `.dhpt` et matrice typee de l'architecture (R-15)
- [reference/poste-memory-template.md](reference/poste-memory-template.md) -- capture/relecture des conventions du poste en memoire de session (R-16)

## Scripts utilitaires

| Script | Role | Entree | Sortie JSON |
|--------|------|--------|-------------|
| `scripts/parse_implicit.py` | Parse R-2 + R-6 : classifie ligne par ligne le fichier implicite | `--path <chemin_implicite>` `--confirmed-by-user` [+ `--encoding`] | `{implicit_file, total_lines, useful_lines, entries[], summary_by_type}` -- exit 0 OK, 1 si lignes 'unknown', 2 si erreur, **3 si --confirmed-by-user absent** |
| `scripts/find_canonical_file.py` | Applique R-13 : trouve le chemin canonique d'un fichier en parcourant le search path dans l'ordre | `--implicit <chemin>` `--file <nom>` `--confirmed-by-user` [+ `--recursive` / `--no-recursive`] | `{file, implicit_file, diva_root, search_path[], found, canonical_path, hit_in_line, hit_source}` -- exit 0 si trouve, 1 sinon, 2 si erreur, **3 si --confirmed-by-user absent** |
| `scripts/check_workspace_coherence.py` | Audit complet R-1 + R-2 + R-3/R-4/R-5 + R-7/R-8 + R-13 + R-15 : verifie existence physique des chemins harmony ET des URL SQL, parse les `.dhpt`, cross-check coherence implicite ↔ profil et inter-`.dhpt` | `--workspace <chemin>` `--implicit <chemin>` `--confirmed-by-user` | `{workspace, implicit_file, diva_root, implicit_lines[], dhpts[], summary{errors,warnings,infos}, findings[]}` -- exit 0 si OK, 1 si findings, 2 si erreur, **3 si --confirmed-by-user absent** |
| `scripts/_resolver.py` | Module helper interne (import) : R-3 parse `divaltopath.cfg`, R-4 lecture brute `fconfig.dhfd`, R-5 lookup registre Windows, R-7 parse `divaltoserver.cfg`, R-8 stub (non implemente). Aussi appelable en CLI avec `--harmony-path` ou `--discover` (debug) | (import) | (import) |

**Convention** : tous les scripts utilisent `py` comme lanceur, sortie JSON sur stdout, erreurs sur stderr. Exit code 0 = succes, 1 = no result / findings detected, 2 = erreur, **3 = `--confirmed-by-user` absent (R-1/P-B viole)**.

### Garde-fou `--confirmed-by-user` (R-1/P-B)

Les 3 scripts d'audit (`parse_implicit.py`, `find_canonical_file.py`, `check_workspace_coherence.py`) refusent de demarrer sans le flag `--confirmed-by-user`. Sans ce flag, ils emettent un warning explicite sur stderr et terminent en exit 3. Ce garde-fou materialise la regle R-1 ("demander confirmation au collaborateur meme si on pense l'avoir trouve") et le principe P-B ("Interdiction de presumer -- silence != approbation").

**Workflow pour Claude** :
1. Identifier les candidats du fichier implicite (R-1 procedure, heuristiques (a)-(d))
2. **Presenter** les candidats au collaborateur et **demander confirmation explicite**
3. **Apres** confirmation, invoquer le script avec `--confirmed-by-user` sur le fichier choisi
4. Sans confirmation, ne pas lancer les scripts -- exit 3 garantit que la doctrine est respectee mecaniquement

**Limitations actuelles** :
- L'acces registre (R-5) requiert Windows + module `winreg`. Sur autre OS / sandboxe : `discover_diva_root()` retourne une erreur exploitable par l'appelant (P-A).
- `fconfig.dhfd` est lu en **raw bytes** par `_resolver.py` (heuristique : marqueur `^Y` litteral `\x5E\x59`, suivi d'un champ alias 32 chars). A remplacer par une lecture ISAM propre via le skill `reading-isam-files` quand un `structure_fconfig.json` sera disponible -- la lecture brute actuelle est correcte sur les workspaces observes mais sensible aux changements de structure des records.

**Convention d'invocation** : ne pas appeler ces scripts directement depuis une session Claude (regle CLAUDE.md generale). Passer par l'outil `Skill` avec le nom `understanding-integrator-workspace` et laisser le skill orchestrer.

## Note sur le perimetre

Le skill couvre les operations de **lecture / interpretation / verification** d'un workspace existant.

La **generation** d'un nouveau workspace (creation d'un `.dhpt`, mise en place d'un implicite, declaration d'une nouvelle connexion SQL) releve de **Layer 1** : enoncer EXPLICITEMENT les valeurs des parametres cles (`cheminbases`, `versioncible`, `repobjet*`, `repbrowse*`, nom du profil, etc.) au moment de la creation, plutot que les copier silencieusement d'un workspace voisin. Ce concept est dans le perimetre conceptuel du skill mais sa procedure step-by-step n'est pas encore formalisee -- a capturer lors d'une prochaine iteration.

Champs hors-perimetre actuel :
- Cas multi-base (plusieurs `<implicite>` dans le `.xml` compagnon, plusieurs lignes URL SQL dans le `.txt`) -- rare
- Role exact de `<harmonyShareServer>` dans `connexions.xml`
- Generation/ecriture de `fconfig`, `divaltopath.cfg`, `divaltoserver.cfg`, `connexions.xml`, `fhsql.dhfi`
