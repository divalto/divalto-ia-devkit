#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_table_scope -- portee d'une table de parametrage Tnnn (commune vs par-dossier).

Une table de parametrage `Tnnn` du standard Divalto est soit COMMUNE a tous les
dossiers (ses enregistrements vivent sur le dossier commun 999), soit PROPRE a
chaque dossier. L'information est portee par la table `T000` : une ligne unique
(sur DOS=999) avec une colonne `TABTYP_<nnnn>` par numero de table.

  TABTYP = 2  -> table COMMUNE      -> requeter le dossier 999
  TABTYP = 1  -> table PAR-DOSSIER  -> requeter le dossier metier

Mecanisme detaille : understanding-integrator-workspace/sql-resolution.md.

Posture (delegation R-12) : par defaut, ce script NE se connecte PAS a la base
client -- il construit la requete a faire executer. Deux raccourcis :
  * --tabtyp <valeur>  : interprete une valeur deja lue (aucun acces base).
  * --execute + -E     : lit T000 en LECTURE SEULE via sqlcmd, en authentification
                         Windows UNIQUEMENT. Aucun mot de passe SQL en clair n'est
                         accepte sur la ligne de commande -- une base en auth SQL
                         passe donc par le mode delegation (defaut).

Sortie : JSON sur stdout. Exit 0 = ok, 2 = erreur.
"""

import argparse
import json
import re
import subprocess
import sys


def _fail(msg):
    print("[ERREUR] " + msg, file=sys.stderr)
    sys.exit(2)


def parse_table_number(table):
    """'T021' / 't21' -> 21. Renvoie None si le format n'est pas Tnnn."""
    m = re.fullmatch(r"[Tt](\d{1,4})", table.strip())
    if not m:
        return None
    return int(m.group(1))


def interpret(tabtyp, dossier_metier):
    """Mappe une valeur TABTYP vers une portee. Ne devine jamais une valeur hors {1,2}."""
    if tabtyp == 2:
        return "commune", "999"
    if tabtyp == 1:
        return "par-dossier", (dossier_metier or "<dossier_metier>")
    # Valeur inattendue : ne pas inventer (P-A).
    return "inconnu", None


def run_query(colonne, args):
    """Execute en LECTURE SEULE `SELECT <colonne> FROM T000` via sqlcmd. Renvoie int ou None."""
    if not args.server or not args.database:
        _fail("--execute requiert --server et --database.")
    if not args.trusted:
        _fail("--execute requiert -E (authentification Windows). Pour une base en "
              "authentification SQL, ne pas utiliser --execute : le mode delegation "
              "(par defaut) fournit la requete a lancer dans votre propre session "
              "authentifiee, puis relancer avec --tabtyp <valeur> -- on evite ainsi "
              "tout mot de passe en clair sur la ligne de commande.")

    cmd = ["sqlcmd", "-S", args.server, "-d", args.database, "-E",
           "-h", "-1", "-W", "-b", "-Q",
           "SET NOCOUNT ON; SELECT {0} FROM T000".format(colonne)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30)
    except FileNotFoundError:
        _fail("sqlcmd introuvable dans le PATH (installer les outils SQL Server, "
              "ou omettre --execute et fournir --tabtyp).")
    except subprocess.TimeoutExpired:
        _fail("Timeout de la requete T000 (30 s).")

    if proc.returncode != 0:
        _fail("sqlcmd a echoue (code {0}) : {1}".format(
            proc.returncode, (proc.stderr or proc.stdout or "").strip()))

    out = (proc.stdout or "").strip()
    m = re.search(r"-?\d+", out)
    if not m:
        _fail("Valeur TABTYP illisible dans la reponse sqlcmd : {0!r}".format(out))
    return int(m.group(0))


def main():
    ap = argparse.ArgumentParser(
        description="Portee d'une table de parametrage Tnnn (commune/999 vs par-dossier).")
    ap.add_argument("--table", required=True, help="Table de parametrage, ex. T021.")
    ap.add_argument("--tabtyp", type=int, default=None,
                    help="Valeur TABTYP deja connue (2=commune, 1=par-dossier) -- aucun acces base.")
    ap.add_argument("--dossier", default=None,
                    help="Dossier metier concerne (pour le cas par-dossier).")
    ap.add_argument("--execute", action="store_true",
                    help="Lit T000 en lecture seule via sqlcmd (requiert --server, --database, -E).")
    ap.add_argument("--server", default=None, help="Serveur SQL (avec --execute).")
    ap.add_argument("--database", default=None, help="Base SQL (avec --execute).")
    ap.add_argument("-E", "--trusted", action="store_true",
                    help="Authentification Windows -- SEULE auth acceptee pour --execute "
                         "(pas de mot de passe SQL en clair ; sinon, utiliser le mode delegation).")
    args = ap.parse_args()

    numero = parse_table_number(args.table)
    if numero is None:
        _fail("Format de table invalide : {0!r}. Attendu Tnnn (ex. T021).".format(args.table))
    if numero < 1 or numero > 200:
        _fail("Numero de table hors plage attendue 1-200 (T000 porte TABTYP_0001..0200) : "
              "{0}.".format(numero))

    colonne = "TABTYP_{0:04d}".format(numero)
    requete = "SELECT {0} FROM T000".format(colonne)
    table_norm = "T{0:03d}".format(numero)

    result = {
        "table": table_norm,
        "colonne": colonne,
        "requete": requete,
        "tabtyp": None,
        "scope": None,
        "dossier_a_requeter": None,
        "mode": None,
    }

    if args.tabtyp is not None:
        result["mode"] = "valeur-fournie"
        result["tabtyp"] = args.tabtyp
    elif args.execute:
        result["mode"] = "execute"
        result["tabtyp"] = run_query(colonne, args)
    else:
        # Delegation (regle R-12 du skill understanding-integrator-workspace) :
        # on ne se connecte pas -- on rend la requete a executer.
        result["mode"] = "delegation"
        result["note"] = ("Aucun acces base (ce skill ne se connecte pas de lui-meme). Executer la requete, "
                          "puis relancer avec --tabtyp <valeur>, ou passer --execute "
                          "avec les parametres de connexion.")
        print(json.dumps(result, ensure_ascii=True, indent=2))
        sys.exit(0)

    scope, dossier = interpret(result["tabtyp"], args.dossier)
    result["scope"] = scope
    result["dossier_a_requeter"] = dossier
    if scope == "inconnu":
        result["note"] = ("Valeur TABTYP inattendue (ni 1 ni 2) : portee indeterminee. "
                          "Verifier la table T000 sur la base cible.")

    print(json.dumps(result, ensure_ascii=True, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
