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
