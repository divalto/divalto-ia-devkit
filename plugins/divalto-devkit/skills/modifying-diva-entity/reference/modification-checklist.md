# Checklist de modification d'entite

## Avant toute modification

- [ ] Identifier le fichier .dhsd et le nom exact de la table
- [ ] Lancer `list-fields` pour voir l'etat actuel (champs, positions, taille, index)
- [ ] Identifier le masque ecran (.dhsf) si ajout ou suppression de champ
- [ ] Verifier que le projet compile sans erreur avant de commencer (baseline)

## Ajout de champ

- [ ] Verifier que le nom de champ n'existe pas deja dans le dictionnaire avec une Nature differente
- [ ] Choisir la Nature (voir `reference/nature-types.md` dans managing-diva-dictionaries)
- [ ] Decider du placement (apres quel champ existant)
- [ ] Si le champ est cle d'un nouvel index, planifier la creation d'index separement

## Modification de Nature

- [ ] Ne JAMAIS modifier les champs standard (Ce1, Dos, UserCr, UserMo, UserTrace)
- [ ] Passer d'une petite taille a une grande : augmente la taille du record
- [ ] Passer d'une grande taille a une petite : libere de l'espace (Filler augmente)
- [ ] Si le champ est dans un index : les positions cumulees de l'index seront recalculees
- [ ] Verifier que le code source DIVA n'assume pas une taille specifique

## Suppression de champ

- [ ] PERTE DE DONNEES : toutes les valeurs de cette colonne seront perdues apres synchro SQL
- [ ] Ne JAMAIS supprimer le U-field ni les champs standard
- [ ] Verifier que le champ n'est pas reference dans le code source (RecordSql, Module Check, Zoom)
- [ ] Verifier que le champ n'est pas dans un index critique
- [ ] Le bloc [CHAMP] global n'est PAS supprime (peut etre utilise par d'autres tables)

## Apres toute modification

- [ ] `validate_dhsd.py --path --table` doit retourner 0 erreurs
- [ ] `list-fields` pour verifier le nouvel etat
- [ ] Recompiler le projet/sous-projet concerne
- [ ] Synchro SQL si ajout ou suppression de colonne
- [ ] Tester dans l'ERP que le zoom fonctionne correctement
