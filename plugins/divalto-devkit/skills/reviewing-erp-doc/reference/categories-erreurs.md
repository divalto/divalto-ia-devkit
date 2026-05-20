# Categories d'erreurs detectees par reviewing-erp-doc

4 categories, exhaustives et mutuellement exclusives. En cas de chevauchement potentiel entre un item et plusieurs categories, la priorite est E1 > E3 > E4 > E2 (l'item est classe dans la premiere categorie applicable).

## Sommaire

- [E1 -- Affirmation narrative non sourcee](#e1----affirmation-narrative-non-sourcee)
- [E2 -- Desalignement entre narratif et citation](#e2----desalignement-entre-narratif-et-citation)
- [E3 -- Omission structurelle](#e3----omission-structurelle)
- [E4 -- Contradiction avec le referentiel DIVA](#e4----contradiction-avec-le-referentiel-diva)
- [Priorite en cas de chevauchement](#priorite-en-cas-de-chevauchement)

---

## E1 -- Affirmation narrative non sourcee

**Definition** : une affirmation textuelle dans les couches `business.*`, `schema.*` ou `technical.*` d'une entite qui n'a ni citation `fichier:ligne` vers une source X.13, ni marquage explicite dans `meta.a_verifier`.

**Pourquoi c'est une erreur** : viole CA4 de UC-200 ("Regle de citation stricte"). Une affirmation non tracee est soit le resultat d'une hallucination LLM, soit un oubli de sourcing du producteur. Dans les deux cas, elle degrade la confiance dans tout le livrable.

**Severite par defaut** : `erreur`.

**Comment la detecter** : regex sur chaque champ texte des YAML d'entite.
- Expression de citation acceptee : `[A-Za-z0-9_./\\-]+\.(dhsp|dhsq|dhsd|dhsf|dhop|sql|dll):\d+` (forme `fichier:ligne`)
- Expression de marquage accepte : exhaustivement enumere dans `meta.a_verifier[]` avec reference au champ YAML

**Exemple remonte** :

```yaml
# Dans entity/CLI.yaml
business:
  role: "Le client est l'entite pivot du module DAV."
# Pas de citation, pas de meta.a_verifier -> E1 erreur
```

Rapport :
```
[E1 erreur] CLI / business.role
Extrait livrable : "Le client est l'entite pivot du module DAV."
Challenge : affirmation non sourcee (ni citation fichier:ligne, ni meta.a_verifier). Viole CA4 UC-200.
```

**Ce qui N'EST PAS E1** :
- Un champ vide -> pas d'erreur (rien a sourcer)
- Un champ qui dit litteralement "[A VERIFIER]" -> OK (marquage explicite)
- Un champ qui cite une source externe type `docs/X.md:42` -> OK (citation valide, meme si pas X.13)

---

## E2 -- Desalignement entre narratif et citation

**Definition** : une affirmation narrative est correctement citee (la reference `fichier:ligne` existe et pointe un code valide), mais la paraphrase du narratif diverge de ce que dit reellement le code cite. Le producteur a cite la bonne source mais l'a mal lue.

**Pourquoi c'est un warning** : le livrable est formellement conforme a CA4 (source citee), mais semantiquement incorrect. Detectable uniquement par jugement semantique -- seule categorie LLM-driven du relecteur.

**Severite par defaut** : `warning` (`non`) ou `info` (`douteux`).

**Comment la detecter** :
1. Script `prepare_misalign_batch.py` extrait pour chaque citation un contexte de 20 lignes autour de la ligne pointee.
2. Claude evalue chaque paire `{narratif, context_source}` :
   - `oui` : narratif fidele au contexte -> pas d'item
   - `non` : narratif contredit le contexte -> warning
   - `douteux` : contexte ambigu ou trop court -> info

**Exemple remonte (test plante dans scenario 2 UC-201)** :

```yaml
business:
  regles: |
    CLI.Bloque = client actif.
    Citation: Gttmchkcli.dhop:142
```

Le contexte X.13 autour de la ligne 142 contient :
```
Case Sql_Bloque <> 0 ; Gosub RejectActive
```

Rapport :
```
[E2 warning] CLI / business.regles
Extrait livrable : "CLI.Bloque = client actif."
Extrait source (Gttmchkcli.dhop:142) : "Case Sql_Bloque <> 0 ; Gosub RejectActive"
Challenge : la source rejette les clients avec Bloque <> 0, le narratif affirme le contraire.
```

**Ce qui N'EST PAS E2** :
- Un narratif non source -> c'est E1
- Un champ omis dans le livrable alors qu'il existe en source -> c'est E3
- Une divergence avec une regle du referentiel DIVA (et non avec une source X.13) -> c'est E4

---

## E3 -- Omission structurelle

**Definition** : une structure (champ, index, cle primaire, relation FK) est presente dans la source de verite X.13 (dictionnaire `.dhsd`, masque `.dhsf`, schema SQL) mais absente du livrable, sans qu'un item `meta.a_verifier` justifie l'omission.

**Pourquoi c'est une erreur** : UC-200 garantit (CA2) que les structures sont extraites automatiquement. Une omission est soit un bug du producteur, soit un filtrage non declare. Dans les deux cas, le livrable est incomplet par rapport a la source de verite.

**Severite par defaut** : `erreur`.

**Comment la detecter** :
1. Re-parse `.dhsd` via `_dhsd_parser.py` vendore -> liste de reference des fields + indexes
2. Re-parse `.dhsf` via `_dhsf_parser.py` vendore -> liste des zooms et onglets
3. Lecture du schema SQL JSON -> liste des FK declarees
4. Diff avec l'IR du livrable. Pour chaque element en source mais pas en livrable, verifier si un `meta.a_verifier` couvre l'omission. Si non -> erreur.

**Exemple remonte** :

Le dictionnaire `Gttcli.dhsd` declare le champ `CLI.DateDernierAchat` avec Nature `Dt`. Le YAML `entity/CLI.yaml` ne le mentionne pas. Aucun `meta.a_verifier` ne dit "DateDernierAchat non documente".

Rapport :
```
[E3 erreur] CLI / technical.fields
Extrait source (Gttcli.dhsd:87) : "CLI.DateDernierAchat = Dt ;"
Challenge : champ present dans le dictionnaire mais absent de technical.fields du livrable, sans justification meta.a_verifier.
```

**Ce qui N'EST PAS E3** :
- Un champ present dans le livrable mais non documente dans les sources -> c'est suspect (possible E2 si cite), pas E3
- Un champ omis mais explicitement liste dans `meta.a_verifier` (ex: "DateDernierAchat : non documente, a confirmer") -> OK

---

## E4 -- Contradiction avec le referentiel DIVA

**Definition** : une affirmation du livrable contredit une regle documentee dans le referentiel `docs/` du workspace (Nature d'un suffixe, convention de prefixe de domaine, pattern 3 fichiers, anti-pattern connu).

**Pourquoi c'est un warning** : le referentiel DIVA est une source complementaire aux sources X.13. Une contradiction peut signifier soit une erreur du livrable, soit un referentiel obsolete. Dans les deux cas, a verifier.

**Severite par defaut** : `warning`.

**Comment la detecter** : heuristiques deterministes sur un corpus cible de `docs/*.md`. Details dans [docs-corpus.md](docs-corpus.md).

Exemples de regles detectables :
- Le champ `SOC.CodePostal` est declare Nature `Fl` dans le livrable, mais `docs/DICTIONNAIRE-DHSD.md` dit que les codes postaux doivent etre `Ch5` -> contradiction
- Le livrable declare un domaine `ABC` pour une entite `CLI`, mais `docs/MODULES-ERP.md` liste `CLI` dans le domaine `DAV` -> contradiction
- Le livrable cite un fichier `Gttcli.dhop` mais le pattern 3 fichiers (documente dans `docs/ARCHITECTURE-ENTITE.md`) attend `Gttmchkcli.dhop` -> contradiction

**Interdit** :
- Proposer une modification du referentiel `docs/`
- Considerer une contradiction comme une erreur bloquante -- c'est toujours `warning` car le referentiel peut etre en retard

**Ce qui N'EST PAS E4** :
- Une contradiction avec une source X.13 directe -> c'est E2 (si citee) ou E3 (si omission)
- Une information absente du referentiel -> non detectable, hors scope

---

## Priorite en cas de chevauchement

Un item ne doit jamais etre remonte dans deux categories. Regle de precedence :

1. **E1 prime** -- si une affirmation est non sourcee, peu importe ce qu'elle contient, elle est E1
2. **E3 ensuite** -- si E1 ne s'applique pas et qu'une omission structurelle existe, E3
3. **E4 ensuite** -- si ni E1 ni E3, mais contradiction referentiel, E4
4. **E2 en dernier** -- si rien de ce qui precede, desalignement narratif vs citation

Exemple : une affirmation "CLI.Bloque = client actif" non sourcee contredit aussi le referentiel. Reportee en E1, pas en E4.
