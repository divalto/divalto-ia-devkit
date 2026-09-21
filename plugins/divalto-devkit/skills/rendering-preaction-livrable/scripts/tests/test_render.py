"""Tests du renderer + validator anti-ref."""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_livrable import _render, validate_livrable  # noqa: E402


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
# Reutilise la fixture nominale du skill amont pour eviter la duplication
AMONT_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "building-preaction-report"
    / "scripts"
    / "tests"
    / "fixtures"
    / "ticket-contremarque.facts.json"
)


def _load_fixture() -> dict:
    with open(AMONT_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


class TestRender(unittest.TestCase):

    def setUp(self):
        self.facts = _load_fixture()
        self.rendered = _render(self.facts)

    def test_render_succeeds(self):
        self.assertIsInstance(self.rendered, str)
        self.assertGreater(len(self.rendered), 100)

    def test_has_three_layers(self):
        self.assertIn("## Strategique", self.rendered)
        self.assertIn("## Tactique", self.rendered)
        self.assertIn("## Technique", self.rendered)

    def test_has_verdict(self):
        self.assertIn("**Verdict**", self.rendered)

    def test_has_panorama(self):
        self.assertIn("**Panorama de l'analyse**", self.rendered)

    def test_size_under_200_lines(self):
        """CA11 cible : livrable < 200 lignes pour un ticket typique."""
        line_count = len(self.rendered.splitlines())
        self.assertLess(line_count, 200, f"livrable fait {line_count} lignes")

    def test_no_absolute_path(self):
        """Aucun chemin `C:/...` ou `C:\\...` dans le livrable."""
        self.assertNotIn("C:/", self.rendered)
        self.assertNotIn("C:\\", self.rendered)

    def test_no_line_reference(self):
        """Aucun `fichier.dhsp:123` dans le livrable (noms courts uniquement)."""
        import re
        matches = re.findall(r"\b[a-zA-Z0-9_-]+\.dhs[pq]:\d+", self.rendered)
        self.assertEqual(
            matches,
            [],
            f"Le livrable contient des refs fichier:ligne: {matches}",
        )

    def test_no_x12_x13_marker(self):
        """Aucun marqueur [X.12] / [CONFIRME X.13] / etc dans le livrable."""
        import re
        markers = re.findall(
            r"\[X\.1[23]\]|\[(?:CONFIRME|DISPARU|NOUVEAU)\s+X\.1[23]\]",
            self.rendered,
        )
        self.assertEqual(
            markers,
            [],
            f"Le livrable contient des marqueurs X.12/X.13: {markers}",
        )

    def test_passes_validator(self):
        violations = validate_livrable(self.rendered)
        self.assertEqual(violations, [], f"violations : {violations}")


class TestValidator(unittest.TestCase):
    """Tests unitaires du validator (cas pathologiques)."""

    def test_detects_absolute_path(self):
        md = "Voir le fichier C:/Developpements/foo.dhsp pour details."
        violations = validate_livrable(md)
        self.assertTrue(any("chemin absolu" in v for v in violations))

    def test_detects_x12_marker(self):
        md = "Cette piste est [X.12] advisory."
        violations = validate_livrable(md)
        self.assertTrue(any("marqueur de statut" in v for v in violations))

    def test_detects_status_markers_toutes_formes(self):
        """Aucun marqueur de statut ne doit fuir dans le livrable externe.

        Le test porte sur le COMPORTEMENT (le marqueur est-il intercepte ?), pas sur le
        libelle du message -- l'assertion precedente cherchait la chaine "X.12/X.13" dans
        le message, ce qui la rendait fragile au moindre reformulage.

        Les formes sans numero de version sont les plus importantes : `verify_x13.py` emet
        desormais des statuts NEUTRES (il lit la racine qu'on lui donne sans savoir quelle
        version elle contient). Un garde-fou exigeant `X.12`/`X.13` apres le mot de statut
        les laissait FUIR -- et laissait deja fuir `[CONFIRME X.7]` chez un partenaire
        travaillant contre une autre version.
        """
        formes = [
            "[X.12]", "[X.13]", "[X.7]", "[X.11]",
            "[CONFIRME]", "[DISPARU]", "[NOUVEAU]",
            "[CONFIRME X.13]", "[DISPARU X.12]", "[NOUVEAU X.7]",
        ]
        for marqueur in formes:
            with self.subTest(marqueur=marqueur):
                violations = validate_livrable(f"La procedure {marqueur} existe.")
                self.assertTrue(
                    any("marqueur de statut" in v for v in violations),
                    f"{marqueur} a fui dans le livrable externe",
                )

    def test_texte_propre_sans_marqueur_passe(self):
        """Garde-fou : le motif elargi ne doit pas intercepter du texte legitime."""
        for md in ("La procedure existe et le comportement est conforme.",
                   "Voir la section [Analyse] du document.",
                   "Le tableau [1] recapitule les cas."):
            with self.subTest(md=md):
                violations = validate_livrable(md)
                self.assertFalse([v for v in violations if "marqueur de statut" in v],
                                 f"faux positif sur : {md}")

    def test_detects_todo(self):
        md = "TODO : verifier ce point."
        violations = validate_livrable(md)
        self.assertTrue(any("TODO" in v for v in violations))

    def test_detects_pronoun_fragment(self):
        md = "- **Observe** : qui se produit quand on clique sur le bouton."
        violations = validate_livrable(md)
        self.assertTrue(any("pronom relatif" in v for v in violations))

    def test_detects_mermaid_html(self):
        md = """```mermaid
flowchart TD
    A["<code>Test</code>"]
```"""
        violations = validate_livrable(md)
        self.assertTrue(any("HTML" in v for v in violations))

    def test_detects_italic_with_placeholder(self):
        md = "_Un texte avec <champ> dedans._"
        violations = validate_livrable(md)
        self.assertTrue(any("italique" in v for v in violations))

    def test_clean_markdown_passes(self):
        md = (
            "# Rapport\n\n"
            "## Section\n\n"
            "Contenu sans stub ni reference. La procedure `Foo_Bar` "
            "dans `myfile.dhsp` fait quelque chose."
        )
        violations = validate_livrable(md)
        self.assertEqual(violations, [])


class TestPerClaimKind(unittest.TestCase):
    """Test que chaque kind de claim produit bien un fragment."""

    def setUp(self):
        self.facts = _load_fixture()
        self.rendered = _render(self.facts)

    def test_example_claims_rendered(self):
        # Au moins 1 exemple dans la couche tactique
        self.assertIn("### Exemples a etudier", self.rendered)

    def test_action_site_claims_rendered(self):
        self.assertIn("### Plan d'action", self.rendered)
        self.assertIn("**Proposition 1.**", self.rendered)

    def test_call_chain_rendered_as_mermaid(self):
        self.assertIn("### Chaine d'appels", self.rendered)
        self.assertIn("```mermaid", self.rendered)
        self.assertIn("flowchart TD", self.rendered)

    def test_verification_rendered(self):
        self.assertIn("### Commandes de verification", self.rendered)

    def test_literal_table_rendered_in_technical(self):
        # Le fixture ticket-contremarque a une table Ce4
        # Elle doit apparaitre dans la couche technique
        idx_tech = self.rendered.find("## Technique")
        self.assertGreater(idx_tech, 0)
        tech_section = self.rendered[idx_tech:]
        # Au moins un des kinds attendus en couche technique
        has_technical_content = any(
            marker in tech_section
            for marker in (
                "Constantes et codes metier",
                "Parametrage dossier",
                "Points d'attention",
                "Fonctions du langage",
            )
        )
        self.assertTrue(has_technical_content)


class TestEmptyLayers(unittest.TestCase):
    """Tests de robustesse : couches partiellement vides."""

    def test_only_strategic_layer(self):
        """Facts avec aucun claim : seule la couche strategique est rendue."""
        facts = _load_fixture()
        facts["claims"] = []
        # Selection inclus mais sans claim (edge case)
        facts["selection"] = [s for s in facts["selection"] if not s["included"]]
        rendered = _render(facts)
        self.assertIn("## Strategique", rendered)
        # Les couches tactique/technique devraient etre absentes
        self.assertNotIn("## Tactique", rendered)
        self.assertNotIn("## Technique", rendered)

    def test_render_without_verdict_action(self):
        facts = _load_fixture()
        facts = copy.deepcopy(facts)
        facts["verdict"]["action_critique_id"] = None
        rendered = _render(facts)
        # Le rendu ne doit pas echouer, et la section "Action prioritaire"
        # doit etre absente si aucun action_critique ne peut etre determine
        # (le template itere sur action_critique seulement si pose)
        self.assertIn("**Verdict**", rendered)


class TestPanoramaLibelles(unittest.TestCase):
    """Le panorama de la couche strategique ne doit pas exposer le jargon du pipeline.

    Cette couche s'adresse a un **chef de projet** (2 minutes, savoir *quoi*). Un retour
    terrain a signale qu'elle affichait les slugs bruts -- `endroit_agir`,
    `verification_prealable` -- et que le lecteur avait du demander ce que ca voulait dire.

    Le libelle vient de `facts.selection[].title`, emis par le skill amont depuis
    `content_types.py`. **Aucune table de libelles n'est tenue ici** : deux tables
    finiraient par diverger.
    """

    TITRES = {
        4: "Endroit ou agir", 10: "Verification prealable (commandes)",
        7: "Constantes et conventions metier", 1: "Exemples de code DIVA",
        3: "Etude d'impact", 8: "Parametrage dossier",
        5: "Pistes de recherche complementaires", 2: "Fonctions du langage DIVA utiles",
        6: "Points d'attention",
    }

    def _panorama(self, facts):
        lignes = [l for l in _render(facts).split("\n")
                  if l.startswith("Types inclus") or l.startswith("Types omis")]
        self.assertTrue(lignes, "le panorama a disparu de la couche strategique")
        return "\n".join(lignes)

    def _avec_titres(self):
        facts = copy.deepcopy(_load_fixture())
        for s in facts["selection"]:
            s["title"] = self.TITRES[s["id"]]
        return facts

    def test_panorama_affiche_le_libelle_humain(self):
        panorama = self._panorama(self._avec_titres())
        self.assertIn("Endroit ou agir", panorama)
        self.assertIn("Fonctions du langage DIVA utiles", panorama)

    def test_aucun_slug_de_pipeline_dans_le_panorama(self):
        """L'invariant : c'est l'ABSENCE des slugs qui prouve l'intention tenue."""
        panorama = self._panorama(self._avec_titres())
        for slug in ("endroit_agir", "verification_prealable", "parametrage_dossier",
                     "constantes_metier", "pistes_recherche", "fonctions_langage"):
            self.assertNotIn(slug, panorama,
                             "le slug %r reste visible dans une couche destinee a un "
                             "chef de projet" % slug)

    def test_repli_sur_le_slug_si_le_libelle_manque(self):
        """Retrocompatibilite : un facts.json anterieur n'a pas le champ `title`."""
        facts = copy.deepcopy(_load_fixture())
        for s in facts["selection"]:
            s.pop("title", None)
        panorama = self._panorama(facts)
        self.assertIn("endroit_agir", panorama,
                      "sans libelle, le panorama doit retomber sur le slug -- pas se vider")

    def test_libelle_vide_traite_comme_absent(self):
        facts = copy.deepcopy(_load_fixture())
        for s in facts["selection"]:
            s["title"] = ""
        panorama = self._panorama(facts)
        self.assertIn("endroit_agir", panorama,
                      "un libelle vide doit se comporter comme un libelle absent")

    def test_aucune_table_de_libelles_dans_ce_skill(self):
        """Garde-fou d'architecture : le libelle vient de l'amont, pas d'ici.

        Une seconde table de libelles a cote de `content_types.py` divergerait -- c'est
        le motif d'asymetrie entre scripts freres que le workspace suit.
        """
        # Chercher un USAGE, pas une MENTION : les commentaires citent les slugs pour
        # expliquer POURQUOI on ne les affiche pas. Ce controle les retire d'abord --
        # sans quoi il tombe sur l'explication de la regle qu'il fait respecter.
        # (Il l'a fait au premier lancement.)
        skill = Path(__file__).resolve().parents[2]
        for chemin in list(skill.rglob("*.py")) + list(skill.rglob("*.j2")):
            if "tests" in chemin.parts:
                continue
            texte = chemin.read_text(encoding="utf-8")
            texte = re.sub(r"\{#.*?#\}", "", texte, flags=re.S)          # commentaires Jinja
            texte = re.sub(r"^\s*#.*$", "", texte, flags=re.M)           # commentaires Python
            texte = re.sub(r'"""(?:.|\n)*?"""', "", texte)               # docstrings
            for slug in ("endroit_agir", "verification_prealable", "constantes_metier"):
                self.assertNotIn(
                    slug, texte,
                    "%s cite le slug %r hors commentaire : une table de libelles locale "
                    "est en train d'apparaitre" % (chemin.name, slug))


if __name__ == "__main__":
    unittest.main()
