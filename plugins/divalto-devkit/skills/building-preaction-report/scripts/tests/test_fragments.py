"""Tests unitaires sur les fragments Jinja et le validator.

Objectif : attraper hors-ligne les regressions de rendu identifiees dans le RETEX
Session 2 (2026-04-18) avant qu'elles n'atteignent le collaborateur. En particulier :
- Bugs Mermaid (balises HTML non rendues : <code>, <em>)
- Italique casse par angle brackets (_..._ avec <champ>)
- Fragments de phrase apres label de bullet (Observe : qui active...)
- Stubs residuels ((cf. ticket d'origine), a completer, TODO)

Lancer : py -m unittest tests.test_fragments  (depuis scripts/)
       : py scripts/tests/test_fragments.py   (direct)
"""

import sys
import unittest
from pathlib import Path

# Rendre importable build_report.py et acceder au repertoire templates
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from build_report import (  # noqa: E402
    _reformuler_anomalie,
    _verbe_to_infinitif,
    preflight_check,
    validate_report,
)

TEMPLATES_DIR = SCRIPTS_DIR / "templates"


def render_fragment(fragment_name: str, ctx: dict) -> str:
    """Rend un fragment Jinja avec le meme environnement que le pipeline de prod."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    tpl = env.get_template(f"fragments/{fragment_name}")
    return tpl.render(**ctx)


class TestChainOfBlame(unittest.TestCase):
    """Fragment chain_of_blame.md.j2 -- chaine d'appels UI -> ... -> listener inconnu."""

    def _chain_ctx(self, nodes: list[dict]) -> dict:
        return {"seeds": {"chain_of_blame": {"available": True, "nodes": nodes}}}

    def test_nominal_5_nodes(self):
        """Cas nominal : UI -> fn -> fn_noline -> action -> gap. Doit rendre 5 noeuds."""
        ctx = self._chain_ctx([
            {"kind": "ui", "label": "Supprimer la ligne de commande fournisseur et le lien de contremarque"},
            {"kind": "fn", "name": "Supprimer_LienContremarque", "file": "gtppctm310.dhsp", "line": 224,
             "file_uri": "file:///C:/x/gtppctm310.dhsp"},
            {"kind": "fn_noline", "name": "ActionERP_Contremarque_Fournisseur_SupprLienCtm",
             "file": "gttmaction.dhsp", "file_uri": "file:///C:/x/gttmaction.dhsp"},
            {"kind": "action", "const": "C_Action_Ctm_Lien_Suppr", "file": None, "line": None,
             "name": "A5_Action_Generer_Action"},
            {"kind": "gap", "label": "LISTENER INCONNU - chercher qui consomme C_Action_Ctm_Lien_Suppr"},
        ])
        rendered = render_fragment("chain_of_blame.md.j2", ctx)

        # Structure attendue
        self.assertIn("flowchart TD", rendered)
        self.assertIn("N0", rendered)
        self.assertIn("N1", rendered)
        self.assertIn("N2", rendered)
        self.assertIn("N3", rendered)
        self.assertIn("N4", rendered)
        # Edges
        self.assertIn("N0 --> N1", rendered)
        self.assertIn("N3 --> N4", rendered)
        # Gap stylise
        self.assertIn("fill:#f96", rendered)

        # Aucune balise HTML problematique pour Mermaid
        self.assertNotIn("<code>", rendered)
        self.assertNotIn("<em>", rendered)
        # <br/> est OK (seule balise rendue par Mermaid)
        self.assertIn("<br/>", rendered)

        # Validator passe
        self.assertEqual([], validate_report(rendered))

    def test_action_sans_ligne_mentionne_emplacement(self):
        """Action sans file:line : le label doit contenir '(emplacement dans le callee)',
        pas un fichier:ligne invente."""
        ctx = self._chain_ctx([
            {"kind": "ui", "label": "Test"},
            {"kind": "action", "const": "C_Test_Action", "file": None, "line": None,
             "name": "A5_Action_Generer_Action"},
        ])
        rendered = render_fragment("chain_of_blame.md.j2", ctx)
        self.assertIn("C_Test_Action", rendered)
        self.assertIn("emplacement", rendered.lower())
        # Pas de fichier:ligne fantome
        self.assertNotIn(".dhsp:", rendered)
        self.assertEqual([], validate_report(rendered))

    def test_fn_noline_mentionne_ligne_inconnue(self):
        """Un fn_noline (ligne non trouvee) doit afficher l'indicateur (ligne ?)."""
        ctx = self._chain_ctx([
            {"kind": "ui", "label": "Test"},
            {"kind": "fn_noline", "name": "Ma_Procedure", "file": "mon_fichier.dhsp",
             "file_uri": "file:///C:/x/mon_fichier.dhsp"},
        ])
        rendered = render_fragment("chain_of_blame.md.j2", ctx)
        self.assertIn("Ma_Procedure", rendered)
        self.assertIn("(ligne ?)", rendered)
        self.assertEqual([], validate_report(rendered))

    def test_available_false_ne_rend_rien(self):
        """Si chain_of_blame.available = False, le fragment doit etre vide."""
        ctx = {"seeds": {"chain_of_blame": {"available": False, "nodes": []}}}
        rendered = render_fragment("chain_of_blame.md.j2", ctx)
        self.assertEqual("", rendered.strip())

    def test_ouvrir_fichiers_section_presente(self):
        """La section 'Ouvrir les fichiers' doit lister les noeuds avec file_uri."""
        ctx = self._chain_ctx([
            {"kind": "ui", "label": "Test"},
            {"kind": "fn", "name": "Foo", "file": "foo.dhsp", "line": 10,
             "file_uri": "file:///C:/x/foo.dhsp"},
        ])
        rendered = render_fragment("chain_of_blame.md.j2", ctx)
        self.assertIn("Ouvrir les fichiers", rendered)
        self.assertIn("file:///C:/x/foo.dhsp", rendered)

    def test_label_ui_sans_guillemets_en_dur(self):
        """Le label UI ne doit pas contenir de guillemets droits ou &quot; dans le Mermaid."""
        ctx = self._chain_ctx([
            {"kind": "ui", "label": 'Libelle "avec guillemets" pour tester'},
            {"kind": "fn", "name": "Foo", "file": "foo.dhsp", "line": 10,
             "file_uri": "file:///C:/x/foo.dhsp"},
        ])
        rendered = render_fragment("chain_of_blame.md.j2", ctx)
        # Le template supprime les guillemets droits pour eviter de casser la syntaxe Mermaid
        # (qui utilise lui-meme les guillemets pour delimiter les labels)
        # On verifie juste que le bloc mermaid est syntaxiquement coherent :
        # chaque N["..."] doit avoir un nombre pair de "
        mermaid_block = rendered.split("```mermaid")[1].split("```")[0]
        for line in mermaid_block.splitlines():
            if 'N' in line and '[' in line:
                # Le nombre de " dans un label doit etre pair (sauf si '"]' termine le label)
                # Test simple : la ligne doit bien se terminer par '"]' ou ']' ou similaire
                self.assertTrue(line.rstrip().endswith(('"]', '])', '}', ')')) or '"]' in line,
                                f"Ligne Mermaid mal formee : {line!r}")


class TestValidatorExtended(unittest.TestCase):
    """Validator etendu (_FORBIDDEN_PATTERNS Session 2)."""

    def test_catches_fragment_pronom_relatif(self):
        """Detecte '**Observe** : qui active...' (fragment sans sujet)."""
        md = "- **Observe** : qui active la commande fournisseur provisoire\n"
        violations = validate_report(md)
        self.assertTrue(any("fragment de phrase" in v for v in violations),
                        f"Attendu detection fragment, got: {violations}")

    def test_accepte_pronom_capitalise(self):
        """'**Qui** ...' (majuscule = vrai debut de phrase / question) doit passer."""
        md = "- **Question** : Qui est responsable du module ?\n"
        violations = validate_report(md)
        self.assertEqual([], violations, "Phrase commencant par 'Qui' majuscule ne doit pas etre un fragment")

    def test_catches_italique_angle_brackets(self):
        """Detecte _..._  avec <champ> dedans (casse le rendu)."""
        md = "_Chercher `ENT.<champ> = '<valeur>'` partout._\n"
        violations = validate_report(md)
        self.assertTrue(any("italique" in v.lower() for v in violations),
                        f"Attendu detection italique risque, got: {violations}")

    def test_accepte_italique_simple(self):
        """Italique sans angle brackets doit passer."""
        md = "_Pas de constantes nommees -- litteraux bruts dans 30+ sites._\n"
        violations = validate_report(md)
        self.assertEqual([], violations)

    def test_catches_stub_cf_ticket(self):
        """Detecte '(cf. ticket d'origine)' comme stub inutile."""
        md = "- **Attendu** : comportement oppose attendu (cf. ticket d'origine)\n"
        violations = validate_report(md)
        self.assertTrue(any("cf. ticket" in v.lower() or "inutile" in v.lower() for v in violations),
                        f"Attendu detection stub (cf. ticket...), got: {violations}")

    def test_catches_a_completer(self):
        md = "- **Hypothese** : a completer\n"
        violations = validate_report(md)
        self.assertTrue(any("a completer" in v.lower() for v in violations))

    def test_catches_todo_seul(self):
        md = "# Section\nTODO: revoir cette partie.\n"
        violations = validate_report(md)
        self.assertTrue(any("todo" in v.lower() for v in violations))

    def test_catches_fixme_xxx(self):
        md = "FIXME: bug connu.\nXXX important.\n"
        violations = validate_report(md)
        # Au moins 2 violations (FIXME, XXX)
        todo_violations = [v for v in violations if any(m in v.upper() for m in ("FIXME", "XXX"))]
        self.assertGreaterEqual(len(todo_violations), 2)

    def test_catches_mermaid_code_tag(self):
        """Detecte <code> dans un bloc Mermaid (ne rend pas)."""
        md = '```mermaid\nN1["<code>foo.dhsp:10</code><br/>Proc"]\n```\n'
        violations = validate_report(md)
        self.assertTrue(any("HTML non rendue" in v or "Mermaid" in v for v in violations),
                        f"Attendu detection <code>, got: {violations}")

    def test_catches_mermaid_em_tag(self):
        md = '```mermaid\nN1["Proc<br/><em>(ligne ?)</em>"]\n```\n'
        violations = validate_report(md)
        self.assertTrue(any("HTML non rendue" in v or "Mermaid" in v for v in violations))

    def test_accepte_br_tag(self):
        """<br/> est autorise dans Mermaid (seule balise HTML rendue)."""
        md = '```mermaid\nN1["Label<br/>Detail"]\n```\n'
        violations = validate_report(md)
        self.assertEqual([], violations, f"<br/> doit etre accepte, got: {violations}")

    def test_accepte_details_summary(self):
        """<details>/<summary> sont des blocs MD valides."""
        md = "<details>\n<summary>Titre</summary>\nContenu.\n</details>\n"
        violations = validate_report(md)
        self.assertEqual([], violations)

    def test_accepte_rapport_final(self):
        """Le rapport final reel doit passer sans violation."""
        final = SCRIPTS_DIR.parent.parent.parent.parent / "output" / "UC100-refactor-final-20260418.md"
        if not final.exists():
            self.skipTest(f"Rapport final introuvable : {final}")
        md = final.read_text(encoding="utf-8")
        violations = validate_report(md)
        self.assertEqual([], violations, f"Rapport final non publishable : {violations}")


class TestReformulerAnomalie(unittest.TestCase):
    """_reformuler_anomalie() -- extraction observe/attendu depuis le resume.

    INVARIANT : ne jamais produire un observe commencant par un pronom relatif.
    """

    def test_contremarque_reel(self):
        """Cas reel du ticket contremarque : doit produire phrase complete avec sujet."""
        req = {"resume": (
            "Anomalie contremarque Un probleme avec la contremarque, qui active la "
            "commande fournisseur provisoire alors qu'il ne faudrait pas"
        )}
        r = _reformuler_anomalie(req)
        # Observe reconstitue : sujet "la contremarque" + verbe "active" + complement
        self.assertFalse(r["fallback"])
        self.assertIn("contremarque", r["observe"].lower())
        self.assertIn("active", r["observe"].lower())
        self.assertNotIn("qui active", r["observe"].lower())  # plus de fragment
        # Observe commence par une capitale, pas par "qui"
        self.assertTrue(r["observe"][0].isupper())
        self.assertFalse(r["observe"].lower().startswith(("qui ", "que ", "dont ")))
        # Attendu : inverse avec infinitif
        self.assertIn("ne doit pas", r["attendu"].lower())
        self.assertIn("activer", r["attendu"].lower())

    def test_au_lieu_de(self):
        req = {"resume": "Le bouton ferme la fenetre au lieu de valider la saisie."}
        r = _reformuler_anomalie(req)
        self.assertFalse(r["fallback"])
        self.assertIn("ferme", r["observe"].lower())
        self.assertIn("valider", r["attendu"].lower())

    def test_fallback_phrase_verbale_sans_pronom(self):
        """Resume sans pattern clair mais avec verbe -> fallback OK, pas de fragment."""
        req = {"resume": "Le module plante lors de l'ouverture du menu principal."}
        r = _reformuler_anomalie(req)
        self.assertTrue(r["fallback"])
        self.assertIn("plante", r["observe"].lower())
        # INVARIANT : pas de pronom relatif en debut
        self.assertFalse(r["observe"].lower().startswith(("qui ", "que ", "dont ")))

    def test_fallback_rejette_fragment_pronom_relatif(self):
        """Si la seule phrase candidate commence par un pronom relatif, ne rien produire."""
        req = {"resume": "qui active la commande alors que pas bien."}
        r = _reformuler_anomalie(req)
        self.assertEqual(r["observe"], "")
        self.assertTrue(r["fallback"])

    def test_resume_vide(self):
        r = _reformuler_anomalie({"resume": ""})
        self.assertEqual(r["observe"], "")
        self.assertEqual(r["attendu"], "")
        self.assertTrue(r["fallback"])

    def test_resume_manquant(self):
        r = _reformuler_anomalie({})
        self.assertEqual(r["observe"], "")
        self.assertTrue(r["fallback"])

    def test_observe_ne_commence_jamais_par_pronom_relatif(self):
        """Batterie de cas varies : aucun observe ne doit commencer par qui/que/dont/ou."""
        cases = [
            "Un probleme avec la fonction, qui retourne null alors qu'il ne faudrait pas.",
            "Un souci sur le module, que l'utilisateur ne peut pas fermer.",
            "La table, dont l'index est perdu.",
            "Le bouton ne repond pas.",
            "Bonjour, probleme reproduit en 222e : le zoom plante a l'ouverture.",
            "",
        ]
        for resume in cases:
            r = _reformuler_anomalie({"resume": resume})
            if r["observe"]:
                self.assertFalse(
                    r["observe"].lower().startswith(("qui ", "que ", "qu'", "dont ", "ou ")),
                    f"Fragment detecte pour resume={resume!r} : observe={r['observe']!r}",
                )

    def test_validator_accepte_sortie(self):
        """L'observe/attendu produit doit passer le validator (pas de fragment detecte)."""
        req = {"resume": (
            "Un probleme avec la contremarque, qui active la commande fournisseur "
            "provisoire alors qu'il ne faudrait pas"
        )}
        r = _reformuler_anomalie(req)
        md = f"- **Observe** : {r['observe']}\n- **Attendu** : {r['attendu']}\n"
        self.assertEqual([], validate_report(md))


class TestAllFragmentsRender(unittest.TestCase):
    """Test meta : chaque fragment doit se rendre avec un contexte minimal sans
    generer de violation `validate_report()`. Protege contre les bugs de rendu
    introduits par une modif de template.
    """

    def _minimal_seeds(self) -> dict:
        """ReportContext minimal pour chaque fragment Jinja."""
        return {
            "seeds": {
                "chain_of_blame": {"available": False, "nodes": [], "action_const": None},
                "type_1": {"examples": []},
                "type_2": {"functions_by_family": {}},
                "type_3": {"callers": [], "propagation_sites": []},
                "type_4": {"propositions": []},
                "type_5": {"pistes": []},
                "type_6": {"overwrites": [], "notes": []},
                "type_7": {"detections": []},
                "type_8": {"triggers_hit": [], "file_path": "", "file_uri": ""},
                "type_10": {"verifications": []},
                "ca_mapping": {"entries": [], "item_type": None},
            },
            "request": {"titre": "Test", "type": "ticket", "keywords_techniques": []},
            "metrics_condensed": {"confiance_globale": "moyenne"},
            "types_included_ids": [],
            "types_omitted_ids": [],
            "anomalie_reformulee": {"observe": "", "attendu": "", "fallback": True},
            "disappeared": [],
        }

    def test_each_fragment_renders_and_passes_validator(self):
        """Chaque fragment doit rendre sans violation avec un contexte minimal."""
        from pathlib import Path as _P
        frag_dir = TEMPLATES_DIR / "fragments"
        fragments = sorted(frag_dir.glob("*.md.j2"))
        self.assertGreater(len(fragments), 0, "Aucun fragment trouve")

        for frag_path in fragments:
            name = frag_path.name
            with self.subTest(fragment=name):
                rendered = render_fragment(name, self._minimal_seeds())
                violations = validate_report(rendered)
                self.assertEqual(
                    [], violations,
                    f"{name} genere des violations : {violations}"
                )


class TestFragmentsContentSpecific(unittest.TestCase):
    """Tests plus cibles par fragment : quand il a de la matiere, le rendu est-il correct ?"""

    def test_type_4_avec_proposition_affiche_lien(self):
        """type_4 : une proposition avec file/line doit rendre un lien file://."""
        ctx = {
            "seeds": {
                "chain_of_blame": {"available": False, "nodes": [], "action_const": None},
                "type_4": {
                    "propositions": [{
                        "file": "Dav/gttmaction.dhsp",
                        "line": 356,
                        "file_uri": "file:///C:/x/Dav/gttmaction.dhsp",
                        "enclosing": "ActionERP_Contremarque",
                        "hypothese": "Tracer les appels sortants pour identifier le site qui bascule l'etat.",
                        "next_uc": "rg 'ActionERP_Contremarque' X.13/",
                    }],
                },
                "type_10": {"verifications": []},
            }
        }
        rendered = render_fragment("type_4_endroit_agir.md.j2", ctx)
        self.assertIn("file:///C:/x/Dav/gttmaction.dhsp", rendered)
        self.assertIn("ActionERP_Contremarque", rendered)
        # Hypothese rendue en blockquote (pas en italique) -- P0d
        self.assertIn("**Hypothese :**", rendered)
        self.assertEqual([], validate_report(rendered))

    def test_type_7_avec_literal_affiche_table(self):
        """type_7 : si un literal Ce4 est present, la table doit apparaitre."""
        ctx = {
            "seeds": {
                "type_7": {
                    "literals": [{
                        "name": "Ce4 (etat piece)",
                        "canonical_source_doc": "../docs/ETATS-PIECE.md",
                        "canonical_source_code": "Dav/dav_sd.dhsq:453",
                        "table": [
                            {"code": "1", "label": "active"},
                            {"code": "7", "label": "provisoire"},
                        ],
                        "note": "Litteraux bruts dans 30+ sites.",
                    }],
                }
            }
        }
        rendered = render_fragment("type_7_constantes_metier.md.j2", ctx)
        # Table metier Ce4
        self.assertIn("Ce4", rendered)
        self.assertIn("provisoire", rendered)
        self.assertEqual([], validate_report(rendered))

    def test_type_8_avec_trigger_affiche_grep(self):
        """type_8 : parametrage dossier avec trigger -> commande grep_hint visible."""
        ctx = {
            "seeds": {
                "type_8": {
                    "triggers_hit": ["parametrage", "onglet"],
                    "grep_hint": 'rg -ni "cont" "<ERP>/Fichier/gtfdd.dhsd"',
                }
            }
        }
        rendered = render_fragment("type_8_parametrage_dossier.md.j2", ctx)
        # Commande d'investigation + mention du trigger
        self.assertIn("parametrage", rendered)
        self.assertIn("gtfdd.dhsd", rendered)
        self.assertEqual([], validate_report(rendered))


class TestPreflightCheck(unittest.TestCase):
    """preflight_check() -- validation des JSON d'entree avant build_report."""

    def _ok_request(self):
        return {
            "type": "ticket",
            "resume": "La contremarque active la commande fournisseur provisoire.",
            "domaine_pressenti": "GT_",
            "keywords_techniques": ["Contremarque", "CommandeFournisseur"],
        }

    def _ok_candidates(self):
        return {
            "functions": [{"name": "Supprimer_LienContremarque", "program": "gtppctm310.dhsp", "line": 224}],
            "programs": [],
            "relations": {"callers_of": []},
            "neo4j_status": "available",
        }

    def _ok_evidence(self):
        return {
            "confirmed": [{
                "targeted_symbol": "Supprimer_LienContremarque",
                "context_sample": {"enclosing_block": {"name": "Supprimer_LienContremarque"}},
            }],
            "new_findings": [],
        }

    def test_cas_nominal_pas_d_erreur(self):
        errors, warns = preflight_check(self._ok_request(), self._ok_candidates(), self._ok_evidence())
        self.assertEqual([], errors)
        self.assertEqual([], warns)

    def test_type_absent_est_erreur(self):
        req = self._ok_request()
        req["type"] = ""
        errors, _ = preflight_check(req, self._ok_candidates(), self._ok_evidence())
        self.assertTrue(any("type" in e for e in errors))

    def test_type_unknown_est_erreur(self):
        req = self._ok_request()
        req["type"] = "unknown"
        errors, _ = preflight_check(req, self._ok_candidates(), self._ok_evidence())
        self.assertTrue(any("unknown" in e for e in errors))

    def test_resume_vide_est_erreur(self):
        req = self._ok_request()
        req["resume"] = ""
        errors, _ = preflight_check(req, self._ok_candidates(), self._ok_evidence())
        self.assertTrue(any("resume" in e for e in errors))

    def test_candidates_vides_est_erreur(self):
        cand = {"functions": [], "programs": [], "relations": {}, "neo4j_status": "available"}
        errors, _ = preflight_check(self._ok_request(), cand, self._ok_evidence())
        self.assertTrue(any("candidates" in e.lower() for e in errors))

    def test_candidates_vides_et_neo4j_down_est_warn_pas_erreur(self):
        """Si Neo4j est down, candidates vide est normal -- warn seulement."""
        cand = {"functions": [], "programs": [], "relations": {}, "neo4j_status": "unavailable"}
        errors, warns = preflight_check(self._ok_request(), cand, self._ok_evidence())
        # Pas d'erreur bloquante, mais warn car pas de functions pour un ticket
        self.assertEqual([], errors)
        self.assertTrue(any("chaine d'appels" in w.lower() or "functions" in w for w in warns))

    def test_evidence_vide_est_erreur(self):
        ev = {"confirmed": [], "new_findings": []}
        errors, _ = preflight_check(self._ok_request(), self._ok_candidates(), ev)
        self.assertTrue(any("evidence" in e.lower() for e in errors))

    def test_confirmed_sans_targeted_symbol_est_warn(self):
        ev = {
            "confirmed": [{"context_sample": {"enclosing_block": {"name": "X"}}}],
            "new_findings": [],
        }
        errors, warns = preflight_check(self._ok_request(), self._ok_candidates(), ev)
        self.assertEqual([], errors)
        self.assertTrue(any("targeted_symbol" in w for w in warns))

    def test_keywords_peu_nombreux_est_warn(self):
        req = self._ok_request()
        req["keywords_techniques"] = ["OnlyOne"]
        errors, warns = preflight_check(req, self._ok_candidates(), self._ok_evidence())
        self.assertEqual([], errors)
        self.assertTrue(any("keywords_techniques" in w for w in warns))

    def test_domaine_pressenti_absent_est_warn(self):
        req = self._ok_request()
        req["domaine_pressenti"] = None
        errors, warns = preflight_check(req, self._ok_candidates(), self._ok_evidence())
        self.assertEqual([], errors)
        self.assertTrue(any("domaine" in w for w in warns))


class TestVerbeToInfinitif(unittest.TestCase):
    """Heuristique de conversion 3e pers sing -> infinitif."""

    def test_er_singulier(self):
        self.assertEqual(_verbe_to_infinitif("active"), "activer")
        self.assertEqual(_verbe_to_infinitif("supprime"), "supprimer")
        self.assertEqual(_verbe_to_infinitif("passe"), "passer")
        self.assertEqual(_verbe_to_infinitif("modifie"), "modifier")

    def test_er_pluriel(self):
        self.assertEqual(_verbe_to_infinitif("activent"), "activer")
        self.assertEqual(_verbe_to_infinitif("suppriment"), "supprimer")

    def test_ir(self):
        self.assertEqual(_verbe_to_infinitif("finit"), "finir")
        self.assertEqual(_verbe_to_infinitif("reussit"), "reussir")

    def test_re(self):
        self.assertEqual(_verbe_to_infinitif("vend"), "vendre")

    def test_irreguliers(self):
        self.assertEqual(_verbe_to_infinitif("est"), "etre")
        self.assertEqual(_verbe_to_infinitif("fait"), "faire")
        self.assertEqual(_verbe_to_infinitif("dit"), "dire")
        self.assertEqual(_verbe_to_infinitif("doit"), "devoir")

    def test_inconnu_retourne_tel_quel(self):
        self.assertEqual(_verbe_to_infinitif("xyzzy"), "xyzzy")
        self.assertEqual(_verbe_to_infinitif(""), "")


if __name__ == "__main__":
    unittest.main()
