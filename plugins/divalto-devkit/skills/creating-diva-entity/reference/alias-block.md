# Bloc d'alias pour *pmficsql.dhsp

Source : `docs/SQUELETTES.md`, `docs/ARCHITECTURE-ENTITE.md`, fichier ERP `rtpmficsql.dhsp`

---

## Format

```
; === Alias pour {NomVue} ({Description}) ===
Alias {PREFIX_}Select_RecordSql       Select_{NomVue}
Alias {PREFIX_}Seek_RecordSql_ID      Seek_{NomVue}_ID
Alias {PREFIX_}Insert_recordSql       Insert_{NomVue}
Alias {PREFIX_}UpDate_recordSql       UpDate_{NomVue}
Alias {PREFIX_}Delete_recordSql       Delete_{NomVue}
Alias {PREFIX_}ReaderOpen_recordSql   ReaderOpen_{NomVue}
Alias {PREFIX_}ReaderClose_recordSql  ReaderClose_{NomVue}
Alias {PREFIX_}ReaderSelect_recordSql ReaderSelect_{NomVue}
Alias {PREFIX_}ReaderUpDate_recordSql ReaderUpDate_{NomVue}
Alias {PREFIX_}ReaderDelete_recordSql ReaderDelete_{NomVue}
Alias {PREFIX_}ReaderNext_recordSql   ReaderNext_{NomVue}
Alias {PREFIX_}ReaderEnd_recordSql    ReaderEnd_{NomVue}
Alias {PREFIX_}ReaderBegin_recordSql  ReaderBegin_{NomVue}
Alias {PREFIX_}DeleteWhere_recordSql  DeleteWhere_{NomVue}
Alias {PREFIX_}UpdateWhere_recordSql  UpdateWhere_{NomVue}
Alias {PREFIX_}GetCount_recordSql     GetCount_{NomVue}
```

---

## Les 16 alias

| # | Fonction framework | Alias entite | Role |
|---|-------------------|-------------|------|
| 1 | `{PREFIX_}Select_RecordSql` | `Select_{NomVue}` | Executer SELECT |
| 2 | `{PREFIX_}Seek_RecordSql_ID` | `Seek_{NomVue}_ID` | Recherche par ID |
| 3 | `{PREFIX_}Insert_recordSql` | `Insert_{NomVue}` | Insertion |
| 4 | `{PREFIX_}UpDate_recordSql` | `UpDate_{NomVue}` | Mise a jour |
| 5 | `{PREFIX_}Delete_recordSql` | `Delete_{NomVue}` | Suppression |
| 6 | `{PREFIX_}ReaderOpen_recordSql` | `ReaderOpen_{NomVue}` | Ouvrir curseur |
| 7 | `{PREFIX_}ReaderClose_recordSql` | `ReaderClose_{NomVue}` | Fermer curseur |
| 8 | `{PREFIX_}ReaderSelect_recordSql` | `ReaderSelect_{NomVue}` | Select curseur |
| 9 | `{PREFIX_}ReaderUpDate_recordSql` | `ReaderUpDate_{NomVue}` | Update curseur |
| 10 | `{PREFIX_}ReaderDelete_recordSql` | `ReaderDelete_{NomVue}` | Delete curseur |
| 11 | `{PREFIX_}ReaderNext_recordSql` | `ReaderNext_{NomVue}` | Suivant curseur |
| 12 | `{PREFIX_}ReaderEnd_recordSql` | `ReaderEnd_{NomVue}` | Fin curseur |
| 13 | `{PREFIX_}ReaderBegin_recordSql` | `ReaderBegin_{NomVue}` | Debut curseur |
| 14 | `{PREFIX_}DeleteWhere_recordSql` | `DeleteWhere_{NomVue}` | Suppression WHERE |
| 15 | `{PREFIX_}UpdateWhere_recordSql` | `UpdateWhere_{NomVue}` | Mise a jour WHERE |
| 16 | `{PREFIX_}GetCount_recordSql` | `GetCount_{NomVue}` | Comptage |

---

## Regles

- **16 alias exactement** par entite — ni plus, ni moins
- Les fonctions **Pre/Post** (PreInsert, PostInsert, PreUpdate, PostUpdate, PreDelete, PostDelete) **n'ont PAS d'alias** — elles s'appellent toujours avec le prefixe domaine directement
- Le bloc se copie dans le fichier `{domaine}pmficsql.dhsp` existant, a la suite des blocs d'alias existants
- Le nom cote droit de l'alias utilise **NomVue** (instance RecordSql), pas TableSQL
