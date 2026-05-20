# Policy SVN pour ce skill

Condense local (vendoring) de la policy SVN du workspace, pour que ce skill reste autonome.

## Principe premier

SVN est consulte en **lecture seule**. Aucun script de ce skill ne doit executer une sous-commande ecrivante. La livraison reste humaine.

## Whitelist (sous-commandes autorisees)

| Commande | Usage |
|----------|-------|
| `svn log` | Historique revisionnel d'un fichier ou repertoire |
| `svn blame` | Attribution ligne par ligne (couteux meme sur petits fichiers) |
| `svn diff` | Difference entre revisions |
| `svn diff_local` (pas de `-r`) | Modifs locales non committees (WC vs BASE) |
| `svn cat -r <rev>` | Contenu a une revision, sans checkout |
| `svn info` | Metadonnees WC/URL |
| `svn list` | Liste d'un chemin |

## Blacklist (interdits absolus)

`commit`, `ci`, `merge`, `resolve`, `update`, `switch`, `copy`, `move`, `delete`, `rm`, `mkdir` (distant), `lock`, `unlock`, `propset`, `propdel`, `propedit`, `revert`, `import`, `cleanup --remove-unversioned`.

## Timeouts recommandes

| Primitive | Timeout |
|-----------|---------|
| `info`, `list` | 5s |
| `log --limit N` | 15s |
| `cat -r` | 10s |
| `blame` | 60s (couteux, preferer borne `-L` ou eviter sur gros fichiers) |
| `diff` | 30s |

Max absolu : 120s. Jamais de retry automatique.

## Degradation gracieuse (obligatoire)

Tous les appels SVN de ce skill sont wrappes en try/except avec flag `svn_available`. Si SVN est indisponible (binaire absent, reseau down, timeout), le skill continue sans enrichissement -- il ne plante pas.

## Rate-limit applicatif

Max 10 appels `svn log`/`info`/`list` par invocation de script. Pas de parallelisation (serveur SVN partage, charge a ne pas pomper).

## Enforcement technique

Le script `scripts/svn_consult.py` (vendore dans ce skill) implemente la whitelist via une fonction `_validate_subcommand()` qui leve `SvnWriteAttempted` (sous-classe de `NotImplementedError`) pour toute sous-commande ecrivante.
