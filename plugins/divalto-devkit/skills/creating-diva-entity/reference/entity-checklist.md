# Checklist creation d'entite DIVA

Source : `docs/ARCHITECTURE-ENTITE.md`

---

## Les 6 elements d'une entite metier

| # | Element | Fichier | Genere par le skill ? |
|---|---------|---------|----------------------|
| 1 | Table + champs + index dans le dictionnaire | `{DICT}.dhsd` | Non (modification manuelle) |
| 2 | Source RecordSql (vue SQL) | `{dbprefix}rs{base}.dhsq` | Oui (generating-recordsql) |
| 3 | Module Check (objet metier) | `{moduleprefix}mchk{dict}{entity}.dhsp` | Oui (generating-objet-metier) |
| 4 | Zoom SQL (ecran CRUD) | `{moduleprefix}z{entity}_sql.dhsp` | Oui (generating-zoom-sql) |
| 5 | Masque ecran | `{moduleprefix}z{entity}_sql.dhsf` | Oui (copie + adaptation d'un template) |
| 6 | Alias dans `*pmficsql.dhsp` | bloc de 16 alias | Oui (generate_alias.py) |

---

## Dependances de compilation

```
RecordSql (.dhsq) --compile--> .dhoq
    |
    v
Module Check (.dhsp) --importe le .dhoq-->
    |
    v
Zoom SQL (.dhsp) --importe le mchk + le .dhoq-->
```

**Ordre de creation** : Dictionnaire → RecordSql → Module Check → Zoom SQL → Alias → Masque

---

## Etapes manuelles post-generation

1. **Dictionnaire** : Ajouter la table et ses champs dans le fichier `.dhsd` du domaine
2. **Alias** : Copier le bloc de 16 alias dans le fichier `*pmficsql.dhsp` du domaine
3. **Compilation** : Compiler les 3 fichiers dans l'IDE Divalto (ordre : rsql → mchk → zoom)
4. **Menu** : Enregistrer le zoom dans le menu Divalto (constante `C_ZOOM_*`)
