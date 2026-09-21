# API DhxIsam64.dll -- Reference Python ctypes

## Contenu

- 1. Chargement de la DLL
- 2. Signatures ctypes
- 3. Structure TDF51 (Table De Fichier)
- 4. Sequence d'operations
- 5. Mode = code de reservation (F / P / R)
- 6. Positionnement via TDF.KEY
- 7. Detection de fin d'iteration
- 8. Table de reservations (~1003 slots)
- 9. Codes d'erreur
- 10. Pieges critiques

Revision 2026-04-22 : la semantique du parametre `mode` a ete corrigee --
c'est un code de reservation (F/P/R) et non un code de direction/positionnement.

---

## 1. Chargement de la DLL

```python
import ctypes

dll = ctypes.WinDLL(r"C:\divalto\sys\DhxIsam64.dll")
```

`WinDLL` = convention d'appel StdCall (obligatoire pour cette DLL).

**Documentation de reference :**
- Header C : `C:\divalto\Exemples\Xisam\xisam.h`
- Declarations VB : `C:\divalto\Exemples\Xisam\VB\defxisam.txt`

---

## 2. Signatures ctypes

```python
# xisam_begin(ushort tache) -> short
dll.xisam_begin.argtypes = [ctypes.c_ushort]
dll.xisam_begin.restype = ctypes.c_short

# xisam_end(ushort tache) -> ushort
dll.xisam_end.argtypes = [ctypes.c_ushort]
dll.xisam_end.restype = ctypes.c_ushort

# xisam_topenlong(ushort tache, byte[] tdf, byte[] mode) -> ushort
dll.xisam_topenlong.argtypes = [
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.POINTER(ctypes.c_ubyte),
]
dll.xisam_topenlong.restype = ctypes.c_ushort

# xisam_treadlong(ushort tache, byte[] tdf, byte[] enreg, ushort lg, byte[] mode) -> ushort
dll.xisam_treadlong.argtypes = [
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
]
dll.xisam_treadlong.restype = ctypes.c_ushort

# xisam_twritelong -- meme signature que treadlong
dll.xisam_twritelong.argtypes = dll.xisam_treadlong.argtypes
dll.xisam_twritelong.restype = ctypes.c_ushort

# xisam_tpreadlong -- protected read. MEME SIGNATURE que treadlong, mais PAS
# interchangeable : a cle vide (parcours sequentiel) tpreadlong echoue des le
# 1er appel la ou treadlong parcourt toute la table (mesure, cf. section 9).
dll.xisam_tpreadlong.argtypes = dll.xisam_treadlong.argtypes
dll.xisam_tpreadlong.restype = ctypes.c_ushort

# xisam_trewritelong(ushort tache, byte[] tdf, byte[] enreg, ushort lg) -> ushort (UPDATE, pas de mode)
dll.xisam_trewritelong.argtypes = [
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_ushort,
]
dll.xisam_trewritelong.restype = ctypes.c_ushort

# xisam_tdeletelong -- DELETE, meme signature que trewritelong
dll.xisam_tdeletelong.argtypes = dll.xisam_trewritelong.argtypes
dll.xisam_tdeletelong.restype = ctypes.c_ushort

# xisam_tcloselong(ushort tache, byte[] tdf) -> ushort
dll.xisam_tcloselong.argtypes = [
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
]
dll.xisam_tcloselong.restype = ctypes.c_ushort
```

---

## 3. Structure TDF51 (Table De Fichier)

Buffer de **1024 octets** representant un fichier ouvert.

| Offset | Taille | Champ | Description |
|--------|--------|-------|-------------|
| 0 | 4 | interne0 | Reserve systeme |
| 4 | 256 | NAME | Chemin complet du fichier .dhfi |
| 260 | 1 | PROT | Protection |
| 261 | 256 | KEY | Cle courante (KEY[0]=lettre index, KEY[1..]=valeur) |
| 517 | 17 | interne1 | Reserve |
| 534 | 2 | SIZELAST | Taille du dernier enregistrement lu |
| 536 | 143 | interne2 | Reserve |
| 679 | 1 | READONLY | Flag lecture seule |

### Creation en Python

```python
tdf = (ctypes.c_ubyte * 1024)()
name_bytes = chemin.encode("windows-1252")
for i, b in enumerate(name_bytes[:256]):
    tdf[4 + i] = b
```

---

## 4. Sequence d'operations

```python
TACHE = ctypes.c_ushort(15)

# 1. Initialiser la session
ret = dll.xisam_begin(TACHE)

# 2. Preparer le TDF
tdf = (ctypes.c_ubyte * 1024)()
# ... ecrire le chemin a l'offset 4

# 3. Ouvrir le fichier
mode = (ctypes.c_ubyte * 1)(0x50)  # P = partage
ret = dll.xisam_topenlong(TACHE, tdf, mode)

# 4. Construire l'enregistrement
rec = (ctypes.c_ubyte * taille_enreg)()
for i in range(taille_enreg):
    rec[i] = 0x20  # espaces
# ... copier les champs aux bons offsets

# 5. Ecrire
mode_w = (ctypes.c_ubyte * 1)(0x50)
ret = dll.xisam_twritelong(TACHE, tdf, rec, ctypes.c_ushort(taille_enreg), mode_w)

# 6. Fermer et liberer
dll.xisam_tcloselong(TACHE, tdf)
dll.xisam_end(TACHE)
```

---

## 5. Mode = code de reservation (F / P / R)

Le parametre `mode` de `treadlong` / `tpreadlong` (et des variantes write associees)
est **uniquement un code de reservation**. Il ne controle ni la direction de lecture,
ni le positionnement.

| Mode | Code | Description |
|------|------|-------------|
| `F` | 0x46 | **Forcee** -- force la lecture meme si le record est deja reserve par un autre process |
| `P` | 0x50 | **Partage** (shared) -- ne consomme PAS de slot de reservation. **A utiliser pour tout parcours en lecture seule** |
| `R` | 0x52 | **Reserve** -- lock record-by-record, pour le pattern read-then-update |

**Mode ouverture fichier** (`xisam_topenlong`) : `"P"` (partage) ou `"R"` (exclusif).
**Mode ecriture** (`xisam_twritelong`) : `"P"` (standard).

### Codes invalides interpretes par effet de bord

Les codes `S` (0x53), `D` (0x44), `G` (0x47), `E` (0x45) **ne sont PAS officiels**.
La DLL les interprete par effet de bord, typiquement comme alias de `R` (Reserve).
Consequence : un parcours en mode `S` consomme la table de reservations a chaque
lecture et plafonne les iterations a ~1003 enregistrements.

---

## 6. Positionnement via TDF.KEY

Le positionnement est porte par `TDF.KEY` (offset 261, 256 octets) :

- `TDF.KEY[0]` = lettre d'index (ex: `A`)
- `TDF.KEY[1..]` = valeur de cle (partielle ou complete)

Toute lecture retourne **le premier enregistrement >= cle demandee** (**Greater-or-Equal
implicite**). Si la cle exacte n'existe pas, la DLL glisse sur le voisin.

**Consequence pour update/delete** : le positionnement seul **ne suffit pas**. Toujours
verifier champ par champ apres la lecture que l'enreg positionne correspond exactement
a la cle cible. Sinon corruption silencieuse.

---

## 7. Detection de fin d'iteration

1. **Applicative** : comparer la valeur de la cle lue avec la cle attendue pour
   detecter une **rupture** (ex: `Ce` change -> arret logique).
2. **Physique** : `ret != 0`. Typiquement `ret=2` (EOF / enregistrement absent).

---

## 8. Table de reservations (~1003 slots)

La DLL maintient une table de reservations avec capacite ~1003 slots. Toute
lecture en mode `R` (ou alias invalide) consomme un slot, libere uniquement par
`tcloselong` ou `xisam_obj_tlibmlong`.

**Depassement** : `ret=46` observe empiriquement (voir aussi `0x2F=47` E_SHARE).
Symptome : parcours qui s'arrete prematurement a ~1003 records sans changement
de cle apparent (cas observe sur `a5f.dhfi` 7480 records).

**Regle pour les scripts d'ecriture** :
- Lectures prealables (parcours) -> mode `P` (pas de consommation).
- Lecture pour update/delete (read-then-write) -> mode `R`. Libere au `tcloselong`.

---

## 9. Codes d'erreur

| Code | Constante | Description |
|------|-----------|-------------|
| 0 | -- | Succes |
| 2 | E_EOF / E_RECABS | Fin de fichier / enregistrement absent |
| 3 | E_OVF | Fichier plein |
| 9 | E_EXIST | L'enregistrement existe deja (doublon de cle) -- **PAS un garde-fou d'unicite** : sur un index non unique la DLL accepte le doublon sans emettre ce code (mesure, cf. section 9) |
| 12 | -- | Erreur d'acces (tache non initialisee, TDF invalide) |
| 20 | E_ABSENT | Fichier introuvable |
| 47 | E_SHARE | Erreur de partage |

---

## 10. Pieges critiques

### Task ID doit etre c_ushort

```python
# CORRECT
tache = ctypes.c_ushort(15)

# INCORRECT -- passe un int Python, la DLL recoit un int32 -> erreur 12
tache = 15
```

### TDF cree in-place

Le buffer TDF est modifie par `xisam_topenlong`. Il doit etre cree dans le scope appelant, jamais retourne par une fonction (la copie par valeur perd les modifications).

### Record initialise a 0x20

Tous les octets non remplis doivent etre des espaces (0x20), pas des zeros.

### Encoding Windows-1252

Les champs texte dans les enregistrements sont en ANSI (codepage 1252). Utiliser :
```python
val_bytes = valeur.encode("windows-1252")
```

### Padding espaces

Les champs texte sont paddes a droite avec des espaces jusqu'a leur taille declaree dans la structure. Les valeurs plus longues sont tronquees.

### Positionnement GE implicite -- verification obligatoire

Le positionnement via `TDF.KEY` retourne toujours le premier enreg `>= cle demandee`.
Si la cle exacte n'existe pas, on se retrouve sur un voisin, potentiellement meme `Ce`
different. **JAMAIS** faire un `trewritelong` / `tdeletelong` sans verification
champ par champ -- sinon corruption silencieuse (un enreg voisin est ecrase ou
supprime a la place de la cible).

### Update / delete : pattern correct `tpreadlong R + verif + trewrite/tdelete`

```python
# 1. Charger TDF.KEY (lettre + valeur cle)
build_tdf_key(tdf, key_letter, key_fields, donnees, fields)

# 2. Lire avec reservation (mode R = Reserve, lock record-by-record)
mode_R = (ctypes.c_ubyte * 1)(0x52)
ret = dll.xisam_tpreadlong(TACHE, tdf, rec, SIZE, mode_R)
if ret != 0: return "Not found"

# 3. VERIFIER champ par champ que la cle correspond exactement
for field in key_fields:
    actual   = bytes(rec[field.offset : field.offset+field.size]).rstrip(b" ")
    expected = donnees[field.nom].encode("windows-1252").rstrip(b" ")
    if actual != expected:
        return "Not found (match approximatif refuse)"

# 4. OK : appliquer rewrite ou delete (pas de mode)
dll.xisam_trewritelong(TACHE, tdf, new_rec, SIZE)
# ou
dll.xisam_tdeletelong(TACHE, tdf, rec, SIZE)

# 5. Close (libere la reservation prise par tpreadlong R)
dll.xisam_tcloselong(TACHE, tdf)
```

### Ne pas confondre mode et direction

L'ancienne documentation presentait D/S/P/G/F comme des codes de direction
("Debut/Suivant/Precedent/..."). **C'etait faux**. Le parametre `mode` est
un code de reservation uniquement (F/P/R). Dans du code nouveau :
- lecture de parcours -> `P`
- lecture pour update/delete -> `R`
- ne PAS utiliser `S` / `D` / `G` / `E` (alias invalides interpretes comme `R`).

### Task slot peut rester bloque (fallback requis)

Apres un crash Python mi-session, le slot `xisam_begin(15)` peut rester dans un etat contradictoire : `begin` retourne -1 (deja alloue), `end` retourne -4 (non alloue). Implementer un fallback sur 2..16 pour etre robuste.
---

## 9. Ecarts MESURES entre cette doc et la DLL livree

Trois affirmations de cette page etaient fausses. Chacune a ete verifiee sur la DLL et
sur un fichier reel (une **copie**, jamais un fichier de production).

### `xisam_obj_tlibmlong` n'existe pas

La fonction **n'est pas exportee** par le `DhxIsam64.dll` livre -- verifie sur la table
d'exports. Elle n'a jamais ete appelee par les scripts du devkit, seulement documentee.

La liberation d'une reservation passe donc par `tcloselong` ou par
**`xisam_record_liball`**, qui lui est bien exporte (#241).

### `twritelong` ne garantit PAS l'unicite de cle -- le code 9 n'arrive pas toujours

**Mesure** : deux `insert` du **meme** enregistrement dans un dictionnaire de multichoix
(index non unique) renvoient tous deux `ret=0`. Le fichier contient ensuite **deux
enregistrements physiques identiques**, et **aucun code 9 n'a ete emis** (#240).

Le code `9 = E_EXIST` existe et a son sens, mais **il ne peut pas servir de garde-fou
d'unicite** : sur un index non unique la DLL accepte le doublon sans broncher. **La
deduplication est applicative** -- c'est a l'appelant de verifier l'absence avant
d'ecrire, par une lecture.

### `treadlong` et `tpreadlong` ne sont PAS interchangeables

Elles ont la meme signature, d'ou la formule « meme signature que treadlong » plus haut
-- mais la difference ne se limite pas a la reservation.

**Mesure**, lettre d'index posee **sans valeur de cle** (parcours sequentiel complet) :

| Fonction | Resultat |
|----------|----------|
| `xisam_treadlong` mode `P` | parcourt la table, 5 enregistrements lus sur 5 demandes |
| `xisam_tpreadlong` mode `P` | **echoue des le 1er appel** (`ret=2`) |

`tpreadlong` semble exiger une valeur de cle exploitable. **Pour un parcours a cle vide,
seul `treadlong` fonctionne** (#291).

---

## 10. La cle DECLAREE n'est pas forcement la cle PHYSIQUE

Les blocs `Keys` des structures JSON sont ecrits **a la main**. Une cle fausse ne se voit
pas a la lecture (les scripts de lecture parcourent sequentiellement) : elle se manifeste
au premier `update`/`delete`, par un echec incomprehensible.

**Le piege est le champ CE.** Il appartient a la cle physique de **certains index
seulement**. Mesure sur le dictionnaire standard, 959 index :

| | Nombre |
|---|---|
| index **sans** champ CE dans leurs champs de cle | **822 (86 %)** |
| index **avec** un champ CE | **137 (14 %)** |

Ce n'est donc pas une regle : **cela se lit dans le dictionnaire, index par index.** Deux
structures livrees par ce skill illustraient les deux cas -- la cle du menu M2 inclut bien
`Ce`, celle du multichoix ne l'incluait qu'a tort.

### Verifier une cle declaree

```
py .claude/skills/writing-isam-files/scripts/validate_structure.py \
    --path <structure.json> --probe-key <NomIndex> --file <copie.dhfi>
```

La sonde **s'auto-verifie** -- elle n'a pas besoin de connaitre la bonne reponse : elle lit
un enregistrement, releve ses **propres** valeurs de cle, se repositionne dessus, et
verifie qu'elle retombe sur le meme enregistrement. Verdict `CONFIRMEE` ou `REFUTEE`, et
une cle refutee rend la structure **invalide** (exit 1).

Exemple de refutation reelle : *demande `{Ce: 2, Nc: ACOMPTE}`, atterri sur
`{Ce: 1, Nc: ACOMPTE}`* -- le positionnement ignorait `Ce` et tombait sur le premier
enregistrement du meme `Nc`.

> Travailler sur une **copie** du `.dhfi` si le fichier est en production. La sonde ne
> fait que lire, mais la prudence sur ces fichiers ne coute rien.
