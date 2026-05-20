# Menu domaine — ajout d'une entree (CP10)

## Contenu

- Modele Divalto du menu
- Prerequis du checkpoint
- Questions a poser avant l'insertion
- Commande d'insertion
- Champs M2 obligatoires
- Contraintes

---


Reference detaillee pour l'etape 17 du workflow `creating-diva-entity` (ajout d'une entree dans le menu domaine ERP).

---

## Modele Divalto du menu

Voir `docs/NAVIGATION-ERP.md` section 2 pour le detail. En synthese :

- Le menu n'est **pas une arborescence imbriquee** mais un **graphe de regroupements plats**.
- Chaque entree appartient a un regroupement (code court comme `FIC`, `FICTABPG`, etc.).
- **Creer une entree = ajouter une ligne dans un regroupement existant**, pas "creer un menu".

---

## Prerequis du checkpoint

Avant d'inserer l'enregistrement M2, il faut avoir identifie :

- Le regroupement cible (code court `Reg`)
- L'ordre libre dans ce regroupement
- Le libelle a afficher

Cela requiert une discussion avec le collaborateur (CP10 est un checkpoint obligatoire).

---

## Questions a poser avant l'insertion

### 1. Dans quel regroupement ajouter l'entree ?

Exemples courants Commerce & logistique :
- `FIC` (Fichiers)
- `FICTABAR` (Tables liees aux articles)
- `FICTABPG` (Parametrage general)
- `FICTABTI` (Liees aux tiers)

Lire les regroupements existants via `reading-isam-files` (cle A2 du fichier menu
domaine) pour proposer des options au collaborateur.

### 2. Quel ordre dans ce regroupement ?

**Convention** : multiples de 10 (10, 20, 30, ...) pour permettre d'intercaler
plus tard. Suggerer `max(ordre existant) + 10`.

**Pas obligatoire** : l'utilisateur peut choisir librement (ex : 15 entre 10 et 20).

### 3. Quel libelle afficher ?

Texte vu par l'utilisateur final. Par defaut le token `description`.

### 4. Icone ?

Champ `Image` = nom symbolique comme `#fichier`, `#parametrage`, `#DavFichiers`.
Optionnel — conserver le defaut si inconnu.

### 5. Code Produit ?

`10999` par defaut (produit standard Divalto).

---

## Commande d'insertion

```
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --params-file {OUTPUT_DIR}/data_menu.json \
    --structure-dir .claude/skills/writing-isam-files/scripts/structures
```

---

## Champs M2 obligatoires

Voir `docs/ZOOM-INTEGRATION.md` section 5.6 pour la reference complete.

```json
{
    "Ce": "2",
    "Reg": "{code_regroupement_existant}",
    "Ordre": "      {ordre_cadre_droite}",
    "Lib": "{libelle_affiche}",
    "TypeChain": "3",
    "Enchain": "0{numero_zoom}",
    "BitmapExp": "{icone_ex_#fichier}",
    "Echange": "{clone_depuis_entree_existante_meme_TypeChain}",
    "ChoixActif": "2",
    "ChoixVisible": "2",
    "ChoixIZY": "2",
    "ProductCode": "10999",
    "EnrNo": "{enr_unique_>=_100000}"
}
```

---

## Champ `Echange` -- **obligatoire, cloner d'une entree existante**

Le champ `Echange` (offset 194, taille 600 octets) contient le **packing binaire**
de ~17 sous-champs visibles dans la fiche "Choix du Menu" en mode Fiche (Shift+F4) :
Type de tiers, Type de piece, Type de traitement, Categorie de piece, Profil, OP
implicite/associe, Mode de fonctionnement, Edition de programme, Confidentialite
(distinct de ConfL), Masque ecran, Masque imprimante, Module de traitement,
Parametres decisionnel, Modele d'imprimante, **Aide** (numero d'aide en ligne),
**Mnemonique** (pour tunnel).

**Si `Echange` est laisse vide** (600 octets a `0x00` ou `0x20`), l'ERP echoue au
clic sur l'entree avec **"Type d'enchainement incompatible avec un lancement de
programme. Type="**, meme si `TypeChain=3` (Zoom) et `Enchain` sont corrects.
Constate empiriquement le 2026-04-20.

Le layout interne des 600 octets n'est pas encore formellement caracterise
(cf. `docs/NAVIGATION-ERP.md` section 4.1c). **Strategie recommandee** : cloner
le champ `Echange` depuis une entree M2 existante du **meme `TypeChain`**
(Zoom avec Zoom, Page avec Page, Programme avec Programme), puis adapter
uniquement les champs distinctifs.

**Snippet Python (methode degradee via string trimmee)** :

```python
import json
import subprocess

# 1. Lire une entree modele du meme TypeChain (ici : Articles, FIC/10, zoom)
result = subprocess.run([
    "py",
    ".claude/skills/reading-isam-files/scripts/read_isam.py",
    "--file", "C:/Developpements harmony/Standard/Version X.13/Achat-Vente/fichier/g3f.dhfi",
    "--structure", ".claude/skills/reading-isam-files/scripts/structures/structure_xmenuf_m2.json",
    "--key", "A2", "--key-value", "FIC", "--max", "1",
], capture_output=True, text=True, encoding="utf-8")
modele = json.loads(result.stdout)["records"][0]

# 2. Cloner et surcharger les champs distinctifs
nouvelle_entree = dict(modele)
nouvelle_entree["Ordre"] = "51"                  # auto-padding gauche via Justify:right
nouvelle_entree["Lib"] = "{libelle}"
nouvelle_entree["Enchain"] = "0{numero_zoom}"
nouvelle_entree["EnrNo"] = "{enr_unique}"
# Echange, BitmapExp, ChoixActif, etc. viennent du modele
```

> **Limitation connue de cette methode** : `read_isam.py` retourne le champ
> `Echange` comme une string **strip()** (espaces de tete et de fin supprimes).
> Le reecriture via `write_isam.py` repositionne alors le contenu a l'offset 0
> du champ, alors que les sous-champs reels (Type tiers, Aide, Masque, ...) sont
> a des offsets fixes non nuls (cf. `docs/NAVIGATION-ERP.md` section 4.1c).
> En pratique, l'ERP est tolerant sur ce decalage pour les entrees Zoom simples
> (sous-champs lus a leurs offsets attendus = espaces = vide, mais l'enreg reste
> exploitable). Pour des entrees complexes (Programme avec Masque/Module), ce
> decalage **casse** l'execution. Cf. BACKLOG MNU-01 pour la caracterisation et
> l'exposition des sous-champs comme virtual fields dans la structure JSON
> (permettrait un clone bytes-correct).

---

## Contraintes

- `Reg` est le **code** du regroupement cible (ex : `FIC`, `FICTABPG`), pas un texte.
- `Ordre` est cadre a droite (padding espaces, numerique).
- `Enchain` est le numero de zoom prefixe `0` (ex : zoom 9500 -> `"09500"`).
- `TypeChain = 3` correspond au type `Zoom` (le type de choix standard pour un zoom SQL).
  Les valeurs pour `Page` et `Programme` sont differentes — non necessaires pour
  une creation d'entite standard qui aboutit toujours a un zoom.

## Visibilite F7 via M1 dans `a5f.dhfi` (R-002, 2026-04-23)

### Probleme

Apres ecriture M4 (zoom des zooms) et M2 (menu domaine), le zoom peut **rester invisible via F7** dans l'ERP si aucun enreg M1 (`Ce=5`) correspondant n'existe dans `a5f.dhfi`. La declaration M4 est necessaire mais insuffisante pour la visibilite contextuelle.

RETEX R-002 : sur le zoom "Race de chien" (9987), M4 avait ete ecrit mais aucun M1 n'etait present -> zoom invisible jusqu'a l'ajout manuel des M1.

### Pattern M1

Un enreg M1 **autorise un zoom (`ZoomNum`) dans une application (`Applic`)**. Pour chaque domaine ou le zoom doit etre visible, un enreg M1 dedie est necessaire.

| Cas | Nb M1 | Exemple |
|-----|-------|---------|
| Table metier propre a son domaine | 1 | RaceChien (DAV uniquement) -> 1 M1 Applic=DAV |
| Table commune multi-domaine | N | Pays (zoom 540), visible DAV + DCPT + DPAIE -> 3 M1 avec Applic variant |

### Schema M1 (cf `structure_a5f_m1.json`)

50 octets, 6 champs :

| Offset | Taille | Champ | Valeur pour un zoom |
|--------|--------|-------|---------------------|
| 0 | 1 | `Ce` | `5` (constant) |
| 1 | 5 | `ZoomNum` | `M4.ZoomNum` |
| 6 | 8 | `Ap` | `M4.Ap` (domaine d'origine) |
| 14 | 8 | `Reg` | `M4.Reg` |
| 22 | 8 | `Ordre` | `M4.Ordre` |
| 30 | 20 | `Applic` | **domaine cible de visibilite** (varie) |

### Questions a poser au collaborateur

1. "Dans quel(s) domaine(s) ce zoom doit-il etre visible via F7 ?"
   - Defaut : **M4.Ap** (domaine propre, cas mono-domaine)
   - Reponse typique pour une entite metier custom : le domaine proprietaire (ex DAV pour un zoom DAV)
2. Si plusieurs domaines cites : 1 enreg M1 par domaine, meme `ZoomNum/Ap/Reg/Ordre`, seul `Applic` varie.

### Commande d'insertion (par domaine)

```bash
py .claude/skills/writing-isam-files/scripts/write_isam.py \
    --file "{CHEMIN_CIBLE}/a5f.dhfi" \
    --structure .claude/skills/writing-isam-files/scripts/structures/structure_a5f_m1.json \
    --params '{
        "Ce":      "5",
        "ZoomNum": "<M4.ZoomNum>",
        "Ap":      "<M4.Ap>",
        "Reg":     "<M4.Reg>",
        "Ordre":   "<M4.Ordre>",
        "Applic":  "<domaine_visible>"
    }'
```

Repeter pour chaque `domaine_visible` demande.

### Observations empiriques (X.13 Achat-Vente a5f.dhfi, 2026-04-23)

- ~4997 enregs M1 au total dont ~4310 avec ZoomNum significatif
- Zooms multi-domaine bien presents : `ZoomNum=540 Ap=DAV` a 3 M1 (Applic in DAV/DCPT/DPAIE)
- 687 M1 avec `ZoomNum=0` (probablement entrees "defaut" de categorie/separateur -- non-critique pour la creation d'entite custom)

### Test de verification

Apres ecriture, relire pour confirmer :

```bash
py .claude/skills/reading-isam-files/scripts/read_isam.py \
    --file "a5f.dhfi" \
    --structure .claude/skills/reading-isam-files/scripts/structures/structure_a5f_m1.json \
    --key A5 --filter "ZoomNum=<NUM>" --max 10
```

Doit retourner N lignes = nombre de domaines declares.
