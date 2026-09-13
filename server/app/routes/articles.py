"""Création et modification d'articles (chantier C4, cycles 9 et 11).

Un article naît TOUJOURS à ``quantite_stock = 0`` (défaut du schéma) : la
reprise d'un stock initial dépend du point j de l'addendum (volumétrie),
non tranché — voir ``db/migrations/014_...``. Toute quantité réelle passe
ensuite par une réception (``POST /stock/entrees``).

Le prix n'est accepté que pour un responsable : un agent stock qui en
envoie un le voit simplement ignoré (la base le refuserait de toute façon,
mais un ``INSERT`` échoué renverrait une erreur brute — ici, on ne construit
la requête qu'avec les colonnes que le rôle appelant a le droit d'écrire).

Cycle 11 (écran de stock) y ajoute ``PUT /articles/{id}`` (modification,
avec traçabilité dans les tables d'historique du cycle 1) et
``GET /articles/autre-site`` (choisir la destination d'un transfert sans
exposer le stock de l'autre site — migration 015).
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
    ReponseArticleAutreSite,
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
            try:
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
            except psycopg.errors.ForeignKeyViolation as exc:
                # Trouvé au contrôle de boucle après le cycle 9 : un site_id
                # ou fournisseur_id invalide remontait en 500 générique
                # avant ce correctif (cycle 11).
                raise erreur_metier(exc) from exc
            article_id = cur.fetchone()["id"]

    return ReponseArticle(article_id=article_id, nom=demande.nom, unite=demande.unite, site_id=site_cible)


@routeur.get("/autre-site", response_model=list[ReponseArticleAutreSite])
def articles_de_lautre_site(
    request: Request,
    session: Session = Depends(exiger_role("agent_stock")),
):
    """Articles de l'AUTRE site — nom et unité seulement, jamais prix ni
    quantité (migration 015) — pour choisir la destination d'un transfert
    inter-sites (cycle 11) sans exposer l'état du stock de l'autre site.
    Un responsable n'en a pas besoin : ``GET /articles`` lui montre déjà les
    deux sites, sans restriction RLS."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nom, unite, site_id FROM articles_autre_site()")
            lignes = cur.fetchall()

    return lignes


@routeur.put("/{article_id}", response_model=ReponseModificationArticle)
def modifier_article(
    article_id: int,
    demande: DemandeModificationArticle,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_stock")),
):
    """Modifie un article existant (chantier C4, cycle 11) : nom, catégorie,
    unité pour les deux rôles ; prix d'achat/vente et fournisseur pour le
    responsable seulement — mêmes colonnes que le ``GRANT UPDATE`` du
    cycle 2 (migration 008). ``quantite_stock`` et ``seuil_alerte`` ne sont
    JAMAIS acceptés ici, quel que soit le rôle, même si PostgreSQL le
    permettrait techniquement à un agent stock (migration 008) : toute
    quantité passe par les fonctions de mouvement (cycle 9), jamais par une
    modification de fiche — sinon l'audit de ``mouvements_stock`` serait
    contournable.

    Chaque champ réellement changé est tracé dans
    ``historique_modifications_articles`` ; un changement de prix est en
    plus tracé dans ``historique_prix_articles`` (responsable seulement) —
    deux tables qui existaient depuis le cycle 1 sans jamais avoir reçu de
    ligne, faute de route.
    """
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            if session.role == "responsable":
                cur.execute(
                    "SELECT nom, categorie, unite, prix_achat, prix_vente, fournisseur_id, site_id"
                    " FROM articles WHERE id = %s",
                    (article_id,),
                )
            else:
                cur.execute(
                    "SELECT nom, categorie, unite, site_id FROM articles WHERE id = %s",
                    (article_id,),
                )
            actuel = cur.fetchone()
            # RLS rend un article de l'autre site introuvable, pas interdit
            # (même principe qu'ailleurs dans le serveur) : on ne distingue
            # pas ce cas d'un identifiant simplement inexistant.
            if actuel is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Article introuvable.")

            champs: dict[str, object] = {}
            if demande.nom is not None:
                champs["nom"] = demande.nom
            if demande.unite is not None:
                champs["unite"] = demande.unite
            if demande.categorie is not None:
                champs["categorie"] = demande.categorie
            if session.role == "responsable":
                if demande.fournisseur_id is not None:
                    champs["fournisseur_id"] = demande.fournisseur_id
                if demande.prix_achat is not None:
                    champs["prix_achat"] = demande.prix_achat
                if demande.prix_vente is not None:
                    champs["prix_vente"] = demande.prix_vente

            if not champs:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Aucun champ à modifier.")

            colonnes_retour = "id, nom, categorie, unite, site_id"
            if session.role == "responsable":
                colonnes_retour += ", prix_achat, prix_vente"
            set_clause = ", ".join(f"{colonne} = %s" for colonne in champs)

            try:
                cur.execute(
                    f"UPDATE articles SET {set_clause} WHERE id = %s RETURNING {colonnes_retour}",  # noqa: S608
                    # `champs` (les clés) et `colonnes_retour` viennent de
                    # noms de colonnes fixes connus à l'avance ci-dessus,
                    # jamais du corps de la requête HTTP — pas d'injection
                    # possible.
                    (*champs.values(), article_id),
                )
                ligne = cur.fetchone()
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation) as exc:
                raise erreur_metier(exc) from exc

            for champ in ("nom", "categorie", "unite", "fournisseur_id"):
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

            if "prix_achat" in champs or "prix_vente" in champs:
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
        unite=ligne["unite"], site_id=ligne["site_id"],
        prix_achat=ligne.get("prix_achat"), prix_vente=ligne.get("prix_vente"),
    )
