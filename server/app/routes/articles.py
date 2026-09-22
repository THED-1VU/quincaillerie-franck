"""Création et modification d'articles (chantier C4, cycles 9 et 11 ;
adapté au modèle multi-site au cycle 35, chantier 13b).

Depuis la décision du 2026-09-19 (VISION_PRODUIT.md « une fiche, un stock
par site »), un article est une FICHE sans site : le stock vit dans
``stocks_sites``. La création d'une fiche ne prend donc plus aucun site, et
toute quantité réelle passe par les fonctions de mouvement (cycle 9) —
jamais par une modification de fiche.

Le prix n'est accepté que pour un responsable : un agent stock qui en
envoie un le voit simplement ignoré (la base le refuserait de toute façon,
mais un ``INSERT`` échoué renverrait une erreur brute — ici, on ne construit
la requête qu'avec les colonnes que le rôle appelant a le droit d'écrire).

``GET /articles/autre-site`` (cycle 11) n'existe plus : le catalogue est
désormais commun aux deux sites, le transfert ne désigne plus un article de
destination (migration 028).
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeArticle,
    DemandeModificationArticle,
    ReponseArticle,
    ReponseModificationArticle,
)
from ..securite import Session

routeur = APIRouter(prefix="/articles", tags=["articles"])


@routeur.post("", response_model=ReponseArticle, status_code=status.HTTP_201_CREATED)
def creer_article(
    demande: DemandeArticle,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                if session.role == "responsable":
                    cur.execute(
                        """
                        INSERT INTO articles
                            (nom, categorie, unite, prix_achat, prix_vente, fournisseur_id,
                             quantite_decimale_autorisee)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            demande.nom, demande.categorie, demande.unite,
                            demande.prix_achat or 0, demande.prix_vente or 0,
                            demande.fournisseur_id, demande.quantite_decimale_autorisee,
                        ),
                    )
                else:
                    # Agent stock : ni prix_achat ni prix_vente ne sont écrits
                    # (la colonne prend son DEFAULT 0 en base, migration 008) —
                    # un prix envoyé quand même est silencieusement ignoré.
                    # quantite_decimale_autorisee suit l'unité (migration 033,
                    # point f) : même paire de rôles autorisée à la fixer.
                    cur.execute(
                        """
                        INSERT INTO articles
                            (nom, categorie, unite, fournisseur_id, quantite_decimale_autorisee)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            demande.nom, demande.categorie, demande.unite,
                            demande.fournisseur_id, demande.quantite_decimale_autorisee,
                        ),
                    )
            except psycopg.errors.ForeignKeyViolation as exc:
                raise erreur_metier(exc) from exc
            article_id = cur.fetchone()["id"]

    return ReponseArticle(
        article_id=article_id, nom=demande.nom, unite=demande.unite,
        quantite_decimale_autorisee=demande.quantite_decimale_autorisee,
    )


@routeur.put("/{article_id}", response_model=ReponseModificationArticle)
def modifier_article(
    article_id: int,
    demande: DemandeModificationArticle,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Modifie une fiche article existante : nom, catégorie, unité pour les
    deux rôles ; prix d'achat/vente et fournisseur pour le responsable
    seulement — mêmes colonnes que les ``GRANT`` du cycle 2, révisés au
    cycle 35 (migration 029). La quantité et le seuil d'alerte vivent dans
    ``stocks_sites`` et ne sont JAMAIS acceptés ici : toute quantité passe
    par les fonctions de mouvement, sinon l'audit de ``mouvements_stock``
    serait contournable.

    Chaque champ réellement changé est tracé dans
    ``historique_modifications_articles`` ; un changement de prix est en
    plus tracé dans ``historique_prix_articles`` (responsable seulement).
    """
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            if session.role == "responsable":
                cur.execute(
                    "SELECT nom, categorie, unite, prix_achat, prix_vente, fournisseur_id,"
                    " quantite_decimale_autorisee"
                    " FROM articles WHERE id = %s",
                    (article_id,),
                )
            else:
                cur.execute(
                    "SELECT nom, categorie, unite, quantite_decimale_autorisee"
                    " FROM articles WHERE id = %s",
                    (article_id,),
                )
            actuel = cur.fetchone()
            if actuel is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Article introuvable.")

            champs: dict[str, object] = {}
            if demande.nom is not None:
                champs["nom"] = demande.nom
            if demande.unite is not None:
                champs["unite"] = demande.unite
            if demande.categorie is not None:
                champs["categorie"] = demande.categorie
            if demande.quantite_decimale_autorisee is not None:
                champs["quantite_decimale_autorisee"] = demande.quantite_decimale_autorisee
            if session.role == "responsable":
                if demande.fournisseur_id is not None:
                    champs["fournisseur_id"] = demande.fournisseur_id
                if demande.prix_achat is not None:
                    champs["prix_achat"] = demande.prix_achat
                if demande.prix_vente is not None:
                    champs["prix_vente"] = demande.prix_vente

            if not champs:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Aucun champ à modifier.")

            colonnes_retour = "id, nom, categorie, unite, quantite_decimale_autorisee"
            if session.role == "responsable":
                colonnes_retour += ", prix_achat, prix_vente"
            set_clause = ", ".join(f"{colonne} = %s" for colonne in champs)

            try:
                cur.execute(
                    f"UPDATE articles SET {set_clause} WHERE id = %s RETURNING {colonnes_retour}",  # noqa: S608
                    (*champs.values(), article_id),
                )
                ligne = cur.fetchone()
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation) as exc:
                raise erreur_metier(exc) from exc

            for champ in ("nom", "categorie", "unite", "fournisseur_id", "quantite_decimale_autorisee"):
                if champ in champs and str(actuel[champ]) != str(champs[champ]):
                    cur.execute(
                        """
                        INSERT INTO historique_modifications_articles
                            (article_id, utilisateur_id, champ, ancienne_valeur, nouvelle_valeur)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            article_id, session.utilisateur_id, champ,
                            None if actuel[champ] is None else str(actuel[champ]),
                            str(champs[champ]),
                        ),
                    )

            prix_achat_change = (
                "prix_achat" in champs and float(actuel["prix_achat"]) != champs["prix_achat"]
            )
            prix_vente_change = (
                "prix_vente" in champs and float(actuel["prix_vente"]) != champs["prix_vente"]
            )
            if prix_achat_change or prix_vente_change:
                nouveau_prix_achat = champs.get("prix_achat", actuel["prix_achat"])
                nouveau_prix_vente = champs.get("prix_vente", actuel["prix_vente"])
                cur.execute(
                    """
                    INSERT INTO historique_prix_articles
                        (article_id, utilisateur_id, ancien_prix_achat, nouveau_prix_achat,
                         ancien_prix_vente, nouveau_prix_vente)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        article_id, session.utilisateur_id,
                        actuel["prix_achat"], nouveau_prix_achat,
                        actuel["prix_vente"], nouveau_prix_vente,
                    ),
                )

    return ReponseModificationArticle(
        article_id=ligne["id"], nom=ligne["nom"], categorie=ligne["categorie"],
        unite=ligne["unite"], quantite_decimale_autorisee=ligne["quantite_decimale_autorisee"],
        prix_achat=ligne.get("prix_achat"), prix_vente=ligne.get("prix_vente"),
    )
