# Portee : entite dans un domaine maison (hors domaine standard)

`creating-diva-entity` cree des entites custom **dans un domaine STANDARD enregistre**
(DAV, Retail, GRM...). Il ne couvre pas un **domaine propre au partenaire** : prefixe
maison (ex. `<prefixe>_`), dictionnaire maison (ex. `<prefixe>_gtfdd.dhsd`), sans les fichiers
`*pmficsql` / `gttcficsql` du standard. La liste des domaines valides est figee dans
`naming-diva-entities` (`_naming.py`) ; un `--domaine` non enregistre est refuse par
`compute_names.py` (message listant les domaines valides).

Raison : tout le nommage (prefixes, `FichierDico`, RecordSql, zoom, mchk, masque) et
les etapes d'integration ERP (alias dans `*pmficsql`, include `gttcficsql`, menu
domaine, synchro) sont **derives d'un domaine standard**. Un domaine maison ne possede
pas cette plomberie standard -- l'orchestrateur genererait des artefacts faux (alias
vers un ficsql inexistant, declaration `gttcficsql` parasite).

## Chemin recommande : la composition

Pour creer une entite dans un domaine maison, composer les skills unitaires plutot que
l'orchestrateur :

1. **`managing-diva-dictionaries`** -- creer l'entite dans le dictionnaire maison
   (ex. `<prefixe>_gtfdd.dhsd`), y compris en surcharge si besoin ;
2. si un acces SQL / zoom / masque ecran est voulu :
   **`generating-zoom-sql`** + **`manipulating-dhsf-screens`** sur les fichiers maison ;
3. **`understanding-integrator-workspace`** aide a localiser le bon dictionnaire
   specifique et les conventions de nommage du poste.

C'est exactement le contournement classiquement adopte par les integrateurs pour ce cas, rendu officiel.

## Evolution candidate (non implementee) : `--custom-domain`

Un mode ouvrant un **registre de domaines partenaire** serait coherent avec la vocation
du skill (creation custom), mais n'est **pas** un simple flag :

- il faudrait fournir les **tokens de nommage** du domaine maison (prefixe code, prefixe
  module + surcharge, prefixe DB, domaine 2 lettres, dictionnaire, module ficsql,
  `SetPrefixeModule`) -- soit tout ce que `DOMAIN_REGISTRY` fige aujourd'hui par domaine ;
- il faudrait surtout **rendre optionnelles** les etapes d'integration ERP standard
  (alias `*pmficsql`, include `gttcficsql`, menu domaine, synchro) qu'un domaine maison
  ne possede pas.

A ouvrir en **SC dedie** si le besoin d'industrialiser la creation d'entites dans un
domaine maison devient recurrent chez les integrateurs. En attendant : composition.
