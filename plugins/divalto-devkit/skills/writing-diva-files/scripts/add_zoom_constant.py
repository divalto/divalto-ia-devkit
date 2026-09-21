"""
Ajoute une constante de zoom dans a5tczoom.dhsp.

Format genere :
    Const C_ZOOM_<NomInstance>_<NumZoom> = <NumZoom>    ;<Commentaire>

La constante est inseree avant le bloc de commentaires ";REGLE ECRITURE:"
situe en fin de fichier.

Usage:
    py add_zoom_constant.py --file <chemin> --instance <nom> --num <numero> --comment <texte>
    py add_zoom_constant.py --file a5tczoom.dhsp --instance MaEntite --num 9400 --comment "Ma nouvelle entite"

Sortie JSON:
    {
        "success": true/false,
        "file": "chemin",
        "constant_name": "C_ZOOM_MaEntite_9400",
        "constant_line": "Const C_ZOOM_MaEntite_9400 = 9400    ;Ma nouvelle entite",
        "line_number": 2294,
        "already_exists": false,
        "error": null
    }

Exit codes: 0 = succes, 1 = erreur utilisateur, 2 = erreur interne
"""

import argparse
import json
import os
import shutil
import sys

ENCODING = "iso-8859-1"
LINE_END = "\r\n"
MARKER = ";REGLE ECRITURE:"


def build_constant_line(instance, num, comment):
    """Construit la ligne de constante au format a5tczoom.dhsp."""
    name = f"C_ZOOM_{instance}_{num}"
    # Alignement : le nom est padde a 40 caracteres pour lisibilite
    padded_name = f"Const\t{name}".ljust(50)
    return f"{padded_name}=  {num}\t\t;{comment}", name


def main():
    # Sortie en UTF-8 (stdout + stderr) : sinon print() encode avec la console (cp1252 sur
    # Windows) et les caracteres non-ASCII cassent un json.loads(utf-8) cote appelant.
    # Meme garde-fou que read_isam.py.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
            _stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Ajoute une constante de zoom dans a5tczoom.dhsp"
    )
    parser.add_argument("--file", required=True, help="Chemin vers a5tczoom.dhsp")
    parser.add_argument("--instance", required=True, help="Nom de l'instance (ex: MaEntite)")
    parser.add_argument("--num", required=True, help="Numero du zoom (ex: 9400)")
    parser.add_argument("--comment", required=True, help="Commentaire (ex: Ma nouvelle entite)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche la ligne sans modifier le fichier")
    args = parser.parse_args()

    result = {
        "success": False,
        "file": args.file,
        "constant_name": None,
        "constant_line": None,
        "line_number": None,
        "already_exists": False,
        "error": None,
    }

    # Validation du numero
    try:
        num_val = int(args.num)
        if num_val <= 0:
            raise ValueError
    except ValueError:
        result["error"] = f"Numero de zoom invalide: {args.num} (entier positif attendu)"
        print(f"Erreur : {result['error']}", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Construction de la ligne
    constant_line, constant_name = build_constant_line(args.instance, args.num, args.comment)
    result["constant_name"] = constant_name
    result["constant_line"] = constant_line

    if args.dry_run:
        # Le dry-run doit VALIDER ce que l'ecriture reelle fera, sinon il donne une fausse
        # confiance : un caractere hors Latin-1 dans --comment (apostrophe typographique,
        # tiret cadratin...) passait le dry-run puis faisait echouer l'ecriture.
        try:
            constant_line.encode(ENCODING)
        except UnicodeEncodeError as e:
            result["error"] = (f"Caractere non encodable en {ENCODING} : {e}. "
                               f"Corriger --comment (apostrophe typographique, tiret cadratin ?) "
                               f"avant l'ecriture reelle.")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(1)
        result["success"] = True
        result["error"] = "dry-run: fichier non modifie"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Lecture du fichier
    if not os.path.isfile(args.file):
        result["error"] = f"Fichier introuvable: {args.file}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        with open(args.file, "r", encoding=ENCODING) as f:
            content = f.read()
    except Exception as e:
        result["error"] = f"Erreur lecture: {e}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    # Verifier que la constante n'existe pas deja
    if constant_name in content:
        result["already_exists"] = True
        result["error"] = f"La constante {constant_name} existe deja dans le fichier"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Verifier que le numero n'est pas deja utilise (avec un autre nom)
    search_pattern = f"=  {args.num}\t"
    if search_pattern in content:
        result["error"] = f"Le numero de zoom {args.num} est deja utilise dans le fichier"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Trouver le marqueur d'insertion
    lines = content.split("\n")
    # Nettoyer les \r en fin de ligne
    lines = [line.rstrip("\r") for line in lines]

    insert_index = None
    for i, line in enumerate(lines):
        if line.startswith(MARKER):
            insert_index = i
            break

    if insert_index is None:
        # Si le marqueur n'est pas trouve, inserer en fin de fichier
        insert_index = len(lines)
        # Ajouter une ligne vide avant si necessaire
        if lines and lines[-1].strip():
            lines.append("")
            insert_index = len(lines)

    # Inserer la constante
    lines.insert(insert_index, constant_line)
    result["line_number"] = insert_index + 1  # 1-indexed

    # Reecrire le fichier en ISO-8859-1 + CRLF.
    #
    # ORDRE CRITIQUE : encoder AVANT d'ouvrir la cible. `open(..., "w")` TRONQUE le fichier
    # a l'ouverture ; si l'encodage ISO-8859-1 echoue ensuite (un seul caractere hors Latin-1
    # dans --comment suffit : apostrophe typographique, tiret cadratin, emoji), la cible reste
    # a 0 octet et le travail est perdu. C'est la meme classe de data-loss que celle corrigee
    # dans patch_file.py -- ce script y avait echappe.
    output = LINE_END.join(lines)
    if not output.endswith(LINE_END):
        # CRLF final obligatoire : sans lui, la compilation echoue (Erreur 135). Le cas
        # arrivait quand le marqueur d'insertion etait absent (insertion en fin de fichier).
        output += LINE_END
    try:
        encoded = output.encode(ENCODING)
    except UnicodeEncodeError as e:
        result["error"] = (f"Caractere non encodable en {ENCODING} : {e}. "
                           f"RIEN n'a ete ecrit, le fichier est intact. "
                           f"Corriger --comment (apostrophe typographique, tiret cadratin ?).")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Backup avant ecriture (comme write_file/patch_file/convert_file) : ce script en etait
    # le seul depourvu, donc le seul ou une ecriture ratee ne laissait rien a restaurer.
    try:
        backup = args.file + ".bak"
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copyfile(args.file, backup)
        result["backup"] = os.path.abspath(backup)
    except Exception as e:
        print(f"Avertissement: backup non cree ({e})", file=sys.stderr)
        result["backup"] = None

    try:
        with open(args.file, "wb") as f:
            f.write(encoded)
    except Exception as e:
        result["error"] = f"Erreur ecriture: {e}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    result["success"] = True
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
