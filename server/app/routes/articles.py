"""Création d'articles (chantier C4, cycle 9).

Un article naît TOUJOURS à ``quantite_stock = 0`` (défaut du schéma) : la
reprise d'un stock initial dépend du point j de l'addendum (volumétrie),
non tranché — voir ``db/migrations/014_...``. Toute quantité réelle passe
ensuite par une réception (``POST /stock/entrees``).

Le prix n'est accepté que pour un responsable : un agent stock qui en
envoie un le voit simplement ignoré (la base le refuserait de toute façon,
mais un ``INSERT`` échoué renverrait une erreur brute — ici, on ne construit
la requête qu'avec les colonnes que le rôle appelant a le droit d'écrire).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..schemas import DemandeArticle, ReponseArticle
from ..securite import Session

routeur = APIRouter(prefix="/articles", tags=["articles"])


@routeur.post("", response_model=ReponseArticle, status_code=status.HTTP_201_CREATED)
def creer_article(
    demande: DemandeArticle,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
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
        role_pg(session.role), site_id=site_cible, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            if session.role == "responsable":
                cur.execute(
                    """
                    INSERT INTO articles (nom, categorie, unite, prix_achat, prix_vente, site_id, fournisseur_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        demande.nom, demande.categorie, demande.unite,
                        demande.prix_achat or 0, demande.prix_vente or 0,
                        site_cible, demande.fournisseur_id,
                    ),
                )
            else:
                # Agent stock : ni prix_achat ni prix_vente ne sont écrits
                # (la colonne prend son DEFAULT 0 en base, migration 008) —
                # un prix envoyé quand même est silencieusement ignoré,
                # jamais transmis à la base.
                cur.execute(
                    """
                    INSERT INTO articles (nom, categorie, unite, site_id, fournisseur_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (demande.nom, demande.categorie, demande.unite, site_cible, demande.fournisseur_id),
                )
            article_id = cur.fetchone()["id"]

    return ReponseArticle(article_id=article_id, nom=demande.nom, unite=demande.unite, site_id=site_cible)
