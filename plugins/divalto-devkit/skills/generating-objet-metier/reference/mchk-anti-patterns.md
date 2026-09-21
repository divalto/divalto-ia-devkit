# Anti-patterns Module Check — Regles MCHK01-MCHK07

## Contenu

- Regles verifiees par validate_mchk.py
- Detail des regles
- Fonctions obligatoires verifiees (MCHK06)

---


Anti-patterns Module Check : le digest livré avec ce skill.

---

## Regles verifiees par validate_mchk.py

| Regle | Severite | Description | Detection | Regle linter |
|-------|----------|-------------|-----------|--------------|
| MCHK01 | **error** | `Init_Module` absent ou sans `Get_CheckObject_Data` | Recherche de `Function int Init_Module` + `Get_CheckObject_Data(` | `M01` |
| MCHK02 | **error** | Record `_INIT` non initialise dans `Init_Module` | Recherche de `Initialize_*_New(*_INIT)` | `M02` |
| MCHK03 | warning | `A5_Stack_OutputMode` / `A5_UnStack_OutputMode` absent dans PostFetch | Recherche dans le fichier si PostFetch existe | `M03` |
| MCHK04 | warning | `OverWrittenBy` absent ou incoherent avec les tokens | Recherche de `OverWrittenBy` + comparaison avec token | -- |
| MCHK05 | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire du fichier | -- |
| MCHK06 | **error** | Fonctions obligatoires manquantes (22 verifiees) | Recherche regex de chaque signature | -- |
| MCHK07 | warning | Nommage incoherent avec les tokens | Comparaison ChkData_ et RS_ avec tokens | -- |

> **La colonne « Regle linter ».** `validate_mchk.py` et `lint_diva.py` verifient
> parfois la meme chose et le disent avec deux codes : c'est le prix d'un prefixe par
> outil, et cette colonne fait le lien. Une cellule vide n'est pas un oubli -- elle
> dit que la verification n'existe que du cote producteur.

---

## Detail des regles

### MCHK01 — Init_Module (ERREUR CRITIQUE)

**Anti-pattern :** Module check sans `Init_Module` ou `Init_Module` sans appel a `{PREFIX_}Get_CheckObject_Data`.

**Risque :** Le module ne s'initialise pas. Les donnees ChkData sont vides, tous les controles echouent.

**Bonne pratique :**
```
Function int Init_Module
beginF
    Init_Module_DAV
    ChkData_{TABLE} = {PREFIX_}Get_CheckObject_Data(RS_{NomVue})
    ChkData_{TABLE}.ImportTableurFl = OUI
    Initialize_{entity}_New({table}_INIT)
    FReturn(0)
endF
1   InitModule 1,0 = Init_Module()
```

### MCHK02 — Record INIT (ERREUR)

**Anti-pattern :** `{table}_INIT` non initialise dans `Init_Module`.

**Risque :** Le record de reference est vide. Les comparaisons avant/apres dans PostFetch echouent. Les valeurs par defaut dans Duplication sont incorrectes.

**Bonne pratique :** Appeler `Initialize_{entity}_New({table}_INIT)` dans `Init_Module`.

### MCHK03 — Stack/UnStack OutputMode (WARNING)

**Anti-pattern :** `Initialize_*_PostFetch` sans `A5_Stack_OutputMode` / `A5_UnStack_OutputMode`.

**Risque :** Les messages d'erreur s'affichent a l'ecran alors que l'appel devrait etre silencieux. PostFetch est appele dans des contextes de chargement ou les erreurs de validation ne doivent pas etre visibles.

**Bonne pratique :**
```
Function int Initialize_{table}_PostFetch(&{table})
beginf
    A5_Stack_OutputMode
    A5_Set_OutputMode(C_SORTIE_AUCUNE)
    ; ... validations ...
    A5_UnStack_OutputMode
    freturn(0)
endf
```

### MCHK04 — OverWrittenBy (WARNING)

**Anti-pattern :** `OverWrittenBy` absent du fichier mchk.

**Risque :** Impossible de surcharger le module check cote client (personnalisation bloquee).

**Bonne pratique :**
```
OverWrittenBy "{moduleprefix_u}mchk{prefix_db}{entity}.dhop"
```

### MCHK05 — Encodage (ERREUR)

**Anti-pattern :** Fichier en UTF-8 ou avec des fins de ligne LF.

**Risque :** Corruption a la compilation. Tous les fichiers `.dhsp` doivent etre en ISO-8859-1 + CRLF.

---

## Fonctions obligatoires verifiees (MCHK06)

22 signatures de fonctions sont verifiees comme obligatoires :

1. `Get_{TABLE}_ChkData` — proprietes objet metier
2. `Get_{TABLE}_FieldProperties` — proprietes par champ
3. `Get_{TABLE}_FieldNames_Min` — champs minimum du SELECT
4. `Get_{TABLE}_FieldNames_All` — tous les champs
5. `Get_{TABLE}_Record` — record entier
6. `Get_{TABLE}_Lib` — libelle
7. `Get_{TABLE}_Key` — cle primaire concatenee
8. `Get_{entity}_Reservation` — chaine de reservation
9. `Check_{TABLE}_Key` — controle cles
10. `Check_{TABLE}_FieldCod` — controle champ par code
11. `Initialize_{entity}_New` — creation
12. `Initialize_{entity}_PostFetch` — post-lecture
13. `Initialize_{entity}_Duplication` — duplication
14. `Initialize_{entity}_PreInsert` — avant insertion
15. `Initialize_{entity}_PostInsert` — apres insertion
16. `Initialize_{entity}_PreUpdate` — avant mise a jour
17. `Initialize_{entity}_PostUpdate` — apres mise a jour
18. `Initialize_{entity}_PreDelete` — avant suppression
19. `Initialize_{entity}_PostDelete` — apres suppression
20. `Authorize_{entity}_Insert` — autorisation creation
21. `Authorize_{entity}_Update` — autorisation modification
22. `Authorize_{entity}_Delete` — autorisation suppression
