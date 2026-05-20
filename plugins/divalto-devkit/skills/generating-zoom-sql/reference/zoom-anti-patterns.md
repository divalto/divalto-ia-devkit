# Anti-patterns Zoom SQL — Regles Z01-Z12

Source : `docs/ANTI-PATTERNS.md` (section 2).

---

## Regles verifiees par validate_zoom.py

| Regle | Severite | Description | Detection |
|-------|----------|-------------|-----------|
| Z01 | **error** | Procedures obligatoires manquantes | Recherche des 27 signatures `Procedure Zoom*` |
| Z02 | warning | `preturn` absent apres `Zoom.OK = 'I'/'S'/'C'` | Analyse ligne par ligne |
| Z03 | **error** | Melange de prefixes domaine (RT_ dans un zoom GT_, etc.) | Recherche des appels Pre/Post avec mauvais prefixe |
| Z08 | **error** | Module ficsql absent | Recherche `Module '*pmficsql.dhop'` |
| Z10 | warning | Prefixe `-` non gere dans ZOOM.Scevaleur | Recherche `Mid(ZOOM.Scevaleur` |
| OWB | warning | OverWrittenBy absent ou incoherent | Recherche + comparaison avec token |
| M04 | **error** | `majuser=true` absent dans PreUpdate | Recherche dans l'appel PreUpdate_recordSql |
| S08 | warning | Zoom.Valretour non initialise dans ZoomValidation | Analyse de la section ZoomValidation |
| ENC | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire |
| NAMING | warning | Nommage incoherent avec les tokens | Comparaison RecordSql et _Sel avec tokens |

---

## Detail des regles principales

### Z01 — Procedures obligatoires (ERREUR)

Le framework zoom attend 27 procedures. Leur absence provoque des erreurs runtime.

### Z02 — preturn apres Zoom.OK (WARNING)

**Anti-pattern :** `Zoom.OK = 'I'` sans `preturn` ensuite.

**Risque :** Le code continue sur les lignes suivantes, provoquant des effets de bord.

### Z03 — Melange de prefixes (ERREUR)

**Anti-pattern :** Un zoom Retail utilisant `GT_PreInsert_recordSql` au lieu de `RT_PreInsert_recordSql`.

**Risque :** Appel a la mauvaise implementation framework.

### Z08 — Module ficsql absent (ERREUR)

**Anti-pattern :** `Module '{domaine}pmficsql.dhop'` manquant.

**Risque :** Erreur compilateur "Mot inconnu : GT_*" (ou RT_*, GG_*).

### M04 — majuser=true (ERREUR)

**Anti-pattern :** `{PREFIX_}PreUpdate_recordSql({NomVue})` sans `majuser = true`.

**Risque :** Les champs `UserMo` et `UserMoDh` ne sont pas mis a jour en base.

**Bonne pratique :** `{PREFIX_}PreUpdate_recordSql({NomVue},majuser = true)`

### ENC — Encodage (ERREUR)

Tous les fichiers `.dhsp` doivent etre en ISO-8859-1 + CRLF.
