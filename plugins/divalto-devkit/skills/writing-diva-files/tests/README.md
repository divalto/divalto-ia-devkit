# Tests — `writing-diva-files`

Tests **exécutables** des 5 scripts du skill. **Aucun poste Divalto requis** : tout se joue
sur des fichiers temporaires, hors du dépôt.

Ce skill garde l'écriture des sources DIVA : ses garde-fous protègent contre la **perte** et
la **corruption** de données. Ils avaient jusqu'ici zéro couverture exécutable — chacun des
défauts ci-dessous a réellement été livré avant d'être corrigé.

## Lancer

```
py .claude/skills/writing-diva-files/tests/run_all.py
```

…ou une suite à la fois :

```
py .claude/skills/writing-diva-files/tests/test_encoding_guards.py
py .claude/skills/writing-diva-files/tests/test_patch_file.py
py .claude/skills/writing-diva-files/tests/test_add_zoom_constant.py
```

Exit `0` = tous les comportements attendus ; exit `1` = au moins un écart.

| Suite | Couvre |
|---|---|
| `test_encoding_guards.py` | La chaîne `write_file` / `verify_encoding` / `convert_file` : décodage stdin, refus du mojibake, BOM, extensions reconnues, règle des 251, CRLF final, réparation d'un mojibake franc **et** refus honnête sur un mojibake mêlé |
| `test_patch_file.py` | Les garde-fous d'édition : `--expect-content` et sa **portée**, ancre unique, refus du contenu non encodable, `verified` = `valid`, restauration depuis le `.bak`, fichiers structurés |
| `test_add_zoom_constant.py` | Le data-loss : cible intacte sur contenu non encodable, `--dry-run` qui valide, backup, CRLF final |

---

## Ce que chaque garde protège

| Défaut réellement livré | Garde |
|---|---|
| `write_file --stdin` décodait stdin avec l'encodage console → **mojibake silencieux**, et rapportait `iso-8859-1` à tort | `[#287/#305/#309]` |
| `patch_file --stdin` : idem sur un `.dhsp` Latin-1 | `[#312]` |
| Un BOM UTF-8 se collait en tête du contenu pipé depuis PowerShell | `[#262]` |
| Les guillemets d'un `--content` étaient absorbés par PowerShell → syntaxe DIVA invalide | `[#314]` |
| `verify_encoding` rejetait `.dhsi` (faux positif) | `[#285]` |
| Une ligne > 251 caractères empêche XWin d'**ouvrir** le source | `[#277]` |
| Des numéros de ligne périmés écrasaient le mauvais bloc, sans erreur | `[#303]` `[#263]` |
| `--op delete` refusait `--line` alors que l'usage l'annonçait | `[#313]` |
| Une ancre présente 2 fois patchait au hasard | `[#288]` |
| `patch_file` **tronquait** la cible avant d'encoder → fichier vidé sur un caractère hors Latin-1 | `P1` (LOT B) |
| `add_zoom_constant` faisait de même, **sans backup**, et son `--dry-run` ne validait rien | — |
| `patch_file` écrivait du mojibake en rapportant `verified: true` | — |
| `verified` ignorait la règle des 251 et le mojibake → certifiait des fichiers invalides | — |
| `--expect-content` était **accepté puis ignoré** hors de sa portée (`insert`, `--anchor`) | — |
| La restauration depuis le `.bak` rendait le source **caché** et non réinscriptible | — |
| Le message annonçait « fichier restauré » même avec `--no-backup`, où rien n'est restauré | — |
| `write_file` écrasait quand le `.bak` échouait (filet perdu, exit 0) | — |
| `convert_file` répondait `verified: true` sur un mojibake mêlé qu'il ne réparait pas | — |

## Un principe

Un test qui ne tomberait pas en panne sur le code d'avant ne garde rien. Les cas ci-dessus
ont tous été construits **à partir du défaut observé**, puis vérifiés contre le comportement
corrigé — et pour les plus graves, rejoués contre la version précédente.

## Une nuance de conception

`patch_file` ne répond que de ce qu'il **écrit** : un défaut **préexistant** ailleurs dans le
fichier n'empêche pas le patch (sinon réparer un fichier corrompu deviendrait impossible —
or c'est justement la voie que recommande `convert_file`). Il est alors signalé dans
`preexisting_issues`, et `verified` reste `false` tant que le fichier n'est pas propre.
