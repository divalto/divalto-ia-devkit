# Structure du menu ERP Divalto

## Contenu

- Modele reel -- graphe de regroupements
- Modules (selecteur de regroupement racine)
- Regroupement racine Commerce & logistique (regroupement "")
- Regroupement FIC (Fichiers Commerce & logistique)
- Regroupements de niveau superieur (exemples)
- Numeros de zoom connus (Commerce & logistique)
- Navigation via Playwright -- strategie generale

---


> Reference complete : `docs/NAVIGATION-ERP.md` section 2

## Modele reel -- graphe de regroupements

Le menu ERP n'est **pas une arborescence imbriquee**. C'est un **graphe de regroupements plats**.

- Chaque entree appartient a un seul **regroupement** (code 3-9 caracteres majuscules)
- Un regroupement vide (`""`) designe la **racine d'un module**
- Chaque entree a un **Type de choix** qui determine son comportement :

| Type | Enchainement | Effet |
|------|-------------|-------|
| `Zoom` | numero de zoom (ex `09000`) | **FEUILLE** : ouvre le zoom dans un nouvel onglet |
| `Programme` | fichier .dhop | **FEUILLE** : lance un programme Diva |
| `Page` | code de regroupement cible | **NAVIGATION** : deploie le regroupement cible dans le panneau suivant |

La "profondeur" visible dans l'UI est le resultat de navigations successives via des entrees `Page`.

---

## Modules (selecteur de regroupement racine)

16 modules. Les modules Administration et Commun basculent le titre sur "Dossier 998"
(dossier technique cross-dossier, comportement normal).

| Module | Code application | Equivalent fonctionnel |
|--------|-----------------|----------------------|
| Commerce & logistique | DAV | Gestion commerciale |
| Production | GG | Fabrication |
| Relation Tiers | GR | CRM |
| Affaire | GA | Gestion de projets |
| Comptabilite | DCPT | Comptabilite |
| Reglement NEW | DREG | Reglements nouvelle generation |
| Reglement OLD | DREG | Reglements ancienne generation |
| Paie | DPAIE | Paie |
| Qualite | DQUAL | Qualite |
| Documentation | DDOC | Documents sortants |
| Controle | CO | Controle de gestion |
| Ressources materielles | GM | GRM |
| Administration | DSP | Administration systeme (Dossier 998) |
| Commun | COMMUN | Modules communs (Dossier 998) |
| Processus | DSP | Workflows |
| Point de vente | PV | PDV |

---

## Regroupement racine Commerce & logistique (regroupement "")

27 entrees observees, toutes de type `Page` sauf exception. Chaque entree pointe vers
un regroupement de niveau suivant.

| Ordre | Libelle | Type | Enchainement | Parametre |
|-------|---------|------|--------------|-----------|
| 10 | Fichiers | Page | FIC | |
| 20 | Administration ventes | Page | PCECLI | |
| 30 | Administration achats | Page | PCEFOU | |
| 35 | Installation Maintenance | Page | DTRV | |
| 40 | Cessions inter-etablissements | Page | PCEETB | |
| 50 | Contrats et abonnements | Page | CEA | |
| 60 | Stocks | Page | STOC | |
| 70 | Listes | Page | LST | |
| 80 | Interrogations | Page | INT | |
| 90 | Traitements | Page | TRT | |
| 100 | Utilitaires | Page | UTI | |
| 110 | D.E.B. | Page | DEB | |
| 120 | Donnees techniques | Page | GAM | DPROD |
| 130 | O.F. | Page | OFM | DPROD |
| 140 | Maintenance | Page | MAINT | DPROD |
| 150 | Atelier | Page | ATE | DPROD |
| 160 | Demande De Modification | Page | DDM | DPROD |
| 160 | WMS | Page | WMS | DWMS |
| 170 | Devis technique | Page | DT | DT |
| 180 | Retail | Page | RTL | |
| 190 | Data hub | Page | DHB | |
| 200 | Cartographie de produits | Page | CARTO | |
| 220 | Grand import | Page | GIM | |
| 230 | GMS | Page | GMS | |
| 240 | Mobilite logistique | Page | DMTW | |
| 250 | Configurateur | Page | CFG | |
| 260 | Fabricants - Distributeurs | Page | FABDIS | |
| 280 | Tracabilite article | Page | TRACART | |

> **Ordre duplique** : ordre 160 est present deux fois (DDM + WMS) avec parametres
> complementaires differents (DPROD et DWMS). Seule une entree s'affiche selon la
> licence installee.

---

## Regroupement FIC (Fichiers Commerce & logistique)

| Ordre | Libelle | Type | Enchainement |
|-------|---------|------|--------------|
| 10 | Articles | Zoom | 09000 |
| 11 | Articles indices | Zoom | 09483 |
| 12 | Recherche avancee d'articles | Programme | GTPP299.dhop |
| 13 | Catalogue reference externe | Zoom | 09010 |
| 15 | Tarification | Page | FICTAR |
| 16 | Historique Articles | Zoom | 9198 |
| 20 | Frais supplementaires | Page | FICFRAIS |
| 50 | Clients | Zoom | 09021 |
| 60 | Fournisseurs | Zoom | 09022 |
| 70 | Prospects | Zoom | 09023 |
| 80 | Commerciaux | Zoom | 09024 |
| 90 | Autres tiers | Zoom | 09025 |
| 100 | Opportunite - Affaire | Page | FICAFF |
| 110 | Organisation | Page | FICDOS |
| 220 | Tables | Page | FICTAB |
| 250 | Impressions | Page | FICIMP |
| 260 | Fiche 360 | Page | FIC360 |
| 270 | Saisie panier | Programme | gtpppce500.dhop |
| 270 | Acompte | Page | ACOMPTE |

---

## Regroupements de niveau superieur (exemples)

| Regroupement | Role | Contenu typique |
|--------------|------|-----------------|
| FICTAB | Tables (parametrage commercial) | FICTABPC, FICTABAR, FICTABTA, FICTABGP, FICTABTI, FICTABUS, FICTABST, FICTABQU, FICTABTR, FICTABGI, FICTABRE, FICTABDT, FICTABCEA, FICTABRTL... |
| FICAFF | Opportunite - Affaire | Opportunite (09501), Affaire (09500), Avenant (09502) |
| FICDOS | Organisation | Dossiers (09020), Etablissements (09026) |
| FICFRAIS | Frais supplementaires | Regles (9321) |
| FIC360 | Fiche 360 | Fiche article 360 (GTPPART360.dhop), client 360, fournisseur 360 |
| FICIMP | Impressions | Etiquettes article, tiers, Articles, Clients, Prospects, Fournisseurs |

---

## Numeros de zoom connus (Commerce & logistique)

| Numero | Entite |
|--------|--------|
| 09000 | Articles |
| 09010 | Catalogue reference externe |
| 09020 | Dossiers |
| 09021 | Clients |
| 09022 | Fournisseurs |
| 09023 | Prospects |
| 09024 | Commerciaux |
| 09025 | Autres tiers |
| 09026 | Etablissements |
| 09483 | Articles indices |
| 09500 | Affaire |
| 09501 | Opportunite |
| 09502 | Avenant |
| 9198 | Historique Articles |
| 9321 | Regles frais supplementaires |

---

## Navigation via Playwright -- strategie generale

1. Cliquer sur **"Menu"** pour le deployer (bouton en bas a gauche)
2. Cliquer sur le **module** (bascule le regroupement racine du module)
3. Cliquer sur l'**entree de type Page** pour deployer le regroupement suivant
4. Repeter jusqu'a atteindre une entree `Zoom` ou `Programme`
5. Cliquer : **un nouvel onglet s'ouvre** avec le zoom ou le programme
6. Basculer avec `browser_tabs action=select index=1`

> Un nouvel onglet ne s'ouvre **que** pour `Zoom` et `Programme`. Un clic sur une
> entree `Page` ne fait que deployer le regroupement cible dans le panneau courant.

### Classes CSS utiles

| Classe | Role |
|--------|------|
| `.ChoixFinder` | Entree de menu (tous niveaux) |
| `.ChoixFinder.Current` | Entree selectionnee (panneau suivant deploye) |
| `.IaContextMenu` | Menu contextuel (clic droit) |
| `.ContextMenu_modifier` | Option "Modifier via F4" |
| `.ContextMenu_ajouterFavoris` | Option "Ajouter aux favoris" |
| `.celluleTableauDefaut` | Cellule d'une grille/liste de zoom |
