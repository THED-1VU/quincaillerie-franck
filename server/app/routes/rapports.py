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

Trois exports, correspondant chacun au périmètre déjà établi pour ce rôle
ailleurs dans l'application :
  * ``/rapports/articles`` — catalogue articles/stock, les 3 rôles (mêmes
    colonnes que ``GET /articles``), aucune notion de période (un
    catalogue est un instantané, pas un historique).
  * ``/rapports/stock`` — stock valorisé par site (quantités, valorisation
    aux prix d'achat et de vente, alertes de seuil), RESPONSABLE SEULEMENT
    (cycle 67, écart C4-02) : ``prix_achat`` n'est un privilège que du rôle
    responsable (migration 008), et l'agent stock conserve son export
    catalogue sans ce prix (``/rapports/articles``).
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
    docstring du module. Instantané : aucun filtre de période. Le modèle
    multi-site (cycle 35) : une fiche, un stock par site ; l'export du
    responsable porte une ligne par (article, site)."""
    format_ = _valider_format(format)

    if session.role == "responsable":
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_achat, a.prix_vente,
                   s.site_id, s.quantite_stock, s.seuil_alerte
              FROM articles a
              JOIN stocks_sites s ON s.article_id = a.id
             WHERE a.actif = TRUE
             ORDER BY a.nom, s.site_id
        """
        colonnes = ["id", "nom", "unite", "prix_achat", "prix_vente",
                    "site_id", "quantite_stock", "seuil_alerte"]
    elif session.role == "agent_stock":
        requete = """
            SELECT a.id, a.nom, a.unite,
                   COALESCE(s.site_id, qf_site_courant()) AS site_id,
                   COALESCE(s.quantite_stock, 0) AS quantite_stock,
                   COALESCE(s.seuil_alerte, 0) AS seuil_alerte
              FROM articles a
              LEFT JOIN stocks_sites s
                ON s.article_id = a.id AND s.site_id = qf_site_courant()
             WHERE a.actif = TRUE
             ORDER BY a.nom
        """
        colonnes = ["id", "nom", "unite", "site_id", "quantite_stock", "seuil_alerte"]
    else:
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_vente
              FROM articles a
             WHERE a.actif = TRUE
             ORDER BY a.nom
        """
        colonnes = ["id", "nom", "unite", "prix_vente"]

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(requete)
            lignes = cur.fetchall()

    if format_ == "xlsx":
        contenu = _classeur_xlsx(colonnes, lignes)
    else:
        contenu = _pdf_tableau("Catalogue articles", colonnes, lignes)
    return _reponse_fichier(contenu, format_, "articles")


@routeur.get("/stock")
def exporter_stock(
    request: Request,
    format: str = Query(...),  # noqa: A002
    session: Session = Depends(exiger_role("responsable")),
):
    """Stock valorisé par site — responsable seulement (cycle 67, écart
    C4-02 du registre). Une ligne par (article, site) portant quantités,
    seuil, prix d'achat, prix de vente, valorisations calculées EN SQL et
    état d'alerte (RUPTURE / SOUS_SEUIL / OK). Le xlsx ajoute une feuille
    « totaux par site » (valorisation globale, nombres de ruptures et de
    lignes sous le seuil) ; le PDF reste le tableau plat, comme les autres
    exports. L'agent stock conserve son export catalogue sans prix d'achat
    (``/rapports/articles``) : ``prix_achat`` n'est jamais restitué à un
    rôle qui n'en a pas le privilège en base (migration 008)."""
    format_ = _valider_format(format)
    colonnes = [
        "id", "nom", "unite", "site_id", "quantite_stock", "seuil_alerte",
        "prix_achat", "prix_vente", "valorisation_achat", "valorisation_vente",
        "alerte",
    ]
    colonnes_totaux = ["site_id", "total_achat", "total_vente", "nb_ruptures", "nb_sous_seuil"]

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.nom, a.unite, s.site_id, s.quantite_stock, s.seuil_alerte,
                       a.prix_achat, a.prix_vente,
                       s.quantite_stock * a.prix_achat AS valorisation_achat,
                       s.quantite_stock * a.prix_vente AS valorisation_vente,
                       CASE
                           WHEN s.quantite_stock <= 0 THEN 'RUPTURE'
                           WHEN s.quantite_stock <= s.seuil_alerte THEN 'SOUS_SEUIL'
                           ELSE 'OK'
                       END AS alerte
                  FROM articles a
                  JOIN stocks_sites s ON s.article_id = a.id
                 WHERE a.actif = TRUE
                 ORDER BY s.site_id, a.nom
                """
            )
            lignes = cur.fetchall()
            cur.execute(
                """
                SELECT s.site_id,
                       SUM(s.quantite_stock * a.prix_achat) AS total_achat,
                       SUM(s.quantite_stock * a.prix_vente) AS total_vente,
                       COUNT(*) FILTER (WHERE s.quantite_stock <= 0) AS nb_ruptures,
                       COUNT(*) FILTER (WHERE s.quantite_stock > 0
                                         AND s.quantite_stock <= s.seuil_alerte) AS nb_sous_seuil
                  FROM articles a
                  JOIN stocks_sites s ON s.article_id = a.id
                 WHERE a.actif = TRUE
                 GROUP BY s.site_id
                 ORDER BY s.site_id
                """
            )
            totaux = cur.fetchall()

    if format_ == "xlsx":
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = "stock"
        feuille.append(colonnes)
        for ligne in lignes:
            feuille.append([_valeur_cellule(ligne[c]) for c in colonnes])
        feuille_totaux = classeur.create_sheet("totaux par site")
        feuille_totaux.append(colonnes_totaux)
        for total in totaux:
            feuille_totaux.append([_valeur_cellule(total[c]) for c in colonnes_totaux])
        tampon = BytesIO()
        classeur.save(tampon)
        contenu = tampon.getvalue()
    else:
        contenu = _pdf_tableau("Stock valorisé par site", colonnes, lignes)
    return _reponse_fichier(contenu, format_, "stock")


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


# ---------------------------------------------------------------------------
# Rapport « écarts de prix par vendeur » — point c, question 5, décidé
# 2026-09-18 : 10 % sous le prix catalogue, en configuration, signale SANS
# JAMAIS bloquer. JSON lu à l'écran (pas un fichier) ; la vue
# `ecarts_prix_vendeurs` (migration 048, SECURITY INVOKER) porte la logique
# et la RLS par site (008) filtre l'agent comptabilité à SON site.
# ---------------------------------------------------------------------------
@routeur.get("/ecarts-prix-vendeurs")
def rapports_ecarts_prix_vendeurs(
    request: Request,
    date_debut: str | None = Query(default=None),
    date_fin: str | None = Query(default=None),
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Lignes de ventes payées dont le prix payé diffère du prix catalogue,
    groupées par vendeur (fiche employé, migration 040). L'écart ligne à
    ligne peut être négatif (upsell, toléré par 037) : il est restitué tel
    quel, seul le signalement suit la décision — strictement au-delà du
    seuil SOUS le catalogue. Les dates sont facultatives : absentes, le
    rapport couvre toute l'histoire (aucune période par défaut inventée).
    """
    debut = fin = None
    if date_debut is not None or date_fin is not None:
        try:
            debut = _date.fromisoformat(date_debut) if date_debut else None
            fin = _date.fromisoformat(date_fin) if date_fin else None
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "date_debut et date_fin doivent être au format AAAA-MM-JJ.",
            ) from exc
        if debut is not None and fin is not None and debut > fin:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "date_debut ne peut pas être postérieure à date_fin.",
            )

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT vente_id, site_id, site_nom, numero_facturier, date_vente,
                       vendeur_id, vendeur_nom, remise_globale_montant,
                       article_id, article_nom, quantite,
                       prix_catalogue, prix_unitaire,
                       ecart_unitaire, ecart_total, ecart_pct, seuil_pct, signale
                  FROM ecarts_prix_vendeurs
                 WHERE ecart_unitaire <> 0
                   AND (%s::date IS NULL OR date_vente::date >= %s::date)
                   AND (%s::date IS NULL OR date_vente::date <= %s::date)
                 ORDER BY vendeur_nom NULLS LAST, vendeur_id NULLS LAST,
                          date_vente, vente_id, article_id
                """,
                (debut, debut, fin, fin),
            )
            lignes = cur.fetchall()

    vendeurs: dict[tuple, dict] = {}
    seuil_pct = None
    for l in lignes:
        seuil_pct = float(l["seuil_pct"])
        cle = (l["vendeur_id"], l["vendeur_nom"])
        if cle not in vendeurs:
            vendeurs[cle] = {
                "vendeur_id": l["vendeur_id"],
                "vendeur_nom": l["vendeur_nom"],
                "nb_lignes": 0,
                "nb_signalees": 0,
                "cumul_ecart": 0.0,
                "lignes": [],
            }
        groupe = vendeurs[cle]
        groupe["nb_lignes"] += 1
        if l["signale"]:
            groupe["nb_signalees"] += 1
        groupe["cumul_ecart"] = round(groupe["cumul_ecart"] + float(l["ecart_total"]), 2)
        groupe["lignes"].append({
            "vente_id": l["vente_id"],
            "site_id": l["site_id"],
            "site_nom": l["site_nom"],
            "numero_facturier": l["numero_facturier"],
            "date_vente": l["date_vente"].isoformat() if l["date_vente"] else None,
            "article_id": l["article_id"],
            "article_nom": l["article_nom"],
            "quantite": float(l["quantite"]),
            "prix_catalogue": float(l["prix_catalogue"]),
            "prix_unitaire": float(l["prix_unitaire"]),
            "ecart_unitaire": float(l["ecart_unitaire"]),
            "ecart_total": float(l["ecart_total"]),
            "ecart_pct": float(l["ecart_pct"]),
            "remise_globale_montant": (
                float(l["remise_globale_montant"]) if l["remise_globale_montant"] is not None else None
            ),
            "signale": l["signale"],
        })

    return {
        "seuil_pct": seuil_pct,
        "vendeurs": sorted(
            vendeurs.values(),
            key=lambda g: (g["nb_signalees"] == 0, -(g["cumul_ecart"] or 0),
                           g["vendeur_nom"] or ""),
        ),
    }
