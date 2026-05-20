# Erreurs de compilation courantes

## Format du rapport

La derniere partie du rapport contient une ligne de resume :

```
Erreur(s)=0   Warning(s)=0   Diva=42   Masques=5   Dictionnaires=3   Sql=8   Objets proteges=0
Duree=0:01:23
```

| Champ | Signification |
|-------|---------------|
| `Erreur(s)=` | Nombre d'erreurs (0 = succes) |
| `Warning(s)=` | Nombre de warnings |
| `Diva=` | Fichiers source DIVA compiles |
| `Masques=` | Masques ecran compiles |
| `Dictionnaires=` | Dictionnaires compiles |
| `Sql=` | RecordSql compiles |
| `Objets proteges=` | Objets proteges compiles |
| `Duree=` | Temps total (format H:M:S) |

---

## Extraction des erreurs

Les erreurs apparaissent dans le corps du rapport avec le contexte (1 ligne avant = nom du fichier source).

Pattern de detection :
```
(^| |\])Erreur
```

Extraction PowerShell :
```powershell
Select-String -Path $LogFile -Pattern '(^| |\])Erreur' -Context 1,0
```

---

## Erreurs courantes et solutions

### Profil absent du projet

**Symptome** : xwin7 ne trouve pas le profil dans le .dhpt
**Cause** : encodage du nom de profil (`développement`) en UTF-8 au lieu d'ISO-8859-1
**Solution** : encoder le script .ps1 en ISO-8859-1 (voir reference/xwin7-syntax.md)

### Fichier source introuvable

**Symptome** : `Erreur : fichier "xxx.dhsp" introuvable`
**Cause** : fichier reference dans [fichiers] du .dhps mais absent du repertoire source
**Solution** : verifier que le fichier existe, ou le retirer du .dhps

### Erreur de syntaxe DIVA

**Symptome** : `Erreur de syntaxe` avec numero de ligne
**Cause** : code DIVA invalide (variable non declaree, procedure manquante, etc.)
**Solution** : corriger le code source a la ligne indiquee

### Erreur de compilation masque (.dhsf)

**Symptome** : erreur dans un fichier .dhsf
**Cause** : element graphique mal configure, reference de champ inexistant
**Solution** : verifier la structure du masque (voir docs/MASQUE-DHSF.md)

### Erreur de compilation dictionnaire (.dhsd)

**Symptome** : erreur dans un fichier .dhsd
**Cause** : trou de position, champ non declare, section mal fermee (D01-D11)
**Solution** : valider avec managing-diva-dictionaries

### Erreur de compilation RecordSql (.dhsq)

**Symptome** : erreur dans un fichier .dhsq
**Cause** : colonne inexistante, table inexistante, syntaxe SQL invalide
**Solution** : verifier le RecordSql (voir generating-recordsql)

---

## Prerequis avant compilation

1. `C:\divalto\sys\xwin7.exe` accessible
2. Fichier .dhpt valide (voir managing-diva-projects)
3. Tous les .dhps references existent
4. Tous les fichiers source references existent
5. Nom de profil avec accent correct en ISO-8859-1
6. Repertoire de sortie du rapport existe
7. Tous les fichiers source en ISO-8859-1 + CRLF (P01, P02)

## Post-compilation

1. Verifier `Erreur(s)=0` dans le rapport
2. Si erreurs : extraire avec contexte, identifier fichier + ligne
3. Si 0 erreurs : possibilite de lancer la synchronisation SQL (voir syncing-diva-sql)
