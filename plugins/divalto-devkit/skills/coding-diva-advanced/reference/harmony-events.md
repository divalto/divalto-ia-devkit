# Harmony -- Evenements et codes touches

Le record `Harmony` expose les evenements clavier, souris et systeme dans les ecrans (Zooms). Les champs sont lus dans les procedures d'arret (`ZoomArret`).

## Champs evenementiels

| Champ | Type | Role |
|-------|------|------|
| `Harmony.Key` | X | Code touche pressee (code Harmony, pas ANSI) |
| `Harmony.Arret` | integer | Identifiant du point d'arret (champ ou custom 5001, 8002...) |
| `Harmony.DataArret` | integer | Type de breakpoint (8002 = clic liste) |
| `Harmony.Sourisbout` | code | Bouton souris (`RIGHT_BUTTON`, `LEFT_BUTTON`) |
| `Harmony.Sourisclic` | code | Type de clic (`DOUBLE_CLICK`, `SINGLE_CLICK`) |
| `Harmony.Retour` | code | Action retour (`XMENEXT_SIMULATION_TOUCHE`) |
| `Harmony.Cplretour` | code | Touche a simuler (`K_F8`, `K_F7`...) |
| `Harmony.DataModif` | boolean | Flag record modifie |
| `Harmony.PopupMenu` | | Declenchement menu contextuel |

## Codes touches courants

```
K_F1 .. K_F16
K_SHIFT_F1 .. K_SHIFT_F16
K_CTRL_F1 .. K_CTRL_F16
K_ALT_F1 .. K_ALT_F16
```

## Pattern ZoomArret

```
ZoomArret()
    Switch Harmony.Key
        Case K_F8
            Zoom_Call(Harmony.Arret)    ; Ouvrir sous-zoom sur le champ
        Case Harmony.DataArret = 8002   ; Clic dans la liste
            If Harmony.Sourisbout = RIGHT_BUTTON
                ; Menu contextuel
            ElsIf Harmony.Sourisclic = DOUBLE_CLICK
                Harmony.Retour = XMENEXT_SIMULATION_TOUCHE
                Harmony.Cplretour = K_F8
            EndIf
    EndSwitch
```

### Simulation de touche

Pour simuler un appui clavier (ex: ouvrir un sous-zoom au double-clic) :

```
Harmony.Retour = XMENEXT_SIMULATION_TOUCHE
Harmony.Cplretour = K_F8    ; touche a simuler
```

## Timer dans les ecrans

```
XmeSetTimer(Delay, Code, Shift, Ctrl)   ; Lance un timer pendant XmeConsult
; Delay en ms, simule un appui clavier a intervalles reguliers
; Delay = 0 pour arreter le timer
```

Le timer declenche un evenement clavier a intervalles reguliers, utile pour le rafraichissement automatique d'ecrans de monitoring.
