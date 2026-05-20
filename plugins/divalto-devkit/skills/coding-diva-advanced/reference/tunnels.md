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
