# Tests de `migrating-erp-downgrade`

```
py plugin/skills/migrating-erp-downgrade/tests/test_montee_version_verifiee.py
```

## `test_montee_version_verifiee.py` -- montee de version d'une surcharge (#230, 9 cas)

Le retour terrain avait reconstruit la semantique de deux actions `xwin7` **en extrayant les
chaines du binaire**, faute de documentation accessible. Nous avons **refait la mesure**
plutot que de le croire -- et tout ce qu'il annonce se verifie, y compris son point le plus
utile.

### Ce que ces cas gardent

| Cas | Ce qu'il empeche |
|---|---|
| 1 | qu'un parametre perde **sa ligne de tableau** (la simple presence du mot ailleurs ne suffit pas) |
| 2 | que le piege **`-Base_Nm1`** redevienne une prescription, **ou perde sa preuve** |
| 3-4 | que les **trois niveaux de preuve** (`[binaire]`, `[observe]`, `[rapporte]`) soient effaces, ou qu'un point non reproduit soit presente comme etabli |
| 5 | que la demarche perde l'analyse a blanc, la raison de vider le journal, ou le run par `.dhpt` |
| 6 | que la table de `compiling-diva-projects` **redocumente** la syntaxe au lieu de renvoyer -- ou qu'elle perde les deux actions, alors que c'est **la page ou le partenaire a cherche** |
| 7 | qu'une **URL de wiki interne** ou un chemin de poste entre dans une page distribuee |
| 9 | que la page cesse d'expliquer pourquoi une **montee** de version est documentee dans un skill nomme `downgrade` |

### Validation : 12 mutations, 12 discriminantes -- apres trois corrections

Deux faiblesses de mes cas, **toutes deux « satisfait par une autre occurrence »** :

1. Le cas 1 cherchait le parametre **dans la page entiere** ; supprimer sa ligne de tableau
   ne le faisait pas tomber, le mot survivant dans la demarche. Il lit desormais **les lignes
   de tableau**.
2. Le cas 4 cherchait la marque `[rapporte]` dans une **fenetre de 400 caracteres** autour du
   point : la fenetre attrapait la marque d'un point **voisin**. Il verifie desormais **la
   phrase** qui porte le point.

Et une faiblesse de l'**outil** de decoupage, corrigee en deux temps :

3. Couper sur chaque fin de ligne hachait les phrases d'un markdown a la ligne dure -- la
   negation d'une phrase pouvait tomber sur la ligne suivante, et « ...un `-Base_Nm1` **qui
   n'existe / pas** » etait lu comme une **prescription**. Puis, une fois les lignes
   recollees, couper a chaque ligne de **citation** (`>`) rehachait les encadres. Le
   decoupeur recolle donc les lignes d'un meme paragraphe et retire le marqueur de citation
   avant de decouper.

> **Deux de ces trois corrections ont porte sur la PAGE, pas sur le test** : les marques de
> preuve etaient placees **apres** le point de la phrase qu'elles qualifiaient. Un lecteur
> qui s'arrete a la phrase ne les voyait pas non plus.
