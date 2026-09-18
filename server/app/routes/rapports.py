"""Exports Excel et PDF (chantier C8, cycle 10, CDC §3.7/§3.14).

Principe non négociable rappelé par le propriétaire : le gating du prix de
vente selon le rôle de l'exportateur est une exigence du cahier des
charges, et c'est une fuite classique quand un export contourne le
masquage appliqué à l'écran. Il est donc posé ICI, dans la clause
``SELECT`` elle-même — jamais en filtrant des colonnes après coup dans le
fichier — en réutilisant l'unique liste blanche de ``colonnes.py`` (la même
que ``GET /articles``, cycle 3). Un agent stock ne reçoit tout simplement
jamais les colonnes de prix depuis PostgreSQL : il n'y a rien à retirer du
fichier parce qu'elles n'ont jamais existé dans les lignes en mémoire.

Deux exports, correspondant chacun au périmètre déjà établi pour ce rôle
ailleurs dans l'application :
  * ``/rapports/articles`` — catalogue articles/stock, les 3 rôles (mêmes
    colonnes que ``GET /articles``), aucune notion de période (un
    catalogue est un instantané, pas un historique).
  * ``/rapports/ventes`` — ventes payées sur une période, responsable et
    agent comptabilité seulement (mêmes rôles que ``GET
    /ventes/synthese-jour`` — un agent stock n'a de toute façon aucun
    privilège sur la table ``ventes``, migration 008). ``numero_facture``
    (facture fiscale détaillée) reste restitué tel quel, y compris NULL :
    non tranché. ``numero_facturier`` (référence du carnet papier, point c
    de l'addendum, décidé le 2026-09-13, cycle 27) est obligatoire sur
    toute vente depuis ce cycle, NULL pour les ventes antérieures.

Hors périmètre, volontairement : clôture de caisse (point g, non tranché),
export de l'historique de comptages (route JSON seule, pas de fichier ce
cycle-ci).
"""

from __future__ import annotations

from datetime import date as _date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from ..colonnes import COLONNES_ARTICLES
from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..securite import Session

routeur = APIRouter(prefix="/rapports", tags=["rapports"])

_TYPES_MIME = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _classeur_xlsx(colonnes: list[str], lignes: list[dict]) -> bytes:
    classeur = Workbook()
    feuille = classeur.active
    feuille.append(colonnes)
    for ligne in lignes:
        feuille.append([_valeur_cellule(ligne[c]) for c in colonnes])
    tampon = BytesIO()
    classeur.save(tampon)
    return tampon.getvalue()


def _pdf_tableau(titre: str, colonnes: list[str], lignes: list[dict]) -> bytes:
    tampon = BytesIO()
    document = SimpleDocTemplate(tampon, pagesize=A4, title=titre)
    donnees = [colonnes] + [[str(_valeur_cellule(ligne[c])) for c in colonnes] for ligne in lignes]
    tableau = Table(donnees, repeatRows=1)
    tableau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    document.build([tableau])
    return tampon.getvalue()


def _valeur_cellule(valeur):
    # openpyxl refuse d'écrire certains types (Decimal passe, mais on
    # normalise ici pour que le PDF (str()) et le classeur affichent la
    # même chose sans divergence de formatage.
    return valeur if valeur is not None else ""


def _reponse_fichier(contenu: bytes, format_: str, nom_base: str) -> Response:
    return Response(
        content=contenu,
        media_type=_TYPES_MIME[format_],
        headers={"Content-Disposition": f'attachment; filename="{nom_base}.{format_}"'},
    )


def _valider_format(format: str) -> str:  # noqa: A002 - nom du paramètre de requête
    if format not in _TYPES_MIME:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Format inconnu (xlsx ou pdf).")
    return format


@routeur.get("/articles")
def exporter_articles(
    request: Request,
    format: str = Query(...),  # noqa: A002
    session: Session = Depends(exiger_role("responsable", "agent_stock", "agent_comptabilite")),
):
    """Catalogue articles/stock, colonnes gatées par rôle EN SQL — voir le
    docstring du module. Instantané : aucun filtre de période."""
    format_ = _valider_format(format)
    colonnes = [c.strip() for c in COLONNES_ARTICLES[session.role].split(",")]

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {COLONNES_ARTICLES[session.role]} FROM articles WHERE actif = TRUE ORDER BY nom"  # noqa: S608
                # Pas d'injection : `COLONNES_ARTICLES[session.role]` vient
                # d'une whitelist fixe à 3 valeurs indexée par le rôle de la
                # session, jamais d'une entrée de la requête HTTP — même
                # garantie que GET /articles (routes/demonstration.py).
            )
            lignes = cur.fetchall()

    if format_ == "xlsx":
        contenu = _classeur_xlsx(colonnes, lignes)
    else:
        contenu = _pdf_tableau("Catalogue articles", colonnes, lignes)
    return _reponse_fichier(contenu, format_, "articles")


@routeur.get("/ventes")
def exporter_ventes(
    request: Request,
    date_debut: str,
    date_fin: str,
    format: str = Query(...),  # noqa: A002
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Ventes payées sur une période — responsable et agent comptabilité
    seulement (un agent stock n'a aucun privilège sur ``ventes``,
    migration 008 : il n'atteint même pas cette route, ``exiger_role`` le
    refuse avant d'aller inutilement jusqu'à la base)."""
    format_ = _valider_format(format)
    try:
        debut = _date.fromisoformat(date_debut)
        fin = _date.fromisoformat(date_fin)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_debut et date_fin doivent être au format AAAA-MM-JJ.",
        ) from exc
    if debut > fin:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_debut ne peut pas être postérieure à date_fin.",
        )

    colonnes = [
        "id", "site_id", "numero_facture", "numero_facturier", "mode_paiement",
        "sous_total_ht", "taux_tva", "montant_tva", "total_ttc", "date_encaissement",
    ]
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {", ".join(colonnes)}
                  FROM ventes
                 WHERE statut = 'payee'
                   AND date_encaissement::date BETWEEN %s AND %s
                 ORDER BY date_encaissement
                """,  # noqa: S608 - `colonnes` est une constante fixe ci-dessus, jamais une entrée HTTP
                (debut, fin),
            )
            lignes = cur.fetchall()

    if format_ == "xlsx":
        contenu = _classeur_xlsx(colonnes, lignes)
    else:
        contenu = _pdf_tableau("Ventes", colonnes, lignes)
    return _reponse_fichier(contenu, format_, "ventes")
