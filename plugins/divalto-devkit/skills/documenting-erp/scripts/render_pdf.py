#!/usr/bin/env python3
"""render_pdf.py -- Convertit un Markdown en PDF via Chrome/Edge headless.

Chaine de conversion : Markdown -> HTML (lib python `markdown`) -> PDF (browser headless).

Rendu des diagrammes Mermaid : les blocs ```mermaid ...``` sont convertis en
<div class="mermaid"> puis rendus cote browser par mermaid.js charge depuis le
CDN jsdelivr. Zero install requis (juste Chrome/Edge + acces internet). Si le
CDN est inaccessible, le bloc reste visible comme code source (degradation
gracieuse -- pas d'echec de generation).

Usage :
  py render_pdf.py --input DAV.md --output DAV.pdf
  py render_pdf.py --input DAV.md --output DAV.pdf --title "Documentation technique DAV"
  py render_pdf.py --input DAV.md --output DAV.pdf --no-mermaid  # desactive le rendu JS
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import pathname2url

import re

try:
    import markdown
except ImportError:
    print("ERREUR : markdown requis. Installer : py -m pip install markdown", file=sys.stderr)
    sys.exit(2)


# Mermaid via CDN jsdelivr : zero install, rendu cote browser. La version figee (@10)
# evite les breakings sans test. L'acces internet est requis au moment du rendu PDF.
_MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"

# Duree laissee a Chrome headless pour executer mermaid.js avant --print-to-pdf.
# 5s suffisent en pratique pour un module DAV (~5 diagrammes).
_MERMAID_RENDER_DELAY_MS = 5000


def _mermaid_head() -> str:
    """Retourne le fragment HTML <script> pour charger et initialiser mermaid.js."""
    return (
        f'<script src="{_MERMAID_CDN_URL}"></script>\n'
        '<script>\n'
        '  mermaid.initialize({ startOnLoad: true, theme: "default", '
        'flowchart: { useMaxWidth: true, htmlLabels: true } });\n'
        '</script>\n'
    )


def _convert_mermaid_blocks(html: str) -> str:
    """Convertit les blocs <pre><code class="language-mermaid">...</code></pre> produits
    par la lib `markdown` en <div class="mermaid">...</div> consommes par mermaid.js.
    """
    pattern = re.compile(
        r'<pre><code[^>]*class="[^"]*language-mermaid[^"]*"[^>]*>(.*?)</code></pre>',
        re.DOTALL,
    )

    def replace(m):
        # mermaid.js attend le source brut, pas du HTML echappe. La lib markdown
        # produit deja du HTML echappe : &lt; &gt; &amp; -> on reconvertit.
        code = m.group(1)
        code = code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        return f'<div class="mermaid">\n{code}\n</div>'

    return pattern.sub(replace, html)


# Chemins candidats pour un browser headless sur Windows standard (installation classique).
# Chrome en premier : Edge se heurte souvent a un conflit de user-data-dir si une instance
# Edge est deja ouverte cote utilisateur. Le premier trouve est utilise.
BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


# Feuille de style minimale pour un PDF lisible.
# Orientee documentation technique : serif pour le corps, monospace pour le code,
# cellules de table compactes, marges A4 classiques.
DEFAULT_CSS = """
@page {
  size: A4;
  margin: 2cm 1.8cm 2cm 1.8cm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #777; }
}
html { font-size: 10pt; }
body {
  font-family: "Segoe UI", "Calibri", Arial, sans-serif;
  color: #222;
  line-height: 1.45;
}
h1 { font-size: 22pt; color: #0F3D68; border-bottom: 2px solid #0F3D68; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 16pt; color: #0F3D68; margin-top: 1.6em; border-bottom: 1px solid #BBB; padding-bottom: 2px; }
h3 { font-size: 13pt; color: #225; margin-top: 1.3em; }
h4 { font-size: 11pt; color: #444; margin-top: 1em; text-transform: uppercase; letter-spacing: 0.3px; }
p, li { font-size: 10pt; }
code {
  font-family: Consolas, "Courier New", monospace;
  background: #F3F5F8;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 9.5pt;
}
pre {
  background: #F3F5F8;
  padding: 8px 10px;
  border-left: 3px solid #0F3D68;
  overflow-x: auto;
  font-size: 9pt;
}
pre code { background: transparent; padding: 0; }
table {
  border-collapse: collapse;
  margin: 0.6em 0;
  width: 100%;
  font-size: 9pt;
}
th, td {
  border: 1px solid #CCD;
  padding: 3px 6px;
  text-align: left;
  vertical-align: top;
}
th { background: #E8EEF5; font-weight: 600; }
tr:nth-child(even) td { background: #FAFBFD; }
blockquote {
  border-left: 3px solid #CCA900;
  background: #FFFBE5;
  padding: 8px 12px;
  margin: 0.6em 0;
  font-size: 9.5pt;
}
hr { border: 0; border-top: 1px solid #CCC; margin: 1.5em 0; }
em { color: #555; }
/* liens internes (ancres) : conservent la couleur mais sans sous-lignage distrayant dans un PDF */
a { color: #0F3D68; text-decoration: none; }
a:hover { text-decoration: underline; }
/* Diagrammes Mermaid : forcer a tenir sur une page, ne pas couper au milieu.
   Chrome respecte `break-inside: avoid` en print-to-pdf, `page-break-inside: avoid`
   est le fallback historique. `max-width: 100%` empeche un debordement horizontal. */
.mermaid {
  break-inside: avoid;
  page-break-inside: avoid;
  max-width: 100%;
  margin: 1em 0;
  text-align: center;
}
.mermaid svg { max-width: 100%; height: auto; }
/* bloc specifique : items [A VERIFIER] en couleur warning */
li:has(strong:first-child) { /* fallback simple */ }
"""


def find_browser() -> Path:
    env = os.environ.get("DOCERP_BROWSER")
    if env and Path(env).exists():
        return Path(env)
    # 1) PATH
    for name in ("chrome", "msedge", "chrome.exe", "msedge.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    # 2) chemins d'installation classiques Windows
    for cand in BROWSER_CANDIDATES:
        if Path(cand).exists():
            return Path(cand)
    raise RuntimeError(
        "Aucun browser headless trouve. Installer Chrome ou Edge, "
        "ou definir DOCERP_BROWSER=<chemin> dans l'environnement."
    )


def md_to_html(md_path: Path, title: str, enable_mermaid: bool = True) -> str:
    with md_path.open(encoding="utf-8") as f:
        text = f.read()
    # Injecte un sommaire cliquable juste apres le H1 du document. L'extension `toc`
    # remplace [TOC] par la liste des titres H2/H3 avec liens intra-document (Chrome
    # headless conserve ces liens dans le PDF final).
    text = re.sub(
        r"^(# [^\n]+\n)",
        r"\1\n## Sommaire\n\n[TOC]\n\n",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    # Extensions : tables, code fences, toc, attr_list (pour ancres), def_list
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "toc", "attr_list", "def_list", "sane_lists"],
        output_format="html5",
    )
    mermaid_head = ""
    if enable_mermaid:
        body = _convert_mermaid_blocks(body)
        mermaid_head = _mermaid_head()
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{DEFAULT_CSS}</style>
{mermaid_head}</head>
<body>
{body}
</body>
</html>
"""


def html_to_pdf(html_path: Path, pdf_path: Path, browser: Path,
                 virtual_time_budget_ms: int = 0) -> None:
    # URL file:// avec forward slashes et chemin absolu resolu.
    html_url = "file:///" + str(html_path.resolve()).replace("\\", "/")
    # Chemin PDF absolu en forward slashes (Chrome accepte, evite les surprises).
    pdf_str = str(pdf_path.resolve()).replace("\\", "/")
    # user-data-dir dedie : evite les conflits si le browser est deja ouvert cote utilisateur.
    user_data = tempfile.mkdtemp(prefix="docerp_browser_")
    base_args = [
        str(browser),
        f"--user-data-dir={user_data}",
        "--disable-gpu",
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_str}",
    ]
    # virtual-time-budget laisse tourner le JS (mermaid.js) avant le snapshot PDF.
    # Sans ca, Chrome imprime avant que mermaid ait eu le temps de remplacer les
    # <div class="mermaid"> par des SVG.
    if virtual_time_budget_ms > 0:
        base_args.append(f"--virtual-time-budget={virtual_time_budget_ms}")
    base_args.append(html_url)
    try:
        # 1er essai : --headless=new (Chrome 109+, Edge recents)
        cmd = [base_args[0], "--headless=new"] + base_args[1:]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if not pdf_path.exists():
            # Fallback : --headless (ancien mode, plus compatible)
            cmd = [base_args[0], "--headless"] + base_args[1:]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if not pdf_path.exists():
            raise RuntimeError(
                f"Conversion PDF echouee. Browser={browser}. "
                f"exit={proc.returncode} "
                f"stdout={proc.stdout[:300]} stderr={proc.stderr[:300]}"
            )
    finally:
        import shutil as _sh
        _sh.rmtree(user_data, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="Chemin du Markdown source")
    ap.add_argument("--output", required=True, help="Chemin du PDF a produire")
    ap.add_argument("--title", help="Titre HTML (defaut : nom du fichier md)")
    ap.add_argument("--keep-html", action="store_true",
                    help="Conserve le HTML intermediaire a cote du PDF")
    ap.add_argument("--no-mermaid", action="store_true",
                    help="Desactive le rendu des diagrammes Mermaid via mermaid.js CDN. "
                         "Les blocs ```mermaid restent visibles comme code source. "
                         "A utiliser quand l'acces internet au CDN jsdelivr est indisponible.")
    ap.add_argument("--mermaid-delay-ms", type=int, default=_MERMAID_RENDER_DELAY_MS,
                    help=f"Duree (ms) laissee a Chrome pour executer mermaid.js avant impression. "
                         f"Defaut : {_MERMAID_RENDER_DELAY_MS}. Passer 0 pour desactiver le delai "
                         f"(sans rendu Mermaid fiable).")
    args = ap.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(json.dumps({"error": f"markdown introuvable : {md_path}"}), file=sys.stderr)
        sys.exit(1)

    enable_mermaid = not args.no_mermaid
    title = args.title or md_path.stem
    html_content = md_to_html(md_path, title, enable_mermaid=enable_mermaid)

    pdf_path = Path(args.output)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # ecrire le HTML intermediaire (permanent si --keep-html, sinon temporaire)
    if args.keep_html:
        html_path = pdf_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        used_html = html_path
        tmp_dir = None
    else:
        tmp_dir = tempfile.mkdtemp(prefix="docerp_")
        used_html = Path(tmp_dir) / (md_path.stem + ".html")
        used_html.write_text(html_content, encoding="utf-8")

    try:
        browser = find_browser()
        # Si Mermaid est actif, laisser a Chrome le temps d'executer le JS avant print.
        virtual_time = args.mermaid_delay_ms if enable_mermaid else 0
        html_to_pdf(used_html, pdf_path, browser, virtual_time_budget_ms=virtual_time)
    finally:
        if tmp_dir:
            import shutil as _sh
            _sh.rmtree(tmp_dir, ignore_errors=True)

    summary = {
        "input": str(md_path),
        "output": str(pdf_path),
        "size_bytes": pdf_path.stat().st_size,
        "browser": str(browser),
        "html_kept": str(used_html) if args.keep_html else None,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
