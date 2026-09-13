"""Mouvements de stock : réception, transfert inter-sites, casse, retours
(chantier C4, cycle 9, addendum points a et f).

Chaque route n'est qu'une mince couche autour d'une fonction PostgreSQL
``SECURITY DEFINER`` (migration 014) qui porte, seule, la vraie logique et
les vraies garanties (atomicité, verrous, refus). Le motif d'erreur affiché
au client est le message même de la fonction (``exc.diag.message_primary``)
— jamais un message brut de PostgreSQL : chaque ``RAISE EXCEPTION`` de ces
fonctions est déjà écrit en français, à l'intention de l'utilisateur final.

Portée volontairement NON traitée ce cycle (voir la migration et
l'addendum) : remises, unités/conversions décimales, chargement du stock
initial, régularisation d'un écart d'inventaire, workflow d'approbation en
deux temps pour une casse — aucune de ces règles n'est inventée ici.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..roles import role_pg
from ..schemas import (
    DemandeCasse,
    DemandeEntreeStock,
    DemandeRetourClient,
    DemandeRetourFournisseur,
    DemandeTransfert,
    ReponseMouvementStock,
    ReponseTransfert,
)
from ..securite import Session

routeur = APIRouter(prefix="/stock", tags=["stock"])


def _erreur_metier(exc: psycopg.Error) -> HTTPException:
    """Traduit un refus métier de la base (CHECK ou clé étrangère levés par
    nos fonctions) en 422 avec le message même de la fonction — toujours en
    français, jamais un message brut, puisque c'est nous qui l'avons écrit.
    ``InsufficientPrivilege`` n'est PAS traitée ici : le gestionnaire global
    (main.py) répond déjà "Accès refusé." pour cette classe d'erreur."""
    message = (exc.diag.message_primary or "Opération refusée.").strip()
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, message)


@routeur.post("/entrees", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_entree(
    demande: DemandeEntreeStock,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Réception fournisseur : seule opération qui recalcule le seuil
    d'alerte (20 % de la quantité reçue, cycle 2) — jamais un transfert, une
    casse ou un retour."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_entree_stock(%s, %s, %s, %s) AS quantite_stock",
                    (demande.article_id, demande.quantite, session.utilisateur_id,
                     demande.motif or "entrée de stock"),
                )
            except psycopg.errors.ForeignKeyViolation as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseMouvementStock(article_id=demande.article_id, quantite_stock=ligne["quantite_stock"])


@routeur.post("/transferts", response_model=ReponseTransfert, status_code=status.HTTP_201_CREATED)
def transferer(
    demande: DemandeTransfert,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Transfert inter-sites (addendum, point a) : une seule opération
    atomique, sortie + entrée, même horodatage, même auteur, motif
    obligatoire. Ne recalcule jamais le seuil d'alerte. Un agent stock ne
    peut transférer que depuis SON site (vérifié par la fonction elle-même,
    pas par cette route)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT * FROM transferer_stock(%s, %s, %s, %s, %s)",
                    (
                        demande.article_id_origine, demande.article_id_destination,
                        demande.quantite, session.utilisateur_id, demande.motif,
                    ),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseTransfert(
        article_id_origine=demande.article_id_origine,
        article_id_destination=demande.article_id_destination,
        quantite_stock_origine=ligne["stock_origine_restant"],
        quantite_stock_destination=ligne["stock_destination_final"],
    )


@routeur.post("/casse", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_casse(
    demande: DemandeCasse,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Casse ou avarie (addendum, point f) : réservée au responsable —
    « validée par le responsable » se lit ici comme « c'est lui qui
    l'enregistre », faute d'un flux d'approbation en deux temps décrit par
    le propriétaire."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_casse(%s, %s, %s, %s) AS quantite_stock",
                    (demande.article_id, demande.quantite, session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseMouvementStock(article_id=demande.article_id, quantite_stock=ligne["quantite_stock"])


@routeur.post("/retours-client", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_retour_client(
    demande: DemandeRetourClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Retour client (addendum, point f) : entrée rattachée à la vente
    d'origine, même site. Ne recalcule pas le seuil d'alerte."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_retour_client(%s, %s, %s, %s, %s) AS quantite_stock",
                    (demande.article_id, demande.vente_id, demande.quantite,
                     session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseMouvementStock(article_id=demande.article_id, quantite_stock=ligne["quantite_stock"])


@routeur.post("/retours-fournisseur", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_retour_fournisseur(
    demande: DemandeRetourFournisseur,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Retour fournisseur (addendum, point f) : sortie rattachée à la
    réception d'origine, même article. Refusé si le mouvement référencé
    n'est pas une réception fournisseur."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_retour_fournisseur(%s, %s, %s, %s) AS resultat",
                    (demande.mouvement_origine_id, demande.quantite, session.utilisateur_id, demande.motif),
                )
                ligne = cur.fetchone()
                cur.execute(
                    "SELECT article_id FROM mouvements_stock WHERE id = %s",
                    (demande.mouvement_origine_id,),
                )
                article = cur.fetchone()
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc

    return ReponseMouvementStock(article_id=article["article_id"], quantite_stock=ligne["resultat"])
