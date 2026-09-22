"""Comptage d'inventaire à l'aveugle et écarts (chantier C7).

Principe absolu, énoncé au cycle 5 et vérifié depuis par exécution : la
quantité que le système attend pour un article n'atteint JAMAIS le
navigateur de l'agent stock — ni avant le comptage (route dédiée, sans la
colonne), ni après (la réponse de ``POST /inventaire/comptages`` ne renvoie
que ce que le client a lui-même envoyé). Le calcul de l'écart reste un fait
de la base (``ecart`` généré, ``quantite_attendue`` figée par déclencheur —
migration 003) ; ce module ne fait que l'exposer, jamais le recalculer.

Défense en profondeur (migration 012, cycle 7) : même en contournant cette
route et en interrogeant directement PostgreSQL sous le rôle de l'agent
stock, ``ecart`` et ``quantite_attendue`` restent illisibles — un ``GRANT``
par colonne, pas une simple discipline de code.
"""

from __future__ import annotations

from datetime import date as _date

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeComptage,
    DemandeRegularisationComptage,
    ReponseComptage,
    ReponseRegularisationComptage,
    ReponseRegularisationEcart,
)
from ..securite import Session

routeur = APIRouter(prefix="/inventaire", tags=["inventaire"])


@routeur.get("/articles-a-compter")
def articles_a_compter(
    moment: str,
    request: Request,
    session: Session = Depends(exiger_role("agent_stock", "responsable")),
):
    """Liste d'articles à compter pour le site de l'appelant, pour un
    moment donné (matin/soir) — SANS AUCUNE colonne de quantité en stock.

    Un article déjà compté aujourd'hui pour ce moment est exclu de la
    liste (évite un refus prévisible à la soumission), sans jamais
    indiquer sa quantité comptée ni l'écart constaté.

    ``site_id`` figure dans la réponse : un agent stock a toujours un seul
    site (la colonne est alors constante), mais le responsable couvre les
    deux — sans elle, sa liste mélangerait Magasin et Comptoir sans moyen
    de les distinguer (constat du contrôle de boucle après le cycle 7).
    """
    if moment not in ("matin", "soir"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Moment invalide (matin ou soir).")

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            if session.site_id is not None:
                # Agent : uniquement les fiches qui ont une ligne de stock à
                # SON site, non comptées aujourd'hui pour ce moment.
                cur.execute(
                    """
                    SELECT a.id, a.nom, a.unite, %s::INTEGER AS site_id
                      FROM articles a
                      JOIN stocks_sites s ON s.article_id = a.id
                     WHERE a.actif = TRUE
                       AND s.site_id = %s
                       AND NOT EXISTS (
                             SELECT 1 FROM comptages_stock c
                              WHERE c.article_id = a.id
                                AND c.site_id = %s
                                AND c.moment = %s
                                AND c.date_comptage::date = CURRENT_DATE
                           )
                     ORDER BY a.nom
                    """,
                    (session.site_id, session.site_id, session.site_id, moment),
                )
            else:
                # Responsable : tous les (article, site) — sans quantités.
                cur.execute(
                    """
                    SELECT a.id, a.nom, a.unite, s.site_id
                      FROM articles a
                      JOIN stocks_sites s ON s.article_id = a.id
                     WHERE a.actif = TRUE
                       AND NOT EXISTS (
                             SELECT 1 FROM comptages_stock c
                              WHERE c.article_id = a.id
                                AND c.site_id = s.site_id
                                AND c.moment = %s
                                AND c.date_comptage::date = CURRENT_DATE
                           )
                     ORDER BY s.site_id, a.nom
                    """,
                    (moment,),
                )
            lignes = cur.fetchall()

    return {"articles": lignes}


@routeur.post("/comptages", response_model=ReponseComptage, status_code=status.HTTP_201_CREATED)
def enregistrer_comptage(
    demande: DemandeComptage,
    request: Request,
    session: Session = Depends(exiger_role("agent_stock", "responsable")),
):
    if session.site_id is not None:
        site_cible = session.site_id
    elif demande.site_id is not None:
        site_cible = demande.site_id
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Le site est obligatoire pour un compte responsable.",
        )

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            # Plafond de vraisemblance (décision 2026-09-22) : tant que le
            # paramètre est `a_decider`, AUCUN comptage n'est refusé. Dès que
            # le propriétaire fixe une valeur, toute quantité comptée
            # supérieure est refusée ici, avant même d'atteindre la base.
            cur.execute(
                "SELECT valeur, a_decider FROM parametres"
                " WHERE cle = 'plafond_vraisemblance_comptage'"
            )
            plafond = cur.fetchone()
            if (
                plafond is not None
                and not plafond["a_decider"]
                and plafond["valeur"] not in (None, "a_definir")
                and int(plafond["valeur"]) >= 0
                and demande.quantite_comptee > int(plafond["valeur"])
            ):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Quantité comptée invraisemblable (plafond : "
                    + str(plafond["valeur"]) + ").",
                )

            try:
                cur.execute(
                    """
                    INSERT INTO comptages_stock (article_id, site_id, utilisateur_id, moment, quantite_comptee)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (demande.article_id, site_cible, session.utilisateur_id,
                     demande.moment, demande.quantite_comptee),
                )
                comptage_id = cur.fetchone()["id"]
            except psycopg.errors.UniqueViolation as exc:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Cet article a déjà été compté ce " + demande.moment + " aujourd'hui pour ce site.",
                ) from exc
            except psycopg.errors.ForeignKeyViolation as exc:
                # Levée par le déclencheur figer_quantite_attendue() quand
                # l'article n'a pas de stock à ce site (ou n'existe pas).
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Article introuvable pour ce site.",
                ) from exc

    # Ne renvoie QUE ce que le client a lui-même envoyé — jamais
    # quantite_attendue ni ecart (voir le docstring du module).
    return ReponseComptage(
        comptage_id=comptage_id,
        article_id=demande.article_id,
        moment=demande.moment,
        quantite_comptee=demande.quantite_comptee,
    )


@routeur.get("/ecarts")
def ecarts_du_jour(
    request: Request, session: Session = Depends(exiger_role("responsable"))
):
    """Écarts de comptage du jour, réservés au responsable. Un agent stock
    n'a de toute façon plus le droit de lire ``ecart``/``quantite_attendue``
    (migration 012) — cette route ne fait que refléter, au niveau
    applicatif, ce que la base impose déjà."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, a.nom AS article_nom, c.site_id, c.moment,
                       c.quantite_comptee, c.quantite_attendue, c.ecart, c.date_comptage
                  FROM comptages_stock c
                  JOIN articles a ON a.id = c.article_id
                 WHERE c.ecart <> 0
                   AND c.date_comptage::date = CURRENT_DATE
                 ORDER BY c.date_comptage DESC
                """
            )
            lignes = cur.fetchall()

    return {"ecarts": lignes}


@routeur.get("/historique-comptages")
def historique_comptages(
    date_debut: str,
    date_fin: str,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Historique de TOUS les comptages (pas seulement ceux en écart) sur
    une période, tous sites — chantier C8, CDC §3.3 et §3.13 : « Historique
    des comptages d'inventaire, tous sites, filtre par période », « réservé
    au responsable ». Distinct de ``/ecarts`` ci-dessus, qui ne montre que
    les écarts du jour courant.

    ``date_debut``/``date_fin`` au format AAAA-MM-JJ, bornes incluses. La
    comparaison se fait sur ``date_comptage::date`` : comme pour
    ``/ventes/synthese-jour`` (cycle 8), le fuseau qui compte est celui de
    la CONNEXION (Africa/Douala, fixé par ``database.py``), jamais celui du
    système d'exploitation.
    """
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

    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, a.nom AS article_nom, c.site_id, c.moment,
                       c.quantite_comptee, c.quantite_attendue, c.ecart, c.date_comptage
                  FROM comptages_stock c
                  JOIN articles a ON a.id = c.article_id
                 WHERE c.date_comptage::date BETWEEN %s AND %s
                 ORDER BY c.date_comptage DESC
                """,
                (debut, fin),
            )
            lignes = cur.fetchall()

    return {"comptages": lignes}


@routeur.get("/ecarts-ventes")
def ecarts_ventes_du_jour(
    request: Request, session: Session = Depends(exiger_role("responsable"))
):
    """Écarts de stock issus d'une vente à découvert (chantier C5, addendum
    point e) survenus aujourd'hui — distincts des écarts de comptage
    ci-dessus : ici, aucun comptage n'a eu lieu, c'est une vente qui a
    dépassé le stock réellement disponible."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, a.nom AS article_nom, e.site_id, e.vente_id,
                       e.quantite_manquante, e.regularise, e.date_ecart
                  FROM ecarts_stock_ventes e
                  JOIN articles a ON a.id = e.article_id
                 WHERE e.date_ecart::date = CURRENT_DATE
                 ORDER BY e.date_ecart DESC
                """
            )
            lignes = cur.fetchall()

    return {"ecarts": lignes}


@routeur.post(
    "/ecarts-ventes/{ecart_id}/regulariser",
    response_model=ReponseRegularisationEcart,
)
def regulariser_ecart_vente(
    ecart_id: int,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Marque un écart de vente à découvert comme traité (chantier C5,
    cycle 17) — ``regulariser_ecart_vente()``, migration 017. Jamais
    l'inverse : un écart déjà régularisé, ou introuvable, est refusé par la
    fonction elle-même (``regulariser_ecart_vente`` ne fait aucun ``UPDATE``
    direct exposé, réservé au rôle responsable)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT regulariser_ecart_vente(%s, %s)",
                    (ecart_id, session.utilisateur_id),
                )
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation) as exc:
                raise erreur_metier(exc) from exc

            # regulariser_ecart_vente() renvoie VOID : on relit l'écart pour
            # confirmer son nouvel état plutôt que de renvoyer un 204 muet.
            cur.execute(
                "SELECT regularise FROM ecarts_stock_ventes WHERE id = %s", (ecart_id,)
            )
            ligne = cur.fetchone()

    return ReponseRegularisationEcart(ecart_id=ecart_id, regularise=ligne["regularise"])


@routeur.post(
    "/ecarts/{comptage_id}/regulariser",
    response_model=ReponseRegularisationComptage,
    status_code=status.HTTP_201_CREATED,
)
def regulariser_ecart_comptage(
    comptage_id: int,
    demande: DemandeRegularisationComptage,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Décision du responsable sur un écart de COMPTAGE (chantier C7,
    cycle 36) — traçabilité pure, jamais d'effet sur le stock (décision
    2026-09-22). Refusée par la base si le comptage ne porte aucun écart ou
    si une résolution existe déjà."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT regulariser_ecart_comptage(%s, %s, %s, %s) AS regularisation_id",
                    (comptage_id, demande.type_resolution,
                     session.utilisateur_id, demande.motif),
                )
                ligne = cur.fetchone()
            except (
                psycopg.errors.ForeignKeyViolation,
                psycopg.errors.CheckViolation,
                psycopg.errors.UniqueViolation,
            ) as exc:
                raise erreur_metier(exc) from exc

            cur.execute(
                "SELECT comptage_id, type_resolution, motif,"
                " date_regularisation::TEXT AS date_regularisation"
                " FROM regularisations_ecarts_comptage WHERE id = %s",
                (ligne["regularisation_id"],),
            )
            reg = cur.fetchone()

    return ReponseRegularisationComptage(
        regularisation_id=ligne["regularisation_id"],
        comptage_id=reg["comptage_id"],
        type_resolution=reg["type_resolution"],
        motif=reg["motif"],
        date_regularisation=reg["date_regularisation"],
    )
