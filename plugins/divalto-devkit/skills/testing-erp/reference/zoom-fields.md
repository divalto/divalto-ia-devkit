# Champs du zoom des zooms

> Reference : `docs/NAVIGATION-ERP.md` section 5.3
> Cross-reference : `docs/ZOOM-INTEGRATION.md` section 2.3 (structure ISAM M4)

## Champs principaux (mode fiche)

### Section Definition

| Champ ecran | Champ M4 (ISAM) | Description |
|-------------|-----------------|-------------|
| Numero du zoom | ZoomNum | Identifiant unique (ex: 9000) |
| Libelle | Lib | Nom affiche (ex: Articles) |
| Application | Ap | Module proprietaire (DAV, DCPT, DGRM...) |
| Regroupement | Reg | Categorie fonctionnelle (ARTICLE, TARIF...) |
| Ordre affichage | Ordre | Position dans le regroupement |
| Mode d'ouverture Divalto One | -- | Mixte / Fiche / Liste |
| Nom du fichier | ZoomFic | Type (toujours ZOOMSQL pour les zooms SQL) |
| Nom de l'enregistrement | ZoomEnr | Record cible (ex: Article) |
| Masque ecran | MsqEcran | Fichier .dhof compile (ex: gtez000_sql.dhof) |
| Module de traitement | ModTrait | Fichier .dhop principal (ex: gttz000_sql.dhop) |
| Masque d'impression | MsqImp | Ecran d'impression associe |
| Traitement lie a l'impression | ModTraitI | Module impression |
| Module traitement RF | ModTraitRF | Traitement mobile |
| Parametre ZoomCombo | ParamZoomCombo | Format : `<C>COL<L>Libelle<C>COL2<L>Libelle2` |
| Code Produit | -- | Licence requise (ex: 10999) |
| Fichier aide | ZoomFicAid + ZoomAide | Numero d'aide contextuelle |
| Dictionnaire Search | SearchDico | Pour Divalto Search (ex: Dico_Document_DAV) |
| Reference Search | SearchRef | Entite Search (ex: Article) |
| Zoom Divalto iZy | ChoixIZY | Visible pour assistant IA (Oui/Non) |
| Visible par F7 | Zoomlz | Visible dans zoom generalise (Oui/Non) |

### Section Scenario

| Champ ecran | Champ M4 | Valeurs |
|-------------|----------|---------|
| Mode initial | SceMode | Fiche (0) / Liste (1) |
| Sens de lecture | SceSens | Normal (0) / Inverse (1) |
| Mode autorise | SceModeLF | Fiche (0) / Liste (1) / Tous (2) |
| Saisie cle de depart | SceSaisie | Non (0) / Oui (1) / Pas la 1ere fois (2) / Manuelle (3) |
| Saisir la cle en creation | SceCleCrea | Non (0) / Oui (1) |
| Retour apres action | SceRetour | Non (0) / Oui (1) |
| Rester en modification | SceRModif | Non (0) / Oui (1) |
| Rester en creation | SceRCrea | Non (0) / Oui (1) |

### Section Confidentialite

| Champ ecran | Champ M4 | Description |
|-------------|----------|-------------|
| En consultation | ConfL | Code confidentialite lecture |
| En modification | ConfM | Code confidentialite modification |
| En creation | ConfC | Code confidentialite creation |
| En suppression | ConfS | Code confidentialite suppression |
| En export imprimante | ConfExpImp | Export impression |
| En export fichier | ConfExpFic | Export fichier |
| En modification en serie | ConfModifEnSerie | Modification batch |

### Section Applications liees

Liste des modules dans lesquels le zoom est accessible. Chaque module a une checkbox "Lie a l'application".
