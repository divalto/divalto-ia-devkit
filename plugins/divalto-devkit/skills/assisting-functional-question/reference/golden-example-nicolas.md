# Exemple golden -- Cas Nicolas (2026-04-23)

## Sommaire

- Entree (texte chat recu)
- Etapes de traitement (5 etapes attendues)
- Sortie golden (reponse chat-ready de reference)
- Scoring sur les 7 CA du UC-110
- Pieges deja rencontres (anti-patterns a eviter)

---

Cet exemple sert **a la fois** de specification de sortie du skill (UC-110 CA1-CA7)
et de cas de test pour toute modification du skill. Toute regression detectee
ici doit etre corrigee avant de merger une modification.

---

## Entree

Copie d'ecran de chat interne (Teams), 2026-04-23, Nicolas SINGER 09:03 :

> je suis bloque sur quelque chose que personne a fait gerer les tiers par etablissement
> on a pas eu le cas recemment quand j'active l'option dans le dossier je ne vois plus mes clients
> et quand j'en cree un il n'apparait pas dans le zoom client
> il doit me manquer une info
> j'ai regarde sur confluence et la c'est le drame
> si tu as une info ca serait super cool

---

## Etapes de traitement (ce que le skill doit faire)

### Etape 1 -- Comprehension

Trois elements cles :
1. **Option activee** : "gestion des tiers par etablissement" au niveau dossier
2. **Symptome 1** : clients existants disparus du zoom apres activation
3. **Symptome 2** : client cree apres activation invisible dans le zoom

Besoin d'une precision ? **Non** -- la question est autosuffisante. Ne pas
demander "quel dossier", "quel utilisateur" : ces details n'influencent pas
le diagnostic standard.

### Etape 2 -- Traduction metier -> technique

Via le lexique (`reference/lexique-metier-technique.md`) :

| Concept metier | Symbole technique |
|----------------|-------------------|
| "option dans le dossier" | `SOC.EntCodN(N) = 2` (codage standard) |
| "gestion des tiers par etablissement" | `Soc_Gerer_Tiers_Etablissement` -> `SOC.EntCodN(24) = 2` |
| prerequis implicite | `Soc_Gerer_Etablissements` -> `SOC.EntCodN(22) = 2` |
| "zoom client" | `a5rsrub.dhsq` + programmes de zoom clients (RS partage) |
| "creer un client" | module check `gttmchkcli.dhsp` / `gttmchkpro.dhsp` / `gttmchkfou.dhsp` (selon type de tiers) |
| contexte utilisateur | `MZ.Etb`, `MZ.Dos` |
| autorisation par etab | `Give_ETS(Etab, code)`, `ETS.Tiers1(*)`, `ETS.Tiers2(*)` |
| confidentialite | `SOC.ConfEnr(1)`, `G3_Protection(ETS_loc.Conf)` |

### Etape 3 -- Investigation ciblee

Grep parallele (budget : 4-6 grep en un seul appel) :

1. `Soc_Gerer_Tiers_Etablissement` dans X.13 -> usages et definition
2. `SOC.EntCodN(24)` + `SOC.EntCodN(22)` -> lire les tests de prerequis
3. `Client.Etb = etb` dans `a5rsrub.dhsq` -> localiser le filtre zoom
4. `Give_ETS` + `ETS.Tiers1` / `ETS.Tiers2` -> fourchettes par etab
5. Dans les modules check `gttmchk*.dhsp` : ligne `FOU.Etb = MZ.Etb` / `PRO.Etb = MZ.Etb`

Chaque grep remonte un ou deux file:line critiques. Budget total ~5 min.

### Etape 4 -- Classement des causes par probabilite

Patterns connus (cf. `reference/patterns-causes.md`, a venir) :

| Probabilite | Cause | Diagnostic verifiable |
|-------------|-------|----------------------|
| **Haute** | Clients existants sans `Etb` renseigne | Requete SQL : `SELECT COUNT(*) FROM CLIENT WHERE DOS='xxx' AND ETB=' '` -- si > 0, c'est la cause |
| **Haute** | Prerequis `SOC.EntCodN(22)=2` non active | Aller dans parametrage dossier, onglet Etablissements : est-il actif ? |
| **Moyenne** | Utilisateur sans `MZ.Etb` defini | Consulter la table Utilisateur : champ Etb renseigne ? Sinon `DOS_1_Ap` dans `divaltouserdrt_sql.dhsp:286` prend le 1er ETS |
| **Moyenne** | Fourchettes `ETS.Tiers1/Tiers2` mal parametrees | Consulter la fiche Etablissement : fourchettes couvrant le code client ? |
| **Basse** | Confidentialite active bloquant l'acces | `SOC.ConfEnr(1) = Oui` ET utilisateur sans autorisation ETS |

### Etape 5 -- Formatage chat-ready

Contraintes :
- **< 40 lignes** au total
- Paragraphe d'introduction (< 3 lignes)
- 4-5 causes numerotees, chacune 2-4 lignes max avec `fichier:ligne`
- Check-list finale ordonnee (4-6 items)
- **Pas** de couche strategique / tactique / technique
- Langue : francais, registre collegial (tutoiement possible, "Nicolas" nomme)
- Pas de disclaimer X.12, pas de balises markdown lourdes (#, ##)

---

## Sortie golden

> Salut Nicolas, j'ai fouille le code standard, voila ce que j'ai trouve.
> La "gestion des tiers par etablissement" c'est `SOC.EntCodN(24) = 2` dans le parametrage
> dossier. Deux points qui expliquent probablement tes deux symptomes :
>
> **1) Tu ne vois plus tes clients existants**
> C'est normal. Des que l'option est activee, le zoom filtre sur
> `Client.Etb = etb_courant` (cf. `a5rsrub.dhsq:758-766`, et `grtz002_sql.dhsp`).
> Tous les clients crees *avant* l'activation ont `Etb = ' '` (vide), donc ils sortent
> du filtre. Il faut faire une reprise SQL pour leur affecter un etablissement, sinon
> ils restent invisibles.
>
> **2) Les nouveaux clients n'apparaissent pas**
> Quatre choses a verifier dans l'ordre :
>
> - **`SOC.EntCodN(22) = 2`** doit aussi etre a 2 (gestion des etablissements tout court).
>   C'est un prerequis de `EntCodN(24)` -- sans ca tout le mecanisme est inoperant.
>   Regarde `grpp001.dhsp:9235` ou `grtm000.dhsp:1196`, le code teste toujours les deux.
> - **`MZ.Etb` de ton utilisateur** : a la creation, le module check fait
>   `FOU.Etb = MZ.Etb` (cf. `gttmchkfou.dhsp:3546`, idem pro et cli). Si ton utilisateur
>   n'a pas d'etablissement par defaut, le client est cree avec Etb vide -> invisible.
> - **Fourchettes tiers sur l'etablissement (table ETS)** : le zoom charge
>   `Etab.Tiers1(*)` / `Etab.Tiers2(*)` et borne sa selection
>   (cf. `grtz002_sql.dhsp:247-253`). Si les fourchettes ne sont pas configurees sur
>   l'etablissement, ou mal parametrees, ton nouveau client sort des bornes. C'est
>   souvent ca qu'on oublie.
> - **Confidentialite** : si `SOC.ConfEnr(1) = Oui`, il faut aussi que l'utilisateur ait
>   le droit sur l'etablissement (cf. `grpp001.dhsp:5000-5006`, `Give_ETS` + `G3_Protection`).
>
> Ma check-list dans l'ordre :
> 1. `SOC.EntCodN(22) = 2` ? (sinon c'est mort avant de commencer)
> 2. Ton user a-t-il un Etb par defaut ?
> 3. L'etablissement a-t-il des fourchettes Tiers1/Tiers2 correctes ?
> 4. En SQL brut, ton nouveau client a-t-il bien un Etb renseigne ?
>
> Si ca ne debloque pas je regarde avec toi.

---

## Scoring sur les 7 CA du UC-110

| CA | Cible | Realise |
|----|-------|---------|
| CA1 | < 40 lignes | 38 lignes |
| CA2 | 1-5 causes classees par probabilite | 5 causes (haute/moyenne/basse implicite) |
| CA3 | fichier:ligne cliquable pour chaque cause | `a5rsrub.dhsq:758-766`, `grpp001.dhsp:9235`, `gttmchkfou.dhsp:3546`, `grtz002_sql.dhsp:247-253`, `grpp001.dhsp:5000-5006` |
| CA4 | check-list actionnable ordonnee | 4 items ordonnes du plus critique au plus specifique |
| CA5 | cycle < 5 min | ~5 min (5 grep + 3 read) |
| CA6 | precision ciblee si ambigu | Pas de precision demandee (question autosuffisante) |
| CA7 | prerequis implicites signales | `EntCodN(22)` marque comme prerequis de `EntCodN(24)` |

Verdict : **7/7 CA satisfaits**.

---

## Pieges deja rencontres (anti-patterns)

Liste enrichie au fil des cas traites :

- **Piege 1** : repondre sans citer de `fichier:ligne`. La credibilite de la reponse
  vient de la verifiabilite. Toujours citer.
- **Piege 2** : mentionner un symbole sans signaler le prerequis standard
  (ex: `EntCodN(24)` sans dire que `EntCodN(22)` doit aussi etre a 2). Violation CA7.
- **Piege 3** : produire un livrable markdown formel avec titres `#`/`##`.
  Pas chat-ready. Utiliser seulement `**gras**` et listes.
- **Piege 4** : demander plus d'une precision a la fois. Choisir la plus utile et
  avancer sinon on sature le collegue.
- **Piege 5** : ne lister que les causes techniques. Les causes parametrage
  (fourchettes ETS, confidentialite) sont souvent le vrai blocage.
