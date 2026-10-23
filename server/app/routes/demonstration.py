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

from fastapi import APIRouter, Depends, Request

from ..deps import exiger_role, obtenir_bd, obtenir_session
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

    D7 (validée le 2026-10-23) : un compte CUMULANT agent_stock et
    agent_comptabilite atteint à la fois vente.html (prix) et
    inventaire/stock.html (quantités) — la liste lui porte donc les deux
    familles de colonnes. Chaque famille reste lue via le rôle PostgreSQL qui
    la porte (jamais une élévation vers qf_responsable, qui verrait les deux
    sites) : deux requêtes séparées, fusionnées sur l'article, le stock restant
    celui du site de la session.

    Le cloisonnement par site de la quantité n'est pas fait par cette requête :
    il vient de la politique RLS de ``stocks_sites`` (migration 029),
    déclenchée par ``qf_site_courant()``, lui-même positionné par
    ``connexion_pour`` — jamais d'un paramètre de la requête HTTP.
    """
    bd = obtenir_bd(request)
    roles = session.roles or (session.role,)
    est_responsable = "responsable" in roles
    est_compta = "agent_comptabilite" in roles
    est_stock = "agent_stock" in roles

    requete_stock = """
        SELECT a.id, a.nom, a.unite, a.quantite_decimale_autorisee,
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

    if est_responsable:
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_achat, a.prix_vente,
                   a.quantite_decimale_autorisee,
                   s.site_id, s.quantite_stock, s.seuil_alerte
              FROM articles a
              JOIN stocks_sites s ON s.article_id = a.id
             WHERE a.actif = TRUE
             ORDER BY a.nom, s.site_id
        """
        with bd.connexion_pour(
            role_pg("responsable"), site_id=session.site_id, utilisateur_id=session.utilisateur_id
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(requete, parametres)
                lignes = cur.fetchall()
    elif est_compta and est_stock:
        with bd.connexion_pour(
            role_pg("agent_comptabilite"), site_id=session.site_id, utilisateur_id=session.utilisateur_id
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT a.id, a.prix_vente FROM articles a WHERE a.actif = TRUE"
                )
                prix_par_article = {r["id"]: r["prix_vente"] for r in cur.fetchall()}
        with bd.connexion_pour(
            role_pg("agent_stock"), site_id=session.site_id, utilisateur_id=session.utilisateur_id
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(requete_stock, parametres)
                lignes = [
                    dict(r) | {"prix_vente": prix_par_article.get(r["id"])}
                    for r in cur.fetchall()
                ]
    elif est_compta:
        requete = """
            SELECT a.id, a.nom, a.unite, a.prix_vente, a.quantite_decimale_autorisee
              FROM articles a
             WHERE a.actif = TRUE
             ORDER BY a.nom
        """
        with bd.connexion_pour(
            role_pg("agent_comptabilite"), site_id=session.site_id, utilisateur_id=session.utilisateur_id
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(requete, parametres)
                lignes = cur.fetchall()
    else:
        with bd.connexion_pour(
            role_pg("agent_stock"), site_id=session.site_id, utilisateur_id=session.utilisateur_id
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(requete_stock, parametres)
                lignes = cur.fetchall()

    return {"articles": lignes}


@routeur.get("/ventes/synthese-jour")
def synthese_ventes_du_jour(
    request: Request,
    # D7 (cycle 75) : la résolution du rôle effectif passe par exiger_role,
    # qui regarde la liste COMPLÈTE des rôles du compte (union) et fixe
    # session.role pour la connexion PG — pas le rôle principal seul.
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Nombre de ventes encaissées aujourd'hui et total, par site.

    Réservé au responsable et à la comptabilité : un agent stock n'a de toute
    façon aucun droit sur la table ``ventes`` (migration 008) — la requête
    échouerait à ce niveau si on la laissait quand même passer ; on préfère
    lui répondre 403 avant d'aller inutilement jusqu'à la base.
    """
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

    D7 (validée le 2026-10-23) : la réponse porte la liste COMPLÈTE des rôles
    effectifs (``roles_utilisateur``, migration 035), pas seulement le rôle
    principal — l'union est ce qui détermine les écrans accessibles. La liste
    est relue EN BASE (source de vérité), pas décodée du jeton : une rôle
    retiré par le responsable s'applique à la requête suivante. Lecture faite
    via ``connexion_anonyme`` (qf_app) : ``roles_utilisateur`` n'est exécutable
    que par qf_app et qf_responsable, et un agent connecté sous son rôle PG ne
    pourrait pas l'appeler.
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

    with bd.connexion_anonyme() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM roles_utilisateur(%s)", (session.utilisateur_id,)
            )
            roles = [r["role"] for r in cur.fetchall()]

    profil = dict(ligne)
    profil["roles"] = roles or [ligne["role"]]
    return profil
