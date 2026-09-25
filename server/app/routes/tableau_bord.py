"""Tableau de bord du responsable (chantier C8, cycle 10).

Une seule route ici : les autres cartes du tableau de bord (ventes du jour,
écarts d'inventaire, écarts de stock issus des ventes) sont déjà réelles
depuis les cycles 5 et 7 — voir ``ventes.py`` (en fait ``demonstration.py``)
et ``inventaire.py``. Celle-ci câble la dernière carte encore marquée
« donnée simulée » dans ``maquette/tableau-bord.html``.

Aucune règle métier inventée : le seuil d'alerte existe et se recalcule
depuis le cycle 2 (20 % de la quantité reçue) ; cette route ne fait que
comparer deux colonnes déjà là (``quantite_stock``, ``seuil_alerte``).
Réservée au responsable, comme la carte correspondante au CDC §3.3 — ni
l'agent stock ni l'agent comptabilité n'y figurent au cahier des charges
pour cet indicateur précis.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..securite import Session

routeur = APIRouter(prefix="/tableau-bord", tags=["tableau de bord"])


@routeur.get("/alertes-stock")
def alertes_stock(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Articles dont le stock est descendu à son seuil d'alerte ou en
    dessous, tous sites (vue consolidée) — le tri par ``site_id`` permet à
    l'écran de les répartir par site s'il choisit d'afficher une vue non
    consolidée, sans requête supplémentaire."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id AS article_id, a.nom, a.unite, s.site_id,
                       s.quantite_stock, s.seuil_alerte
                  FROM stocks_sites s
                  JOIN articles a ON a.id = s.article_id
                 WHERE a.actif = TRUE
                   AND s.quantite_stock <= s.seuil_alerte
                 ORDER BY s.site_id, a.nom
                """
            )
            lignes = cur.fetchall()

    return {"alertes": lignes}


@routeur.get("/articles-offerts-en-attente")
def articles_offerts_en_attente(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Déclarations d'article offert EN ATTENTE de validation, tous sites
    (chantier C4/C5, point f, décision 2026-09-24) — décision du
    propriétaire : « une déclaration qui traîne depuis une semaine est un
    signal, pas un oubli administratif ». ``date_declaration`` est renvoyée
    telle quelle ; l'ancienneté se calcule côté écran, à partir de l'heure
    du navigateur, pour éviter tout écart de fuseau entre le serveur et
    l'affichage."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id AS declaration_id, a.nom AS article_nom, d.site_id, d.quantite,
                       d.valeur_normale, d.vente_id, d.client_nom, e.nom_complet AS employe_nom,
                       d.motif, d.date_declaration
                  FROM declarations_article_offert d
                  JOIN articles a ON a.id = d.article_id
                  JOIN employes e ON e.id = d.employe_id
                 WHERE d.statut = 'en_attente'
                 ORDER BY d.date_declaration
                """
            )
            lignes = cur.fetchall()

    return {"declarations": lignes}


@routeur.get("/credit-client")
def credit_client(
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Encours total et vieillissement (addendum, point b, décidé le
    2026-09-25) — allocation FIFO calculée par ``vieillissement_creances()``
    (migration 045), même principe que ``calculer_attendu_caisse`` : lecture
    seule, pas de SECURITY DEFINER, le responsable a déjà SELECT sur les
    tables sources."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tranche, montant FROM vieillissement_creances()")
            tranches = cur.fetchall()

    par_tranche = {t: 0.0 for t in ("0-30", "31-60", "61-90", "91+")}
    for ligne in tranches:
        par_tranche[ligne["tranche"]] = float(ligne["montant"])
    return {
        "encours_total": round(sum(par_tranche.values()), 2),
        "vieillissement": par_tranche,
    }
