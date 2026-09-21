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


@routeur.get("/articles")
def liste_articles(request: Request, session: Session = Depends(obtenir_session)):
    """Catalogue des articles, colonnes et périmètre selon le rôle.

    - agent stock : sa quantité (son site), pas de prix ;
    - agent comptabilité : prix de vente, pas de quantité ;
    - responsable : tout, une ligne par (article, site) — la fiche est unique,
      le stock est par site (décision 2026-09-19).

    Le cloisonnement par site de la quantité n'est pas fait par cette requête :
    il vient de la politique RLS de ``stocks_sites`` (migration 029),
    déclenchée par ``qf_site_courant()``, lui-même positionné par
    ``connexion_pour`` — jamais d'un paramètre de la requête HTTP.
    """
    bd = obtenir_bd(request)

    if session.role == "responsable":
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_achat, a.prix_vente,
                   s.site_id, s.quantite_stock, s.seuil_alerte
              FROM articles a
              JOIN stocks_sites s ON s.article_id = a.id
             WHERE a.actif = TRUE
             ORDER BY a.nom, s.site_id
        """
        parametres = ()
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
        parametres = ()
    else:
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_vente
              FROM articles a
             WHERE a.actif = TRUE
             ORDER BY a.nom
        """
        parametres = ()

    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(requete, parametres)
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
