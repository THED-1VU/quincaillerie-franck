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
    DemandeDeclarationArticleOffert,
    DemandeDeclarationCasse,
    DemandeDeclarationRetourClient,
    DemandeEntreeStock,
    DemandeRetourFournisseur,
    DemandeTransfert,
    DemandeValidationArticleOffert,
    DemandeValidationCasse,
    DemandeValidationRetourClient,
    ReponseArticleOffertDetail,
    ReponseCasseDetail,
    ReponseDeclarationArticleOffert,
    ReponseDeclarationCasse,
    ReponseDeclarationRetourClient,
    ReponseMouvementStock,
    ReponseRetourClientDetail,
    ReponseTransfert,
    ReponseValidationArticleOffert,
    ReponseValidationCasse,
    ReponseValidationRetourClient,
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


@routeur.post(
    "/casse/declarations", response_model=ReponseDeclarationCasse, status_code=status.HTTP_201_CREATED
)
def declarer_casse(
    demande: DemandeDeclarationCasse,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Déclaration d'une casse ou avarie (addendum, point f, décision
    2026-09-22) : ouverte à tout rôle qui touche au stock — c'est un
    CONSTAT, sans aucun effet sur le stock. Seule la validation (ci-dessous)
    décrémente réellement."""
    site_cible = _site_cible(session, demande.site_id)
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT declarer_casse(%s, %s, %s, %s, %s, %s) AS declaration_id",
                    (demande.article_id, site_cible, demande.quantite,
                     demande.motif, session.utilisateur_id, demande.observation),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseDeclarationCasse(declaration_id=ligne["declaration_id"], statut="en_attente")


@routeur.get("/casse/declarations", response_model=list[ReponseCasseDetail])
def lister_declarations_casse(
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Déclarations de casse EN ATTENTE de validation — un responsable voit
    les deux sites, un agent stock seulement le sien (RLS,
    `p_declarations_casse_site`, migration 036)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id AS declaration_id, article_id, site_id, quantite, motif, observation,"
                " declarant_id, date_declaration, statut"
                " FROM declarations_casse WHERE statut = 'en_attente' ORDER BY date_declaration"
            )
            lignes = cur.fetchall()

    return lignes


@routeur.post(
    "/casse/declarations/{declaration_id}/valider",
    response_model=ReponseValidationCasse,
)
def valider_casse(
    declaration_id: int,
    demande: DemandeValidationCasse,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Validation d'une casse déclarée (addendum, point f) : réservée au
    responsable — décrémente réellement le stock. Un responsable peut
    valider sa propre déclaration (décision 2026-09-23, pas de séparation
    stricte déclarant/validateur)."""
    del demande  # corps volontairement vide, voir DemandeValidationCasse
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT article_id, site_id FROM declarations_casse WHERE id = %s",
                    (declaration_id,),
                )
                declaration = cur.fetchone()
                if declaration is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Déclaration de casse introuvable.")
                cur.execute(
                    "SELECT valider_casse(%s, %s) AS quantite_stock",
                    (declaration_id, session.utilisateur_id),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.RestrictViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseValidationCasse(
        declaration_id=declaration_id, article_id=declaration["article_id"],
        site_id=declaration["site_id"], quantite_stock=ligne["quantite_stock"],
    )


@routeur.post(
    "/retours-client/declarations",
    response_model=ReponseDeclarationRetourClient,
    status_code=status.HTTP_201_CREATED,
)
def declarer_retour_client(
    demande: DemandeDeclarationRetourClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Déclaration d'un retour client (addendum, point f, décision
    2026-09-22) : SANS effet sur le stock — la validation du responsable
    (ci-dessous) est obligatoire avant toute réintégration."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT declarer_retour_client(%s, %s, %s, %s, %s, %s, %s) AS declaration_id",
                    (demande.article_id, demande.vente_id, demande.quantite, demande.issue,
                     demande.etat_marchandise, session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseDeclarationRetourClient(declaration_id=ligne["declaration_id"], statut="en_attente")


@routeur.get("/retours-client/declarations", response_model=list[ReponseRetourClientDetail])
def lister_declarations_retour_client(
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Déclarations de retour client EN ATTENTE de validation — mêmes
    règles de site que les déclarations de casse (RLS,
    `p_declarations_retour_site`, migration 036)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id AS declaration_id, article_id, vente_id, site_id, quantite, issue,"
                " etat_marchandise, motif, declarant_id, date_declaration, statut"
                " FROM declarations_retour_client WHERE statut = 'en_attente' ORDER BY date_declaration"
            )
            lignes = cur.fetchall()

    return lignes


@routeur.post(
    "/retours-client/declarations/{declaration_id}/valider",
    response_model=ReponseValidationRetourClient,
)
def valider_retour_client(
    declaration_id: int,
    demande: DemandeValidationRetourClient,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Validation d'un retour client déclaré (addendum, point f) : réservée
    au responsable. Refuse un remboursement espèces sans
    ``confirmation_remboursement`` explicite (règle posée par la fonction
    elle-même, pas seulement ici)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT article_id, site_id FROM declarations_retour_client WHERE id = %s",
                    (declaration_id,),
                )
                declaration = cur.fetchone()
                if declaration is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Déclaration de retour introuvable.")
                cur.execute(
                    "SELECT valider_retour_client(%s, %s, %s) AS quantite_stock",
                    (declaration_id, session.utilisateur_id, demande.confirmation_remboursement),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.RestrictViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseValidationRetourClient(
        declaration_id=declaration_id, article_id=declaration["article_id"],
        site_id=declaration["site_id"], quantite_stock=ligne["quantite_stock"],
    )


@routeur.post(
    "/articles-offerts/declarations",
    response_model=ReponseDeclarationArticleOffert,
    status_code=status.HTTP_201_CREATED,
)
def declarer_article_offert(
    demande: DemandeDeclarationArticleOffert,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Déclaration d'un article offert (addendum, point f, décision
    2026-09-22/24) : SANS effet sur le stock — la validation du responsable
    (ci-dessous) est obligatoire avant toute sortie réelle. Ouverte à qui
    vend (agent comptabilité, responsable), jamais à l'agent stock — à la
    différence de la casse."""
    site_cible = _site_cible(session, demande.site_id)
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT declarer_article_offert(%s, %s, %s, %s, %s, %s, %s, %s) AS declaration_id",
                    (demande.article_id, site_cible, demande.quantite, demande.motif,
                     demande.employe_id, session.utilisateur_id, demande.vente_id, demande.client_nom),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation,
                    psycopg.errors.InsufficientPrivilege) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseDeclarationArticleOffert(declaration_id=ligne["declaration_id"], statut="en_attente")


@routeur.get("/articles-offerts/declarations", response_model=list[ReponseArticleOffertDetail])
def lister_declarations_article_offert(
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Déclarations d'article offert EN ATTENTE de validation — mêmes règles
    de site que les déclarations de casse/retour (RLS,
    `p_declarations_offert_site`, migration 039)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id AS declaration_id, article_id, site_id, quantite, valeur_normale,"
                " vente_id, client_nom, employe_id, motif, declarant_id, date_declaration, statut"
                " FROM declarations_article_offert WHERE statut = 'en_attente' ORDER BY date_declaration"
            )
            lignes = cur.fetchall()

    return lignes


@routeur.post(
    "/articles-offerts/declarations/{declaration_id}/valider",
    response_model=ReponseValidationArticleOffert,
)
def valider_article_offert(
    declaration_id: int,
    demande: DemandeValidationArticleOffert,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Validation d'un article offert déclaré (addendum, point f) : réservée
    au responsable — décrémente réellement le stock."""
    del demande  # corps volontairement vide, voir DemandeValidationArticleOffert
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT article_id, site_id FROM declarations_article_offert WHERE id = %s",
                    (declaration_id,),
                )
                declaration = cur.fetchone()
                if declaration is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, "Déclaration d'article offert introuvable.")
                cur.execute(
                    "SELECT valider_article_offert(%s, %s) AS quantite_stock",
                    (declaration_id, session.utilisateur_id),
                )
            except (psycopg.errors.CheckViolation, psycopg.errors.RestrictViolation) as exc:
                raise _erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseValidationArticleOffert(
        declaration_id=declaration_id, article_id=declaration["article_id"],
        site_id=declaration["site_id"], quantite_stock=ligne["quantite_stock"],
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
