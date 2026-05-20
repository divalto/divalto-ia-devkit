# Rapport de relecture -- TST

> Genere le 2026-04-22 18:32 UTC
> Livrable : `.claude\skills\reviewing-erp-doc\test_fixtures\fixture-simple`
> Relecteur : reviewing-erp-doc

## Resume executif

**Verdict : `corrections necessaires avant publication`**

### Compteurs par categorie

| Categorie | Erreurs | Warnings | Infos | Total |
|-----------|--------:|---------:|------:|------:|
| E1 (non sourcee) | 6 | 0 | 0 | 6 |
| E2 (desalignement) | 0 | 1 | 4 | 5 |
| E3 (omission) | 2 | 0 | 1 | 3 |
| E4 (contradiction docs/) | 0 | 1 | 0 | 1 |
| **Total** | **8** | **2** | **5** | **15** |

### Couverture du producteur

- Items `[A VERIFIER]` deja presents dans le livrable : **1**
- Items detectes par le relecteur : **15**
- Ratio de couverture du producteur : **6.2%**

### Top entites critiques (par erreurs)

- **BAD** -- 6 erreur(s)
- **OKK** -- 2 erreur(s)


---

## Detail par entite

### BAD -- Entite avec affirmations non sourcees
#### E1 -- 6 item(s)

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `business.business_rules[0]`
  - Source : `<aucune>`
  - Extrait livrable : Les entites BAD sont recalculees a chaque cloture mensuelle automatiquement.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `business.business_rules[1]`
  - Source : `<aucune>`
  - Extrait livrable : Les BAD archivees sont conservees 10 ans puis supprimees de la base.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `business.role`
  - Source : `<aucune>`
  - Extrait livrable : BAD est une entite critique du processus de vente, pivot pour les commissions.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `technical.fields[0].business_note`
  - Source : `<aucune>`
  - Extrait livrable : Identifiant fonctionnel issu d'un compteur applicatif.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `technical.fields[1].business_note`
  - Source : `<aucune>`
  - Extrait livrable : Montant TTC arrondi au centime superieur.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

- **[erreur]** Affirmation narrative non sourcee
  - Champ YAML : `technical.performance_notes`
  - Source : `<aucune>`
  - Extrait livrable : La table BAD doit etre partitionnee par annee pour performance.
  - Challenge : Aucune citation fichier:ligne dans l'affirmation, aucun marquage [A VERIFIER] inline, aucun item meta.a_verifier couvrant le champ. Viole CA4 de UC-200 (regle de citation stricte).

#### E3 -- 1 item(s)

- **[info]** Source .dhsd introuvable
  - Champ YAML : `technical.dictionary_source`
  - Source : `<aucun fichier .dhsd trouve sous erp-root pour table BAD>`
  - Challenge : Le relecteur n'a pas pu localiser le dictionnaire source pour cette entite (essaye : Gttbad.dhsd, baddd.dhsd). Detection E3 partielle.

### OKK -- Entite propre (sourcee correctement)
#### E3 -- 2 item(s)

- **[erreur]** Champ Telephone absent du livrable
  - Champ YAML : `technical.fields`
  - Source : `Gttokk.dhsd`
  - Extrait livrable : technical.fields ne contient pas 'Telephone'
  - Extrait source : [CHAMPS] Nom=Telephone...
  - Challenge : Champ 'Telephone' declare dans le dictionnaire source mais absent de technical.fields du livrable, sans justification dans meta.a_verifier.

- **[erreur]** Index IdxTel absent du livrable
  - Champ YAML : `technical.indexes`
  - Source : `Gttokk.dhsd`
  - Extrait livrable : technical.indexes ne contient pas 'IdxTel'
  - Extrait source : [INDEX] Nom=IdxTel...
  - Challenge : Index 'IdxTel' declare dans le dictionnaire source mais absent de technical.indexes du livrable, sans justification dans meta.a_verifier.

#### E4 -- 1 item(s)

- **[warning]** Nature de AnnulFl incoherente avec suffixe Fl
  - Champ YAML : `technical.fields[AnnulFl].nature`
  - Source : `DICTIONNAIRE-DHSD.md:section 2 (+ managing-diva-dictionaries/scripts/suggest_nature.py)`
  - Extrait livrable : AnnulFl = C20
  - Extrait source : suffixe Fl attendu en Nature 1,... (Flottant (1,0 ou 1,N))
  - Challenge : Le champ 'AnnulFl' porte le suffixe typee 'Fl' (Nature attendue : 1,..., Flottant (1,0 ou 1,N)), mais le livrable declare Nature 'C20'. Soit le nom du champ derive de la convention, soit la Nature a ete mal extraite.

#### E2 -- 5 item(s)

- **[warning]** Desalignement narratif vs source (inversion logique)
  - Champ YAML : `business.business_rules[2]`
  - Source : `Gttokk.dhsq:22`
  - Extrait livrable : Les OKK dont Bloque = 0 sont rejetes automatiquement de la selection par defaut.
  - Extrait source : ; Parcourt les OKK actifs (Bloque = 0) / Collate OKKSelect By OKK.Bloque = 0
  - Challenge : Inversion : la source selectionne les OKK avec Bloque=0 comme actifs (commentaire et Collate explicites 'LoadAllActifs'), le narratif affirme qu'ils sont rejetes.

- **[info]** Source citee introuvable
  - Champ YAML : `business.business_rules[0]`
  - Source : `Gttmchkokk.dhop:55`
  - Extrait livrable : Un OKK bloque ne peut plus etre facture.
  - Extrait source : <source_not_found>
  - Challenge : Le fichier cite est introuvable sous erp-root. Impossible de verifier l'alignement narratif/source. A confirmer que la citation pointe un fichier existant.

- **[info]** Paraphrase deductive a confirmer (contexte .dhsd structurel)
  - Champ YAML : `technical.fields[0].business_note`
  - Source : `Gttokk.dhsd:15`
  - Extrait livrable : Identifiant unique du client OKK.
  - Extrait source : [CHAMPS] Nom=OKK_ID,1,20,... (+ [INDEX] Nom=IdxOKK_ID,Ce1,Dos,OKK_ID)
  - Challenge : Le contexte cite est la declaration .dhsd du champ OKK_ID. La qualification 'identifiant unique' est plausible (nom suffixe _ID + index dedie) mais n'est pas explicitement sourcee dans les lignes citees. A renforcer par une reference au mchk ou un marquage metier.

- **[info]** Contexte source insuffisant pour evaluation E2
  - Champ YAML : `technical.fields[4].business_note`
  - Source : `Gttokk.dhsd:99`
  - Extrait livrable : Drapeau annulation, source: Gttokk.dhsd:99
  - Extrait source : <contexte vide : ligne au-dela du fichier source>
  - Challenge : La ligne citee (99) est au-dela de la fin du fichier source (~23 lignes). Citation probablement incorrecte -- a verifier.

- **[info]** Contexte source insuffisant pour evaluation E2
  - Champ YAML : `technical.performance_notes`
  - Source : `Gttokk.dhsd:120`
  - Extrait livrable : Index recommande sur (OKK_ID, Dos) pour volumetrie > 100k.
  - Extrait source : <contexte vide : ligne au-dela du fichier source>
  - Challenge : La ligne citee (120) est au-dela de la fin du fichier source (~23 lignes). Citation probablement incorrecte -- a verifier.


---

## Items `[A VERIFIER]` deja presents dans le livrable

### OKK
- business.role : criticite metier a confirmer avec le DAF

