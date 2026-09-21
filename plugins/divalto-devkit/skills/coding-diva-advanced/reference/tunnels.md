# Tunnels inter-modules (Ping/Pong)

DIVA n'a pas de multi-threading. La communication entre modules passe par les **tunnels**.

## Ping / Pong -- echange entre programmes

| Fonction | Direction | Description |
|----------|-----------|-------------|
| `Ping('nom', donnee)` | Envoi vers programme appele | Donnees pour ProgramCall |
| `PingReceive('nom', &variable)` | Reception (persistent) | Lire donnees envoyees par Ping |
| `PingReceiveAndDelete('nom', &var)` | Reception (one-shot) | Lire et supprimer |
| `Pong('nom', donnee)` | Retour vers programme appelant | Donnees de retour |
| `PongReceive('nom', &variable)` | Reception retour | Lire donnees Pong |

### Pattern d'initialisation zoom via PingReceive

```
If PingReceive('ZECHANGE', MZ) <> 0 Or \
   PingReceive('ZOOMPAR', G7.ZOOMPAR) <> 0
    ZOOM.Ok = 'N'
    PReturn
EndIf
```

Les zooms recoivent leurs parametres d'initialisation via `PingReceive`. Si la reception echoue, le zoom se ferme (`ZOOM.Ok = 'N'`).

---

## PingLocal -- echange intra-programme

| Fonction | Description |
|----------|-------------|
| `PingLocal('nom', donnee)` | Envoi local (meme process) |
| `PingLocalReceive('nom', &var)` | Reception locale |
| `PingLocalReceiveAndDelete('nom', &var)` | Reception et suppression |

PingLocal est plus rapide que Ping/Pong car il ne passe pas par le mecanisme inter-processus.

---

## ProgramCall -- appel inter-programmes

```
; Envoi des donnees
Ping('MONPARAM', valeur)

; Appel du programme
ProgramCall("MONPROG.dhop")

; Reception du retour
PongReceive('MONRETOUR', resultat)
```

Sequence complete :
1. `Ping()` pour envoyer les parametres
2. `ProgramCall()` pour lancer le programme cible
3. Le programme cible lit via `PingReceive()`, traite, et retourne via `Pong()`
4. L'appelant lit le retour via `PongReceive()`

> **Cette sequence est incomplete des que la cible est un programme ERP.** Un programme du
> standard ne lit pas seulement vos parametres : il reconstruit tout son **contexte metier**
> -- dossier, etablissement, echange -- a partir de ce que vous lui envoyez. Voir
> « Le contrat de contexte » plus bas : c'est le piege le plus couteux de cette page, et il
> **compile**.

### Le nom du programme porte TOUJOURS l'extension `.dhop`

**Regle : ecrire `ProgramCall('monprogramme.dhop')`, jamais `ProgramCall('monprogramme')`.**

La documentation native -- `Long ProgramCall (programme, [mode_affichage], [mode_appel],
[wpfNoClient])` -- ne dit rien de l'extension. Le standard, lui, est unanime :

| Appels de `ProgramCall` dans le standard X.13 | Nombre |
|---|---|
| Sites d'appel vivants | **38** |
| dont nom **litteral AVEC** extension | **24** |
| dont nom **litteral SANS** extension | **0** |
| dont nom passe par une **variable ou une expression** | **14** |

La **casse** de l'extension varie (`.dhop`, `.Dhop`) ; sa **presence**, non.

> **Ce qui n'est pas etabli** : que le nom nu *echoue*. Personne ne l'a mesure, la doc native
> est muette, et les 14 appels qui passent une variable transportent une valeur qu'on ne peut
> pas lire -- leurs fabricants de noms (`A5_Programme_Tunnel`, une constante de la famille
> logistique) vivent dans des modules proteges ou hors du graphe. La regle ci-dessus est une
> regle **de conformite au standard**, pas un theoreme sur le runtime.

### Le contrat de contexte -- ce qu'il faut remplir avant le `Ping`

**Le piege** : un enchainement qui ne renseigne que `.Tunnel` compile a 0 erreur, lance bien
le programme cible, et celui-ci demarre avec un **dossier et un etablissement vides**.

```diva
; MAUVAIS -- compile, lance, et la cible perd son contexte metier
G3XQ = ' '
G3XQ.Tunnel = TRUE
Ping('XQ', G3XQ)
ProgramCall('xxx.dhop')
```

**Pourquoi.** Tout programme du standard entre par une procedure `Hql_Init`, portee par le
module de domaine (`gtqc000`, `ppqcbas000`, `cctcq000`...). Elle a **deux branches** :

```diva
If PingReceive("XQ", G3XQ) = 0 and PingReceive('ZECHANGE_GTPCE', GTPCE) = 0
    MZ.ECHANGE = G3XQ.ECHANGE       ; branche TUNNEL : MZ est rempli DEPUIS le XQ recu
    MZ.DOS     = G3XQ.DOS
    MZ.ETB     = G3XQ.ETB
    Charger_DosCommun()
    PingLocal("Batch", 2)
Else
    If Np = 1 And (PingReceive("zechange", MZ) <> 0 or ...)
        ProgramExit                 ; <-- sortie SILENCIEUSE
    EndIf
    G3XQ            = ' '           ; branche NON-TUNNEL : le programme se fabrique
    G3XQ.TUNNEL     = Tunnel_Init(C_APPLIC_DAV)    ; son propre XQ depuis MZ et SYSTEM
    G3XQ.LOGDH      = Time(7)
    G3XQ.USER       = SYSTEM.USER
    G3XQ.ACCES      = SYSTEM.ZACCES
    G3XQ.DOS        = MZ.DOS
    G3XQ.Etb        = MZ.Etb
    G3XQ.VERSION    = Version
    G3XQ.versionExt = Version_ERP_UX & ' ' & Indice_ERP_UX
    G3XQ.JOB        = 0
    G3XQ.ECHANGE    = MZ.ECHANGE
    G3XQ.PRG        = SYSTEM.ZNOMPROG
    PingLocal("Batch", 0)
EndIf
```

Envoyer un `XQ` dont seul `.Tunnel` est renseigne fait **reussir** le `PingReceive` : le
programme prend la branche tunnel et recopie du **vide** dans `MZ`.

**La branche `Else` EST la specification a reproduire.** C'est elle qui enumere les champs que
le programme attend, et c'est le programme cible lui-meme qui l'ecrit.

> **Mesure (X.13).** Cette forme a deux branches est presente a l'identique dans les **10**
> modules de domaine du standard : `gtqc000`, `ggqc000`, `rtqc000`, `wmqc000`, `gaqc000`,
> `cctcq000`, `rctcq000`, `ppqcbas000`, `pvqc000`, `grqc000`. Les **10** contiennent un
> `ProgramExit` dans leur branche de secours.

#### `Tunnel` n'est PAS un booleen

`Tunnel` est declare **`2,0`** -- un numerique a deux chiffres. Il porte un **code d'action**,
pas un drapeau.

- Le standard l'initialise par `Tunnel_Init(C_APPLIC_<domaine>)` -- une valeur applicative.
- Les emetteurs reels y mettent une valeur qui *veut dire quelque chose* : on lit
  `G3XQ_Print.Tunnel = 1` suivi du commentaire `;Imprimer piece`.

**Consequence** : `G3XQ.Tunnel = TRUE` ne "rate" pas -- il ecrit **1**, qui est un code
d'action valide. Le programme cible peut donc faire **autre chose** que ce que vous vouliez,
ce qui se diagnostique bien plus mal que ne rien faire du tout.

#### La liste des champs depend du domaine -- il faut aller la lire

Elle n'est pas universelle. Ecarts releves entre les 10 modules :

| Ecart | Ou |
|---|---|
| `DosCpt` en plus | `cctcq000`, `rctcq000` |
| `NomPrg8` au lieu de `Prg` | `rctcq000` |
| `User` et `Prg` **mis en commentaire** | `ppqcbas000` |
| Second `PingReceive` obligatoire (`ZECHANGE_GTPCE`) | `gtqc000`, `ggqc000`, `pvqc000` |

**Methode** : avant d'ecrire l'appel, ouvrir le `Hql_Init` du domaine de la cible et recopier
la liste de sa branche non-tunnel. C'est la seule source qui ne se trompe pas, parce que c'est
celle que la cible executera.

#### Deux facons supportees de lancer -- et une facon de tout perdre

| Mode | Ce qu'on envoie | Quand |
|---|---|---|
| **XQ complet** | `Ping('XQ', <XQ integralement rempli>)`, plus `Ping('ZECHANGE_GTPCE', GTPCE)` selon le domaine | on veut **piloter** la cible : code d'action, criteres |
| **zechange** | `Ping('zechange', MZ)` -- la cible se fabrique son XQ depuis `MZ` | on veut juste qu'elle **demarre dans le bon contexte** |

Les deux se combinent : la famille logistique envoie `Ping("XQ", G3XQ)` **et**
`Ping("zechange", MZ)` **et** `Ping("ACTION", "<nom>")` avant son `ProgramCall`.

**Ce qu'il ne faut pas faire, c'est ni l'un ni l'autre.** La branche de secours de `Hql_Init`
fait alors `ProgramExit` : la cible **sort sans un message**, et l'appelant reprend la main
comme si tout s'etait bien passe.

---

## Services Harmony (Web Services DIVA)

Les services web DIVA utilisent les tunnels Ping/Pong :

```
; Cote service (reception)
PingReceive('WebServiceAction', action)
PingReceive('WebServiceParameters', params)

; Cote service (retour)
Pong('WebServiceStatus', '0')       ; 0 = OK
Pong('WebServiceResult', resultat)
```

`ServiceMode` retourne `3` quand invoque par un web service, `6` en mode zoom service.

### Alternative : GetEnv

```
params = GetEnv("HARMONYSERVICEPARAMETRES")
HmpSeek(params, "monparam", valeur)
```
