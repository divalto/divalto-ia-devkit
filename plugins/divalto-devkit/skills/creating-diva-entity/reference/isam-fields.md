# Reference exhaustive des champs JSON ISAM (M4 zoom + M2 menu)

## Contenu

- 1. M4 — Zoom des zooms (a5f.dhfi)
- 2. M2 — Menu domaine (rtmenuf.dhfi, gtmenuf.dhfi, ...)
- 3. Regles communes (ecriture ISAM)

---


Liste complete des champs utilisables dans les JSON d'entree de `write_isam.py`
pour les etapes CP9 (zoom des zooms, enregistrement M4) et CP10 (menu domaine,
enregistrement M2). Source autoritative : `docs/ZOOM-INTEGRATION.md` sections
2.5, 2.5bis, 5.6 (confirmes par test reel).

---

## 1. M4 — Zoom des zooms (a5f.dhfi)

### 1.1 Champs obligatoires (20)

| Champ | Valeur / Format | Commentaire |
|-------|-----------------|-------------|
| Ce | `"4"` | Discriminant d'enregistrement (fixe) |
| ZoomNum | `" {numero}"` cadre droite | Moulinette 58, plage par domaine |
| Lib | Libelle du zoom | Visible UI |
| ZoomEnr | Nom RecordSQL (`NomVue`) | Ex : `"LivreRS"` |
| ZoomFic | `"ZOOMSQL"` | Generique, **jamais** le nom physique |
| Ap | Code application | Ex : `"DAV"` |
| Reg | Regroupement dans a5f | Ex : `"LIVRE"` |
| Ordre | `"      {n}"` cadre droite | Multiples de 10 conseilles |
| MsqEcran | Fichier masque **compile** (`.dhof`) | Pas `.dhsf` |
| ModTrait | Module **compile** (`.dhop`) | Pas `.dhsp` |
| ConfM | Confidentialite modification | Ex : `"GzA"` |
| ConfC | Confidentialite creation | Ex : `"GzA"` |
| ConfS | Confidentialite suppression | Ex : `"GzA"` |
| SceAction | Scenario action | `"1"` = Standard |
| SceMode | Mode initial | `"2"` = Liste |
| SceSens | Sens lecture | `"1"` = Normal |
| SceSaisie | Saisie cle depart | `"2"` = Oui |
| SceCleCrea | Saisir cle creation | `"2"` = Oui |
| ChoixIZY | Divalto iZy actif | `"2"` = Oui |
| ProductCode | Code produit | `"10999"` standard |

### 1.2 Champs optionnels (13, visibles via fiche UI Shift+F4)

| Champ | Defaut | Role |
|-------|--------|------|
| ChainAp | `""` | Application a enchainer |
| ChainReg | `""` | Regroupement a enchainer |
| ZoomPar | `""` | Parametres passe au zoom |
| ZoomFicAid | `""` | Fichier aide |
| ZoomAide | `""` | Numero aide |
| SearchDico | `""` | Dictionnaire Power Search |
| MsqImp | `""` | Masque d'impression |
| SearchReference | `""` | Reference Power Search |
| ModTraitI | `""` | Traitement impression |
| ModTraitRF | `""` | Traitement RF |
| ParamZoomCombo | `""` | Parametre ZoomCombo |
| Zoomlz | `""` | Visibilite F7 |
| ConfL | `""` | Confidentialite consultation (defaut = valeur de ConfM) |

Les champs optionnels peuvent etre omis du JSON : `write_isam.py` positionne
alors les octets par defaut (espaces ou zeros selon la Nature).

---

## 2. M2 — Menu domaine (rtmenuf.dhfi, gtmenuf.dhfi, ...)

### 2.1 Champs obligatoires (11)

| Champ | Valeur / Format | Commentaire |
|-------|-----------------|-------------|
| Ce | `"2"` | Discriminant d'enregistrement |
| Reg | Code court du regroupement | Ex : `"FIC"`, pas `"FICHIER"` |
| Ordre | `"      {n}"` cadre droite | Multiples de 10 conseilles |
| Lib | Libelle affiche utilisateur | |
| TypeChain | `"3"` = Zoom | `"1"` = Page, `"2"` = Programme |
| Enchain | `"0{numero_zoom}"` prefixe 0 sur 5 | Ex : zoom 9490 -> `"09490"` |
| ChoixActif | `"2"` | **Pas `"1"`** |
| ChoixVisible | `"2"` | **Pas `"1"`** |
| ChoixIZY | `"2"` | Divalto iZy actif |
| ProductCode | `"10999"` | Code produit |
| EnrNo | `"100001"` | Numero unique >= 100000 |

### 2.2 Champs optionnels

| Champ | Defaut | Role |
|-------|--------|------|
| Image | `""` | Icone (nom symbolique : `#fichier`, `#parametrage`, ...) |
| ChainAp | `""` | Application a enchainer |
| ChainReg | `""` | Regroupement a enchainer |
| RegParent | `""` | Regroupement parent (hierarchie) |
| Param | `""` | Parametres du choix |
| NivConf | `""` | Niveau de confidentialite |

---

## 3. Regles communes (ecriture ISAM)

1. **Cadrage numerique** : les champs numeriques utilises comme cle d'index
   (`ZoomNum`, `Ordre`, `Enchain`) doivent etre **cadres a droite avec espaces**.
   L'index ISAM compare octet par octet.
2. **Champs alphanumeriques** : cadres a gauche, padding espaces.
3. **Champs omis** : `write_isam.py` remplit automatiquement les champs non
   precises dans le JSON avec les valeurs par defaut (espaces / zeros).
4. **Structures ISAM de reference** :
   - `writing-isam-files/scripts/structures/structure_a5f_m4.json`
   - `writing-isam-files/scripts/structures/structure_xmenuf_m2.json`
