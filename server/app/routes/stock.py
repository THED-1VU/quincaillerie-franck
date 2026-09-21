"""Mouvements de stock : réception, transfert inter-sites, casse, retours
(chantier C4, cycle 9, addendum points a et f ; adapté au modèle multi-site
au cycle 35, chantier 13b).

Chaque route n'est qu'une mince couche autour d'une fonction PostgreSQL
``SECURITY DEFINER`` (migrations 014/028) qui porte, seule, la vraie logique
et les vraies garanties (atomicité, verrous, refus). Le motif d'erreur
affiché au client est le message même de la fonction
(``exc.diag.message_primary``) — jamais un message brut de PostgreSQL :
chaque ``RAISE EXCEPTION`` de ces fonctions est déjà écrit en français.

Depuis la décision du 2026-09-19, le transfert porte sur UN article et DEUX
sites, et crée la ligne de stock de destination si elle n'existe pas.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier as _erreur_metier
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


def _site_cible(session: Session, demande_site) -> int:
    """Le site d'une opération : celui de la session pour un agent, celui
    demandé pour un responsable (obligatoire : il couvre les deux sites)."""
    if session.site_id is not None:
        return session.site_id
    if demande_site is not None:
        return demande_site
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Le site est obligatoire pour un compte responsable.",
    )


@routeur.post("/entrees", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_entree(
    demande: DemandeEntreeStock,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Réception fournisseur : seule opération qui recalcule le seuil
    d'alerte (20 % de la quantité reçue, cycle 2) — jamais un transfert, une
    casse ou un retour. Ouvre la ligne de stock du site si elle n'existe pas
    encore (première réception — décision 2026-09-19)."""
    site_cible = _site_cible(session, demande.site_id)
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_entree_stock(%s, %s, %s, %s, %s) AS quantite_stock",
                    (demande.article_id, site_cible, demande.quantite,
                     session.utilisateur_id, demande.motif or "entrée de stock"),
                )
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseMouvementStock(
        article_id=demande.article_id, site_id=site_cible,
        quantite_stock=ligne["quantite_stock"],
    )


@routeur.post("/transferts", response_model=ReponseTransfert, status_code=status.HTTP_201_CREATED)
def transferer(
    demande: DemandeTransfert,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Transfert inter-sites (addendum, point a ; décision 2026-09-19) : UN
    article, deux sites, une seule opération atomique (sortie + entrée, même
    horodatage, même auteur, motif obligatoire). La ligne de destination est
    créée automatiquement si absente. Ne recalcule jamais le seuil. Un agent
    stock ne peut transférer que depuis SON site (vérifié par la fonction)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT * FROM transferer_stock(%s, %s, %s, %s, %s, %s)",
                    (
                        demande.article_id, demande.site_origine, demande.site_destination,
                        demande.quantite, session.utilisateur_id, demande.motif,
                    ),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseTransfert(
        article_id=demande.article_id,
        site_origine=demande.site_origine,
        site_destination=demande.site_destination,
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
    le propriétaire. Cible un (article, site) explicite."""
    site_cible = _site_cible(session, demande.site_id)
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_casse(%s, %s, %s, %s, %s) AS quantite_stock",
                    (demande.article_id, site_cible, demande.quantite,
                     session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseMouvementStock(
        article_id=demande.article_id, site_id=site_cible,
        quantite_stock=ligne["quantite_stock"],
    )


@routeur.post("/retours-client", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_retour_client(
    demande: DemandeRetourClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Retour client (addendum, point f) : entrée rattachée à la vente
    d'origine — le site est celui de la vente (sans ambiguïté). Ne recalcule
    pas le seuil d'alerte."""
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
                ligne = cur.fetchone()
                cur.execute("SELECT site_id FROM ventes WHERE id = %s", (demande.vente_id,))
                vente = cur.fetchone()
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc

    return ReponseMouvementStock(
        article_id=demande.article_id, site_id=vente["site_id"],
        quantite_stock=ligne["quantite_stock"],
    )


@routeur.post("/retours-fournisseur", response_model=ReponseMouvementStock, status_code=status.HTTP_201_CREATED)
def enregistrer_retour_fournisseur(
    demande: DemandeRetourFournisseur,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Retour fournisseur (addendum, point f) : sortie rattachée à la
    réception d'origine, même (article, site). Refusé si le mouvement
    référencé n'est pas une réception fournisseur."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT enregistrer_retour_fournisseur(%s, %s, %s, %s) AS resultat",
                    (demande.mouvement_origine_id, demande.quantite,
                     session.utilisateur_id, demande.motif),
                )
                ligne = cur.fetchone()
                cur.execute(
                    "SELECT article_id, site_id FROM mouvements_stock WHERE id = %s",
                    (demande.mouvement_origine_id,),
                )
                origine = cur.fetchone()
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc

    return ReponseMouvementStock(
        article_id=origine["article_id"], site_id=origine["site_id"],
        quantite_stock=ligne["resultat"],
    )
