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

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..schemas import DemandeComptage, ReponseComptage
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
            cur.execute(
                """
                SELECT a.id, a.nom, a.unite, a.site_id
                  FROM articles a
                 WHERE a.actif = TRUE
                   AND NOT EXISTS (
                         SELECT 1 FROM comptages_stock c
                          WHERE c.article_id = a.id
                            AND c.moment = %s
                            AND c.date_comptage::date = CURRENT_DATE
                       )
                 ORDER BY a.site_id, a.nom
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
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO comptages_stock (article_id, utilisateur_id, moment, quantite_comptee)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (demande.article_id, session.utilisateur_id, demande.moment, demande.quantite_comptee),
                )
                comptage_id = cur.fetchone()["id"]
            except psycopg.errors.UniqueViolation as exc:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Cet article a déjà été compté ce " + demande.moment + " aujourd'hui.",
                ) from exc
            except psycopg.errors.ForeignKeyViolation as exc:
                # Levée par le déclencheur figer_quantite_attendue() quand
                # l'article n'existe pas ou n'est pas visible pour ce site
                # (la RLS d'articles le rend introuvable, pas "interdit").
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
                SELECT c.id, a.nom AS article_nom, a.site_id, c.moment,
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
                SELECT e.id, a.nom AS article_nom, a.site_id, e.vente_id,
                       e.quantite_manquante, e.regularise, e.date_ecart
                  FROM ecarts_stock_ventes e
                  JOIN articles a ON a.id = e.article_id
                 WHERE e.date_ecart::date = CURRENT_DATE
                 ORDER BY e.date_ecart DESC
                """
            )
            lignes = cur.fetchall()

    return {"ecarts": lignes}
