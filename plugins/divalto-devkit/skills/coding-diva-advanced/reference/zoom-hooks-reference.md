# Reference des hooks Zoom* -- codes retour et semantique

## Contenu

- Principe
- Grille de codes retour (zooms a operation simple)
- Couverture validee
- Hooks non couverts -- consulter la doc Divalto interne
- Pattern d'utilisation
- Anti-patterns connus

---

## Principe

Les procedures `Zoom*` du framework Divalto (`ZoomCreation`, `ZoomDuplication`, `ZoomModification`, `ZoomAbandon`, `ZoomSuppression`, `ZoomImpression`, ...) sont des **hooks** : declarees `Public Procedure` dans le module standard du zoom (ex: `gtuz021.dhsp`), elles sont invoquees par le framework au moment approprie (clic bouton, action utilisateur).

Une surcharge `OverWrite` peut redefinir ces hooks pour ajouter du comportement specifique sans modifier le standard. Pour qu'une surcharge **fonctionne au runtime**, il faut connaitre **les codes retour valides** que la procedure doit positionner dans le flag de sortie (`Zoom.Ok` typiquement).

> **Limite documentaire** -- les codes retour exacts dependent du hook et ne sont pas tous documentes officiellement. Cette reference capture l'expertise empirique terrain et invite a remonter les decouvertes (RETEX SUGGESTION-DOC) pour completer la grille au fil du temps.

---

## Grille de codes retour (zooms a operation simple)

Pour les hooks d'**action utilisateur simple** (`ZoomCreation`, `ZoomDuplication`, `ZoomModification`, `ZoomSuppression`, `ZoomAbandon`), le flag de retour `Zoom.Ok` accepte (vraisemblablement) les codes suivants :

| Code | Semantique | Effet runtime | Message utilisateur |
|------|------------|---------------|---------------------|
| `'O'` | Acceptation (defaut) | L'action standard se poursuit | Aucun |
| `'N'` | Refus avec message | L'action est interdite | Message standard "interdit(e)" affiche |
| `'I'` | Refus silencieux | L'action est interdite | Aucun (le specifique a deja gere l'UX) |
| `'C'` | Saute la cle (CreateOnly) | Voir doc Divalto interne -- cas particulier | Variable |

**Niveau de confiance** :
- `'O'` et `'N'` : confiance forte, comportement par defaut documente cote Divalto.
- `'I'` et `'C'` : confiance moyenne, derive empirique (cf. couverture validee).

Le flag est consulte par le framework **apres** le retour de la procedure surchargee. La surcharge a donc la responsabilite de positionner le flag avant de sortir.

---

## Couverture validee

Hooks confirmes terrain ce 2026-05-04 (RETEX R-013, projet ClaudeIntegration sur ERP X.13 v2026_erpX13_p223a) :

| Hook | Codes testes | Status |
|------|--------------|--------|
| `ZoomCreation` | `'O'`, `'N'` | Conforme a la grille -- `'N'` bloque la creation avec message "Creation interdite" |
| `ZoomDuplication` | `'N'` | Conforme a la grille -- `'N'` bloque la duplication avec message "Duplication interdite" |

Hypothese de travail (a confirmer cas par cas) : les hooks `ZoomCreation` et `ZoomDuplication` partagent la meme grille `O/N/I/C`. Par analogie, `ZoomModification` et `ZoomSuppression` devraient suivre la meme grille -- a valider terrain.

---

## Hooks non couverts -- consulter la doc Divalto interne

Hooks dont la grille de codes retour reste a documenter empiriquement :

- `ZoomAbandon` -- cas connu de divergence (R-012) : `Zoom.Ok = 'I'` ne bloque PAS l'abandon malgre l'analogie avec les autres hooks. Le mecanisme reel de la procedure `ZoomAbandon` differe et n'est pas (encore) accessible via cette reference. Solution actuelle : utiliser une `MessageBox` interactive avant de laisser le standard executer son abandon -- voir [overwrite-pattern.md](overwrite-pattern.md) section "Pattern canonique de surcharge de procedure".
- `ZoomImpression` -- non teste
- `ZoomEnvoiMail` -- non teste
- `ZoomDebut`, `ZoomFin`, `ZoomArret` -- hooks de cycle de vie, semantique differente (pas de "refus")
- `ZoomActif`, `ZoomChange` -- hooks de selection / changement de focus
- Hooks transverses (`Pre/PostInsert`, `Pre/PostUpdate`, `Pre/PostDelete`, hooks de tarification, calcul...) -- meme principe mais flag de retour different selon le module

**Pour ces hooks** : consulter la documentation Divalto interne (Confluence partenaire, support Divalto via myService N1). Toute decouverte terrain merite une remontee RETEX (categorie SUGGESTION-DOC, sources type "test runtime sur version ERP X.NN") afin d'enrichir cette reference.

---

## Pattern d'utilisation

```diva
; Surcharge minimale ZoomDuplication interdisant la duplication
Procedure ZoomDuplication
BeginP
    Standard.ZoomDuplication()    ; appel standard d'abord (cf. overwrite-pattern.md)
    Zoom.Ok = 'N'                 ; -> "Duplication interdite" affiche par le framework
EndP

; Surcharge ZoomCreation avec validation conditionnelle
Procedure ZoomCreation
BeginP
    Standard.ZoomCreation()
    if Zoom.Ok = 'O'              ; le standard accepte
        if T013.PaysCode = 'XX'   ; controle metier specifique
            Zoom.Ok = 'I'         ; refus silencieux apres avoir affiche notre propre message
            MessageBox("Pays XX interdit pour ce client.")
        endif
    endif
EndP
```

Voir [overwrite-pattern.md](overwrite-pattern.md) sections "Declaration des procedures surchargees" et "Pattern canonique de surcharge de procedure" pour les conventions structurelles.

---

## Anti-patterns connus

1. **Deduire un code retour par analogie sans validation runtime** -- chaque hook peut avoir sa propre grille. Un `'I'` qui marche sur `ZoomCreation` peut ne rien faire sur `ZoomAbandon` (cas R-012). Toujours tester sur la version ERP cible.
2. **Omettre `Standard.<hook>()`** -- meme si le standard est vide aujourd'hui, ca cree une dette de compatibilite ascendante (cf. [overwrite-pattern.md](overwrite-pattern.md) "Pattern canonique de surcharge de procedure", regle 1).
3. **Positionner le flag de retour AVANT `Standard.<hook>()`** -- le standard ecrasera la valeur ou se comportera de maniere imprevue selon le hook.
4. **Compter sur le compilateur pour signaler un mauvais code retour** -- le compilateur accepte `Zoom.Ok = 'Z'` (chaine arbitraire). Le bug est silencieux au runtime.
