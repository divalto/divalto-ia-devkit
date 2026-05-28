# Profil du `.dhpt` -- architecture typee du workspace

Ce document detaille **R-15** -- la lecture du profil du `.dhpt` pour comprendre l'architecture typee du workspace (objets standard, objets surcharge, browse standard, browse surcharge).

## R-15 -- Lire le profil du `.dhpt` pour comprendre l'architecture typee du workspace

> **Couche semantique au-dessus de l'implicite**. Si l'implicite (R-1 a R-6) donne un **search path ordonne non type**, le `[profil]` du `.dhpt` y ajoute le **typage des chemins par role** : pour chaque type d'artefact (objets compiles, browse / navigation), il distingue explicitement l'emplacement standard (R-only par xwin7) de l'emplacement surcharge (R+W).

- **Question** : Pour chaque type d'artefact (sources / objets compiles / fichiers de navigation), ou xwin7 lit le standard et ou il lit/ecrit les surcharges sur ce workspace ?

- **Entree** : Le `.dhpt` parent du workspace + identification du `[profil]` actif.

### Procedure

1. **Localiser le(s) `.dhpt`** : chercher recursivement les `*.dhpt` dans le workspace (le dossier `projets` n'est pas une norme universelle -- cf. R-1 heuristique a). Un workspace mature en contient typiquement plusieurs, **un par domaine ERP**.

2. **Identifier le `[profil]` actif** : un `.dhpt` peut contenir plusieurs sections `[profil]`. Le profil utilise au runtime/compilation est selectionne par xwin7 via `-profile <nom>`. Si plusieurs profils existent et qu'on ne connait pas le profil actif, **demander au collaborateur** (P-A).

3. **Extraire les 4 champs types** :

   | Champ | Role pour xwin7 | Classification | Acces |
   |-------|-----------------|----------------|-------|
   | `repobjet` | Lecture des **objets compiles** (`.dhof`/`.dhoq`) du standard ERP, pour la phase de link au build | **STANDARD** | R seul |
   | `repbrowse` | Lecture des fichiers de navigation / aide au developpement du standard | **STANDARD** | R seul |
   | `repobjetsurcharge` | Ecriture (et lecture ulterieure) des objets compiles produits par la compilation des surcharges | **SPECIFIQUE** | R + W |
   | `repbrowsesurcharge` | Idem `repbrowse` mais pour les developpements specifiques | **SPECIFIQUE** | R + W |

   > **Ne pas confondre `repobjet` avec `cheminbases`** -- les deux sont des chemins vers le standard mais ils ne pointent **pas** sur le meme type d'artefact :
   >
   > | Champ | Section du `.dhpt` | Pointe sur | Phase d'utilisation |
   > |-------|--------------------|------------|----------------------|
   > | `cheminbases` | `[general]` | **Sources** standard (`/sources/v<X>/`) -- les .dhsp, .dhsq, .dhsd, .dhsf | Resolution des surcharges (xwin7 retrouve les fichiers `<base>_sql.dhsf` etc.) |
   > | `repobjet` | `[profil]` | **Objets compiles** standard (`/objets/v<X>/`) -- les .dhof, .dhoq | Phase de link au build |
   >
   > Confondre les deux (declarer `cheminbases` vers `/objets/...` au lieu de `/sources/...`) fait ouvrir le `.dhpt` en erreur dans xwin7. Voir [`managing-diva-projects/reference/dhpt-structure.md`](../../managing-diva-projects/reference/dhpt-structure.md) section "[general] -- Sous-section `cheminbases`" pour le detail de la convention (relatif au `.dhpt` avec `flagrelatif=1`, casse lowercase des noms de version, exemple complet).

4. **Resoudre chaque chemin** : tous ces champs contiennent des chemins harmony (`/<alias>/<reste>`) ou Windows absolus -> resolution via R-3/R-4/R-5 (voir [harmony-paths.md](harmony-paths.md)).

5. **Construire la matrice typee** :

   |                | STANDARD | SPECIFIQUE |
   |----------------|----------|-----------|
   | Objets compiles | `repobjet` (R) | `repobjetsurcharge` (R+W) |
   | Browse / Navigation | `repbrowse` (R) | `repbrowsesurcharge` (R+W) |

### Sortie

Carte typee des 4 paths du profil avec leur classification et role.

### Controle de coherence implicite ↔ profil

Chaque path du profil doit exister dans le search path de l'implicite (ou etre un sous-segment derive d'une ligne, comme `<repobjet>/browse` peut etre un sous-dossier de la ligne `/objets/v<version>/`). Sur un workspace coherent :
- `repobjet` matche une ligne STANDARD de l'implicite (ex: `/objets/v<version>/`)
- `repobjetsurcharge` matche une ligne SPECIFIQUE de l'implicite (ex: `/specifs/<workspace>/objets/`)
- `repbrowse` est typiquement un sous-segment de la ligne standard objets
- `repbrowsesurcharge` matche une ligne SPECIFIQUE de l'implicite (ex: `/specifs/<workspace>/navigation/`)

Si un path du profil n'a pas de correspondance dans l'implicite -> configuration incoherente, signaler au collaborateur (P-B), ne pas "reparer" silencieusement.

### Cas d'usage debloques

- **Comprendre l'architecture du workspace** : ou va chaque type de production de xwin7 (predit avant compilation, pas observe apres-coup).
- **Creer ou modifier un profil** : savoir quels chemins fournir et avec quel role.
- **Controle de coherence d'environnement** : profil ↔ implicite doivent matcher.
- **Localisation d'artefacts compiles** : ou sont les `.dhof` du standard (`repobjet`) ? Ou atterrissent les `.dhof` de mes surcharges apres build (`repobjetsurcharge`) ?
- **Renforcement de R-14** : le profil donne une classification **formelle typee** pour les 4 paths concernes (voir [classification.md](classification.md)).

### Garde-fou

- **Multi-profils dans UN `.dhpt`** : si plusieurs `[profil]` existent dans le meme `.dhpt`, ne pas presumer lequel est actif (P-A). Demander au collaborateur (la selection xwin7 se fait via `-profile <nom>` au lancement).

- **Coherence implicite ↔ profil** : a verifier systematiquement quand R-15 est invoque. Une divergence est un signal d'erreur, jamais a "auto-reparer".

- **Multi-`.dhpt` dans le workspace -- cas typique, pas edge case** : un workspace d'integration contient **typiquement plusieurs `.dhpt`, un par domaine ERP** (`divalto achat-venteu.dhpt`, `divalto comptabiliteu.dhpt`, `divalto paieu.dhpt`, etc.). Selection :
  - **Pour une tache scopee a un domaine** (creer/modifier des surcharges du domaine X) -> utiliser le `.dhpt` du domaine concerne (nom standard : `divalto <domaine>u.dhpt`).
  - **Pour une classification globale R-14** (vue d'ensemble du workspace) -> agreger les profils de tous les `.dhpt` de surcharge presents. Les paths STANDARD (`repobjet`, `repbrowse`) sont en general **identiques** entre les `.dhpt` d'un meme workspace (meme version ERP cible). Les paths SPECIFIQUE (`repobjetsurcharge`, `repbrowsesurcharge`) peuvent etre partages au niveau workspace OU specifiques par domaine selon la convention du partenaire -- comparer entre les `.dhpt` pour s'en assurer.
  - **Si plusieurs `.dhpt` divergent sur un path STANDARD** : signal de configuration incoherente (cas anormal) -> demander au collaborateur (P-B).

### Verification de coherence inter-`.dhpt`

Pour un audit complet, comparer les valeurs des 4 champs entre tous les `.dhpt` de surcharge du workspace :

| Champ | Comportement attendu | Anomalie possible |
|-------|----------------------|-------------------|
| `repobjet` | Identique entre tous les `.dhpt` (meme version ERP) | Divergence -> deux `.dhpt` qui pointent sur deux versions de standard differentes (suspect) |
| `repbrowse` | Identique entre tous les `.dhpt` | Idem |
| `repobjetsurcharge` | Identique OU specifique par domaine (selon convention partenaire) | Divergence -> verifier si c'est intentionnel |
| `repbrowsesurcharge` | Identique OU specifique par domaine | Idem |
| `cheminbases` | Identique entre tous les `.dhpt` | Divergence = bug critique |
| `versioncible` | Identique entre tous les profils de meme niveau (debug/release) | Divergence = probable typo (cas observe en terrain) |

Une typo sur `versioncible` (par ex. `X.41` partout sauf un profil ou c'est `X.37`) est une anomalie classique a detecter -- elle ne casse pas necessairement la compilation immediatement mais cree des artefacts incompatibles a terme.
