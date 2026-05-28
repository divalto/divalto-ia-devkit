# Chemins harmony -- resolution

Ce document detaille **R-3**, **R-4** et **R-5** -- les regles qui resolvent un chemin "harmony" (commençant par `/`) en chemin filesystem absolu. Il presente aussi le workflow R-13 (trouver la version canonique d'un fichier) qui compose ces regles.

## Concept -- chemins harmony

Les chemins du fichier implicite (et plus generalement de tous les fichiers Divalto) qui commencent par `/` sont des **chemins harmony** -- l'equivalent d'un lien symbolique sous Linux : un alias court qui pointe vers un chemin absolu Windows. Forme : `/<alias>/<reste>` (ex: `/specifs/<workspace>/fichiers/`).

Le skill manipule exclusivement les **alias harmony** ; il ne pose aucune presomption sur la racine filesystem reelle (lettre de lecteur, nom de dossier d'integrateur, etc.) -- celle-ci varie d'un poste a l'autre.

## Precedence de resolution (hors `/divalto/`)

Pour tout chemin harmony qui ne commence pas par `/divalto/`, la resolution suit un ordre **strict** :

| Etape | Source consultee | Regle | Si trouve | Si absent |
|-------|------------------|-------|-----------|-----------|
| 1 | `<DIVA_ROOT>/sys/divaltopath.cfg` | R-3 | retourner la resolution | passer a l'etape 2 |
| 2 | `<DIVA_ROOT>/sys/fconfig.dhfi` (cle E) | R-4 | retourner la resolution | appliquer P-A : demander au collaborateur |

**`divaltopath.cfg` fait foi en priorite**. `fconfig` n'est consulte QUE si l'alias est absent du `.cfg`. Si les deux divergeaient sur un meme alias (cas non observe pour l'instant), `divaltopath.cfg` l'emporte -- mais signaler le conflit au collaborateur (P-B) au lieu de proceder silencieusement.

**Cas particulier `/divalto/...`** : exclu de cette chaine. Mecanisme distinct -- la racine d'installation Divalto se decouvre via R-5 (registre Windows).

---

## R-3 -- Resoudre un chemin harmony via `divaltopath.cfg`

- **Question** : Comment resoudre un chemin harmony `/<alias>/<reste>` ?
- **Entree** : Un chemin harmony de la forme `/<alias>/<reste>` (ex: `/specifs/<workspace>/fichiers/`).
- **Procedure** :
  1. **Localiser `divaltopath.cfg`** dans `<DIVA_ROOT>/sys/` (R-5 donne `<DIVA_ROOT>`).
  2. **Lire le fichier** -- une entree par ligne, grammaire :
     ```
     <NAME>nom_alias<PATH>chemin_absolu_windows<MULTIBASE>...<SHARENAME>...
     ```
     `<MULTIBASE>` et `<SHARENAME>` peuvent etre vides (champs utilises pour les configurations multi-base / partage reseau).
  3. **Extraire l'alias** du chemin harmony : premier segment apres le `/` initial (ex: `/specifs/<workspace>/fichiers/` -> alias = `specifs`).
  4. **Chercher l'entree** dans `divaltopath.cfg` dont `NAME` correspond a l'alias (insensible a la casse).
  5. **Substituer** : remplacer `/<alias>/` par la valeur de `<PATH>` (en preservant le separateur trailing si necessaire).
  6. Si **aucune entree** ne correspond a l'alias : NE PAS inventer (P-A), passer en R-4 (fallback `fconfig`).
- **Sortie** : Chemin absolu Windows.
- **Garde-fou** :
  - **P-A** : si l'alias n'est pas dans `divaltopath.cfg`, ne pas inventer une racine plausible -- passer en R-4.
  - **P-B** : meme si l'alias est trouve, presenter la resolution au collaborateur pour confirmation, surtout si le chemin resultant ne correspond pas a ce qui existe sur disque.
  - **Fallback `divaltopath.cfg` absent** : si le fichier lui-meme n'existe pas dans `<DIVA_ROOT>/sys/`, signaler au collaborateur et demander ou se trouve la table de resolution. Ne JAMAIS proceder a une resolution heuristique sans cette table.

### Aliases typiquement presents

| NAME | Type de PATH |
|------|--------------|
| `specifs` | racine `Specifs/` du partenaire (contient les workspaces) |
| `fichiers` | racine `fichiers/` du partenaire (contient `v<version>/` du standard) |
| `objets` | racine `objets/` du partenaire (contient les `.dhof`/`.dhoq` du standard) |
| `liasses`, `point de vente` | racines standard generiques |
| `vx12`, `vx13`, `vx2`, `vx9` | chemins standard generiques `Version X.<n>` -- a ne pas confondre avec les versions partenaire-locales `v<YEAR>_erpX<N>_<patch>` qui vivent sous l'alias `sources` |

L'alias `sources` est typiquement **absent** de `divaltopath.cfg` -- il est resolu par R-4 (fconfig).
L'alias `divalto` est aussi absent (et le sera toujours) -- mecanisme distinct via R-5.

---

## R-4 -- Resoudre un alias absent de `divaltopath.cfg` via `fconfig` cle E (fallback)

> **Pre-requis strict** : R-4 ne s'execute QUE si R-3 a echoue (alias absent de `divaltopath.cfg`). NE JAMAIS consulter `fconfig` AVANT d'avoir epuise `divaltopath.cfg`.

- **Question** : Quand R-3 ne trouve pas l'alias dans `divaltopath.cfg`, comment combler le trou ?
- **Entree** : L'alias non resolu (ex: `sources`) + le chemin de `fconfig.dhfi` (via R-5 `CheminFpartd` du registre, ou compose `<DIVA_ROOT>/sys/fconfig.dhfi`).
- **Procedure** :
  1. **Localiser `fconfig.dhfi`** dans `<DIVA_ROOT>/sys/` (paire ISAM : `fconfig.dhfi` = donnees + index, `fconfig.dhfd` = dictionnaire). Le `.dhfd` peut contenir les enregistrements visibles en clair, mais l'outil propre est le skill ISAM.
  2. **Lire en parcours sequentiel sur la cle E** via le skill `reading-isam-files`. Limitation actuelle : pas de `structure_fconfig.json` dans `<PLUGIN>/skills/reading-isam-files/scripts/structures/` -- a defaut, lecture brute du `.dhfd` (les enregistrements alias-de-chemin sont prefixes par le byte `0x19` / `^Y`).
  3. **Filtrer les enregistrements de type "alias de chemin"** : suivent le format `<alias_padde> <chemin_absolu>`. Les autres types (imprimantes `P001`-`P016`, bases SQL, serveurs xlan) doivent etre ignores pour cette regle.
  4. **Chercher** l'entree dont `NAME` correspond a l'alias.
  5. **Substituer** comme en R-3.
  6. Si **aucune entree** ne correspond : NE PAS inventer (P-A). Signaler au collaborateur que l'alias n'est ni dans `divaltopath.cfg` ni dans `fconfig`, et demander la regle de resolution effective.
- **Sortie** : Chemin absolu Windows (comme R-3).
- **Garde-fou** :
  - **P-A** : pas d'invention si absent des deux sources.
  - **P-B** : confirmer la resolution avec le collaborateur si elle differe de ce que `divaltopath.cfg` aurait donne.
  - **Outil ISAM** : passer par le skill `reading-isam-files`, ne pas appeler directement `read_isam.py` (regle generale CLAUDE.md).

### Note de coherence cfg ↔ fconfig

Les enregistrements alias-de-chemin de `fconfig` portent en general les memes alias que `divaltopath.cfg`. Le `.cfg` est probablement un cache texte du sous-ensemble pertinent de la table fconfig. En cas de divergence -> P-B (signaler, pas trancher silencieusement).

---

## R-5 -- Decouvrir `<DIVA_ROOT>` et le chemin de `fconfig` via le registre Windows

- **Question** : Comment trouver de facon deterministe (a) la racine d'installation Divalto `<DIVA_ROOT>` -- sur n'importe quel lecteur -- et (b) le chemin exact de `fconfig.dhfd` pour s'epargner toute heuristique de localisation ?
- **Entree** : Acces a la base de registre Windows.
- **Procedure** :
  1. **Interroger la base de registre** sur l'une des deux cles (essayer dans cet ordre) :
     - `HKLM\SOFTWARE\WOW6432Node\Divalto\divalto.ini\System` (cas observe : Divalto 32-bit sur Windows 64-bit, redirection WOW6432Node)
     - `HKLM\SOFTWARE\Divalto\divalto.ini\System` (cas Divalto 64-bit natif, ou Windows 32-bit)
     
     Commande (depuis bash Windows) : `reg query "HKLM\SOFTWARE\WOW6432Node\Divalto\divalto.ini\System"`.
  2. **Lire deux valeurs cles** -- et **seulement ces deux** (cf. P-C ci-dessous) :
     - `CheminUl1` (REG_SZ) : racine d'installation Divalto = `<DIVA_ROOT>`. **ATTENTION** : c'est `Ul1` avec un `l` minuscule, pas `UI1` avec un `I` majuscule -- confusion visuelle frequente selon la fonte (l et I se confondent en sans-serif).
     - `CheminFpartd` (REG_SZ) : chemin absolu vers le `.dhfd` de `fconfig` (ex: `c:\Divalto\sys\fconfig.dhfd`). Le `.dhfi` correspondant se deduit par meme base + extension `.dhfi`.
  3. **Verifier l'existence des chemins** retournes (garde-fou "verification d'acces obligatoire" de R-2).
- **Sortie** :
  - `<DIVA_ROOT>` resolu (ex: `c:\Divalto`).
  - Chemin absolu de `fconfig.dhfd` ET `fconfig.dhfi` confirmes.
- **Garde-fou** :
  - **P-A** : si la cle de registre est introuvable sous les deux paths, NE PAS inventer. Demander au collaborateur (Divalto peut-etre installe via une procedure non-standard, ou portable / sans installation registry).
  - **P-B** : meme apres lecture, presenter au collaborateur les deux valeurs pour confirmation avant utilisation.
  - **P-C (liste blanche registre)** : seules les deux valeurs `CheminUl1` et `CheminFpartd` des cles ci-dessus sont autorisees a la lecture. **Interdit** : enumerer les sous-cles ou les autres valeurs de `HKLM\SOFTWARE\[WOW6432Node\]Divalto\divalto.ini\System`, faire un `reg query /s`, ou explorer une cle voisine "au cas ou". Si la cle est absente -> P-A (demander), pas exploration. Cf. SKILL.md section *Principes transverses -- P-C*.
  - **Acces au registre** : si l'environnement ne donne pas acces a `reg query` (sandboxing, droits, OS non-Windows), tomber en P-A.

### Exemple de retour registre

```
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Divalto\divalto.ini\System
    CheminFpartd    REG_SZ    <chemin_vers_fconfig.dhfd>
    CheminUl1       REG_SZ    <racine_divalto>
```

### Effet de bord utile

R-5 court-circuite la dependance de R-4 a `<DIVA_ROOT>` -- le chemin de `fconfig.dhfd` peut etre lu directement du registre (`CheminFpartd`), sans avoir a composer `<DIVA_ROOT> + /sys/fconfig.dhfd`. Si jamais les deux divergent (cas exotique), le registre fait foi puisque c'est ce que xwin7 utilise au runtime.

---

## R-13 -- Trouver la version canonique d'un fichier pour ce workspace

> **Regle d'application** -- c'est la motivation premiere du skill. Toutes les autres regles sont des **briques** ; R-13 est le **cas d'usage** qui les compose pour repondre a la question concrete : "quand je dois lire / copier / referencer un fichier, lequel est LE bon pour ce workspace ?".

- **Question** : Pour un fichier donne (par exemple `gtez077_sql.dhsf` quand on cree un compagnon `_sql_base.dhsf`, ou `gtfdd.dhsd` quand on cross-checke une surcharge dictionnaire), **quelle est la version exacte que ce workspace utilise reellement** -- celle qui sera vue par xwin7 a la compilation et au runtime ?
- **Entree** : Workspace + nom du fichier (sans chemin).
- **Procedure** :
  1. **Identifier le fichier implicite** via R-1 (avec confirmation collaborateur par P-B). Voir [implicit-file.md](implicit-file.md).
  2. **Parser le fichier implicite** ligne par ligne (R-2) -> liste **ordonnee** de chemins / URL SQL.
  3. **Resoudre chaque ligne filesystem** en chemin absolu :
     - Chemins harmony (`/<alias>/<reste>`) -> R-3 puis R-4 si absent du `.cfg`.
     - Cas `/divalto/...` -> resolu via R-5 (registre).
     - Chemins Windows absolus -> tels quels.
     - Lignes URL SQL -> **ignorees** dans cette procedure (filesystem search seulement).
  4. **Parcourir la liste de chemins resolus DANS L'ORDRE** (cf. semantique d'ordre de R-6, dans [implicit-file.md](implicit-file.md)) :
     - Pour chaque chemin, chercher le fichier par nom (recursivement sous le chemin, ou directement selon le contexte attendu).
     - **Le PREMIER hit gagne** -- c'est la version canonique pour ce workspace.
     - Arret au premier hit ; les chemins suivants ne sont pas regardes.
  5. Si aucun chemin ne contient le fichier -> **P-A** : signaler au collaborateur que le fichier est introuvable dans le search path du workspace. NE PAS aller chercher dans un dossier "Standard generique" hors search path.
- **Sortie** : Chemin absolu de la version canonique du fichier pour ce workspace.
- **Garde-fou** :
  - **P-A renforce** : ne JAMAIS faire un `find` aveugle sur un tree "standard generique" hors search path. Le search path du workspace est la **seule** source de verite.
  - **P-B** : pour toute operation critique (copie de fichier comme base d'une surcharge, lecture de reference pour cross-check), presenter au collaborateur le chemin canonique trouve avant utilisation. Lui mentionner explicitement la version du standard derivee du nom du dossier resolu (ex: `v2026_erpX13_p223a` -> X.13 patch 223a).
  - **Ordre = surcharges gagnent** : la procedure traite naturellement les surcharges : si le fichier existe a la fois dans la zone surcharge du workspace et dans le standard versionne, le premier hit est la surcharge -- comportement voulu et identique a celui de xwin7 a l'execution.

### Cas d'usage typiques de R-13

| Tache | Application |
|-------|-------------|
| **Creer le compagnon `<base>_base.dhsf`** d'une surcharge masque (et autres `_base`) | Source = R-13 sur le nom du standard (`<base>_sql.dhsf`). |
| **Cross-checker une surcharge dictionnaire** (`validate_dhsd.py --dhsd-standard <std>`) | `<std>` = R-13 sur le nom du `.dhsd` standard (ex: `gtfdd.dhsd`). |
| **Lire le contenu d'un masque/source standard pour reference** (debug, comprehension de pattern) | R-13 sur le nom du fichier. |
| **Identifier la version d'ERP que le workspace cible** | R-13 produit un chemin dont le segment versionne (ex: `v<YEAR>_erpX<N>_<patch>`) donne la version sans ambiguite. |

R-13 remplace donc **tout** appel a `find` aveugle dans un dossier "Standard generique" lorsque le contexte est un workspace integrateur.

### Note de perimetre -- canal de resolution par type d'artefact

R-13 decrit la resolution via le **search path de l'implicite**. Ce canal s'applique strictement aux **sources** Divalto (`.dhsf`, `.dhsp`, `.dhsd`, `.dhsq`).

Pour les autres types d'artefacts, le canal de resolution est different et passe par le **profil du `.dhpt`** (cf. R-15, [profile.md](profile.md)) :

| Type d'artefact | Canal de resolution |
|-----------------|---------------------|
| Sources (`.dhsf`, `.dhsp`, `.dhsd`, `.dhsq`) | Search path de l'implicite (R-13) |
| Objets compiles (`.dhof`, `.dhoq`) | Champs `repobjet` / `repobjetsurcharge` du profil (R-15) |
| Fichiers de navigation / browse | Champs `repbrowse` / `repbrowsesurcharge` du profil (R-15) |

Quand je cherche un fichier, identifier d'abord son **type** pour choisir le **canal** correct.
