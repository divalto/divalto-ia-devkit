# Anti-patterns RecordSql — Regles R01-R06

Source : `docs/ANTI-PATTERNS.md` (section 4).

---

## Regles verifiees par validate_rsql.py

| Regle | Severite | Description | Detection |
|-------|----------|-------------|-----------|
| R01 | **error** | Filtre `Dos = MZ.Dos` absent dans la section WHERE | Analyse du contenu entre `<WHERE>` et `<ORDERBY>` |
| R02 | warning | `OverWrittenBy` absent dans le `<DictionarySql>` | Recherche dans l'en-tete |
| R03 | warning/error | Nom RecordSql vide ou incoherent avec les tokens | Comparaison `Name=` vs `NomVue` attendu |
| R04 | **error** | Section `<SELECT>` ou `<FROM>` manquante | Recherche des balises |
| R05 | warning | `DefaultDictionary` absent ou incoherent avec les tokens | Comparaison avec `DICT` attendu |
| R06 | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire du fichier |

---

## Detail des regles

### R01 — Filtre multi-dossier (ERREUR CRITIQUE)

**Anti-pattern :** RecordSql sans `{TableSQL}.Dos = MZ.Dos` dans le WHERE.

**Risque :** Faille de securite — acces aux donnees de **tous les dossiers** au lieu du dossier courant uniquement.

**Bonne pratique :** Toujours inclure le filtre en dehors de tout `Case`, juste apres `<WHERE>`.

```xml
<WHERE>
    RtlFamRglt.Dos = MZ.Dos    ← OBLIGATOIRE
    ...
```

### R02 — OverWrittenBy (WARNING)

**Anti-pattern :** `overwrittenby` absent de `<DictionarySql>`.

**Risque :** Impossible de surcharger le RecordSql cote client (personnalisation bloquee).

**Bonne pratique :**
```xml
<DictionarySql ... overwrittenby="{prefix_db}rs{base}u.dhoq" ...>
```

### R03 — Nom RecordSql (WARNING/ERREUR)

**Anti-pattern :** Nom du RecordSql vide, ou ne correspondant pas au `NomVue` calcule.

**Risque :** Erreur de compilation ou incoherence entre les fichiers de l'entite.

### R04 — SELECT et FROM (ERREUR)

**Anti-pattern :** Sections `<SELECT>` ou `<FROM>` manquantes.

**Risque :** RecordSql invalide — le compilateur rejette le fichier.

### R05 — DefaultDictionary (WARNING)

**Anti-pattern :** `DefaultDictionary` absent ou pointant vers le mauvais dictionnaire.

**Risque :** Les tables ne sont pas trouvees a la compilation.

### R06 — Encodage (ERREUR)

**Anti-pattern :** Fichier en UTF-8 ou avec des fins de ligne LF.

**Risque :** Corruption a la compilation. Tous les fichiers `.dhsq` doivent etre en ISO-8859-1 + CRLF.

---

## Validation croisee avec les tokens

Quand `--tokens` est fourni a `validate_rsql.py`, les verifications supplementaires sont :
- R03 : `Name=` vs `NomVue` du JSON
- R05 : `DefaultDictionary=` vs `DICT` du JSON

Sans `--tokens`, seules les verifications structurelles sont effectuees.
