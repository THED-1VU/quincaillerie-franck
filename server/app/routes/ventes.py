"""Enregistrement d'une vente (chantier C5).

Décisions du propriétaire appliquées ici (cycle 6 — voir
ADDENDUM_CAHIER_DES_CHARGES.md, section « Décisions prises », et
db/migrations/011_ventes_fiscalite_anti_survente.sql) :

  * point e (anti-survente) — cette route n'échoue JAMAIS pour cause de
    stock insuffisant. Le circuit réel de la boutique fait encaisser AVANT
    que la comptabilité ne saisisse la vente (le client est déjà reparti
    avec la marchandise) : refuser la saisie n'aurait aucun sens. Le
    décompte du stock passe par ``decrementer_stock_vente()``, qui consigne
    un écart plutôt que de refuser — jamais visible de l'agent stock, qui
    compte à l'aveugle (chantier C7).
  * point d (fiscalité) — régime du réel, TVA 19,25 %, prix négociés TTC,
    arrondi arithmétique sur le TOTAL de TVA de la vente (jamais ligne à
    ligne, pour éviter les écarts d'un franc). Le taux n'est jamais une
    constante du code : il vient de ``parametres`` via ``parametre_numerique``.
  * point b (crédit client) — PAS activé ce cycle. ``mode_paiement =
    'credit_client'`` est explicitement refusé ici, avec un message clair :
    aucune table Client, aucune créance n'existe tant que le reste du
    point b n'est pas tranché.
  * point c (numéro facturier + vendeur) — NON traité ce cycle. La vente est
    enregistrée sans cette traçabilité anti-vol (priorité n°3 du
    propriétaire, volontairement incomplète) — voir loop-state.md.

Une vente saisie ici est immédiatement ``payee`` : il n'existe pas d'étape
``en_attente`` pour ce que cette route couvre (saisie a posteriori d'un
encaissement déjà fait), conformément au circuit réel de la boutique.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from ..roles import role_pg
from ..schemas import (
    DemandeAnnulationVente,
    DemandeVente,
    LigneEcartReponse,
    ReponseAnnulationVente,
    ReponseVente,
)
from ..securite import Session

routeur = APIRouter(prefix="/ventes", tags=["ventes"])

# 'credit_client' existe dans le CHECK du schéma d'origine mais reste
# désactivé au niveau applicatif : décision du propriétaire, cycle 6
# (addendum, point b — voir le message dédié ci-dessous).
_MODES_PAIEMENT_ACTIFS = {"especes", "orange_money", "mtn_momo", "autre"}


@routeur.get("/parametres")
def parametres_vente(
    request: Request, session: Session = Depends(exiger_role("responsable", "agent_comptabilite"))
):
    """Taux de TVA actuellement en vigueur (addendum, point d).

    Jamais une constante écrite en dur côté écran : la maquette lit cette
    route pour afficher un aperçu du total AVANT validation. Le calcul qui
    compte reste celui, faisant foi, de ``enregistrer_vente`` ci-dessous.
    """
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT parametre_numerique(%s) AS v", ("taux_tva",))
            taux_tva = cur.fetchone()["v"]
    return {"taux_tva": float(taux_tva)}


@routeur.post("", response_model=ReponseVente, status_code=status.HTTP_201_CREATED)
def enregistrer_vente(
    demande: DemandeVente,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    if demande.mode_paiement == "credit_client":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La vente à crédit n'est pas encore activée "
            "(décision du propriétaire en attente — addendum, point b).",
        )
    if demande.mode_paiement not in _MODES_PAIEMENT_ACTIFS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mode de paiement inconnu.")

    # Le site vient TOUJOURS de la session pour un agent (jamais du corps de
    # la requête, que l'appelant pourrait manipuler) ; le responsable, qui
    # couvre les deux sites, doit le préciser explicitement.
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
            cur.execute("SELECT parametre_numerique(%s) AS v", ("taux_tva",))
            taux_tva = cur.fetchone()["v"]

            # Point h (rôle caissier) non tranché : il n'existe aujourd'hui
            # qu'un responsable qui encaisse réellement. On le retrouve ici
            # plutôt que d'inventer un choix de caissier côté écran.
            cur.execute("SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1")
            ligne_resp = cur.fetchone()
            if ligne_resp is None:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Aucun compte responsable trouvé pour l'encaissement.",
                )
            utilisateur_caisse_id = ligne_resp["id"]

            # Prix négociés TTC (point d) : on agrège d'abord le TTC de
            # chaque ligne, puis on extrait la TVA sur le TOTAL — jamais
            # ligne à ligne, pour éviter les écarts d'un franc (addendum).
            total_ttc = sum(
                (Decimal(str(ligne.prix_unitaire)) * ligne.quantite for ligne in demande.lignes),
                start=Decimal("0"),
            )
            if taux_tva > 0:
                montant_tva = (total_ttc * taux_tva / (Decimal("100") + taux_tva)).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            else:
                montant_tva = Decimal("0")
            sous_total_ht = total_ttc - montant_tva

            cur.execute(
                """
                INSERT INTO ventes
                    (site_id, utilisateur_id, statut, mode_paiement,
                     utilisateur_caisse_id, sous_total_ht, taux_tva,
                     montant_tva, total_ttc, date_encaissement)
                VALUES (%s, %s, 'payee', %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
                """,
                (
                    site_cible, session.utilisateur_id, demande.mode_paiement,
                    utilisateur_caisse_id, sous_total_ht, taux_tva, montant_tva, total_ttc,
                ),
            )
            vente_id = cur.fetchone()["id"]

            ecarts: list[LigneEcartReponse] = []
            for ligne in demande.lignes:
                try:
                    cur.execute(
                        """
                        INSERT INTO ventes_lignes (vente_id, article_id, quantite, prix_unitaire, site_id)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (vente_id, ligne.article_id, ligne.quantite, ligne.prix_unitaire, site_cible),
                    )
                except psycopg.errors.ForeignKeyViolation as exc:
                    # Article inexistant, ou existant sur l'AUTRE site : la
                    # clé étrangère composite (migration 002) refuse déjà de
                    # vendre au mauvais site un article qui n'y est pas.
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Article introuvable sur ce site (identifiant {ligne.article_id}).",
                    ) from exc

                cur.execute(
                    "SELECT * FROM decrementer_stock_vente(%s, %s, %s, %s, %s)",
                    (
                        ligne.article_id, ligne.quantite, session.utilisateur_id,
                        vente_id, f"vente #{vente_id}",
                    ),
                )
                resultat = cur.fetchone()
                if resultat["quantite_manquante"] > 0:
                    ecarts.append(
                        LigneEcartReponse(
                            article_id=ligne.article_id,
                            quantite_manquante=resultat["quantite_manquante"],
                        )
                    )

            # Une recette par vente (cahier des charges §3.3) — le crédit
            # client étant désactivé ce cycle (point b), toute vente payée
            # ici en crée systématiquement une. L'index unique partiel
            # (migration 002) empêche de toute façon le double comptage.
            cur.execute(
                """
                INSERT INTO transactions (site_id, utilisateur_id, type, montant, description, vente_id)
                VALUES (%s, %s, 'recette', %s, %s, %s)
                """,
                (site_cible, session.utilisateur_id, total_ttc, f"Vente #{vente_id}", vente_id),
            )
        # Commit automatique à la sortie de connexion_pour() (voir auth.py).

    return ReponseVente(
        vente_id=vente_id,
        site_id=site_cible,
        sous_total_ht=float(sous_total_ht),
        taux_tva=float(taux_tva),
        montant_tva=float(montant_tva),
        total_ttc=float(total_ttc),
        ecarts=ecarts,
    )


@routeur.post("/{vente_id}/annuler", response_model=ReponseAnnulationVente)
def annuler_vente(
    vente_id: int,
    demande: DemandeAnnulationVente,
    request: Request,
    session: Session = Depends(exiger_role("responsable")),
):
    """Annulation d'une vente (chantier C5, cycle 17) — **responsable
    seul** (CDC §3.3) : restitue exactement le stock réellement décrémenté
    (``annuler_vente()``, migration 017 — pas la quantité vendue, une
    vente acceptée à découvert n'avait pas tout décrémenté, point e),
    contre-passe la recette par une dépense de même montant, et
    régularise d'office tout écart de vente à découvert devenu sans objet.
    Une vente déjà annulée, ou introuvable, est refusée par la fonction
    elle-même — jamais une seconde fois, jamais réversible (migration 005,
    cycle 2)."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT * FROM annuler_vente(%s, %s, %s)",
                    (vente_id, session.utilisateur_id, demande.motif),
                )
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.CheckViolation,
                    psycopg.errors.RestrictViolation) as exc:
                raise erreur_metier(exc) from exc
            ligne = cur.fetchone()

    return ReponseAnnulationVente(
        vente_id=vente_id,
        montant_ttc=float(ligne["montant_ttc"]),
        articles_restitues=ligne["articles_restitues"],
    )
