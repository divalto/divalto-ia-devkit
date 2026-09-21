# Anti-patterns Zoom SQL — Regles ZSQL01-ZSQL11

Anti-patterns Zoom SQL : le digest livré avec ce skill.

---

## Regles verifiees par validate_zoom.py

| Regle | Severite | Description | Detection | Regle linter |
|-------|----------|-------------|-----------|--------------|
| ZSQL01 | **error** | Procedures obligatoires manquantes | Recherche des 27 signatures `Procedure Zoom*` | `Z01` |
| ZSQL02 | warning | `preturn` absent apres `Zoom.OK = 'I'/'S'/'C'` | Analyse ligne par ligne | `Z02` |
| ZSQL03 | **error** | Melange de prefixes domaine (RT_ dans un zoom GT_, etc.) | Recherche des appels Pre/Post avec mauvais prefixe | `Z03` |
| ZSQL04 | **error** | Module ficsql absent | Recherche `Module '*pmficsql.dhop'` | `Z08` |
| ZSQL05 | warning | Prefixe `-` non gere dans ZOOM.Scevaleur | Recherche `Mid(ZOOM.Scevaleur` | `Z10` |
| ZSQL06 | warning | OverWrittenBy absent ou incoherent | Recherche + comparaison avec token | -- |
| ZSQL07 | **error** | `majuser=true` absent dans PreUpdate | Recherche dans l'appel PreUpdate_recordSql | `M04` |
| ZSQL08 | warning | Zoom.Valretour non initialise dans ZoomValidation | Analyse de la section ZoomValidation | `S08` |
| ZSQL09 | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire | -- |
| ZSQL10 | warning | 4e lettre du nom de fichier differente de `z` | Lue **seulement si la 3e lettre est `e`** -- convention `[prefixe 2 lettres]ez[id]_sql.dhsp` | -- |
| ZSQL11 | warning | Nommage incoherent avec les tokens | Comparaison RecordSql et _Sel avec tokens | -- |

> **La colonne « Regle linter ».** `validate_zoom.py` et `lint_diva.py` verifient
> parfois la meme chose et le disent avec deux codes : c'est le prix d'un prefixe par
> outil, et cette colonne fait le lien. Sept cellules sur onze portent un code -- ce
> skill est le plus chevauchant du plugin. Et trois de ces sept meritent un mot :
> `Z01`, `Z10` et `S08` sont **declares** par le linter mais absents de son registre,
> donc jamais executes (marques *V2* dans ses pages). Ici, ils le sont.
>
> Une cellule vide dit que la verification n'existe que du cote producteur. `ZSQL06`
> merite la meme precision : le linter a bien une regle sur `OverWrittenBy` en
> `.dhsp`, mais elle verifie que sa VALEUR pointe un `.dhop` -- pas sa presence ni sa
> coherence avec le token. Ce n'est pas la meme regle. Et pour `ZSQL09`, le linter
> controle l'encodage sur quatre extensions, jamais sur `.dhsp`.

---

## Detail des regles principales

### ZSQL01 — Procedures obligatoires (ERREUR)

Le framework zoom attend 27 procedures. Leur absence provoque des erreurs runtime.

### ZSQL02 — preturn apres Zoom.OK (WARNING)

**Anti-pattern :** `Zoom.OK = 'I'` sans `preturn` ensuite.

**Risque :** Le code continue sur les lignes suivantes, provoquant des effets de bord.

### ZSQL03 — Melange de prefixes (ERREUR)

**Anti-pattern :** Un zoom Retail utilisant `GT_PreInsert_recordSql` au lieu de `RT_PreInsert_recordSql`.

**Risque :** Appel a la mauvaise implementation framework.

### ZSQL04 — Module ficsql absent (ERREUR)

**Anti-pattern :** `Module '{domaine}pmficsql.dhop'` manquant.

**Risque :** Erreur compilateur "Mot inconnu : GT_*" (ou RT_*, GG_*).

### ZSQL07 — majuser=true (ERREUR)

**Anti-pattern :** `{PREFIX_}PreUpdate_recordSql({NomVue})` sans `majuser = true`.

**Risque :** Les champs `UserMo` et `UserMoDh` ne sont pas mis a jour en base.

**Bonne pratique :** `{PREFIX_}PreUpdate_recordSql({NomVue},majuser = true)`

### ZSQL09 — Encodage (ERREUR)

Tous les fichiers `.dhsp` doivent etre en ISO-8859-1 + CRLF.
