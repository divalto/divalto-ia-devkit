# Patterns de zoom ERP

> Reference : `docs/NAVIGATION-ERP.md` section 3

## Structure commune d'un zoom

### Titre de page

Format : `{Entite} - Papyrus (vX.12) - {Mode} - {Ref} {Designation}`

Modes possibles :
- **Consultation** : lecture seule (defaut a l'ouverture)
- **Modification** : edition en cours (apres F4)
- **Creation** : nouveau enregistrement (apres Inser)

### Elements de l'ecran

| Zone | Position | Contenu |
|------|----------|---------|
| Barre de menus | Haut | Fichier, Edition, Options, Aide + menus specifiques |
| Barre de navigation | Sous les menus | Navigation + actions (voir raccourcis ci-dessous) |
| Boutons contextuels | Sous la navigation | Specifiques a l'entite (sous-fiches, notes, etc.) |
| Zone de selection | Centre haut | Filtres avec onglets Selection 1/2/3 |
| Liste | Centre | Grille des enregistrements |
| Onglets detail | Bas | Sections de la fiche |
| Fiche detail | Bas | Champs de l'enregistrement courant |

---

## Raccourcis de navigation

| Raccourci | Action |
|-----------|--------|
| Home | Premiere fiche |
| Shift+F2 | Fiche precedente |
| F2 | Fiche suivante |
| End | Derniere fiche |
| F4 | Modifier |
| Inser | Creer une fiche |
| Suppr | Supprimer |
| Ctrl+Inser | Dupliquer |
| Shift+F4 | Mode fiche / mode liste |
| F8 | Zoom (sous-zoom) |
| F7 | Zoom generalise |
| Shift+F6 | Note |
| Ctrl+F6 | Fichiers joints |
| Echap | Abandonner / Fermer |
| Entree | Valider |

---

## Lecture de donnees via Playwright

### Depuis le snapshot

Les champs d'un zoom apparaissent dans le snapshot comme :
```yaml
- paragraph [ref=eXXX]: Libelle du champ
- textbox [ref=eYYY]: "valeur"
```

Pour lire un champ : identifier le `paragraph` (libelle) et le `textbox` suivant (valeur).

### Depuis la liste

Les enregistrements de la liste apparaissent comme des `generic` imbriques :
```yaml
- generic [ref=eNNN]:
    - generic "Reference" [ref=eAAA]: "422167"
    - generic "Designation" [ref=eBBB]: Perceuse Visseuse...
```

### Navigation entre fiches

Pour naviguer : cliquer sur les boutons de navigation (Premiere, Precedente, Suivante, Derniere) identifies par leurs titres dans le snapshot.

---

## Gestion des onglets

- Chaque zoom s'ouvre dans un **nouvel onglet navigateur**
- `browser_tabs action=list` : lister les onglets ouverts
- `browser_tabs action=select index=N` : basculer sur l'onglet N
- `browser_tabs action=close` : fermer l'onglet courant
- L'onglet 0 est toujours la page d'accueil ERP
