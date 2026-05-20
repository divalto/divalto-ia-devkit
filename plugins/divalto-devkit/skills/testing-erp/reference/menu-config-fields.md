# Champs de configuration du menu (Modifier via F4)

> Reference : `docs/NAVIGATION-ERP.md` section 4

## Acces

Clic droit sur une entree du menu > "Modifier via F4"
Ouvre "Choix du Menu {module} - Consultation"

---

## Champs principaux (mode fiche)

| Champ | Description | Exemples |
|-------|-------------|----------|
| Regroupement | Code du sous-menu | FIC, FICAFF, FICDOS, FICTAB, FICIMP, FIC360, FICFRAIS |
| Ordre affichage | Position dans le sous-menu | 10, 20, 50... |
| Libelle + Alias | Texte affiche et alias | Clients |
| Type de choix | Type d'enchainement | Zoom / Page / Programme |
| Enchainement | Cible de l'enchainement | Numero zoom (09021) / Code page (FICAFF) / Fichier .dhop |
| Parametres | Parametres complementaires | -- |
| Titre | Titre de la fenetre | -- |
| Masque ecran | Fichier .dhof (pour Programme) | gtee020.dhoe |
| Masque imprimante | Ecran d'impression | *09020 |
| Module de traitement | Fichier .dhop (pour Programme) | gttt020.dhop |
| Type de tiers | Contexte tiers | Interne / Client / Fournisseur / Prospect |
| Type de traitement | Mode de fonctionnement | Saisie |
| OP implicite | Code operation par defaut | -- |
| Mode de fonctionnement | Prix HT ou TTC | Prix HT / TTC |
| Image | Icone du menu | #personne_cravate, #affaire, #immeuble, #imprimante |
| Aide | Numero d'aide en ligne | 154, 155... |
| Mnemonique | Identifiant pour tunnels inter-modules | PANIER, ART360, CLI360 |
| Produit / Code Produit | Licence requise | 10999, Divalto Achat-Vente Mezzo |
| Choix visible | Entree visible dans le menu | Oui / Non |
| Choix actif | Entree active (cliquable) | Oui / Non |
| Choix Divalto iZy | Visible pour assistant IA | Oui / Non |

---

## Types d'enchainement

| Type | Champ Enchainement | Utilisation |
|------|-------------------|-------------|
| **Zoom** | Numero de zoom (ex: 09021) | Ouvre un zoom SQL standard |
| **Page** | Code page (ex: FICAFF) | Sous-page du menu (arborescence) |
| **Programme** | Fichier .dhop (ex: GTPPART360.dhop) | Lance un programme specifique |

## Regroupements connus (Commerce & logistique)

| Code | Sous-menu |
|------|-----------|
| FIC | Fichiers |
| FICAFF | Opportunite - Affaire |
| FICDOS | Organisation (Dossiers, Etablissements) |
| FICTAB | Tables |
| FICIMP | Impressions |
| FIC360 | Fiche 360 |
| FICFRAIS | Frais supplementaires |
