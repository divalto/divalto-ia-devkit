# Tests — `compiling-diva-projects`

Tests **exécutables** des trois scripts du skill. **Aucun xwin7 ni poste Divalto requis** :
les rapports sont des fixtures, les `.dhpt` modèles sont fabriqués dans un dossier
temporaire, et `compile_project.py` est exercé via `--no-execute` (il s'arrête avant de
lancer le compilateur) et par ses fonctions pures.

## Lancer

```
py .claude/skills/compiling-diva-projects/tests/run_all.py
```

…ou une suite à la fois :

```
py .claude/skills/compiling-diva-projects/tests/test_parse_compilation.py
py .claude/skills/compiling-diva-projects/tests/test_generate_harness.py
py .claude/skills/compiling-diva-projects/tests/test_compile_project.py
```

Exit `0` = tous les comportements attendus ; exit `1` = au moins un écart.

| Suite | Couvre |
|---|---|
| `test_parse_compilation.py` | La **règle de verdict** sur des logs réels + les gardes de régression (`--check-outputs`, attribution du fichier source, lignes de continuation) |
| `test_generate_harness.py` | L'**emprunt de config** `--from-dhpt`, l'isolation des objets, les garde-fous (profil ambigu, `implicites=`/`nom=` manquants), le périmètre `.dhsp`/`.dhsq`, l'encodage des fichiers produits |
| `test_compile_project.py` | La résolution de l'utilisateur (**#235**), le `Set-Location` dérivé (**#301**), l'encodage ISO-8859-1 du `.ps1`, la validation du profil, la délégation du verdict |

---

## Fixtures (`tests/fixtures/*.txt`)

Logs de compilation **au format réel xwin7** (marqueurs `[TOTAL_ERRORS]`, `[INFO]`,
`[WARNING]`, `[ERROR]`, `Erreur(s)=`, `N ERREUR(S) autre(s)`, `Compilation interrompue`…).
Capturés sur un vrai projet puis **anonymisés** : noms de projet / sources / profil
génériques — aucun nom partenaire. Encodage **ISO-8859-1 + CRLF** (comme les vrais rapports).

| Fixture | Cas réel | Verdict attendu |
|---|---|---|
| `build_ajour_success.txt` | build incrémental, projet à jour (`[TOTAL_ERRORS]0`, **pas** de `Erreur(s)=`) | succès |
| `buildall_success.txt` | buildall complet 0 erreur (+ un `[WARNING]` clip grille) | succès |
| `echec_syntaxe.txt` | `[ERROR] … Erreur 99 : Mot inconnu` + `Erreur(s)=1` | échec |
| `echec_mauvais_implicite_310.txt` | `[TOTAL_ERRORS]0` + « à jour » + `N ERREUR(S) autre(s)` + `absent … Code=0x14` (**#310**) | échec |
| `echec_include_absent.txt` | `[ERROR] … Erreur fatale 7 : include absent` + `Erreur(s)=1` | échec |
| `interrompu_ide.txt` | `Compilation interrompue. Erreur(s) 0` (build stoppé par l'utilisateur) | échec (`build_incomplet`) |
| `interrompu_abandon_236.txt` | `[TOTAL_ERRORS]0` + `Fin anormale` / `Construction du projet arrêtée` (**#236**) | échec (`build_incomplet`) |
| `log_vide.txt` | log vide — **seul** état où `--check-outputs` peut rattraper le verdict | succès *si* les objets sont valides |
| `deux_erreurs_fichiers.txt` | deux erreurs consécutives, chacune portant son fichier | échec, un fichier **par** erreur |
| `noms_avec_espaces.txt` | nom DIVA contenant des espaces (`gt_piece nouvellepiece.dhps`) | échec, nom capturé **entier** |
| `erreur_avec_continuation.txt` | une erreur + sa continuation ` Fichier:… Erreur numéro N` | échec, **une seule** erreur comptée |

Toutes sont des **captures réelles** (compilées via xwin7) sauf `interrompu_abandon_236.txt`,
**reconstruite** à partir des chaînes verbatim de l'issue #236 : la version de xwin7 utilisée
pour la capture ne produit pas ce message d'abandon (un include absent y donne un `[ERROR]`
fatal normal), mais le parser doit le détecter défensivement. Les 4 dernières fixtures sont
des **gardes de régression** construits à partir de formats observés.

---

## Pourquoi ces gardes existent

Chacun rejoue un défaut qui a **réellement** été livré puis corrigé :

- `--check-outputs` rendait `success:true` sur un build interrompu (`build_incomplet:true`
  dans le même JSON, exit 0) — la sentinelle `summary.errors == -1` servait à deux états.
- Le fichier source était cherché uniquement sur la ligne précédente : sur deux erreurs
  consécutives, la seconde héritait du fichier de la première.
- La regex tronquait les noms DIVA contenant des espaces.
- Les lignes de continuation étaient comptées comme des erreurs distinctes.

Un test qui ne tomberait pas en panne sur le code d'avant ne garde rien : chacun de ces cas
a été **rejoué contre la version précédente** pour vérifier qu'il échoue bien.
