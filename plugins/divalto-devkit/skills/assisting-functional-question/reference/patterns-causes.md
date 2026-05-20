# Patterns de causes frequentes -- Catalogue

## Sommaire

- P1 -- Option activee, prerequis manquant
- P2 -- Filtrage par contexte utilisateur
- P3 -- Donnees historiques non reprises
- P4 -- Fourchettes par etab mal parametrees
- P5 -- Confidentialite / autorisation
- P6 -- Valeur silencieuse rejetee par le module check
- P7 -- Menu ou ecran cache conditionnellement
- P8 -- Ordre d'initialisation des globales
- P9 -- Surcharge (OverWrittenBy) dans un sous-projet
- P10 -- Moulinette / traitement de nuit pas execute
- Comment enrichir ce catalogue

---

Catalogue des **patterns de causes** recurrents pour les questions fonctionnelles
UC-110. Chaque pattern propose :
- une **signature** (symptome + declencheur)
- les **symboles techniques** a chercher
- le **diagnostic verifiable** (ce que le demandeur doit regarder)
- le **taux de succes estime** (a consolider dans le temps)

Utilisation : a l'etape 3 du skill, Claude parcourt ce catalogue et selectionne les
patterns compatibles avec le symptome decrit, puis confirme par un grep cible en X.13.

---

## P1 -- Option activee, prerequis manquant

**Signature** : "j'ai active l'option X dans le dossier, <Y> ne marche plus / pas comme avant"

**Cause** : l'option X a un prerequis (autre option SOC.EntCodN, parametre dossier,
ou option utilisateur) qui n'a pas ete activee.

**Symboles** : chercher tous les usages de l'option dans X.13 et identifier les
conditions `If SOC.EntCodN(X) = 2 And SOC.EntCodN(Y) = 2` ou `If Soc_Gerer_X And Soc_Gerer_Y`.

**Diagnostic** :
1. Lister les prerequis deduits du code standard
2. Verifier chacun dans la fiche dossier ERP

**Exemples reels** :
- `EntCodN(24)` (tiers par etab) requiert `EntCodN(22)` (etablissements)
- `EntCodN(48)` (commerciaux par etab) requiert `EntCodN(22)`
- `EntCodN(97)` (etab = societe compta) requiert parametrage DCPT

---

## P2 -- Filtrage par contexte utilisateur

**Signature** : "je ne vois plus les `X` dans le zoom / la liste"

**Cause** : le zoom filtre par un champ du contexte utilisateur (`MZ.Etb`, `MZ.Dos`,
`MZ.DosCpt`, commercial affecte) qui n'est pas initialise, ou les donnees n'ont pas
la valeur attendue.

**Symboles** : chercher le zoom (`<entite>_sql.dhsf` ou `a5rsrub.dhsq`) et reperer
les clauses `Where.*Equal_*` ou `$Join.<champ> = <MZ.*>`.

**Diagnostic** :
1. Requete SQL brute : les donnees existantes ont-elles la valeur du contexte ?
2. Valeur du contexte utilisateur : est-elle initialisee ?

**Exemples reels** :
- Zoom client filtre sur `Client.Etb = MZ.Etb` si `SOC.EntCodN(24) = 2`
- Zoom piece filtre sur `DHBENT.Dos = MZ.Dos`
- Zoom reglement filtre sur `REC.DosCpt = MZ.DosCpt`

---

## P3 -- Donnees historiques non reprises

**Signature** : "j'ai active X, je ne vois plus mes `<objets>` existants" + creer un nouveau les fait apparaitre

**Cause** : le flag / champ introduit par l'activation n'est pas renseigne sur les
enregistrements anterieurs. Le filtre du zoom / de la liste les exclut.

**Symboles** : chercher le `Init_<Entite>_Record` du module check : la ligne
`<Entite>.<champ> = <defaut>` indique la valeur qui aurait du etre reprise.

**Diagnostic** :
1. Requete SQL : `SELECT COUNT(*) FROM <table> WHERE <champ> = <valeur_defaut>`
2. Si > 0, script de reprise necessaire

**Exemples reels** :
- `EntCodN(24)` + clients avec `Etb = ' '`
- Gestion multi-devises introduite, enregistrements avec `Devise = ' '`
- Nouveau flag `FlgArchive`, enregistrements sans valeur

---

## P4 -- Fourchettes par etab mal parametrees

**Signature** : "l'option est active, l'user a son etab, mais le nouveau `<objet>` n'apparait toujours pas"

**Cause** : le zoom ne filtre pas juste par etab, il borne aussi via des fourchettes
numerotation (`ETS.Tiers1..Tiers2`, `Etab.ArticleD..ArticleF`). Sur un nouvel
etablissement, ces fourchettes sont souvent vides ou a `' '`.

**Symboles** : chercher `Etab.<X>1(*)`, `Etab.<X>2(*)`, `Give_ETS(Etab, code)`.

**Diagnostic** :
1. Ouvrir la fiche etablissement
2. Verifier les fourchettes : non vides, couvrant le code de l'objet concerne

**Exemples reels** :
- `ETS.Tiers1(1..3)` / `ETS.Tiers2(1..3)` pour clients (grtz002_sql.dhsp:247)
- Fourchettes articles dans `gafdd.dhsd`

---

## P5 -- Confidentialite / autorisation

**Signature** : "j'ai acces refuse", "ca dit que je n'ai pas le droit", "l'utilisateur X ne voit pas Y"

**Cause** : `SOC.ConfEnr(N) = Oui` + l'utilisateur n'a pas l'autorisation sur
l'etablissement / le dossier / la rubrique confidentielle.

**Symboles** : `G3_Protection(Conf)`, `Give_ETS(Etab, code)`, `SOC.ConfEnr(N)`,
`Check_Auth_<Entite>_<Action>`.

**Diagnostic** :
1. Consulter la fiche utilisateur : autorisations confidentialite
2. Cross-checker avec le ConfEnr actif

**Exemples reels** :
- Confidentialite etab : `grpp001.dhsp:5000-5006`
- Autorisations sur article : `gatmauth.dhsp`

---

## P6 -- Valeur silencieuse rejetee par le module check

**Signature** : "je saisis X, ca ne s'enregistre pas, pas de message d'erreur visible"

**Cause** : le module check `gttmchk<entite>.dhsp` a une procedure `Check_<Entite>_Field_<champ>`
qui retourne une erreur silencieuse (retour <> 0 sans message), ou la procedure
`PostInsert`/`PreInsert` rejette.

**Symboles** : dans le module check : `Check_<Entite>_Field_<X>`, `PreInsert_<Entite>`,
`PostInsert_<Entite>`.

**Diagnostic** :
1. Reproduire avec trace active (xWin /t)
2. Grep des `Mes_Alert` / `ret = 2` dans les procedures check

**Exemples reels** :
- Champ `Etb` vide rejete si `Soc_Gerer_Tiers_Etablissement`
- Code tiers hors fourchette rejete sans message

---

## P7 -- Menu ou ecran cache conditionellement

**Signature** : "l'ecran / menu n'est pas accessible", "l'option n'apparait pas dans le menu"

**Cause** : le menu / l'ecran est conditionnel a une option dossier ou a un droit
utilisateur.

**Symboles** : fichiers `.dhse` (menu) avec clauses `if SOC.EntCodN(N) = 2`,
`XmeSetAttribut(..., AV_CACHE)`.

**Diagnostic** :
1. Ouvrir le .dhse du menu concerne
2. Reperer les conditions de visibilite

---

## P8 -- Ordre d'initialisation des globales

**Signature** : "j'ai tout parametre correctement, ca ne marche que si je redemarre / reconnecte"

**Cause** : les globales (`MZ.Etb`, `MZ.Dos`, ...) sont initialisees dans une
procedure `*_Ap` qui n'est plus declenchee si le contexte existe deja en memoire.

**Symboles** : `DOS_1_Ap`, `ETB_1_Ap`, `Init_Mz`, `Find_Ets_Premier`.

**Diagnostic** :
1. Reconnexion / redemarrage
2. Lire la procedure d'init concernee pour comprendre l'ordre

**Exemples reels** :
- `divaltouserdrt_sql.dhsp:286` : DOS_1_Ap initialise MZ.Etb via Find_Ets_Premier

---

## P9 -- Surcharge (OverWrittenBy) dans un sous-projet

**Signature** : "sur ma version, ca fait X, mais sur la demo standard ca fait Y" / "personne ne sait pourquoi"

**Cause** : un fichier du sous-projet specifique surcharge le standard.

**Symboles** : grep `OverWrittenBy` dans le sous-projet client.

**Diagnostic** :
1. Chercher le fichier surcharge dans le repertoire specifique
2. Comparer avec le standard

---

## P10 -- Moulinette / traitement de nuit pas execute

**Signature** : "les X n'ont pas ete generes", "le batch n'a pas tourne"

**Cause** : la tache planifiee (scheduler ou batch) n'a pas tourne / a echoue /
a ete desactivee.

**Symboles** : `.dhst` (taches planifiees), `.log` de moulinettes, `mo<entite>.dhsp`.

**Diagnostic** :
1. Verifier le scheduler Divalto
2. Consulter les logs

---

## Comment enrichir ce catalogue

Apres chaque nouveau cas UC-110 resolu avec succes :
1. Identifier le pattern (Pn) ou en creer un nouveau
2. Ajouter un exemple reel (ticket, chat, date)
3. Affiner le diagnostic et les symboles si besoin

Objectif : couvrir 90% des questions recurrentes avec ~20 patterns.
