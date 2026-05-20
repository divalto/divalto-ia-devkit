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

> Source : `docs/MOULINETTES.md`, `docs/MOULINETTES-CATALOGUE.md`

---

## CI01 -- SetModuleInfo absent (moulinette 001)

- **Severite** : warning
- **Cibles** : .dhsp, .dhsi, .dhse, .dhsq, .dhsf
- **Logique** : Verifie la presence de `SetModuleInfo` (ou `ModuleInfo` pour .dhsq) dans les 100 premieres lignes. La ligne doit faire au minimum 30 caracteres (120 pour .dhsq).
- **Pourquoi** : Identification obligatoire du module pour la tracabilite et le versioning.

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
| CI01 | 001 | warning | .dhsp, .dhsi, .dhse, .dhsq, .dhsf | SetModuleInfo absent |
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
