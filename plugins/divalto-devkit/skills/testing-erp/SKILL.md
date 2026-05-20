---
name: testing-erp
description: >
  Interagit avec l'ERP Divalto via navigateur (Playwright MCP) pour verifier
  le resultat de modifications : connexion, navigation dans le menu, ouverture
  de zoom, consultation du zoom des zooms, verification post-compilation.
  A utiliser apres une compilation/synchro SQL pour tester le resultat dans l'ERP,
  ou de maniere autonome pour naviguer et consulter l'ERP.
---

# testing-erp

## Contenu

1. Prerequis
2. Regles critiques
3. Connexion a l'ERP (N1)
4. Navigation dans le menu (N2)
5. Consultation d'un zoom (N3)
6. Verification post-compilation (N6)
7. Coherence technique via F1 "A propos du Zoom" (CP3)
8. Zoom des zooms (N4)
9. Configuration du menu (N5)
10. Gestion de la session (N7)
11. References

---

## 1. Prerequis

- **Playwright MCP** configure dans `.mcp.json` et charge au demarrage de la session
- ERP Divalto en cours d'execution sur `http://localhost:8080/LCWeb`
- Pour N6 (verification post-compilation) : compilation 0 erreur et synchro SQL terminee

Si les outils `browser_*` ne sont pas disponibles, redemarrer la session Claude Code.

---

## 2. Regles critiques

**R1 -- Credentials** : Claude ne doit JAMAIS stocker, afficher ou manipuler les identifiants. Toujours demander a l'utilisateur de les saisir dans le navigateur.

**R2 -- Snapshot avant interaction** : les refs Playwright sont dynamiques et invalidees a chaque changement de page. Toujours faire `browser_snapshot` avant `browser_click` ou `browser_type`.

**R3 -- Gestion des onglets** : chaque zoom/ecran s'ouvre dans un nouvel onglet navigateur. Utiliser `browser_tabs action=select index=N` pour basculer, `browser_tabs action=close` pour fermer. L'onglet 0 est toujours la page principale ERP.

**R4 -- Reset navigateur** : si l'etat du navigateur est inconnu, faire `browser_close` puis `browser_navigate` pour repartir de zero.

---

## 3. Connexion a l'ERP (N1)

### Workflow

1. `browser_navigate` vers `http://localhost:8080/LCWeb`
2. `browser_snapshot` -- verifier la presence de la page de login (champs Identifiant, Mot de passe, Profil)
3. **Demander a l'utilisateur** de saisir ses identifiants et de choisir le profil (ex: X13)
4. Attendre la confirmation de l'utilisateur
5. `browser_snapshot` -- rafraichir les refs (invalidees apres la saisie utilisateur)
6. `browser_click` sur le bouton "Se connecter"
7. Verifier : le titre de page doit contenir "Divalto infinity"

### Validation page d'accueil

Apres connexion reussie :
- Titre : `Divalto infinity - Papyrus (vX.12)`
- Menu lateral gauche visible (section "Favoris")
- Barre d'outils en haut droite (Autres actions, Aide, Zoom, Imprimante)

> **CHECKPOINT CP1 -- Connexion ERP**
> Presenter au collaborateur :
> - URL chargee et titre de la page d'accueil
> - Modules visibles dans le menu lateral
> Attendre validation avant de naviguer.

---

## 4. Navigation dans le menu (N2)

Le menu ERP est **un graphe de regroupements plats** (pas une arborescence imbriquee) :
chaque entree appartient a un regroupement, et certaines entrees de type `Page` naviguent
vers un autre regroupement. Les "niveaux" visuels sont le resultat de navigations successives
via des entrees `Page`.

**Types de choix** (combobox) :
- `Zoom` : feuille, l'enchainement est un **numero de zoom** -> ouvre un onglet
- `Programme` : feuille, l'enchainement est un **nom de fichier .dhop** -> ouvre un onglet
- `Page` : navigation, l'enchainement est un **code de regroupement cible** -> deploie

### Workflow

1. Cliquer sur **"Menu"** en bas a gauche pour deployer le menu
2. `browser_snapshot` -- identifier les modules (selecteur de regroupement racine)
3. Cliquer sur le **module** cible (ex: "Commerce & logistique")
4. `browser_snapshot` -- identifier les entrees du regroupement racine du module
5. Cliquer sur une entree **Page** (ex: "Fichiers" -> regroupement FIC) pour deployer
6. Repeter l'etape 4-5 tant qu'il reste des entrees `Page` a traverser
7. Cliquer sur une entree **Zoom ou Programme** (ex: "Articles")
8. `browser_tabs action=select index=1` -- basculer sur le nouvel onglet

**Indices visuels** :
- Entree `Page` cliquee : un nouveau panneau s'ajoute sur la droite (pas d'onglet)
- Entree `Zoom` / `Programme` cliquee : un nouvel onglet navigateur s'ouvre

Pour la liste complete des modules et regroupements principaux : voir
[reference/menu-structure.md](reference/menu-structure.md)

---

## 5. Consultation d'un zoom (N3)

Apres ouverture depuis le menu (N2), le zoom s'affiche dans un nouvel onglet.

### Identification

- **Titre de page** : `{Entite} - Papyrus (vX.12) - {Mode} - {Ref} {Designation}`
  - Mode : Consultation, Modification, Creation
- `browser_snapshot` pour lire la structure

### Elements communs

- **Barre de navigation** : Premiere (Home), Precedente (Shift+F2), Suivante (F2), Derniere (End)
- **Actions** : Filtrer, Dupliquer (Ctrl+Inser), Creer (Inser), Modifier (F4), Supprimer (Suppr)
- **Zone de selection** : onglets Selection 1/2/3 avec filtres
- **Liste** : grille des enregistrements
- **Onglets detail** : sections de la fiche en bas

### Fermeture

`browser_tabs action=close` ferme l'onglet du zoom. L'onglet principal ERP reste ouvert.

Pour les patterns de lecture detailles : voir [reference/zoom-patterns.md](reference/zoom-patterns.md)

---

## 6. Verification post-compilation (N6)

**Cas d'usage principal du skill.** Apres creation/modification d'une entite, compilation et synchro SQL, verifier que le zoom fonctionne dans l'ERP.

### Prerequis

- Compilation terminee avec 0 erreur (skill `compiling-diva-projects`)
- Synchro SQL terminee (skill `syncing-diva-sql`)
- Si l'ERP etait ouvert avant la recompilation : le fermer (`browser_close`) et se reconnecter (les objets compiles sont charges au demarrage de session)

### Workflow

**Etape 1 -- Session ERP**

Si l'ERP n'est pas ouvert : executer la connexion (section 3, N1).
Si l'ERP etait ouvert avant recompilation : `browser_close` puis reconnecter (N1).
Si l'ERP est ouvert et pas de recompilation entre-temps : reutiliser la session.

**Etape 2 -- Ouvrir le zoom**

Option A -- **Via le menu** (N2) : naviguer dans l'arborescence jusqu'a l'entree du zoom. Verifier que l'entree est presente a l'emplacement prevu (module > sous-menu).

Option B -- **Via le zoom des zooms** (N4, section 7) : rechercher par numero de zoom. Utile si l'entree menu n'est pas encore creee.

**Etape 3 -- Verifier le zoom**

Apres ouverture, `browser_snapshot` et verifier :

| Element | Verification |
|---------|-------------|
| Titre de page | Contient le nom de l'entite et "Consultation" |
| Barre de navigation | Boutons Premiere/Precedente/Suivante/Derniere visibles |
| Mode | Consultation ou Liste selon la config du zoom |
| Onglets | Les onglets detail sont presents |
| Donnees | Au moins un enregistrement visible (si table existante) ou ecran vide avec bouton Creer (si table nouvelle) |

Si un element ne correspond pas aux attentes, prendre un `browser_take_screenshot` pour diagnostic visuel.

**Etape 4 -- Verification menu (optionnel)**

Verifier que l'entree est presente dans le menu au bon emplacement. Clic droit > "Modifier via F4" pour confirmer le numero de zoom et le regroupement (voir section 8, N5).

> **CHECKPOINT CP2 -- Verification post-compilation**
> Presenter au collaborateur :
> - Zoom ouvert : titre, mode, numero
> - Structure de l'ecran : onglets, champs, barre de navigation
> - Donnees : premier enregistrement ou ecran vide (table nouvelle)
> - Menu : entree presente a l'emplacement prevu (si applicable)
> - Screenshot si anomalie detectee
> Attendre validation.

---

## 7. Coherence technique via F1 "A propos du Zoom" (CP3)

Apres CP2, valider que le binaire reellement charge correspond aux specifications de
generation. La dialog **F1 "A propos du Zoom"** expose les metadonnees techniques du
zoom actif : RecordSQL, Table SQL, Masque, Module, Base, Power Search.

### Workflow

1. S'assurer d'etre sur l'onglet du zoom ouvert (pas l'onglet ERP principal)
2. `browser_press_key` avec `F1` (ou menu Aide > "A propos du Zoom")
3. `browser_snapshot` ou `browser_take_screenshot` pour capturer la dialog
4. Extraire les champs affiches (voir [reference/apropos-dialog.md](reference/apropos-dialog.md))
5. Comparer avec les valeurs attendues (voir tableau ci-dessous)
6. `browser_click` sur "OK" pour fermer la dialog

### Tableau de coherence

| Champ F1 | Source attendue cote generation |
|----------|--------------------------------|
| RecordSQL | Token `recordsql` de naming-diva-entities |
| Table | Nom de la table SQL (parametre `--table`) |
| Masque | Fichier .dhof genere par manipulating-dhsf-screens (token `fichier_masque`) |
| Module | Fichier .dhop genere par generating-zoom-sql (token `fichier_zoom`) |
| Base donnees | Base active du dossier -- typiquement `BaseXrpX13` en dev |
| Power Search / Reference | Nom de l'entite (token `entite`) |

**Power Search** est un moteur de recherche integre de l'ERP, sans impact sur la generation.
Le champ `Reference` doit simplement correspondre au nom d'entite.

### Diagnostic en cas d'ecart

| Ecart observe | Cause probable |
|---------------|----------------|
| RecordSQL differe | Mauvais nom calcule par naming-diva-entities ou erreur dans le mchk |
| Table differe | Dictionnaire .dhsd non synchronise ou mauvais parametre --table |
| Masque .dhof non trouve | manipulating-dhsf-screens n'a pas produit le fichier au bon emplacement, ou compilation echouee |
| Module .dhop non trouve | generating-zoom-sql n'a pas ete compile, ou .dhsp absent du sous-projet |
| Base != BaseXrpX13 | Dossier incorrect a l'ouverture, ou config de session erronee |
| Version module ancienne | L'ERP n'a pas ete relance apres recompilation (redemarrer la session ERP) |

> **CHECKPOINT CP3 -- Coherence technique F1**
> Presenter au collaborateur un tableau 2 colonnes :
> - Valeur observee dans F1 (RecordSQL, Table, Masque, Module, Base)
> - Valeur attendue (calculee a partir des tokens de naming-diva-entities)
> Mettre en evidence les lignes avec des ecarts.
> Attendre validation avant de passer a la suite (integration menu, tests fonctionnels).

---

## 8. Zoom des zooms (N4)

Consulter la definition technique d'un zoom enregistre dans l'ERP.

### Acces

1. Sur la page d'accueil ERP, cliquer sur **"Autres actions"** (icone 3 points verticaux, haut droite)
2. `browser_snapshot` -- identifier le menu deroulant
3. Cliquer sur **"Gestion des Zooms"** (raccourci Shift+F7)
4. `browser_tabs action=select index=1` -- basculer sur le nouvel onglet

### Rechercher un zoom par numero

1. `browser_snapshot` -- la page affiche "Description des zooms applications"
2. Cliquer sur **"Rechercher"** dans la barre d'outils
3. `browser_snapshot` -- une boite de dialogue apparait avec "Chaine a rechercher"
4. `browser_type` le numero du zoom (ex: "9000")
5. `browser_click` sur "Valider" dans la boite de dialogue
6. La liste se positionne sur le zoom trouve

### Mode fiche

Pour voir le detail complet : cliquer sur la ligne du zoom puis sur **"Mode fiche ou mode liste"** (Shift+F4).

Pour la description des champs : voir [reference/zoom-fields.md](reference/zoom-fields.md)

---

## 9. Configuration du menu (N5)

Consulter la definition technique d'une entree du menu.

### Workflow

1. **Clic droit** (`button: "right"`) sur l'entree dans le menu lateral
2. `browser_snapshot` -- menu contextuel avec 4 options
3. Cliquer sur **"Modifier via F4"**
4. `browser_tabs action=select index=1` -- basculer sur le nouvel onglet
5. "Choix du Menu {module} - Consultation" s'affiche en mode liste

### Basculer en mode fiche

Cliquer sur l'entree souhaitee dans la liste puis sur **"Mode fiche ou mode liste"** (Shift+F4) pour voir le detail.

Pour la description des champs : voir [reference/menu-config-fields.md](reference/menu-config-fields.md)

---

## 10. Gestion de la session (N7)

### Garder l'ERP ouvert

- Entre deux consultations de zoom, ne pas fermer l'ERP
- Permet d'enchainer navigation, verification, consultation sans redemander les credentials
- `browser_tabs action=list` pour verifier l'etat des onglets

### Fermer l'ERP

Fermer **uniquement** quand :
- Une recompilation a ete effectuee (les objets compiles sont charges au demarrage)
- La session est terminee

Procedure : `browser_close` ferme tous les onglets. A la prochaine operation, reconnecter via N1.

---

## 11. References

### Fichiers de reference du skill
- [reference/menu-structure.md](reference/menu-structure.md) -- graphe de regroupements, Zoom/Programme/Page, modules
- [reference/zoom-patterns.md](reference/zoom-patterns.md) -- structure ecran, raccourcis, lecture de donnees
- [reference/zoom-fields.md](reference/zoom-fields.md) -- champs du zoom des zooms, mapping M4
- [reference/menu-config-fields.md](reference/menu-config-fields.md) -- champs de la fiche menu
- [reference/apropos-dialog.md](reference/apropos-dialog.md) -- dialog F1 "A propos du Zoom" (CP3)

