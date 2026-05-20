# Format chat-ready -- Specification de sortie

## Sommaire

- Principes (contraintes dures : taille, format, destinataire)
- Structure (squelette de la reponse)
- Elements autorises / interdits
- Template Claude (4 questions internes avant l'affichage)
- Exemples courts (bon / mauvais)

---

Forme obligatoire de la reponse finale produite par `assisting-functional-question`.
Contraste avec UC-100 (`analyzing-diva-request`) qui produit un livrable markdown
formel a 3 couches.

---

## Principes

1. **< 40 lignes au total** (CA1 de UC-110). Si ca ne tient pas, le diagnostic est
   trop large -- restreindre au plus probable.
2. **Pas de fichier en sortie**. La reponse est affichee directement dans la conversation.
   Le collaborateur copie / paraphrase pour repondre au demandeur.
3. **Chat-ready** : le destinataire est un collegue qui lit dans Teams / Slack /
   mail interne. Pas de cartouche administratif, pas de date, pas de metrique.
4. **Verifiabilite systematique** : chaque cause doit pointer au moins un
   `fichier:ligne`.
5. **Classement par probabilite** : le collegue doit savoir par quoi commencer.

---

## Structure

```
Salut <Prenom>, <1 phrase de cadrage>. <1 phrase de synthese>.

**1) <Symptome 1 reformule>**
<1 paragraphe : cause probable n.1 + reference code + action de verification>

**2) <Symptome 2 reformule, ou Cause 2 si 1 seul symptome>**
<idem>

<... 3-5 causes au total>

Check-list dans l'ordre :
1. <Verification la plus critique>
2. <...>
3. <...>
4. <Verification la plus specifique>

<Ligne de conclusion proposant un suivi>.
```

---

## Elements autorises / interdits

### Autorises
- `**gras**` pour les noms de symboles et les titres de causes
- Backticks pour le code : `SOC.EntCodN(22) = 2`, `fichier.dhsp:123`
- Listes numerotees ou a puces
- Adressage direct au destinataire ("Salut X", "tu", "toi")
- Questions ouvertes en conclusion ("Si ca ne debloque pas, je regarde avec toi.")

### Interdits
- Titres `#`, `##`, `###`
- Tableaux
- Blocs de code multi-lignes ``` ``` ```
- Diagrammes Mermaid
- Disclaimers "Snapshot X.12", "[CONFIRME X.13]" (invisible pour le destinataire)
- Chemins absolus (`C:\Developpements...`) : prefere `fichier.dhsp:ligne`
- Mentions meta ("voici une analyse structuree", "l'analyse comporte...")
- Mention de l'outillage ("apres interrogation Neo4j", "via le skill X")
- Jargon pipeline ("request.json", "candidates_x12", "claims", etc.)

---

## Template Claude -- invite interne

Quand Claude formule la reponse finale, il doit se poser ces 4 questions
(internes, **pas** imprimees dans la sortie) :

1. Est-ce que le destinataire peut copier-coller cette reponse sans la reformuler
   vers son collegue ? -> si non, trop formel.
2. Est-ce que chaque cause est verifiable independamment ?
   -> si non, ajouter une action concrete (requete SQL, chemin ERP, lecture fichier).
3. Est-ce que la premiere cause listee est la plus probable ?
   -> sinon reordonner.
4. Est-ce que la reponse depasse 40 lignes ?
   -> si oui, retirer la cause la moins probable ou condenser.

---

## Exemples courts

### Bon

> Salut Nicolas, c'est normal : l'option `SOC.EntCodN(24) = 2` active un filtre
> `Client.Etb = etb_courant` sur le zoom (cf. `a5rsrub.dhsq:758`).
>
> **1) Tes clients existants disparaissent**
> Ils ont `Etb = ' '`, le filtre les exclut. Reprise SQL necessaire.
>
> **2) Tes nouveaux clients n'apparaissent pas**
> Trois causes a verifier :
> - `SOC.EntCodN(22) = 2` prerequis -- sans, tout tombe (`grpp001.dhsp:9235`)
> - `MZ.Etb` de l'user pas initialise -- `gttmchkfou.dhsp:3546` fait `.Etb = MZ.Etb`
> - Fourchettes `ETS.Tiers1/Tiers2` mal parametrees (`grtz002_sql.dhsp:247`)
>
> Check-list :
> 1. Option etablissement (22) active ?
> 2. User a un Etb ?
> 3. SQL : nouveau client a un Etb ?
> 4. Fourchettes ETS correctes ?

### Mauvais (trop formel)

> # Analyse du ticket
>
> ## Synthese
>
> Le probleme rencontre provient d'une configuration des etablissements...
>
> ## 1. Cause principale
>
> La table SOC possede un champ EntCodN qui represente un tableau de codes...

Verdict : pas chat-ready. Trop lent a lire, trop formel, destinataire doit reformuler.
