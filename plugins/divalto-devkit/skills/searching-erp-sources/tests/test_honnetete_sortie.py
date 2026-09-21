#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests executables -- la sortie doit dire ce que la recherche a REELLEMENT fait.

Les quatre defauts corriges sur `verify_x13.py` partagent une seule cause :
**la sortie affirmait plus que le travail accompli.**

| Defaut | Ce que la sortie disait | Ce qui se passait |
|--------|-------------------------|-------------------|
| #327 | « recherche effectuee » | seuls les **5 premiers** mots-cles etaient cherches, en silence |
| #328 | 50 correspondances | un mot de 2 lettres matchait a l'interieur d'autres mots et saturait son quota de bruit |
| #329 | cadrage par domaine | le cadrage avait **echoue** et la recherche portait sur tout `erp_root` |
| version | `CONFIRME X.13` | la racine lue pouvait etre **n'importe quelle version** |

Plus un compteur qui melangeait deux unites (`files_examined` additionnait des fichiers
sondes ET des correspondances : il affichait 0 alors que 20 fichiers avaient ete lus).

Aucun poste Divalto requis : les cas fabriquent une arborescence de sources en
ISO-8859-1 + CRLF dans un repertoire temporaire.

Lancer :
    py .claude/skills/searching-erp-sources/tests/run_all.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "scripts"))
VERIFY = os.path.join(SCRIPTS, "verify_x13.py")


def ecrire(path, contenu):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(contenu.replace("\r\n", "\n").replace("\n", "\r\n").encode("iso-8859-1"))


def lance(tmp, keywords, erp_root, scope="auto", version=None, max_files="500"):
    """Lance verify_x13.py et retourne le JSON produit."""
    req = {"type": "ticket", "domaine_pressenti": "GT_",
           "keywords_techniques": list(keywords), "keywords_metier": []}
    cand = {"neo4j_status": "unavailable", "programs": [], "functions": []}
    p_req = os.path.join(tmp, "request.json")
    p_can = os.path.join(tmp, "candidates.json")
    with open(p_req, "w", encoding="utf-8") as fh:
        json.dump(req, fh, ensure_ascii=False)
    with open(p_can, "w", encoding="utf-8") as fh:
        json.dump(cand, fh, ensure_ascii=False)
    cmd = [sys.executable, VERIFY, "--candidates", p_can, "--request", p_req,
           "--erp-root", erp_root, "--domain-scope", scope,
           "--max-matches", "50", "--max-files", max_files, "--timeout", "40"]
    if version:
        cmd += ["--version", version]
    r = subprocess.run(cmd, capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="serp_")
    fails = []

    def check(label, cond, detail=""):
        print(("OK   " if cond else "FAIL ") + label + ("" if cond else "  -> " + detail))
        if not cond:
            fails.append(label)

    try:
        # --- Decor 1 : arborescence PLATE (specifique partenaire, pas de sous-dossiers) ---
        plat = os.path.join(tmp, "specifique")
        ecrire(os.path.join(plat, "alg_tarif.dhsp"),
               "SetModuleInfo('$Id$')\nProcedure P\nBeginP\n"
               "    x = MABSENT_Truc\n    Kunde_Lire()\nEndP\n")
        ecrire(os.path.join(plat, "gtut150u.dhsp"),
               "Procedure Q\nBeginP\n    y = TABLEAU_Machin\nEndP\n")

        # --- Decor 2 : arborescence du STANDARD (sous-dossiers de domaine) ---
        std = os.path.join(tmp, "standard")
        ecrire(os.path.join(std, "Achat-Vente", "source", "Dav", "gttt100.dhsp"),
               "Procedure R\nBeginP\n    Kunde_Lire()\nEndP\n")

        # ============ #327 : les mots-cles ecartes sont DITS ============
        js = lance(tmp, ["A1", "B2", "C3", "D4", "E5", "SIXIEME", "SEPTIEME"], plat, "all")
        s = js.get("scope", {})
        check("[#327] seuls 5 mots sont cherches (budget inchange)",
              s.get("keywords_recherches") == ["A1", "B2", "C3", "D4", "E5"],
              "recherches=%s" % s.get("keywords_recherches"))
        check("[#327] les mots ecartes sont NOMMES dans la sortie",
              s.get("keywords_ecartes") == ["SIXIEME", "SEPTIEME"],
              "ecartes=%s" % s.get("keywords_ecartes"))
        check("[#327] la couverture est declaree INCOMPLETE",
              s.get("couverture_keywords_complete") is False,
              "couverture=%s" % s.get("couverture_keywords_complete"))

        js = lance(tmp, ["Kunde_Lire", "MABSENT_Truc"], plat, "all")
        s = js.get("scope", {})
        check("[#327] 2 mots seulement : couverture declaree COMPLETE",
              s.get("couverture_keywords_complete") is True and not s.get("keywords_ecartes"),
              "scope=%s" % {k: s.get(k) for k in
                            ("keywords_ecartes", "couverture_keywords_complete")})

        # ============ #328 : un mot court ne ramene plus de bruit ============
        js = lance(tmp, ["AB"], plat, "all")
        check("[#328] 'AB' ne matche plus a l'interieur de MABSENT / TABLEAU",
              len(js.get("new_findings") or []) == 0,
              "%d constats de bruit" % len(js.get("new_findings") or []))

        js = lance(tmp, ["Kunde_Lire"], plat, "all")
        check("[#328] un mot entier legitime est toujours trouve",
              len(js.get("new_findings") or []) >= 1,
              "%d constats" % len(js.get("new_findings") or []))

        # ============ #329 : le repli de cadrage est DIT ============
        js = lance(tmp, ["Kunde_Lire"], plat, "GT_")
        cad = js.get("scope", {}).get("cadrage", {})
        check("[#329] arborescence plate : le repli sur erp_root est signale",
              cad.get("repli_sur_erp_root") is True,
              "cadrage=%s" % cad)
        # Assertion sur le CONTENU, pas sur une formulation exacte : la raison doit
        # dire ce qui manque ET ou la recherche a finalement porte.
        raison = (cad.get("raison_repli") or "")
        check("[#329] la raison du repli est explicite",
              "erp_root" in raison and "GT_" in raison,
              "raison=%r" % raison)
        check("[#329] le cadrage effectif dit qu'on est retombe sur tout l'ERP",
              cad.get("cadrage_effectif") == "all (repli)",
              "effectif=%r" % cad.get("cadrage_effectif"))

        js = lance(tmp, ["Kunde_Lire"], std, "auto")
        cad = js.get("scope", {}).get("cadrage", {})
        check("[#329] arborescence du standard, mode auto : PAS de repli",
              cad.get("repli_sur_erp_root") is False, "cadrage=%s" % cad)

        # L'aide CLI annonce `auto|all|<prefix>`, mais un PREFIXE de module n'est pas
        # un nom de repertoire : traite litteralement il ne correspondait a rien, donc
        # `--domain-scope GT_` -- la forme que l'auteur de #329 utilisait -- retombait
        # TOUJOURS sur tout l'ERP, meme la ou GT_ est une cle valide de MODULE_DIRS.
        js = lance(tmp, ["Kunde_Lire"], std, "GT_")
        cad = js.get("scope", {}).get("cadrage", {})
        check("[#329] `--domain-scope GT_` resout le PREFIXE de module, pas un dossier",
              cad.get("repli_sur_erp_root") is False
              and cad.get("cadrage_effectif") == "prefixe GT_",
              "cadrage=%s" % cad)

        js = lance(tmp, ["Kunde_Lire"], plat, "GT_")
        cad = js.get("scope", {}).get("cadrage", {})
        check("[#329] prefixe connu mais arborescence plate : repli DIT, raison precise",
              cad.get("repli_sur_erp_root") is True
              and "prefixe de module" in (cad.get("raison_repli") or ""),
              "cadrage=%s" % cad)

        # ============ version : declaree, jamais affirmee ============
        js = lance(tmp, ["Kunde_Lire"], plat, "all", version="X.12")
        s = js.get("scope", {})
        statuts = sorted({f["status"] for f in (js.get("new_findings") or [])})
        check("[version] --version est rapportee dans scope",
              s.get("version_verifiee") == "X.12", "version=%r" % s.get("version_verifiee"))
        check("[version] les statuts restent NEUTRES (pas de numero dedans)",
              statuts and all(v not in st for st in statuts for v in ("X.1", "X.7")),
              "statuts=%s" % statuts)
        check("[version] statut attendu = NOUVEAU",
              statuts == ["NOUVEAU"], "statuts=%s" % statuts)

        js = lance(tmp, ["Kunde_Lire"], plat, "all")
        check("[version] sans --version : le champ vaut null, rien n'est affirme",
              js.get("scope", {}).get("version_verifiee") is None,
              "version=%r" % js.get("scope", {}).get("version_verifiee"))

        # ============ compteurs : deux unites distinctes ============
        js = lance(tmp, ["Kunde_Lire"], plat, "all")
        s = js.get("scope", {})
        check("[compteurs] `matches_total` existe et compte les correspondances",
              isinstance(s.get("matches_total"), int) and s["matches_total"] >= 1,
              "matches_total=%r" % s.get("matches_total"))
        check("[compteurs] `files_examined` reste un compteur de FICHIERS distinct",
              isinstance(s.get("files_examined"), int),
              "files_examined=%r" % s.get("files_examined"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=== " + ("TOUS OK" if not fails else "%d ECHEC(S)" % len(fails)) + " ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
