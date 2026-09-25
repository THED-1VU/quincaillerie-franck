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
  * point b (crédit client) — activé (décidé le 2026-09-25, migration 045).
    ``mode_paiement = 'credit_client'`` exige un ``client_id``, vérifie que
    le client est actif et que la vente ne dépasse pas son plafond, puis
    crée une CRÉANCE (table ``creances``) au lieu d'une recette
    (``transactions``) — activable/désactivable par boutique via le
    paramètre ``credit_client_actif`` (produit vendu en gamme).
  * point c (numéro facturier + vendeur) — traité au cycle 27, périmètre
    réduit au socle décidé (voir db/migrations/020_facturier_vendeur.sql) :
    ``numero_facturier`` (référence du carnet PAPIER, transcrite par le
    comptable — jamais générée par ce logiciel) et ``vendeur_id`` (qui a
    négocié le prix) sont obligatoires sur toute nouvelle vente, avec
    préfixe vérifié par site (``MAG-``/``CPT-``). ``vendeur_id`` référence
    une fiche employé (module RH), PAS un compte utilisateur, depuis le
    chantier B (question 3, tranchée le 2026-09-25, migration 040) — un
    vendeur peut n'avoir jamais eu de compte. Le rapport « écarts de prix
    par vendeur » et le seuil de validation d'un écart (question 5) ne
    sont toujours PAS construits — non tranchés.

Une vente saisie ici est immédiatement ``payee`` : il n'existe pas d'étape
``en_attente`` pour ce que cette route couvre (saisie a posteriori d'un
encaissement déjà fait), conformément au circuit réel de la boutique.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.sax.saxutils import escape as _echapper_xml

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as ImagePDF
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..deps import exiger_role, obtenir_bd
from ..erreurs import erreur_metier
from .configuration import DOSSIER_LOGO
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

# 'credit_client' est géré à PART (voir `est_credit` ci-dessous, addendum
# point b, migration 045) : jamais dans cet ensemble, dont chaque valeur
# crée une recette de caisse (transactions) — une vente à crédit ne le fait
# jamais.
_MODES_PAIEMENT_ACTIFS = {"especes", "orange_money", "mtn_momo", "autre"}


@routeur.get("/parametres")
def parametres_vente(
    request: Request, session: Session = Depends(exiger_role("responsable", "agent_comptabilite"))
):
    """Taux de TVA actuellement en vigueur (addendum, point d), et si le
    crédit client (addendum, point b) est activé pour cette boutique.

    Jamais une constante écrite en dur côté écran : la maquette lit cette
    route pour afficher un aperçu du total AVANT validation. Le calcul qui
    compte reste celui, faisant foi, de ``enregistrer_vente`` ci-dessous.
    """
    bd = obtenir_bd(request)
    with bd.connexion_pour(role_pg(session.role), utilisateur_id=session.utilisateur_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT parametre_numerique(%s) AS v", ("taux_tva",))
            taux_tva = cur.fetchone()["v"]
            cur.execute("SELECT valeur FROM parametres WHERE cle = 'credit_client_actif'")
            ligne = cur.fetchone()
            credit_client_actif = bool(ligne and ligne["valeur"] == "oui")
    return {"taux_tva": float(taux_tva), "credit_client_actif": credit_client_actif}


@routeur.get("/vendeurs")
def lister_vendeurs(
    request: Request,
    site_id: int | None = None,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Employés utilisables comme ``vendeur_id`` (addendum, point c, question
    3 tranchée le 2026-09-25, migration 040) — pour remplir le menu déroulant
    de l'écran de vente.

    Une fiche employé (module RH), PAS un compte utilisateur : un vendeur
    peut n'avoir jamais eu de compte (aide occasionnel qui négocie un prix
    sans jamais se connecter). Uniquement des employés actifs, du site de
    cette vente (un agent d'un site ne négocie pas de prix pour l'autre) ;
    un employé ``site_id`` NULL couvre les deux sites (même convention que
    ``declarations_article_offert.employe_id``, migration 039)."""
    if session.site_id is not None:
        site_cible = session.site_id
    elif site_id is not None:
        site_cible = site_id
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
            cur.execute(
                """
                SELECT id, nom_complet FROM employes
                 WHERE actif = TRUE AND (site_id = %s OR site_id IS NULL)
                 ORDER BY nom_complet
                """,
                (site_cible,),
            )
            lignes = cur.fetchall()
    return {"vendeurs": lignes}


@routeur.post("", response_model=ReponseVente, status_code=status.HTTP_201_CREATED)
def enregistrer_vente(
    demande: DemandeVente,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    est_credit = demande.mode_paiement == "credit_client"
    if not est_credit and demande.mode_paiement not in _MODES_PAIEMENT_ACTIFS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mode de paiement inconnu.")
    if est_credit and demande.client_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Le client est obligatoire pour une vente à crédit.",
        )

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

            # Crédit client (addendum point b, décidé le 2026-09-25) :
            # activable/désactivable par boutique — vérifié ICI, pas
            # seulement côté écran, puisque c'est la seule vraie source de
            # vérité. Le plafond est vérifié plus bas, une fois le total
            # TTC de la vente connu.
            if est_credit:
                cur.execute("SELECT valeur FROM parametres WHERE cle = 'credit_client_actif'")
                ligne_param = cur.fetchone()
                if not (ligne_param and ligne_param["valeur"] == "oui"):
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "La vente à crédit n'est pas activée pour cette boutique.",
                    )
                cur.execute(
                    "SELECT actif, encours_client(id) AS encours, plafond_credit "
                    "FROM clients WHERE id = %s",
                    (demande.client_id,),
                )
                ligne_client = cur.fetchone()
                if ligne_client is None:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Client introuvable (identifiant {demande.client_id}).",
                    )
                if not ligne_client["actif"]:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Le client {demande.client_id} n'est plus actif.",
                    )

            # Point h (rôle caissier) : décidé le 2026-09-13 (fusionné avec
            # agent_comptabilite, cycle 27 — voir ADDENDUM_CAHIER_DES_CHARGES.md).
            # Cette ligne reste néanmoins inchangée ce cycle : elle attribue
            # TOUJOURS l'encaissement au responsable, même quand c'est un
            # agent_comptabilite qui saisit réellement la vente — un
            # désaccord désormais visible avec la décision ci-dessus,
            # signalé mais volontairement PAS corrigé ici (hors du
            # périmètre validé pour le point c de ce cycle ; vendeur_id,
            # ajouté plus bas, couvre déjà « qui a négocié le prix », ce qui
            # motivait initialement ce chantier).
            cur.execute("SELECT id FROM utilisateurs WHERE role = 'responsable' LIMIT 1")
            ligne_resp = cur.fetchone()
            if ligne_resp is None:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Aucun compte responsable trouvé pour l'encaissement.",
                )
            utilisateur_caisse_id = ligne_resp["id"]

            # Vendeur = une fiche employé, jamais un compte utilisateur
            # (addendum point c, question 3, migration 040) : validé ici
            # plutôt que de laisser la seule contrainte FK répondre — même
            # style de message que declarer_article_offert() (migration 039),
            # pour rester cohérent d'un point d'écriture à l'autre.
            cur.execute(
                "SELECT site_id, actif FROM employes WHERE id = %s", (demande.vendeur_id,)
            )
            ligne_vendeur = cur.fetchone()
            if ligne_vendeur is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Vendeur introuvable (employé {demande.vendeur_id}).",
                )
            if not ligne_vendeur["actif"]:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"L'employé {demande.vendeur_id} n'est plus actif.",
                )
            if ligne_vendeur["site_id"] is not None and ligne_vendeur["site_id"] != site_cible:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"L'employé {demande.vendeur_id} n'appartient pas au site {site_cible}.",
                )

            # Remises (addendum, point f, décision 2026-09-22) : seuil de
            # validation responsable — 'a_definir' tant que le propriétaire
            # n'a pas fixé de chiffre, AUCUN blocage dans ce cas (même
            # principe que duree_session_minutes, seuil_ecart_caisse_tolere,
            # plafond_vraisemblance_comptage).
            cur.execute(
                "SELECT valeur FROM parametres WHERE cle = %s", ("seuil_remise_validation_pct",)
            )
            ligne_seuil = cur.fetchone()
            seuil_remise_pct = (
                Decimal(ligne_seuil["valeur"])
                if ligne_seuil and ligne_seuil["valeur"] != "a_definir"
                else None
            )

            # Résout prix_unitaire/prix_catalogue/remise_montant PAR LIGNE,
            # AVANT toute écriture — le prix catalogue est lu ici, jamais
            # fourni par le client (qui pourrait en inventer un pour
            # maquiller une remise). Une seule des trois entrées
            # (prix_unitaire / remise_montant / remise_pct) est fournie par
            # ligne, imposé par LigneVenteDemande (schemas.py).
            lignes_resolues = []
            for ligne in demande.lignes:
                cur.execute("SELECT prix_vente FROM articles WHERE id = %s", (ligne.article_id,))
                article = cur.fetchone()
                if article is None:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Article introuvable (identifiant {ligne.article_id}).",
                    )
                prix_catalogue = Decimal(str(article["prix_vente"]))

                if ligne.prix_unitaire is not None:
                    prix_unitaire = Decimal(str(ligne.prix_unitaire))
                    # GREATEST(..., 0) : un prix négocié AU-DESSUS du
                    # catalogue reste légitime (point d) — ce n'est pas une
                    # remise négative, juste une remise nulle.
                    remise_montant = max(prix_catalogue - prix_unitaire, Decimal("0"))
                elif ligne.remise_montant is not None:
                    remise_montant = Decimal(str(ligne.remise_montant))
                    prix_unitaire = prix_catalogue - remise_montant
                else:
                    remise_pct = Decimal(str(ligne.remise_pct))
                    remise_montant = (prix_catalogue * remise_pct / Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    prix_unitaire = prix_catalogue - remise_montant

                # Décision 2026-09-23 : une remise à 100 % (ou plus) est
                # REFUSÉE ici — c'est le sous-chantier « article offert »
                # qui la couvre, un mécanisme dédié et distinct (une seule
                # voie d'écriture par concept, même principe qu'au
                # sous-chantier 2 pour la casse/le retour).
                if prix_unitaire <= 0:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "Une remise portant le prix à zéro (ou moins) est refusée pour "
                        "l'article %d : utiliser le mécanisme dédié à l'article offert."
                        % ligne.article_id,
                    )

                if (
                    seuil_remise_pct is not None
                    and session.role != "responsable"
                    and prix_catalogue > 0
                    and (remise_montant / prix_catalogue) * 100 > seuil_remise_pct
                ):
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        f"Remise supérieure à {seuil_remise_pct} % sur l'article "
                        f"{ligne.article_id} : seul un compte responsable peut "
                        "enregistrer cette vente.",
                    )

                lignes_resolues.append({
                    "article_id": ligne.article_id, "quantite": ligne.quantite,
                    "prix_unitaire": prix_unitaire, "prix_catalogue": prix_catalogue,
                    "remise_montant": remise_montant,
                })

            # Prix négociés TTC (point d) : on agrège d'abord le TTC de
            # chaque ligne, puis on extrait la TVA sur le TOTAL — jamais
            # ligne à ligne, pour éviter les écarts d'un franc (addendum).
            total_ttc_brut = sum(
                (lr["prix_unitaire"] * lr["quantite"] for lr in lignes_resolues),
                start=Decimal("0"),
            )
            remise_totale_lignes = sum(
                (lr["remise_montant"] * lr["quantite"] for lr in lignes_resolues),
                start=Decimal("0"),
            )

            # Remise de la vente ENTIÈRE (mécanisme séparé des remises par
            # ligne, décision 2026-09-22) : au plus une des deux entrées,
            # imposé par DemandeVente (schemas.py).
            if demande.remise_globale_montant is not None:
                remise_globale = Decimal(str(demande.remise_globale_montant))
            elif demande.remise_globale_pct is not None:
                remise_globale = (
                    total_ttc_brut * Decimal(str(demande.remise_globale_pct)) / Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                remise_globale = Decimal("0")

            if remise_globale >= total_ttc_brut:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "La remise globale ne peut pas atteindre ni dépasser le total de la vente.",
                )
            remise_globale_pct_reelle = (
                (remise_globale / total_ttc_brut) * 100 if total_ttc_brut > 0 else Decimal("0")
            )
            if (
                seuil_remise_pct is not None
                and session.role != "responsable"
                and remise_globale_pct_reelle > seuil_remise_pct
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    f"Remise globale supérieure à {seuil_remise_pct} % : seul un compte "
                    "responsable peut enregistrer cette vente.",
                )

            total_ttc = total_ttc_brut - remise_globale
            remise_totale = remise_totale_lignes + remise_globale

            if taux_tva > 0:
                montant_tva = (total_ttc * taux_tva / (Decimal("100") + taux_tva)).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            else:
                montant_tva = Decimal("0")
            sous_total_ht = total_ttc - montant_tva

            if est_credit:
                encours_apres = Decimal(str(ligne_client["encours"])) + total_ttc
                plafond = Decimal(str(ligne_client["plafond_credit"]))
                if encours_apres > plafond:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Cette vente porterait l'encours du client à {encours_apres} FCFA, "
                        f"au-delà de son plafond ({plafond} FCFA).",
                    )

            try:
                cur.execute(
                    """
                    INSERT INTO ventes
                        (site_id, utilisateur_id, statut, mode_paiement,
                         utilisateur_caisse_id, sous_total_ht, taux_tva,
                         montant_tva, total_ttc, date_encaissement,
                         numero_facturier, vendeur_id, remise_globale_montant)
                    VALUES (%s, %s, 'payee', %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        site_cible, session.utilisateur_id, demande.mode_paiement,
                        utilisateur_caisse_id, sous_total_ht, taux_tva, montant_tva, total_ttc,
                        demande.numero_facturier, demande.vendeur_id, remise_globale,
                    ),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Le numéro de facturier « {demande.numero_facturier} » est déjà utilisé "
                    "par une autre vente.",
                ) from exc
            except psycopg.errors.CheckViolation as exc:
                if "chk_ventes_numero_facturier_prefixe_site" in str(exc):
                    prefixe_attendu = "MAG-" if site_cible == 1 else "CPT-"
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Le numéro de facturier doit commencer par « {prefixe_attendu} » "
                        "pour ce site.",
                    ) from exc
                raise erreur_metier(exc) from exc
            except psycopg.errors.ForeignKeyViolation as exc:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Vendeur introuvable (compte utilisateur inexistant).",
                ) from exc
            vente_id = cur.fetchone()["id"]

            ecarts: list[LigneEcartReponse] = []
            for lr in lignes_resolues:
                try:
                    cur.execute(
                        """
                        INSERT INTO ventes_lignes
                            (vente_id, article_id, quantite, prix_unitaire, prix_catalogue,
                             remise_montant, site_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            vente_id, lr["article_id"], lr["quantite"], lr["prix_unitaire"],
                            lr["prix_catalogue"], lr["remise_montant"], site_cible,
                        ),
                    )
                except psycopg.errors.ForeignKeyViolation as exc:
                    # Article inexistant, ou sans stock sur ce site : la
                    # clé étrangère composite (migration 002, révisée 027)
                    # refuse déjà de vendre au mauvais site un article qui
                    # n'y a pas de stock.
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Article introuvable sur ce site (identifiant {lr['article_id']}).",
                    ) from exc

                cur.execute(
                    "SELECT * FROM decrementer_stock_vente(%s, %s, %s, %s, %s, %s)",
                    (
                        lr["article_id"], site_cible, lr["quantite"],
                        session.utilisateur_id,
                        vente_id, f"vente #{vente_id}",
                    ),
                )
                resultat = cur.fetchone()
                if resultat["quantite_manquante"] > 0:
                    ecarts.append(
                        LigneEcartReponse(
                            article_id=lr["article_id"],
                            quantite_manquante=resultat["quantite_manquante"],
                        )
                    )

            # Une recette par vente (cahier des charges §3.3) — SAUF une
            # vente à crédit (addendum point b, décidé le 2026-09-25) : elle
            # crée une créance, JAMAIS une recette encaissée (aucun argent
            # n'est réellement entré en caisse). L'index unique partiel
            # (migration 002) empêche de toute façon le double comptage sur
            # le chemin normal.
            if est_credit:
                cur.execute(
                    """
                    INSERT INTO creances (client_id, vente_id, site_id, montant, utilisateur_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (demande.client_id, vente_id, site_cible, total_ttc, session.utilisateur_id),
                )
            else:
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
        numero_facturier=demande.numero_facturier,
        sous_total_ht=float(sous_total_ht),
        taux_tva=float(taux_tva),
        montant_tva=float(montant_tva),
        total_ttc=float(total_ttc),
        remise_totale=float(remise_totale),
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


def _fcfa(montant) -> str:
    return f"{round(float(montant)):,}".replace(",", " ") + " FCFA"


def _construire_recu_pdf(boutique: dict, vente: dict, lignes: list[dict]) -> bytes:
    """Reçu imprimable d'une vente (chantier C5, cycle 19, étendu au cycle
    27 — CDC §3.3, §7.1 « imprimer / réimprimer le reçu »). N'affiche QUE
    ce qui a été réellement décidé par le propriétaire :
      * ``boutique_telephone``/``boutique_numero_contribuable`` restent
        ``a_definir`` (addendum, point d) — omis plutôt qu'inventés ;
      * ``numero_facture`` (facture fiscale détaillée, distincte du
        facturier papier ci-dessous, toujours non tranchée) est restitué
        tel quel — ``None`` ici, jamais fabriqué ; le numéro de vente
        interne est utilisé pour identifier le document si absent, comme
        dans ``/rapports/ventes`` (cycle 10) ;
      * ``numero_facturier``/``vendeur_nom`` (addendum point c, décidé le
        2026-09-13, cycle 27) : affichés quand présents ; ``None`` pour
        toute vente antérieure à ce cycle, jamais rétro-inventés.
    Une vente annulée reste imprimable (aucune règle du CDC ne l'interdit)
    mais porte une mention explicite — jamais un reçu d'apparence valide
    pour une vente qui ne l'est plus.
    """
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("titre", parent=styles["Title"], fontSize=16, spaceAfter=2)
    style_normal = styles["Normal"]
    style_centre = ParagraphStyle("centre", parent=style_normal, alignment=1)
    style_annule = ParagraphStyle(
        "annule", parent=style_normal, textColor=colors.red,
        fontName="Helvetica-Bold", alignment=1, fontSize=13, spaceBefore=6, spaceAfter=6,
    )

    # Paragraph() interprète un sous-ensemble XML (<b>, <br/>...) : tout texte
    # non fixe par le code (paramètres modifiables par le responsable, motif
    # d'annulation saisi librement) doit être échappé avant d'y entrer — un
    # nom de boutique ou un motif contenant "<" ou "&" ne doit ni casser le
    # document ni s'y injecter (même discipline que l'échappement HTML des
    # écrans, vérifié par exécution ailleurs — verifier-echappement-html.mjs).
    elements = []
    # Logo DE LA BOUTIQUE (cycle 28) — pas le logo Akuma (marque de
    # l'éditeur, n'apparaît pas sur un document destiné au client final).
    # Absent (aucun téléversement) : rien n'est ajouté, jamais un espace
    # réservé ni une image cassée sur un document imprimé.
    for extension, _fmt in (("png", "PNG"), ("jpg", "JPEG")):
        chemin_logo = DOSSIER_LOGO / f"logo.{extension}"
        if chemin_logo.is_file():
            logo = ImagePDF(str(chemin_logo))
            logo._restrictSize(30 * mm, 20 * mm)  # proportions gardées, hauteur bornée
            logo.hAlign = "CENTER"
            elements.append(logo)
            elements.append(Spacer(1, 2 * mm))
            break
    elements.append(Paragraph(_echapper_xml(boutique.get("boutique_nom") or "Quincaillerie Franck"), style_titre))
    sous_entete = [t for t in (boutique.get("boutique_ville"), boutique.get("boutique_telephone")) if t]
    if sous_entete:
        elements.append(Paragraph(_echapper_xml(" · ".join(sous_entete)), style_centre))
    if boutique.get("boutique_numero_contribuable"):
        elements.append(Paragraph("N° contribuable : " + _echapper_xml(boutique["boutique_numero_contribuable"]), style_centre))
    elements.append(Spacer(1, 8 * mm))

    identifiant_document = vente["numero_facture"] or f"vente n°{vente['id']}"
    elements.append(Paragraph(_echapper_xml(f"Reçu — {identifiant_document}"), styles["Heading2"]))
    elements.append(Paragraph(
        _echapper_xml(
            f"Date : {vente['date_encaissement']:%d/%m/%Y %H:%M} — "
            f"Mode de paiement : {vente['mode_paiement']}"
        ),
        style_normal,
    ))
    if vente["statut"] == "annulee":
        motif = vente.get("motif_annulation") or "non précisé"
        elements.append(Paragraph(_echapper_xml(f"VENTE ANNULÉE — motif : {motif}"), style_annule))
    if vente.get("numero_facturier") or vente.get("vendeur_nom"):
        details = []
        if vente.get("numero_facturier"):
            details.append(f"N° facturier : {vente['numero_facturier']}")
        if vente.get("vendeur_nom"):
            details.append(f"Vendeur : {vente['vendeur_nom']}")
        elements.append(Paragraph(_echapper_xml(" — ".join(details)), style_normal))
    elements.append(Spacer(1, 4 * mm))

    # Remise (addendum, point f, décision 2026-09-22) : « toujours visibles
    # explicitement sur le ticket — prix normal, montant de la remise,
    # total réellement payé, jamais une modification silencieuse du prix
    # affiché ». Colonnes supplémentaires ajoutées SEULEMENT si une remise
    # existe réellement (ligne ou globale) — un reçu sans aucune remise
    # garde la mise en page historique, inchangée.
    remise_presente = bool(vente.get("remise_globale_montant")) or any(
        ligne.get("remise_montant") for ligne in lignes
    )
    if remise_presente:
        donnees = [["Article", "Qté", "Catalogue", "Remise", "Prix payé", "Total"]]
        for ligne in lignes:
            total_ligne = Decimal(str(ligne["prix_unitaire"])) * ligne["quantite"]
            catalogue = ligne.get("prix_catalogue")
            donnees.append([
                ligne["nom"], str(ligne["quantite"]),
                _fcfa(catalogue) if catalogue is not None else "—",
                _fcfa(ligne["remise_montant"]) if ligne.get("remise_montant") else "—",
                _fcfa(ligne["prix_unitaire"]), _fcfa(total_ligne),
            ])
        tableau = Table(donnees, colWidths=[55 * mm, 12 * mm, 28 * mm, 25 * mm, 25 * mm, 25 * mm])
    else:
        donnees = [["Article", "Qté", "Prix unitaire", "Total"]]
        for ligne in lignes:
            total_ligne = Decimal(str(ligne["prix_unitaire"])) * ligne["quantite"]
            donnees.append([
                ligne["nom"], str(ligne["quantite"]), _fcfa(ligne["prix_unitaire"]), _fcfa(total_ligne),
            ])
        tableau = Table(donnees, colWidths=[80 * mm, 20 * mm, 35 * mm, 35 * mm])
    tableau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(tableau)
    elements.append(Spacer(1, 4 * mm))

    totaux = [
        ["Sous-total HT", _fcfa(vente["sous_total_ht"])],
        [f"TVA ({vente['taux_tva']} %)", _fcfa(vente["montant_tva"])],
    ]
    if vente.get("remise_globale_montant"):
        totaux.append(["Remise sur la vente", "-" + _fcfa(vente["remise_globale_montant"])])
    totaux.append(["Total TTC", _fcfa(vente["total_ttc"])])
    tableau_totaux = Table(totaux, colWidths=[135 * mm, 35 * mm])
    tableau_totaux.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    elements.append(tableau_totaux)

    tampon = BytesIO()
    SimpleDocTemplate(tampon, pagesize=A4, title=f"Reçu {identifiant_document}").build(elements)
    return tampon.getvalue()


@routeur.get("/{vente_id}/recu")
def recu_vente(
    vente_id: int,
    request: Request,
    session: Session = Depends(exiger_role("responsable", "agent_comptabilite")),
):
    """Reçu PDF imprimable d'une vente (chantier C5, cycle 19) — mêmes
    rôles que la saisie elle-même (CDC §3.3) ; un agent stock n'a de toute
    façon aucun privilège sur ``ventes`` (migration 008). Le cloisonnement
    par site pour un agent comptabilité vient de la RLS (``connexion_pour``
    avec ``site_id=session.site_id``, comme partout ailleurs) : une vente
    de l'autre site est simplement introuvable, jamais un refus distinct
    qui révélerait son existence."""
    bd = obtenir_bd(request)
    with bd.connexion_pour(
        role_pg(session.role), site_id=session.site_id, utilisateur_id=session.utilisateur_id
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.numero_facture, v.numero_facturier, v.mode_paiement,
                       v.statut, v.motif_annulation, v.sous_total_ht, v.taux_tva,
                       v.montant_tva, v.total_ttc, v.date_encaissement,
                       v.remise_globale_montant, u.nom_complet AS vendeur_nom
                  FROM ventes v
                  LEFT JOIN employes u ON u.id = v.vendeur_id
                 WHERE v.id = %s
                """,
                (vente_id,),
            )
            vente = cur.fetchone()
            if vente is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Vente introuvable.")

            cur.execute(
                """
                SELECT a.nom, vl.quantite, vl.prix_unitaire, vl.prix_catalogue, vl.remise_montant
                  FROM ventes_lignes vl
                  JOIN articles a ON a.id = vl.article_id
                 WHERE vl.vente_id = %s
                 ORDER BY vl.id
                """,
                (vente_id,),
            )
            lignes = cur.fetchall()

            cur.execute(
                "SELECT cle, valeur FROM parametres WHERE cle IN "
                "('boutique_nom', 'boutique_ville', 'boutique_telephone', 'boutique_numero_contribuable')"
            )
            # Valeurs encore « a_definir » (addendum, point d) omises du reçu
            # plutôt qu'inventées — jamais par parametre_texte() ici, qui les
            # refuserait par une exception (migration 006, comportement voulu
            # ailleurs mais pas approprié pour un simple affichage optionnel).
            boutique = {ligne["cle"]: ligne["valeur"] for ligne in cur.fetchall() if ligne["valeur"] != "a_definir"}

    contenu = _construire_recu_pdf(boutique, vente, lignes)
    identifiant = vente["numero_facture"] or f"vente-{vente_id}"
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="recu-{identifiant}.pdf"'},
    )
