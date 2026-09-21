# Montee de version d'une surcharge -- les deux actions xwin7

Passer un client d'un Service Pack a l'autre demande de **reporter sa surcharge** sur le
nouveau standard. Deux actions `xwin7` le font, et elles ne sont documentees nulle part
ailleurs dans le devkit.

> **Le nom du skill dit « downgrade », ces actions montent de version.** Le skill est
> bidirectionnel : il couvre le rebase de pack dans les deux sens. Ne pas chercher une
> autre page.

## Trois niveaux de preuve, et ils ne se valent pas

Cette page melange trois sources. Chaque affirmation porte sa marque :

| Marque | Ce que ca veut dire |
|---|---|
| **[binaire]** | chaine extraite de `Xwin7.exe` -- le nom ou le parametre existe |
| **[observe]** | constate dans un journal `FUpgrade.log` reel |
| **[rapporte]** | vient d'un retour terrain, **non reproduit de notre cote** |

Une marque **[rapporte]** ne veut pas dire « douteux » : elle veut dire que la verification
demanderait d'**executer** l'action, donc d'ecrire, ce qui ne se fait pas a l'aveugle.

---

## `creerprojetsurcharge` -- creer la surcharge N depuis la surcharge N-1  **[binaire]**

| Parametre | Role | Preuve |
|---|---|---|
| `-project <fichier.dhpt>` | le projet dont on traite le perimetre | **[binaire]** |
| `-profile <profil>` | profil xwin7 | **[binaire]** |
| `-Base_N <sources standard>` | **le standard CIBLE**, pas l'ancien | **[binaire]** |
| `-OverLoad_Nm1 <dossier>` | la surcharge existante, en version N-1 | **[binaire]** |
| `-OverLoad_N <dossier>` | le dossier de destination | **[binaire]** |
| `-AnalyzeOnly` | n'ecrit rien, produit seulement l'analyse | **[binaire]** |
| `-ClearFUpgrade` | vide le journal avant le run | **[binaire]** |

> **La casse ci-dessus est celle du binaire.** Le retour terrain ecrivait `-analyzeOnly` et
> `-ClearfUpgrade` et l'action a fonctionne : la ligne de commande est vraisemblablement
> insensible a la casse. **Ecrire celle du binaire** evite d'avoir a le supposer.

### Le piege : `-Base_Nm1` n'existe pas

Par symetrie avec `-OverLoad_Nm1`, on invente naturellement un `-Base_Nm1` **qui n'existe
pas** -- ni dans le binaire, ni dans la documentation. Verifie : **zero occurrence** sur les
70 000 chaines de `Xwin7.exe`, ou les seules chaines contenant `Nm1` sont `OverLoad_Nm1` et
le message « OverLoad_Nm1 non renseigne ». **[binaire]**

C'est exactement le genre de parametre qu'un agent ajoute « pour completer la paire ». Ne pas
le faire : la commande le refusera, ou pire, l'ignorera en silence.

### `-Base_N` vise la version CIBLE

L'intuition inverse est forte -- on croit designer la version d'ou l'on part. **Symptome
d'une erreur de sens** : le journal se remplit de « fichier de base non localise ». Quand
`-Base_N` pointe la bonne version, ce message disparait. **[rapporte]**

---

## `mettreAJourMasquesSurcharge` -- reporter les pages du masque d'origine  **[binaire]**

| Parametre | Role | Preuve |
|---|---|---|
| `-pack <sources standard>` | le standard de reference | **[binaire]** |
| `-OverLoad <dossier des masques>` | les masques de surcharge a mettre a jour | **[binaire]** |

Met a jour les masques de surcharge avec les pages du masque d'origine.

---

## Ou tombe le resultat : `FUpgrade.log`, jamais `-output`

Le compte rendu **ne va pas** sur `-output`. Il est ecrit dans le journal de mise a niveau,
sous le repertoire de journaux de l'installation Divalto (`DivaltoLog\FUpgrade.log`).
`FUpgrade.log` est une chaine du binaire. **[binaire]**

**Forme reelle d'un journal de mise a niveau de masques** -- observe sur un journal de
1 052 lignes : **[observe]**

```
Mise a niveau de <masque>.dhsf le <date> a <heure>
<Masque  Action=Modifier  Nom=       Prop=Niveau de surcharge />
<Page    Action=Modifier  IdPage=N   Prop=Position fin />
<Objet   Action=Ajouter   IdPage=N   Nom=<objet>  IdUnique=N />
<Objet   Action=Supprimer IdPage=N   Nom=<objet>  IdUnique=N />
<Objet   Action=Modifier  IdPage=N   Nom=<objet>  Prop=Position X  IdUnique=N />
<Objet   Action=Changer ordre IdPage=N  Nom=Ordre de saisie de la page N />
```

Une ligne par action elementaire. Un run de plusieurs dizaines de masques produit donc un
journal de plusieurs centaines de lignes : **le lire, ne pas le survoler**.

Le vocabulaire d'un run `creerprojetsurcharge -AnalyzeOnly` est different : le retour terrain
cite « Conservation de la surcharge » et un decompte d'actions par fichier **[rapporte]**, et
ces messages **n'apparaissent pas** dans le journal que nous avons pu lire, qui provenait de
l'autre action.

> **Le code de sortie 1 est cosmetique [rapporte]** : se fier au **contenu du journal**, pas
> au code retour -- meme comportement que `buildall`.

---

## Perimetre : un run par `.dhpt`

L'analyse porte sur le perimetre du `-project`, et **un `.dhpt` ne couvre qu'un sous-ensemble
des masques**. Couvrir toute une surcharge demande donc **un run par projet**. **[rapporte]**

Consequence pratique : avant de conclure « la surcharge est propre », verifier **combien de
`.dhpt`** composent le perimetre, et que chacun a son journal.

---

## Demarche recommandee

1. **`-AnalyzeOnly` d'abord**, systematiquement : l'action n'ecrit rien et le journal dit ce
   qu'elle ferait.
2. **`-ClearFUpgrade`** au meme run, sinon le journal accumule les runs precedents et on lit
   le compte rendu de quelqu'un d'autre.
3. **Lire `FUpgrade.log`**, pas le code retour.
4. Repeter **par `.dhpt`**.
5. Seulement ensuite, relancer sans `-AnalyzeOnly`.

## Voir aussi

- `migration-build-order.md` -- l'ordre de compilation apres le report de surcharge : un
  standard recompile **apres** sa surcharge efface les procedures fusionnees.
- `compiling-diva-projects` -- syntaxe generale de `xwin7` et des autres actions.
