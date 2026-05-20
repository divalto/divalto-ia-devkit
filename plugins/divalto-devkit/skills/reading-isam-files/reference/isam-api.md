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

# xisam_tcloselong(ushort tache, byte[] tdf) -> ushort
dll.xisam_tcloselong.argtypes = [
    ctypes.c_ushort,
    ctypes.POINTER(ctypes.c_ubyte),
]
dll.xisam_tcloselong.restype = ctypes.c_ushort

# xisam_tpreadlong -- protected read (meme signature que treadlong)
# Retourne le premier enreg matchant la cle meme si la cle est "lache" (utile pour positionner au dernier)
dll.xisam_tpreadlong.argtypes = dll.xisam_treadlong.argtypes
dll.xisam_tpreadlong.restype = ctypes.c_ushort
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

**Mode ouverture fichier** : `"P"` (partage) ou `"R"` (exclusif).
**Mode ecriture** (`twritelong`) : `"P"` (standard).

### Codes invalides interpretes par effet de bord

Les codes `S` (0x53), `D` (0x44), `G` (0x47), `E` (0x45) **ne sont PAS officiels**.
La DLL les interprete par effet de bord, typiquement comme alias de `R` (Reserve).
Consequence : un parcours en mode `S` consomme la table de reservations a chaque
lecture et plafonne les iterations a ~1003 enregistrements. **Ne pas utiliser ces
codes dans du code nouveau**.

---

## 6. Positionnement via TDF.KEY

Le positionnement **n'est pas controle par le mode**. Il est porte par `TDF.KEY`
(offset 261, 256 octets) :

- `TDF.KEY[0]` = lettre d'index (ex: `A`)
- `TDF.KEY[1..]` = valeur de cle partielle ou complete

Toute lecture retourne **le premier enregistrement >= cle demandee** (**Greater-or-Equal
implicite**). Si la cle exacte n'existe pas, la DLL glisse sur le voisin.

### Iteration inverse

Pour positionner en fin de fichier : charger `0xFF` apres la cle logique.

```python
tdf[key_end] = 0xFF   # 1 octet suffit
ret = dll.xisam_tpreadlong(TACHE, tdf, record, record_size, b"P")
```

Continuer la lecture en mode `P` -- la DLL parcourt en sens decroissant tant que
les lectures sont successives sur le meme TDF.

### Parcours forward complet

Charger uniquement la lettre d'index dans `KEY[0]`, rien ensuite. Continuer en mode `P`.

---

## 7. Detection de fin d'iteration

Combiner deux tests :

1. **Applicative** : comparer la valeur de la cle lue avec la cle attendue pour
   detecter une **rupture** (ex: `Ce` change de 4 a 5 -> arreter).
2. **Physique** : `ret != 0`. Typiquement `ret=2` (EOF / enregistrement absent).

```python
while ret == 0 and record_matches_prefix(decoded, expected_key):
    process(decoded)
    ret = dll.xisam_treadlong(TACHE, tdf, record, record_size, b"P")
```

---

## 8. Table de reservations (~1003 slots)

La DLL maintient une table de reservations avec capacite ~1003 slots. Toute
lecture en mode `R` (ou alias invalide) consomme un slot, libere uniquement par
`tcloselong` ou `xisam_obj_tlibmlong`.

**Depassement** : `ret=46` observe empiriquement (voir aussi `0x2F=47` E_SHARE).
Symptome : parcours forward qui s'arrete prematurement a ~1003 records sans changement
de cle apparent (cas R-014 sur `a5f.dhfi` 7480 records).

**Regle** :
- Parcours lecture seule -> mode `P` (pas de consommation). Pas de plafond.
- Pattern read-then-update -> mode `R`. Liberer avant le prochain `R`.

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

### Positionnement GE implicite (piege critique pour update/delete)

Le positionnement via `TDF.KEY` n'est **jamais un match exact** : la DLL retourne
toujours le premier enregistrement `>= cle demandee`. Si la cle cible n'existe pas,
on se retrouve sur un voisin (potentiellement `Ce` different).

**Danger** : JAMAIS faire un `trewritelong` / `tdeletelong` sans verification champ
par champ apres positionnement -- sinon corruption silencieuse (un enreg voisin
est ecrase ou supprime a la place de la cible).

**Pattern correct pour update/delete** :
```python
# 1. Charger TDF.KEY (lettre + valeur cle)
# 2. Lire avec reservation
ret = dll.xisam_tpreadlong(TACHE, tdf, rec, size, b"R")  # mode R = Reserve
# 3. Verifier champ par champ que les valeurs cle correspondent exactement
if not record_matches_key_fields(rec, target_key_fields): abort()
# 4. trewritelong / tdeletelong
dll.xisam_trewritelong(TACHE, tdf, new_rec, size)
# 5. Close -> libere la reservation
dll.xisam_tcloselong(TACHE, tdf)
```

### Ne pas confondre mode et direction

L'ancienne documentation presentait D/S/P/G/F comme des codes de direction
("Debut/Suivant/Precedent/..."). **C'etait faux** (R-014). Le parametre `mode` est
un code de reservation uniquement (F/P/R). La direction est portee par la cle dans
TDF (0xFF en fin = iterer depuis la fin).

### Task slot peut rester bloque (fallback requis)

Apres un crash Python mi-session (sans `xisam_end`), le slot `xisam_begin(15)` peut rester dans un etat ou :
- `xisam_begin(15)` retourne -1 (tache deja allouee)
- `xisam_end(15)` retourne -4 (tache non allouee)

Contradictoire cote DLL. Solution appliquee dans `read_isam.py` : boucle d'acquisition sur 15, 14, 13, ..., 2, 16. Usage du slot reellement acquis pour `end`.
