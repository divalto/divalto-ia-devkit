# Champ `Echange` de la table M2 (menu Xmenuf) -- layout et strategies

## Contenu

- Role du champ Echange
- Piege : Echange vide = erreur runtime
- Layout caracterise empiriquement (offsets)
- Strategies de remplissage pour un insert menu
- Clonage depuis une entree modele (methode recommandee)
- Limitation : clonage via string trimmee

---

Reference autonome du skill `writing-isam-files`. Documente le packing binaire du
champ `Echange` (offset 194, taille 600 octets) de la table M2 dans les fichiers menu
domaine (`g3f.dhfi` DAV, `gaf.dhfi` Affaires, ...). Source empirique : RETEX
2026-04-20 (analyse de 10+ entrees M2 de `g3f.dhfi` par dump ctypes).

---

## Role du champ Echange

La structure ISAM M2 declare un champ `Echange` de **600 octets** ("Zone d'echange").
Ce champ n'est **pas** une zone libre : il contient le **packing binaire** de
plusieurs sous-champs a offsets fixes, exposes individuellement dans la fiche "Choix
du Menu" (mode fiche Shift+F4 dans l'ERP).

Sous-champs connus (non-exhaustif) : Masque ecran, Module de traitement, Titre,
Parametres decisionnel, Type de tiers, Aide (numero d'aide en ligne), Type de piece,
Categorie de piece, Profil, OP implicite/associe, Mode de fonctionnement, Edition
de programme, Confidentialite, Modele d'imprimante, Mnemonique (pour tunnel).

---

## Piege : Echange vide = erreur runtime (R-008)

**Inserer une entree M2 avec `Echange` vide** (600 octets a `0x00` ou `0x20`) casse
l'interpretation des sous-champs par l'ERP : l'ERP echoue au clic sur l'entree avec

> "Type d'enchainement incompatible avec un lancement de programme. Type="

meme si `TypeChain=3` (Zoom) et `Enchain=09000` sont corrects. Constate empiriquement
le 2026-04-20 (ajout entree "Test Article" dans regroupement FIC).

---

## Layout caracterise empiriquement (offsets)

Caracterisation faite en dumpant 10+ entrees M2 fonctionnelles du regroupement FIC
(differents `TypeChain` : Zoom, Programme, Page) via `ctypes` + `xisam_treadlong` et
en correlant les variations inter-entrees avec les valeurs affichees dans la fiche
"Choix du Menu" mode Fiche.

**Offsets identifies avec confiance** (relatifs au debut du champ Echange) :

| Offset | Taille | Champ UI | Observation |
|--------|--------|----------|-------------|
| 0 | 32 | **Masque ecran** | `gtez316_sql.dhof`, `GTee299.dhoe` (vide pour zooms standards) |
| 32 | 32 | Masque imprimante | souvent vide |
| 64 | 32 | **Module de traitement** | `gttz316_sql.dhop`, `GTTT299.dhop` |
| 96 | 64 | **Titre** | `Recherche avanc.e`, vide pour zooms standards |
| 260 | 1 | **Type de tiers** (code) | `0` = Interne ; d'autres codes pour Client/Fournisseur |
| 263 | 3 | **Aide** (numero) | `147`, `148`, `149`, `154`, `1417`, ... |
| 350-353 | ? | Flags courts | `"0"` a 350 + `"0"` a 353 observe sur zooms FIC |
| 411-429 | ~19 | Bloc flags/confidentialite | `"I0   01           I"` observe constamment sur zooms FIC |

Les zones `[448..599]` sont majoritairement a `0x20` (padding). Les champs fiche
suivants n'ont pas encore d'offset caracterise : Type de piece, Categorie de piece,
Profil, OP implicite/associe, Mode de fonctionnement, Edition de programme,
Confidentialite (en maj et/ou execution), Modele d'imprimante, Mnemonique tunnel
(distinct du champ `Mnemo` hors Echange a offset 186 du record).

---

## Strategies de remplissage pour un insert menu

### Clonage depuis une entree modele (methode recommandee)

Cloner les **600 octets bruts** du champ Echange depuis une entree modele du **meme
`TypeChain`** (Zoom avec Zoom, Page avec Page, Programme avec Programme), puis
surcharger eventuellement les sous-champs connus (Aide, Masque ecran, ...) aux
offsets identifies.

Pattern Python (lecture bytes bruts depuis un modele, injection dans le nouvel enreg) :

```python
import ctypes

# 1. Ouvrir le fichier menu et lire un enreg modele (meme TypeChain + meme regroupement)
#    ... (topenlong / treadlong / verifier TypeChain + Reg)

# 2. Copier les 600 octets bruts a l'offset 194 du record modele
echange_source = bytes(record_modele[194:194+600])

# 3. Dans le nouveau record a inserer, placer ces 600 octets bruts
nouveau_record = bytearray(record_size)
# ... remplir les autres champs standards
nouveau_record[194:194+600] = echange_source

# 4. Surcharger les sous-champs connus si besoin (ex: nouveau numero d'Aide)
#    Offset Aide = 263, taille 3 (ASCII)
aide = "200"
nouveau_record[194+263:194+263+3] = aide.encode("windows-1252").ljust(3, b" ")
```

### Clonage via string trimmee (methode degradee)

Alternative si on passe par `read_isam.py` / `write_isam.py` : le champ `Echange`
est retourne en string trimmee (`strip()`), ce qui supprime les 260 premiers octets
d'espaces. Le contenu remonte a l'offset 0, decalant tous les sous-champs.

**En pratique** : l'ERP est tolerant sur ce decalage pour les entrees Zoom simples
(sous-champs lus a leurs offsets attendus = espaces = vide, mais l'enreg reste
exploitable). Cas verifie 2026-04-20 sur "Test Article" : le clone a decale
`"0  147"` de offset 260 vers offset 0 ; l'ERP a lu Type tiers + Aide a leurs
offsets attendus, trouve des espaces, et a traite l'entree comme ayant ces champs
vides -- sans empecher l'ouverture du zoom.

**Pour des entrees plus complexes** (Programme avec Masque/Module obligatoires), ce
decalage **casse** l'execution. Ne pas compter sur cette tolerance.

---

## Limitation : expose les sous-champs comme virtual fields (chantier)

Item BACKLOG : exposer les sous-champs connus (Masque ecran, Module traitement,
Titre, Aide, Type tiers) comme **virtual fields** dans `structure_xmenuf_m2.json`
avec une cle `"ParentField": "Echange"` et `"ParentOffset": N`, et adapter
`read_isam.py` / `write_isam.py` pour les serialiser / deserialiser. Permettrait
un clone bytes-correct et une lecture intelligible des sous-champs sans manipulation
manuelle d'offsets. Chantier BACKLOG MNU-01.
