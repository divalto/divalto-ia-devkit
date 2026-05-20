# Abréviations Divalto

Catalogue des abréviations couramment utilisées dans les noms de tables, fonctions
et procédures de l'ERP Divalto Infinity.

Chargé par `parse_request.py` (fonction `load_abreviations`) pour enrichir l'extraction
des keywords métier : une demande mentionnant "contremarque" élargit automatiquement
à "ctm" (et inversement). Objectif : éviter que Neo4j retourne 0 candidat quand le
rédacteur utilise la forme longue alors que le code ERP utilise la forme courte
(ou inversement).

## Format attendu

Toute ligne commençant par `|`, de la forme :

```
| abr | forme complète | contexte ERP |
```

est chargée au démarrage du parseur. Les séparateurs (`|---|---|---|`) et la ligne
d'en-tête (`| Abréviation | ... |`) sont ignorés automatiquement.

**Règles** :
- `abr` : minuscules, 2 à 6 caractères, pas d'espace
- `forme complète` : minuscules, mot unique ou expression courte, accents autorisés
- `contexte ERP` : informatif uniquement (non consommé par le parseur)

## Catalogue

| Abréviation | Forme complète | Contexte ERP |
|-------------|----------------|--------------|
| ctm | contremarque | Achat-Vente (GT_) |
| pce | pièce | Achat-Vente (GT_), Stock |
| cmde | commande | Achat-Vente (GT_) |
| cmt | commentaire | Transverse |
| rglt | règlement | Règlement (RC_) |
| fac | facture | Achat-Vente (GT_) |
| liv | livraison | Achat-Vente (GT_) |
| cli | client | Achat-Vente (GT_), Relation-Tiers (GR_) |
| art | article | Achat-Vente (GT_), Stock |
| frn | fournisseur | Achat (GT_) |
| ech | échéance | Règlement (RC_), Comptabilité (CC_) |
| mvt | mouvement | Stock, Comptabilité (CC_) |

## Historique

- 2026-04-22 : création initiale (12 entrées) suite à RETEX UC-100 contremarque.
  Source des entrées : analyse des tickets archivés `usecases/UC100-*` et
  convention de nommage Divalto (préfixes de tables observés dans l'ERP standard).

## Évolution future (Jalon 3 F2)

Le Jalon 3 du chantier F2 (catalogue métier branché) prévoit d'étoffer ce fichier
à ≥ 20 entrées en collectant depuis `archive/` et par grep des noms de procédures
contenant des abréviations récurrentes dans `C:\Developpements harmony\Standard\Version X.13\`.
