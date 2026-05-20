# report-template.md -- Rappel de la structure du rapport final

Le rapport markdown produit a la phase 4 suit la structure canonique definie dans `docs/ANALYSE-PRE-ACTION.md`. Ce fichier est un rappel rapide pour l'enrichissement LLM au CP5.

## 7 sections + annexe

| # | Section | Source principale | Enrichissement LLM |
|---|---------|-------------------|---------------------|
| En-tete | Metadonnees | request.json + metrics | Aucun (deterministe) |
| 1 | Comprehension de la demande | request.json | Mineur : reformulation finale post-CP1 |
| 2 | Exemples de code DIVA similaires | evidence.confirmed + evidence.new_findings | Aucun (deterministe, borne a 5) |
| 3 | Fonctions du langage DIVA utiles | Fonctions extraites des snippets | **Majeur** : categoriser + ajouter canoniques |
| 4.1 | Appelants potentiels | evidence.impact.callers | Aucun (deterministe, borne a 15) |
| 4.2 | Propagation des changements | -- | **Majeur** : a rediger selon le type de modif |
| 4.3 | Surcharges existantes | -- | **Majeur** : chercher OverWrittenBy dans section 2 |
| 5 | Endroit ou agir | -- | **Majeur** : 1-3 propositions avec lien section 2 |
| 6 | Pistes complementaires | Suggestions deterministes | Majeur : 3-5 items contextuels |
| 7 | Points d'attention | Metriques | Mineur : conventions domaine |
| Annexe | Sources consultees | evidence.scope | Aucun (deterministe) |

## Enrichissements a faire au CP5

### Section 3 -- Fonctions du langage DIVA utiles

Familles standard :
- `Framework` : `Get_CheckObject_Data`, `Check_*_Field_*`, `Init_Zoom`, `Init_Module`
- `RecordSql` : `Select`, `AddCondition`, `Orderby.Par_*`, `PreInsert`, `PostInsert`
- `ISAM` : `HFileVersion`, `Load_*`, `Check_*`, `Exists_*`
- `HTTP/REST` : `RestCall`, `JsonParse`, `XmlParse` -- voir `docs/LANGAGE-AVANCE.md`
- `UI/Masque` : methodes Zoom, callbacks cycle de vie
- `Utilitaires` : `Translate`, `Formater_*`, `Trace_SOX_*`

Sources : `docs/LANGAGE-AVANCE.md`, `docs/ARCHITECTURE-ENTITE.md`, `docs/SQUELETTES.md`.

### Section 4.2 -- Propagation des changements

Selon le type d'intervention envisage :

- **Ajout de champ** : dictionnaire + masque + RecordSql + audit
- **Modification de signature** : tous les callers de section 4.1
- **Suppression** : verifier qu'aucun appelant n'existe (sinon blocage)
- **Nouveau zoom** : integration menu, zoom des zooms, constante

### Section 4.3 -- Surcharges existantes

Grep regex dans les snippets section 2 :

```regex
^\s*OverWrittenBy\s+['"]([^'"]+)['"]
```

Pour chaque match : `Fichier X surcharge par Y dans le domaine Z`. Implication : `toute modification a porter dans la surcharge aussi`.

### Section 5 -- Endroit ou agir (critique)

Format par proposition (1-3 max) :

```markdown
### Proposition N : <titre imperatif en 1 ligne>
- **Fichier(s)** a creer/modifier : <chemins>
- **Fonction(s)** a creer/modifier : <noms>
- **Pattern de reference** : section 2.M (lien interne)
- **Impact estime** : faible | moyen | fort -- <justification 1 ligne>
- **UC generation suggere** : UC-001 | UC-002 | UC-003 | aucun
```

Regle absolue : chaque proposition doit citer un exemple concret de la section 2.

UC recommandations courantes :
- Creer une entite -> UC-001
- Modifier une entite existante -> UC-002
- Surcharger un zoom -> UC-003 (si cree)
- Debugger une anomalie -> UC-005

### Section 6 -- Pistes complementaires

3-5 items parmi :
- Requete Cypher supplementaire (advisory) avec code copier-coller
- Grep X.13 cible avec commande complete
- Fichier X.13 a lire en entier
- Document `docs/XXX.md` a consulter
- Skill existant a invoquer (ex : `testing-erp` pour valider visuellement)

### Section 7 -- Points d'attention

En plus des elements deterministes (bornes, duree, disparus), le LLM ajoute :

- Convention domaine (prefixe, champ cle canonique)
- Effets de bord identifies (cascade compilation, synchro SQL, moulinette CI)
- Disclaimers metier specifiques au domaine

## Regles transverses

1. **Jamais d'invention `fichier:ligne`** : toute reference vient des JSON intermediaires
2. **Toujours lier sections 5 et 2** : chaque proposition d'action doit citer un pattern existant
3. **Marquage X.12/X.13 systematique** : verifier avant livraison qu'aucun `[X.12]` n'est nu
4. **Max 3 propositions en section 5** : si plus, basculer en section 6
5. **Langue francaise** : pas d'anglicismes sauf termes techniques DIVA (RecordSql, OverWrittenBy)
