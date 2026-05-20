# Anti-patterns Module Check — Regles M01-M05

## Contenu

- Regles verifiees par validate_mchk.py
- Detail des regles
- Fonctions obligatoires verifiees (STRUCT)

---


Source : `docs/ANTI-PATTERNS.md` (section 3).

---

## Regles verifiees par validate_mchk.py

| Regle | Severite | Description | Detection |
|-------|----------|-------------|-----------|
| M01 | **error** | `Init_Module` absent ou sans `Get_CheckObject_Data` | Recherche de `Function int Init_Module` + `Get_CheckObject_Data(` |
| M02 | **error** | Record `_INIT` non initialise dans `Init_Module` | Recherche de `Initialize_*_New(*_INIT)` |
| M03 | warning | `A5_Stack_OutputMode` / `A5_UnStack_OutputMode` absent dans PostFetch | Recherche dans le fichier si PostFetch existe |
| M04 | warning | `OverWrittenBy` absent ou incoherent avec les tokens | Recherche de `OverWrittenBy` + comparaison avec token |
| M05 | **error** | Fichier pas en ISO-8859-1 + CRLF | Analyse binaire du fichier |
| STRUCT | **error** | Fonctions obligatoires manquantes (22 verifiees) | Recherche regex de chaque signature |
| NAMING | warning | Nommage incoherent avec les tokens | Comparaison ChkData_ et RS_ avec tokens |

---

## Detail des regles

### M01 — Init_Module (ERREUR CRITIQUE)

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

### M02 — Record INIT (ERREUR)

**Anti-pattern :** `{table}_INIT` non initialise dans `Init_Module`.

**Risque :** Le record de reference est vide. Les comparaisons avant/apres dans PostFetch echouent. Les valeurs par defaut dans Duplication sont incorrectes.

**Bonne pratique :** Appeler `Initialize_{entity}_New({table}_INIT)` dans `Init_Module`.

### M03 — Stack/UnStack OutputMode (WARNING)

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

### M04 — OverWrittenBy (WARNING)

**Anti-pattern :** `OverWrittenBy` absent du fichier mchk.

**Risque :** Impossible de surcharger le module check cote client (personnalisation bloquee).

**Bonne pratique :**
```
OverWrittenBy "{moduleprefix_u}mchk{prefix_db}{entity}.dhop"
```

### M05 — Encodage (ERREUR)

**Anti-pattern :** Fichier en UTF-8 ou avec des fins de ligne LF.

**Risque :** Corruption a la compilation. Tous les fichiers `.dhsp` doivent etre en ISO-8859-1 + CRLF.

---

## Fonctions obligatoires verifiees (STRUCT)

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
