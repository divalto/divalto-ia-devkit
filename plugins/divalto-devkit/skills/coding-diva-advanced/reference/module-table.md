# Module Table (mtab) -- validation des donnees

Le module table (mtab) centralise la validation metier pour les tables de parametrage.

## Pattern Switch TRUE pour controle en cascade

```
Function Char Controler_Donnees_MaTable
    1   retour   1 = 'N'
BeginF
    Switch TRUE
        Case Verifier_NumeroDossier(MonRecord.Dos)
            ; Erreur dossier (geree auto)
        Case MonRecord.Cle = ' '
            Gerer_Erreur(3554, '"Code"')
        Case MonRecord.Libelle = ' '
            Gerer_Erreur(3554, '"Libelle"')
        Case MonRecord.RefChamp <> ' ' And Give_AutreEntite(AutreRecord, MonRecord.RefChamp) <> 0
            Gerer_Erreur(1106, MonRecord.RefChamp)
        Default
            retour = 'O'
    EndSwitch
    FReturn(retour)
EndF
```

### Logique du Switch TRUE

Le `Switch TRUE` evalue chaque `Case` comme une expression booleenne :
- Le **premier Case qui est TRUE** est execute
- Les suivants sont **ignores** (pas de fall-through)
- `Default` est atteint uniquement si **aucun Case** n'est vrai → toutes les validations passent → `retour = 'O'`

### Pattern de validation d'un champ optionnel

```
Case MonRecord.RefChamp <> ' ' And Give_AutreEntite(...) <> 0
```

**Toujours tester `<> ' '`** avant la validation de reference. Un champ vide ne doit pas declencher une erreur de reference.

## Initialisation des valeurs par defaut

```
Procedure Initialiser_DonneesParDefaut(nomTable)
BeginP
    SwitchString nomTable
        Case 'MATABLE'
            Initialiser_GroupeRadioBouton(MonRecord.Sens, '1..2', 1)
            Initialiser_CaseACocher(MonRecord.Flag, Non)
    EndSwitch
EndP
```

### Fonctions d'initialisation courantes

| Fonction | Role |
|----------|------|
| `Initialiser_GroupeRadioBouton(champ, plage, defaut)` | Initialise un radio bouton |
| `Initialiser_CaseACocher(champ, valeur)` | Initialise une case a cocher |
| `Verifier_NumeroDossier(dos)` | Controle standard du numero de dossier |
| `Gerer_Erreur(numErr, params)` | Affiche un message d'erreur de controle |

## Structure type d'un module mtab

1. `Controler_Donnees_MaTable` -- validations en cascade (Switch TRUE)
2. `Initialiser_DonneesParDefaut` -- valeurs par defaut a la creation
3. Procedures specifiques metier (calculs, derivations)
