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

Revision 2026-04-22 (R-014) : la semantique du parametre `mode` a ete corrigee --
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

# xisam_tpreadlong -- protected read, meme signature que treadlong
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
de cle apparent (cas R-014 sur `a5f.dhfi` 7480 records).

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
| 9 | E_EXIST | L'enregistrement existe deja (doublon de cle) |
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
("Debut/Suivant/Precedent/..."). **C'etait faux** (R-014). Le parametre `mode` est
un code de reservation uniquement (F/P/R). Dans du code nouveau :
- lecture de parcours -> `P`
- lecture pour update/delete -> `R`
- ne PAS utiliser `S` / `D` / `G` / `E` (alias invalides interpretes comme `R`).

### Task slot peut rester bloque (fallback requis)

Apres un crash Python mi-session, le slot `xisam_begin(15)` peut rester dans un etat contradictoire : `begin` retourne -1 (deja alloue), `end` retourne -4 (non alloue). Implementer un fallback sur 2..16 pour etre robuste.
