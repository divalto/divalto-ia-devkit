# Regles CI -- Shift-left des moulinettes CI nightly

## Contenu

- CI01 -- SetModuleInfo absent (moulinette 001)
- CI02 -- Procedure/Function non PUBLIC dans TT/TE (moulinette 004)
- CI03 -- .WHERE sans AddCondition (moulinette 009)
- CI04 -- Include de PC*.dhsp dans TT/TM (moulinette 020)
- CI05 -- #top sans #fetch (moulinette 040)
- CI06 -- GROUP BY avec INSERT/UPDATE/DELETE=YES (moulinette 052)
- CI07 -- Variable SQL casse incoherente (moulinette 056)
- CI08 -- CE/CEBIN compare a un entier (moulinette 801)
- CI09 -- SELECT TOP 1 au lieu de #TOP1 (moulinette 801)
- CI10 -- ScrollBar au lieu de ScrollBar32 (moulinette 802)
- CI11 -- Code mort apres RETURN (moulinette 802)
- Recapitulatif

---


Regles transposees des moulinettes de controle qualite executees en CI nightly (pipeline GenererIntegration.ps1). Ces controles etaient historiquement decouverts au lendemain via mail Weasel ; ils sont desormais disponibles au moment du developpement.

> Ces regles reprennent les controles qualite que Divalto execute en CI nightly sur le standard.

---

## CI01 -- SetModuleInfo absent (moulinette 001)

- **Severite** : `info` -- **HORS du jeu de regles par defaut**
- **Activation** : explicite, `--rules CI01` (eventuellement avec d'autres codes)
- **Cibles quand activee** : `.dhsp`, `.dhsq`, `.dhsf`, `.dhsi`, `.dhse`

### Ce que `SetModuleInfo` EST -- un mecanisme du langage, pas une convention d'outil

`SetModuleInfo` et `ModuleInfo` sont une **paire de fonctions natives DIVA**, section
« Modules et programmes » du manuel de reference :

| Fonction | Ce qu'elle fait |
|---|---|
| `SetModuleInfo(info)` | positionne une information dans le module -- « des informations **qui peuvent etre lues par `ModuleInfo`** » |
| `ModuleInfo(module)` | **retourne** ces informations pour un module charge (retour alphanumerique) |

Meme famille : `ModuleVersion`, `GetModulesNames`, `GetDivaModules`.

**Consequence : l'information est lue A L'EXECUTION.** Divalto s'en sert pour **afficher
les versions des modules**. Ce n'est donc pas une trace inerte dans le source : son absence
prive le produit de cette information.

> **Correction du 2026-09-09.** Cette page affirmait que la directive « sert **uniquement**
> a tracer les releases SVN » et que son absence « n'a **aucun effet a l'execution** ».
> Les deux etaient faux -- verifie au graphe. Le mot-cle SVN `$Id$` est **un** contenu
> possible de l'information, pas sa raison d'etre.

### Pourquoi la regle reste hors du jeu par defaut

`SetModuleInfo` n'est pas **obligatoire** : son absence ne provoque aucune erreur de
compilation, et le standard Divalto la pose systematiquement la ou du specifique peut
legitimement s'en passer. Sur un specifique partenaire mesure, la regle activee par defaut
reprochait **~860 fois** un choix assume (612/700 `.dhsp`, 66/91 `.dhsq`, 185 masques).

C'est donc un **audit de convention** : le partenaire qui veut que ses modules exposent
leur version l'active et obtient un audit utile ; les autres ne voient rien.

### Fenetre de recherche selon le type de fichier

- **Modules de code** (`.dhsp`, `.dhsq`) : les **100 premieres lignes**. Mesure standard
  X.13 : **0** fichier porte la directive au-dela de la ligne 100 -- la fenetre est sure.
- **Types declaratifs** (`.dhsf`, `.dhsi`, `.dhse`) : le **fichier entier**. La description
  du masque (`[masque]`, `[enregistrements]`, `[bloc]`) precede le bloc `[diva]`, donc
  `SetModuleInfo` s'y trouve tres au-dela de la ligne 100 (constate aux lignes 334, 379,
  1586). Mesure standard X.13 : **2431/2438 `.dhsf` et 798/811 `.dhsi`** la portent APRES
  la ligne 100. La fenetre positionnelle produisait donc ~100 % de faux positifs sur les
  masques -- **c'etait la vraie cause de #243**, pas le type de fichier. Les masques du
  standard portent la directive a **100 %** (2438/2438 et 811/811) : les exclure aurait
  supprime une detection legitime.

- **Logique** : presence de `SetModuleInfo` (ou `ModuleInfo` pour `.dhsq`) dans la fenetre
  ci-dessus, sur une ligne d'au moins 30 caracteres (120 pour `.dhsq`) -- le minimum
  garantit que l'information a bien ete **renseignee** et pas laissee a l'etat de gabarit
  non substitue (typiquement un `$Id$` nu, quand le contenu vient d'un mot-cle de
  gestionnaire de sources).
- **Pourquoi** : l'information est lue a l'execution par `ModuleInfo`, et Divalto s'en sert
  pour **afficher les versions des modules**. Un module qui ne la pose pas n'expose pas
  sa version.

## CI02 -- Procedure/Function non PUBLIC dans TT/TE (moulinette 004)

- **Severite** : error
- **Cibles** : .dhsp (fichiers TT*.dhsp et TE*.dhsp uniquement)
- **Logique** : Toute `Procedure` ou `Function` doit etre declaree `Public` ou `Proto`. Exclut les fichiers DIVALTO*, IA_*, et les prefixes intermediaires PP/PC/PM/QC/TC/TM/P9/PZ.
- **Pourquoi** : Les programmes TT (test) et TE (ecran) doivent exposer leurs procedures pour le framework de surcharge.

## CI03 -- .WHERE sans AddCondition (moulinette 009)

- **Severite** : warning
- **Cibles** : .dhsp
- **Logique** : Detecte `.WHERE.` sans appel a `AddCondition`, `AddAndCondition`, `AddOrCondition`, `RemoveCondition`, `UseClause` ou `Exists` dans les 10 lignes suivantes. Les appels directs `.Where.Equal_*()`, `.Where.NotEqual_*()`, etc. sont consideres valides.
- **Pourquoi** : Un `.WHERE` nu cree une clause SQL vide ou un comportement imprevisible.
- **ANGLE MORT CONNU, mesure le 2026-08-28** : CI03 se satisfait d'un **`AddAndCondition`**, qui ne fait qu'**accumuler** dans une variable. Il ne verifie **pas** qu'un `AddCondition(nom, var)` **cloture** le motif -- or c'est ce dernier, et lui seul, qui injecte la condition dans le `WHERE`. Une routine qui accumule cinq criteres et oublie l'injection finale est donc **validee par CI03** alors que sa requete part quasi non filtree, sans aucune erreur. Defaut vecu (RETEX #163).
  - **Pourquoi la regle qui fermerait ce trou n'est pas livree.** Mesure sur le standard X.13, corps proteges exclus : **3 456** routines utilisent `AddAndCondition`, dont **223 sans aucun `AddCondition(`** dans le meme corps. Sur ces 223, **142 (64 %) accumulent dans un parametre passe par adresse** (`&ValeurCondition`) -- l'appelant injecte, c'est **legitime**. Restent **81** cas, dont une part sont des **hooks** dont le contrat est que le framework injecte. Une regle produisant 81 avertissements sur le **standard** serait fausse par construction : le standard est la reference, pas le suspect. Meme verdict que `S09` -- juste et sans prise exploitable.
  - **Ce qu'il faut faire a la place** : le controle est **humain, a la relecture**. Compter les `AddAndCondition` et chercher **le** `AddCondition` qui les cloture -- dans la routine, ou chez l'appelant si l'accumulateur est un `&parametre`. Contrat detaille : [recordsql-advanced.md](../../coding-diva-advanced/reference/recordsql-advanced.md), section « Le contrat de la condition ».
  - **Ne pas lire le silence de CI03 comme une validation du filtre.**

## CI04 -- Include de PC*.dhsp dans TT/TM (moulinette 020)

- **Severite** : error
- **Cibles** : .dhsp (fichiers TT*.dhsp et TM*.dhsp uniquement)
- **Logique** : Detecte `Include` referancant un programme `PC*.dhsp`.
- **Pourquoi** : Les programmes PC (parametres communs) ne doivent pas etre inclus dans les TT (tests) ni TM (modules de menu).

## CI05 -- #top sans #fetch (moulinette 040)

- **Severite** : warning
- **Cibles** : .dhsq
- **Logique** : Detecte la presence de `#top` sans `#fetch` correspondant dans le fichier.
- **Pourquoi** : `#top` sans `#fetch` provoque une fuite de ressources (curseur SQL non libere).

## CI06 -- GROUP BY avec INSERT/UPDATE/DELETE=YES (moulinette 052)

- **Severite** : error
- **Cibles** : .dhsq
- **Logique** : Detecte `<GroupBy>` dans un fichier contenant `INSERT=YES`, `UPDATE=YES` ou `DELETE=YES` dans les blocs `<FROM>`.
- **Pourquoi** : Un RecordSql avec GROUP BY est en lecture seule par nature ; INSERT/UPDATE/DELETE est incoherent et provoque des erreurs runtime.

## CI07 -- Variable SQL casse incoherente (moulinette 056)

- **Severite** : warning
- **Cibles** : .sql
- **Logique** : Detecte les variables declarees avec `DECLARE @Var` et utilisees avec une casse differente (`@var`, `@VAR`).
- **Pourquoi** : Certains moteurs SQL sont sensibles a la casse pour les variables. Incoherence = bug potentiel.

## CI08 -- CE/CEBIN compare a un entier (moulinette 801)

- **Severite** : error
- **Cibles** : .dhsq
- **Logique** : Detecte `CE = 1`, `CEBIN <> 0`, etc. Les champs CE/CEBIN sont des chaines, pas des entiers.
- **Pourquoi** : Comparer un champ chaine a un entier provoque une conversion implicite et potentiellement un comportement incorrect. Ecrire `CE = '1'`.

## CI09 -- SELECT TOP 1 au lieu de #TOP1 (moulinette 801)

- **Severite** : warning
- **Cibles** : .dhsq
- **Logique** : Detecte `SELECT TOP 1` au lieu de `SELECT #TOP1`.
- **Pourquoi** : `TOP 1` est specifique SQL Server ; `#TOP1` est la syntaxe portable DIVA compatible DB2.

## CI10 -- ScrollBar au lieu de ScrollBar32 (moulinette 802)

- **Severite** : warning
- **Cibles** : .dhsp
- **Logique** : Detecte l'utilisation de `ScrollBar` sans le suffixe `32`.
- **Pourquoi** : `ScrollBar` est l'ancien composant 16 bits ; `ScrollBar32` est la version 32 bits requise.

## CI11 -- Code mort apres RETURN (moulinette 802)

- **Severite** : warning
- **Cibles** : .dhsp
- **Logique** : Detecte du code actif (hors commentaires et lignes vides) entre une instruction `RETURN` et le prochain `EndP`/`EndF`/`Procedure`/`Function`.
- **Pourquoi** : Le code apres un `RETURN` est inatteignable (dead code).

---

## Recapitulatif

| Regle | Moulinette | Severite | Cibles | Description courte |
|-------|-----------|----------|--------|-------------------|
| CI01 | 001 | `info` **hors defaut** | .dhsp, .dhsq, .dhsf, .dhsi, .dhse | SetModuleInfo absent -- convention SVN, `--rules CI01` (#243) |
| CI02 | 004 | error | .dhsp (TT/TE) | Procedure/Function non PUBLIC |
| CI03 | 009 | warning | .dhsp | .WHERE sans AddCondition |
| CI04 | 020 | error | .dhsp (TT/TM) | Include PC* interdit |
| CI05 | 040 | warning | .dhsq | #top sans #fetch |
| CI06 | 052 | error | .dhsq | GROUP BY + INSERT/UPDATE/DELETE |
| CI07 | 056 | warning | .sql | Variable SQL casse incoherente |
| CI08 | 801 | error | .dhsq | CE/CEBIN compare a un entier |
| CI09 | 801 | warning | .dhsq | SELECT TOP 1 au lieu de #TOP1 |
| CI10 | 802 | warning | .dhsp | ScrollBar au lieu de ScrollBar32 |
| CI11 | 802 | warning | .dhsp | Code mort apres RETURN |
