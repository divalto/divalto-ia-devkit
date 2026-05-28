# Fichier implicite -- identification, parsing, grammaire

Ce document detaille **R-1**, **R-2** et **R-6** -- les regles qui concernent le fichier implicite, **ancre racine** de tout le skill. C'est de lui que se derivent toutes les autres operations (resolution de chemins, classification, etc.).

## R-1 -- Identifier le fichier implicite du workspace

- **Question** : Quels sont les chemins lies au workspace courant (standard, specifique, runtime, ...) ? Le fichier implicite est le **point d'entree unique** -- il declare le search path complet du workspace.
- **Entree** : Le chemin du workspace racine (ex: la resolution sur le poste de l'alias harmony `/specifs/<nom_workspace>/`).
- **Procedure** :
  1. **Essayer de trouver le fichier implicite par soi-meme** via plusieurs heuristiques complementaires (collecte large, pas de filtre nominal restrictif) :
     - **(a) Via les `.dhpt` du workspace** : chercher RECURSIVEMENT tous les `*.dhpt` dans le workspace (ne PAS presumer qu'ils sont dans `projets/` -- le dossier peut s'appeler `projet`, `project`, autre, ou etre a la racine). Pour chaque `.dhpt` trouve, iterer TOUTES les sections `[profil]` (un meme `.dhpt` peut en contenir plusieurs) et collecter tous les `implicites=...` distincts referenced.
     - **(b) Via les `.txt` du workspace** : lister TOUS les `*.txt` au moins a la racine du workspace, sans filtre sur le prefixe du nom (ne PAS presumer `implicites*`, le fichier peut s'appeler n'importe comment). Eventuellement etendre a `find -maxdepth 2` si la racine est vide.
     - **(c) Via le runtime Divalto** `<DIVA_ROOT>/sys/` : le fichier implicite peut tres bien etre stocke ici (runtime commun a tous les workspaces, pas dans le workspace lui-meme). Lister les candidats `*.txt`. Conventions de nommage observees : `Implicites*.txt` (ex: `ImplicitesDefaut.txt`, `Implicites$web.txt`), prefixes thematiques (`developpement_x12.txt`), noms abreges arbitraires (`impltmp.txt`). Ne pas filtrer par prefixe.
     - **(d) Recoupement** : verifier si les candidats (a) referencent un fichier qui existe en (b) ou (c). Le fichier de `implicites=` du `.dhpt` est resolu par xwin7 selon son path de recherche -- typiquement le workspace D'ABORD puis `<DIVA_ROOT>/sys/`. Un nom du `.dhpt` qui n'existe pas dans le workspace mais existe dans `divalto/sys/` est un fort indicateur. Mais ne pas en faire une certitude.
  2. **Demander confirmation au collaborateur**, **MEME si on pense l'avoir trouve**. La confirmation est obligatoire et binaire ("oui c'est ce fichier" / "non, c'est tel autre"). Lui presenter TOUS les candidats trouves avec leur statut (refere/non refere, present-dans-workspace/present-dans-runtime/absent).
- **Sortie** : Le chemin absolu du fichier implicite confirme par l'utilisateur (typiquement dans `<DIVA_ROOT>/sys/<nom>.txt` ou a la racine du workspace, selon la convention du partenaire).
- **Garde-fou** :
  - **P-A** : si aucun candidat n'est trouve via les heuristiques, ne pas inventer. Demander le chemin absolu.
  - **P-B** : meme si un seul candidat trouve, demander confirmation.

### Lecons et pieges connus

1. Le nom dans `implicites=` du `.dhpt` est un **alias** que xwin7 resout selon un path de recherche -- typiquement le workspace puis le runtime `<DIVA_ROOT>/sys/`.
2. La presence d'un `<nom>.txt` a la racine du workspace n'implique PAS qu'il soit l'implicite actif (il peut etre un vestige).
3. Le fichier implicite peut etre **partage entre plusieurs workspaces** via le runtime -- donc un meme `<implicite>.txt` dans `divalto/sys/` peut servir plusieurs workspaces simultanement.
4. Le **contenu** d'un fichier implicite est typiquement une liste de chemins relatifs/absolus declarant : workspace specifiques (sources, fichiers, projets, objets, navigation), runtime (`/divalto/sys/`), standard ERP (`/sources/v<X>/`, `/objets/v<X>/`, `/fichiers/v<X>/`), serveur SQL (`//<host>/<dbname>`).
5. Seule la confirmation utilisateur tranche.

---

## R-2 -- Analyser le fichier implicite ligne par ligne

- **Question** : Une fois le fichier implicite identifie et confirme (sortie de R-1), quels chemins concrets doit-je etre capable d'atteindre pour travailler sur le workspace ?
- **Entree** : Le chemin absolu du fichier implicite confirme par R-1.
- **Procedure** :
  1. **Lire le contenu** du fichier implicite, ligne par ligne, en preservant l'encodage.
  2. **Ignorer** les lignes vides et les lignes de commentaire (`;` en debut de ligne -- cf. R-6 grammaire).
  3. Pour **chaque ligne non vide** :
     - Identifier le **type de ligne** (chemin harmony, chemin Windows absolu, URL SQL -- cf. R-6 types acceptes).
     - **Resoudre** la ligne en chemin absolu (ou en URL/ressource accessible) selon la regle de resolution propre a ce type. Voir [harmony-paths.md](harmony-paths.md) pour les chemins harmony, [sql-resolution.md](sql-resolution.md) pour les URL SQL.
     - **Verifier l'accessibilite** : pour un chemin filesystem, verifier l'existence et la lisibilite ; pour une URL SQL, ne pas attaquer la base directement -- cf. R-12 dans [sql-resolution.md](sql-resolution.md).
  4. Produire une **table de mapping** : ligne brute -> type -> chemin resolu -> statut d'acces (OK / introuvable / inaccessible / ambigu).
- **Sortie** : Une table ligne-par-ligne avec, pour chaque entree du fichier implicite, son type, sa resolution absolue et son statut d'acces. Cette table est la **carte des chemins du workspace** -- elle alimente toutes les regles suivantes du skill.
- **Garde-fou** :
  - **P-A (interdiction d'inventer)** : si une ligne ne peut pas etre resolue avec certitude, NE PAS inventer la racine. Demander au collaborateur la regle de resolution effective utilisee par xwin7 sur sa machine.
  - **P-B (interdiction de presumer)** : meme apres analyse complete, presenter la table de mapping au collaborateur et lui demander de confirmer chaque entree ambigue avant d'utiliser ces chemins pour la suite.
  - **Verification d'acces obligatoire** : une entree marquee "OK" doit avoir ete reellement verifiee (existence + lisibilite). Pas de "OK" presume.

---

## R-6 -- Grammaire et semantique du fichier implicite

- **Question** : Quelle est la grammaire exacte d'une ligne du fichier implicite, et quelle semantique l'ordre des lignes porte-t-il pour xwin7 ?

### Grammaire d'une ligne

| Aspect | Regle | Notes |
|--------|-------|-------|
| Caractere de commentaire | `;` | Tout ce qui suit `;` jusqu'a la fin de ligne est ignore par xwin7. |
| Ligne vide | autorisee, sans effet | Aucun impact sur le parsing. |
| Espaces de debut/fin | non significatifs | Strippes par xwin7. |
| Slash final sur les chemins (ex: `/specifs/...`) | optionnel mais **recommande** | Facilite la concatenation programmatique d'un chemin parent + segment enfant ; convention adoptee dans tous les fichiers Divalto observes. |
| Encodage | UTF-8 ou ISO-8859-1 (les deux supportes) | Pour generer le fichier, prendre l'un ou l'autre selon le contexte du projet. |
| Fins de ligne | CRLF | Windows. |
| Casse | **insensible** | `/specifs/`, `/Specifs/`, `/SPECIFS/`, `/SpEcIfS/` resolvent au meme alias. |

### Types de lignes acceptes

Trois (et seulement trois) types de contenu sont valides sur une ligne non-vide non-commentaire :

| Type | Forme | Exemple | Resolution |
|------|-------|---------|------------|
| **Chemin harmony** | `/<alias>/<segments>...` | `/specifs/<workspace>/fichiers/` | Via R-3 → R-4 -- voir [harmony-paths.md](harmony-paths.md) |
| **Chemin Windows absolu** | `<lettre>:\<segments>...` | `C:\divalto\sys` | Directement utilise tel quel (pas de resolution intermediaire) |
| **URL serveur SQL** | `//<host>/<base>` (forme stricte) | `//localhost/DIVALTO_<CLIENT>_VX13` | Voir [sql-resolution.md](sql-resolution.md). Pas de port, pas de credentials, pas de protocole. |

Aucun autre type n'est accepte : pas de variables (`KEY=VALUE`), pas de sections (`[xxx]`), pas de directives d'inclusion (`@include`), pas de substitution. Le fichier est volontairement minimaliste.

### Semantique de l'ensemble du fichier : **ordre = priorite de recherche**

C'est la dimension critique du fichier implicite. **L'ordre des lignes est significatif** : xwin7 utilise le fichier comme un **search path ordonne** pour resoudre un fichier par nom.

**Mecanique** : quand un module Divalto cherche un fichier (par exemple `gtfdd.dhsd` au moment d'une compilation), xwin7 parcourt les chemins du fichier implicite **dans l'ordre** ; le **premier hit gagne** -- les suivants sont ignores.

**Consequence pratique** -- c'est la base meme du mecanisme de surcharge :
- Si les chemins specifiques du workspace (ex: `/specifs/<X>/fichiers/`) sont listes **avant** les chemins du standard ERP (ex: `/fichiers/v<version>/`), tout fichier qui existe dans les deux endroits sera resolu sur la version workspace -> **la surcharge gagne**.
- Inversement, lister le standard avant le workspace neutraliserait toute surcharge.

Donc dans un fichier implicite **toute analyse doit preserver l'ordre**, et toute generation de fichier doit le respecter strictement (mettre en tete les chemins specifiques qui doivent gagner, en queue les chemins de fallback / standard).

### Convention de position de la ligne URL SQL

| Aspect | Regle |
|--------|-------|
| Position | **Convention** (pas semantiquement enforce par xwin7) : declarer la base **apres les chemins specifiques au workspace** et **avant les chemins du standard ERP**. Pas une regle dure mais une convention utile a respecter pour la lisibilite. |
| Impact fonctionnel | A la difference des chemins, **la position de la ligne SQL n'a pas d'impact fonctionnel** -- la resolution SQL n'utilise pas le mecanisme de search-path filesystem. |

### Comportement xwin7 face aux lignes invalides

| Cas | Action xwin7 | Recommandation |
|-----|--------------|----------------|
| Ligne mal formee, chemin inexistant, alias inconnu | **Warning** + ligne ignoree silencieusement (xwin7 continue) | En pratique : viser un fichier 100% propre, sans warnings. Les warnings sont des dettes techniques cachees. |

### Garde-fou

- **P-A** : si une ligne ne correspond a aucun des trois types listes (chemin harmony, chemin Windows absolu, URL SQL), ne pas l'interpreter "au mieux" -- signaler au collaborateur que la ligne est non reconnue et lui demander.
- **P-B** : si l'ordre des chemins parait incorrect (par exemple le standard avant le workspace -> surcharges desactivees), avertir explicitement le collaborateur, ne pas reparer silencieusement.
- **Ordre dans toute generation** : ne JAMAIS reordonner les lignes d'un fichier implicite existant sans accord explicite du collaborateur -- l'ordre porte la semantique de surcharge.

### Reference documentaire officielle

- [Confluence Divalto -- Gestion des serveurs, chemins et implicites](https://divalto.atlassian.net/wiki/spaces/PAI/pages/10757537823/Gestion+des+serveurs+chemins+et+implicites) -- cette page va plus loin que les regles capturees ici (cas avances, formats etendus, configurations multi-base / multi-serveur). Pour les cas avances, renvoyer le collaborateur a cette doc plutot que de tenter de tout reproduire.
