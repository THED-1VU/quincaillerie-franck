"""Routes de démonstration (chantier C3) : prouver le cloisonnement par rôle
et par site sur des lectures réelles, sans construire d'écran ni coder de
règle métier de vente ou de stock.

Chaque route choisit la liste de colonnes correspondant au rôle appelant,
mais c'est un CONFORT, pas la protection : si le code choisissait la
mauvaise liste par erreur, la requête échouerait quand même côté PostgreSQL
(privilèges par colonne, migration 008) — voir
server/tests/test_habilitations.py, qui vérifie précisément ce point en
tentant volontairement une colonne interdite en direct, hors de toute route.

Aucune route n'accepte de site_id fourni par le client : le site vient
TOUJOURS de la session (donc de la connexion), jamais d'un paramètre de
requête que l'appelant pourrait manipuler pour viser l'autre site.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import obtenir_bd, obtenir_session
from ..roles import role_pg
from ..securite import Session

routeur = APIRouter(tags=["démonstration"])


_COLONNES_ARTICLES = {
    "agent_stock": "id, nom, unite, quantite_stock, seuil_alerte, site_id",
    "agent_comptabilite": "id, nom, unite, prix_vente, site_id",
    "responsable": "id, nom, unite, prix_achat, prix_vente, quantite_stock, seuil_alerte, site_id",
}


@routeur.get("/articles")
def liste_articles(request: Request, session: Session = Depends(obtenir_session)):
    """Catalogue des articles, colonnes et périmètre selon le rôle.

    - agent stock : quantités, pas de prix ;
    - agent comptabilité : prix de vente, pas de quantité ;
    - responsable : tout, sur les deux sites.

    Le cloisonnement par site n'est pas fait par cette requête : il vient de
    la politique RLS d'``articles`` (cycle 2), déclenchée par
    ``qf_site_courant()``, lui-même positionné par ``connexion_pour`` à
    partir de la session — jamais d'un paramètre de la requête HTTP.
    """
    bd = obtenir_bd(request)
    colonnes = _COLONNES_ARTICLES[session.role]

    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {colonnes} FROM articles WHERE actif = TRUE ORDER BY nom"  # noqa: S608
                # Pas d'injection possible : `colonnes` vient d'une whitelist
                # fixe indexée par session.role (3 valeurs possibles, ci-dessus),
                # jamais d'une entrée de la requête HTTP.
            )
            lignes = cur.fetchall()

    return {"articles": lignes}


@routeur.get("/ventes/synthese-jour")
def synthese_ventes_du_jour(request: Request, session: Session = Depends(obtenir_session)):
    """Nombre de ventes encaissées aujourd'hui et total, par site.

    Réservé au responsable et à la comptabilité : un agent stock n'a de toute
    façon aucun droit sur la table ``ventes`` (migration 008) — la requête
    échouerait à ce niveau si on la laissait quand même passer ; on préfère
    lui répondre 403 avant d'aller inutilement jusqu'à la base.
    """
    if session.role not in ("responsable", "agent_comptabilite"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle non autorisé pour cette route.")

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT site_id, count(*) AS nb_ventes, COALESCE(sum(total_ttc), 0) AS total_ttc
                  FROM ventes
                 WHERE statut = 'payee'
                   AND date_encaissement::date = CURRENT_DATE
                 GROUP BY site_id
                 ORDER BY site_id
                """
            )
            lignes = cur.fetchall()

    return {"synthese_par_site": lignes}


@routeur.get("/moi")
def mon_profil(request: Request, session: Session = Depends(obtenir_session)):
    """Profil de l'utilisateur connecté — jamais celui d'un tiers : l'id
    vient de la session (donc du jeton signé), pas d'un paramètre de route.
    """
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS utilisateur_id, nom_complet, role, site_id, doit_changer_mot_de_passe
                  FROM utilisateurs
                 WHERE id = %s
                """,
                (session.utilisateur_id,),
            )
            ligne = cur.fetchone()

    return ligne
