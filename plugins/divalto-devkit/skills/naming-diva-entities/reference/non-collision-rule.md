# Regle de non-collision RecordSql / Record

Source : `docs/CONVENTIONS.md` (section Regle de non-collision RecordSql / Record).

---

## Le probleme

Le nom du RecordSql (`<RecordSql Name=...>`) **ne doit PAS etre identique** au nom de la table/Record dans le dictionnaire. DIVA est case-insensitive sur les identifiants.

### Exemple de conflit

```
Table dans GTFDD.dhsd : CONSO
RecordSql Name : Conso
→ ERREUR compilateur : "Parametre CONSO deja defini"
```

**Raison technique :** dans le mchk, la declaration `Record GTFDD.dhsd CONSO CONSO` cree un identifiant `CONSO`. Si le RecordSql a le meme nom, il y a collision de noms dans l'espace de nommage DIVA.

---

## La regle

Le script `compute_names.py` detecte automatiquement les collisions en comparant `NomVue` et `TableSQL` en case-insensitive.

### Quand ca arrive

Le probleme se pose principalement avec les **tables a nom court** ou le nom PascalCase derive est identique (case-insensitive) au nom de la table :

| Table SQL | NomVue calcule | Collision ? |
|-----------|---------------|-------------|
| `RtlFamRglt` | `FamRgltRtl` | Non (noms differents) |
| `CLI` | `CliGtf` | Non (noms differents) |
| `CONSO` | `ConsoGtf` | Non (noms differents) |
| `ART` | `ArtGtf` | Non (noms differents) |

Avec la formule standard `{entite}{prefix_db_capitalized}`, la collision est **rare** car le suffixe de domaine rend le NomVue different de la table. Mais elle reste possible si l'utilisateur fournit un `--nom-vue` override identique a la table.

---

## Resolution

Si une collision est detectee (erreur V01 dans validate_names.py) :

1. Relancer `compute_names.py` avec `--nom-vue` pour fournir un nom alternatif
2. Strategies de renommage :
   - Tables a nom court → nom long descriptif (ex: `CLI` → `Client`, `ART` → `Article`)
   - Tables a nom deja long → nom metier different (ex: `SITE` → `SiteCea`)

### Mecanisme anti-collision automatique (R-002)

Quand le collaborateur fournit un `--nomrecordsql` identique a la table SQL,
le script **ajoute le prefixe base (3 lettres domaine)** comme suffixe pour
desambiguer. Ce nom se propage ensuite dans **tous** les fichiers generes
(RecordSql Name, alias, Module Check, constante zoom).

Exemple :

```
--domaine Dav --entite RaceChien --nomrecordsql RaceChien --champ-cle RacCod
                                   ^^^^^^^^^^
                                   collision avec la table RaceChien

NomVue calcule -> RaceChienGtf     ("Gtf" = prefix base domaine DAV)
```

Le resultat est fonctionnel mais le nommage peut surprendre. **Recommandation
forte** : choisir un `--nomrecordsql` distinct de la table SQL des le depart
(ex: `RacChien` au lieu de `RaceChien`) pour obtenir un nommage plus lisible.

---

## Impact

Le NomVue apparait dans **5 fichiers** :
1. `.dhsq` — `<RecordSql Name={NomVue}>`
2. `*_sql.dhsp` — instances `{NomVue}` et `{NomVue}_Sel`
3. `*mchk*.dhsp` — instance `RS_{NomVue}`
4. `*.dhsf` — masque ecran (reference au RecordSql)
5. `*ficsql.dhsp` — alias (reference au RecordSql)

Changer le NomVue apres generation impacte donc tous ces fichiers.
