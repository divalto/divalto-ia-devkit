# RecordSql -- Complements API et structure

Reference complementaire pour la generation de RecordSql.
Pour le detail exhaustif, voir `docs/RECORDSQL.md`.

---

## Callbacks modules

Procedures appelees automatiquement par le framework lors des operations sur un RecordSql.
`XXXX` = prefixe du module appelant (ex: `MCHK` pour le module check).

### Operations Reader

| Callback | Moment | Retour special |
|----------|--------|---------------|
| `XXXX_ReaderSelect_Av` | Avant execution SQL du reader | |
| `XXXX_ReaderSelect_Ap` | Apres execution SQL du reader | |
| `XXXX_ReaderNext_Av` | Avant lecture ligne suivante | |
| `XXXX_ReaderNext_Ap` | Apres lecture d'une ligne | `"I"` = skip ligne, `"N"` = fin |
| `XXXX_ReaderUpdate_Av` | Avant reecriture ligne courante | |
| `XXXX_ReaderDelete_Av` | Avant suppression ligne courante | |

### Operations Direct

| Callback | Moment |
|----------|--------|
| `XXXX_Select_Av` | Avant execution SQL directe |
| `XXXX_Select_Ap` | Apres execution SQL directe |
| `XXXX_Insert_Av` | Avant insertion |
| `XXXX_Update_Av` | Avant reecriture |
| `XXXX_Delete_Av` | Avant suppression |

### Operations multi-enregistrements

| Callback | Moment |
|----------|--------|
| `XXXX_UpdateWhere_Av` | Avant reecriture multiple |
| `XXXX_DeleteWhere_Av` | Avant suppression multiple |

---

## Complements structure XML

### MandatoryColumns

Champs restitues meme apres desactivation de toutes les jointures :

```xml
<MandatoryColumns>
    {TableSQL}.{ChampCle}
    {TableSQL}.Dos
</MandatoryColumns>
```

Restrictions :
- Un champ `NoActivate` ne peut pas figurer dans MandatoryColumns
- Un champ d'une jointure `NoActivate` ne peut pas y figurer
- Utiliser l'alias si le champ en a un dans le Select

### Attributs avances des jointures

```xml
<LeftJoin Name='JoinLib' Dependencies='JoinBase' ColumnNames='LibJoint' NoActivate>
    TABLEJOINTE as ALIAS
    On ALIAS.DOS = {TableSQL}.DOS and ALIAS.CODE = {TableSQL}.CODEREF
```

| Attribut | Role |
|----------|------|
| `Name` | Nom de la jointure (pour Dependencies) |
| `Dependencies` | Jointures prerequises (separees par `;`) |
| `ColumnNames` | Champs du Select necessitant cette jointure |
| `NoActivate` | Jointure desactivee par defaut |

### Join01 vs LeftJoin

`Join01` : recherche dans une table jointe, existante ou non. Retourne 1 seul resultat (NULL si absent). **Chaque champ genere une sous-requete** — preferer `LeftJoin` si plus d'un champ est necessaire.
