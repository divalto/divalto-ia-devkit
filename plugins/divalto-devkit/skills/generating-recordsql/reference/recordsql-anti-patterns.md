# Anti-patterns RecordSql — Regles RSQ01-RSQ08

Anti-patterns RecordSql : le digest livré avec ce skill.

---

## Regles verifiees par validate_rsql.py

| Regle | Severite | Description | Detection | Regle linter |
|-------|----------|-------------|-----------|--------------|
| RSQ01 | **error** | Filtre `Dos = MZ.Dos` absent dans la section WHERE | Analyse du contenu entre `<WHERE>` et `<ORDERBY>` | `R01` |
| RSQ02 | warning | `OverWrittenBy` absent dans le `<DictionarySql>` | Recherche dans l'en-tete | `R02` |
| RSQ03 | warning/error | Nom RecordSql vide ou incoherent avec les tokens | Comparaison `Name=` vs `NomVue` attendu | -- |
| RSQ04 | **error** | Section `<SELECT>` ou `<FROM>` manquante | Recherche des balises | -- |
| RSQ05 | warning | `DefaultDictionary` absent ou incoherent avec les tokens | Comparaison avec `DICT` attendu | -- |
| RSQ06 | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire du fichier | -- |
| RSQ07 | warning | Table implicite du `<FROM>` sans reference dans le `<WHERE>` | Extraction des tables de FROM hors LEFT JOIN, recherche de `<table>.` dans WHERE | -- |
| RSQ08 | warning | Syntaxe `LEFT JOIN` mal formee | Attendu `LEFT JOIN <table> [alias] ON <condition>` | -- |

> **La colonne « Regle linter ».** `validate_rsql.py` et `lint_diva.py` verifient
> parfois la meme chose et le disent avec deux codes : c'est le prix d'un prefixe par
> outil, et cette colonne fait le lien. Une cellule vide n'est pas un oubli -- elle
> dit que la verification n'existe que du cote producteur. `RSQ06` merite un mot : le
> linter controle bien l'encodage, mais seulement sur `.dhsd`, `.dhsf`, `.dhpt` et
> `.dhps` -- son registre n'applique aucune regle d'encodage au `.dhsq`.

---

## Detail des regles

### RSQ01 — Filtre multi-dossier (ERREUR CRITIQUE)

**Anti-pattern :** RecordSql sans `{TableSQL}.Dos = MZ.Dos` dans le WHERE.

**Risque :** Faille de securite — acces aux donnees de **tous les dossiers** au lieu du dossier courant uniquement.

**Bonne pratique :** Toujours inclure le filtre en dehors de tout `Case`, juste apres `<WHERE>`.

```xml
<WHERE>
    RtlFamRglt.Dos = MZ.Dos    ← OBLIGATOIRE
    ...
```

### RSQ02 — OverWrittenBy (WARNING)

**Anti-pattern :** `overwrittenby` absent de `<DictionarySql>`.

**Risque :** Impossible de surcharger le RecordSql cote client (personnalisation bloquee).

**Bonne pratique :**
```xml
<DictionarySql ... overwrittenby="{prefix_db}rs{base}u.dhoq" ...>
```

### RSQ03 — Nom RecordSql (WARNING/ERREUR)

**Anti-pattern :** Nom du RecordSql vide, ou ne correspondant pas au `NomVue` calcule.

**Risque :** Erreur de compilation ou incoherence entre les fichiers de l'entite.

### RSQ04 — SELECT et FROM (ERREUR)

**Anti-pattern :** Sections `<SELECT>` ou `<FROM>` manquantes.

**Risque :** RecordSql invalide — le compilateur rejette le fichier.

### RSQ05 — DefaultDictionary (WARNING)

**Anti-pattern :** `DefaultDictionary` absent ou pointant vers le mauvais dictionnaire.

**Risque :** Les tables ne sont pas trouvees a la compilation.

### RSQ06 — Encodage (ERREUR)

**Anti-pattern :** Fichier en UTF-8 ou avec des fins de ligne LF.

**Risque :** Corruption a la compilation. Tous les fichiers `.dhsq` doivent etre en ISO-8859-1 + CRLF.

---

### RSQ07 — Coherence FROM / WHERE (WARNING)

**Anti-pattern :** une table declaree dans `<FROM>` (hors `LEFT JOIN`) n'apparait dans aucune
condition du `<WHERE>`.

**Risque :** produit cartesien. La table est jointe sans condition, donc chaque ligne de
la table principale est multipliee par toutes les lignes de la seconde.

**Heuristique du controle** : la premiere table de `<FROM>` est la table principale et n'est pas
verifiee ; pour chacune des suivantes, le controle cherche `<table>.` dans le `<WHERE>`.
C'est un warning et non une erreur : une jointure peut etre exprimee autrement que par
un prefixe de table.

---

### RSQ08 — Syntaxe LEFT JOIN (WARNING)

**Anti-pattern :** un `LEFT JOIN` qui ne suit pas la forme `LEFT JOIN <table> [alias] ON <condition>`.

**Risque :** le RecordSql ne compile pas, ou la jointure est silencieusement ignoree selon
la forme employee.

---

## Validation croisee avec les tokens

Quand `--tokens` est fourni a `validate_rsql.py`, les verifications supplementaires sont :
- RSQ03 : `Name=` vs `NomVue` du JSON
- RSQ05 : `DefaultDictionary=` vs `DICT` du JSON

Sans `--tokens`, seules les verifications structurelles sont effectuees.
