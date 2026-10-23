"""Campagne métier C5 — ventes et facturation en FCFA (opération 100 %
Lot B, 2026-10-23).

Ordre du proprietaire : « Prepare une campagne de tests metier avec des
montants en FCFA, comprenant les cas normaux, limites et erreurs. »

Le detail des scenarios (recit metier, cas humains non automatisables)
est dans RAPPORT AVANCEMENT/LOTB_CAMPAGNE_C5_FCFA.md. Ce fichier en
automatise la partie reproductible, en DEUX tests distincts :

1. test_journee_boutique_fcfa — une journee COMPLETE, enchainee : les
   ventes se suivent sur la meme base, l'attendu de caisse n'est calcule
   qu'a la fin, la cloture verifie la coherence D'ENSEMBLE (exigence C5 :
   « coherence des rapports de caisse »). Les tests unitaires existants
   prouent chaque regle ISOLEE (D2, D4, D9, credit, annulation) ; celui-ci
   prouve qu'elles TIENNENT ENSEMBLE sur une journee reelle.

2. test_cas_limites_et_erreurs_fcfa — les bornes : remise au seuil exact,
   au-dela du seuil, mixte incoherent, credit sans client / hors plafond,
   survente a decouvert (comportement migration 011 : jamais un refus de
   vente a un client qui a paye), usurpation d'encaisseur (D9), remise
   negative, reglement excedentaire, mode de paiement inconnu.

Prix du jeu d'essai (db/tests/00_jeu_essai.sql, site 1) :
  article 1 Ciment CIM II 50 kg  6 500 FCFA (stock 30)
  article 2 Fer a beton 8 mm      3 500 FCFA
  article 4 Article rare          2 000 FCFA (stock 1)
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import psycopg
from pypdf import PdfReader

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)

_PRIX_CIMENT = 6500
_PRIX_FER = 3500
_JOUR = date.today().isoformat()


def _id_utilisateur(identifiant: str) -> int:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT id FROM utilisateurs WHERE identifiant = %s", (identifiant,)
        ).fetchone()[0]


def _stock(article_id: int) -> float:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return float(
            conn.execute(
                "SELECT quantite_stock FROM stocks_sites WHERE article_id = %s AND site_id = 1",
                (article_id,),
            ).fetchone()[0]
        )


def _transactions(vente_id: int) -> list[tuple[str, str]]:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT type, montant::text FROM transactions "
                "WHERE vente_id = %s ORDER BY id",
                (vente_id,),
            )
            return cur.fetchall()


def _encaisseur(vente_id: int) -> int:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT utilisateur_caisse_id FROM ventes WHERE id = %s", (vente_id,)
        ).fetchone()[0]


def _encours(client_id: int) -> float:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return float(conn.execute("SELECT encours_client(%s)", (client_id,)).fetchone()[0])


def _mode_paiement(vente_id: int) -> str:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT mode_paiement FROM ventes WHERE id = %s", (vente_id,)
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# 1. Journee complete
# ---------------------------------------------------------------------------
def test_journee_boutique_fcfa(client):
    """Une journee de boutique au comptoir, du premier client du matin a la
    cloture de caisse du soir, puis le client qui vient regler le lendemain.
    Toute incoherence d'ensemble (recette double, attendu faux, encaisseur
    usurpe, creatrice fantome) fait echouer le test."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes_compta = entete_autorisation(session_compta["jeton"])
    id_compta = _id_utilisateur("magasin.compta")

    # -- Le responsable cree la fiche du client a credit de la journee ----
    reponse = client.post(
        "/clients",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"nom": "Awa Diallo", "telephone": "699123456", "plafond_credit": 500000},
    )
    assert reponse.status_code == 201, reponse.text
    client_awa = reponse.json()["id"]

    # -- 08h15 : chantier du matin, un client paye 2 sacs de ciment en
    #    especes : 2 x 6 500 = 13 000 FCFA ---------------------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json={
            "site_id": 1,
            "mode_paiement": "especes",
            "numero_facturier": "MAG-100001",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": _PRIX_CIMENT}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    v1 = reponse.json()
    assert v1["total_ttc"] == 13000
    assert _encaisseur(v1["vente_id"]) == id_compta  # D9 : le compte authentifie
    assert _transactions(v1["vente_id"]) == [("recette", "13000.00")]

    # -- 09h00 : un macon paie un fer a beton par Orange Money ------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json={
            "site_id": 1,
            "mode_paiement": "orange_money",
            "numero_facturier": "MAG-100002",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": _PRIX_FER}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    v2 = reponse.json()
    assert v2["total_ttc"] == _PRIX_FER

    # -- 10h30 : vente mixte D2 — un sac de ciment, 3 000 FCFA en especes
    #    complementes par 3 500 FCFA en Orange Money ----------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json={
            "site_id": 1,
            "numero_facturier": "MAG-100003",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": _PRIX_CIMENT}],
            "paiements": [
                {"mode_paiement": "especes", "montant": 3000},
                {"mode_paiement": "orange_money", "montant": 3500},
            ],
        },
    )
    assert reponse.status_code == 201, reponse.text
    v3 = reponse.json()
    assert _mode_paiement(v3["vente_id"]) == "mixte"
    assert v3["total_ttc"] == _PRIX_CIMENT
    assert v3["paiements"] == [
        {"mode_paiement": "especes", "montant": 3000.0},
        {"mode_paiement": "orange_money", "montant": 3500.0},
    ]
    # Une seule recette du TOTAL (jamais de double comptage), composantes
    # tracees par mode pour l'attendu de caisse.
    assert _transactions(v3["vente_id"]) == [("recette", "6500.00")]

    # Le recu detaille les paiements (exigence C5) : le PDF de la vente
    # mixte nomme chaque mode.
    recu = client.get(f"/ventes/{v3['vente_id']}/recu", headers=entetes_compta)
    assert recu.status_code == 200, recu.text
    assert recu.headers["content-type"] == "application/pdf"
    assert recu.content[:4] == b"%PDF"
    texte_recu = "\n".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(recu.content)).pages
    )
    assert "mixte" in texte_recu
    assert "Espèces" in texte_recu
    assert "Orange Money" in texte_recu

    # -- 11h45 : remise ligne AU SEUIL exact de 10 % (D4) acceptee a un
    #    agent : 6 500 - 650 = 5 850 FCFA -------------------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json={
            "site_id": 1,
            "mode_paiement": "especes",
            "numero_facturier": "MAG-100004",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_pct": 10}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    v4 = reponse.json()
    assert v4["total_ttc"] == 5850

    # -- 14h00 : Awa Diallo achete un sac a credit (6 500 FCFA) ----------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json={
            "site_id": 1,
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-100005",
            "vendeur_id": 1,
            "client_id": client_awa,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 0}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    v5 = reponse.json()
    assert v5["total_ttc"] == _PRIX_CIMENT
    # Aucune recette pour un credit : la recette naitra du reglement.
    assert _transactions(v5["vente_id"]) == []
    assert _encours(client_awa) == _PRIX_CIMENT

    # -- 15h20 : le responsable annule la vente Orange Money (client
    #    revenu chercher son argent) : depense contre-passee, stock
    #    restitue, sortie de l'attendu ------------------------------------
    stock_fer_avant = _stock(2)
    reponse = client.post(
        f"/ventes/{v2['vente_id']}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "Client revenu chercher son argent"},
    )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["montant_ttc"] == _PRIX_FER
    assert _transactions(v2["vente_id"]) == [
        ("recette", "3500.00"),
        ("depense", "3500.00"),
    ]
    assert _stock(2) == stock_fer_avant + 1  # l'unite vendue est restituee

    # -- 18h00 : coherence de la journee AVANT cloture --------------------
    #    especes : 13 000 (V1) + 3 000 (part mixte) + 5 850 (V4) = 21 850
    #    Orange Money : 3 500 (V3) ; V2 annulee en est sortie ; V5 credit
    #    n'y figure pas.
    reponse = client.get(
        "/caisse/attendu",
        headers=entete_autorisation(session_resp["jeton"]),
        params={"site_id": 1, "date_cloture": _JOUR},
    )
    assert reponse.status_code == 200, reponse.text
    attendu = reponse.json()
    assert attendu["attendu_especes"] == 21850
    assert attendu["attendu_orange_money"] == 3500
    assert attendu["attendu_mtn_momo"] == 0
    assert attendu["attendu_autre"] == 0

    # -- 18h05 : cloture exacte du tiroir : 21 850 comptes, ecart nul,
    #    aucun commentaire exigé -----------------------------------------
    reponse = client.post(
        "/caisse",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"site_id": 1, "date_cloture": _JOUR, "espece_comptee": 21850},
    )
    assert reponse.status_code == 201, reponse.text
    cloture = reponse.json()
    assert cloture["attendu_especes"] == 21850
    assert cloture["ecart_especes"] == 0.0
    assert cloture["commentaire"] is None

    # -- Le lendemain : Awa passe regler sa dette en deux fois ------------
    #    3 250 FCFA d'acompte puis le solde ; un reglement excedentaire
    #    est refuse.
    reponse = client.post(
        f"/clients/{client_awa}/reglements",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"montant": 3250, "motif": "Acompte d'Awa Diallo"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["encours"] == 3250

    # Il reste 3 250 dus : un reglement de 3 251 (un franc de trop) est refuse.
    reponse = client.post(
        f"/clients/{client_awa}/reglements",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"montant": 3251, "motif": "un franc de trop"},
    )
    assert reponse.status_code == 422, reponse.text  # jamais au-dela de l'encours

    reponse = client.post(
        f"/clients/{client_awa}/reglements",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"montant": 3250, "motif": "Solde d'Awa Diallo"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["encours"] == 0

    # Une fois reglee, la vente a credit ne peut plus etre annulee : le
    # client a paye, la boutique a l'argent.
    reponse = client.post(
        f"/ventes/{v5['vente_id']}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "trop tard"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "règlement" in reponse.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Cas limites et erreurs
# ---------------------------------------------------------------------------
def test_cas_limites_et_erreurs_fcfa(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes_compta = entete_autorisation(session_compta["jeton"])
    id_compta = _id_utilisateur("magasin.compta")

    def vente(numero, **surcharge):
        corps = {
            "site_id": 1,
            "mode_paiement": "especes",
            "numero_facturier": numero,
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": _PRIX_CIMENT}],
        }
        corps.update(surcharge)
        return corps

    # -- Limite exacte : 10,01 % refuse a l'agent (403, exige un
    #    responsable), 10,01 % passe au responsable avec la remise exacte.
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200001", lignes=[{"article_id": 1, "quantite": 1, "remise_pct": 10.01}]
        ),
    )
    assert reponse.status_code == 403, reponse.text
    assert "responsable" in reponse.json()["detail"].lower()

    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session_resp["jeton"]),
        json={
            "site_id": 1,
            "mode_paiement": "especes",
            "numero_facturier": "MAG-200002",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "remise_pct": 10.01}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["total_ttc"] == 5849.35  # 6500 - 650.65

    # -- La remise GLOBALE ne contourne pas le seuil (meme 403) -----------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200003",
            lignes=[{"article_id": 1, "quantite": 1, "remise_pct": 0}],
            remise_globale_pct=15,
        ),
    )
    assert reponse.status_code == 403, reponse.text

    # -- Remise negative : refusee (jamais une majoration deguisee) -------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200004", lignes=[{"article_id": 1, "quantite": 1, "remise_montant": -100}]
        ),
    )
    assert reponse.status_code == 422, reponse.text

    # -- Mixte incoherent : la somme des composantes DOIT valoir le total -
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200005",
            mode_paiement=None,
            paiements=[
                {"mode_paiement": "especes", "montant": 3000},
                {"mode_paiement": "orange_money", "montant": 3400},
            ],
        ),
    )
    assert reponse.status_code == 422, reponse.text
    assert "6500" in reponse.json()["detail"]

    # -- Mode de paiement inconnu : refuse par validation ------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente("MAG-200006", mode_paiement="bitcoin"),
    )
    assert reponse.status_code == 422, reponse.text

    # -- Credit sans client : 422, message clair ---------------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente("MAG-200007", mode_paiement="credit_client"),
    )
    assert reponse.status_code == 422, reponse.text
    assert "client" in reponse.json()["detail"].lower()

    # -- Credit au-dela du plafond : 422, aucune creatrice creee -----------
    reponse = client.post(
        "/clients",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"nom": "Client Plafond Bas", "plafond_credit": 6500},
    )
    assert reponse.status_code == 201, reponse.text
    client_plafond = reponse.json()["id"]

    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200008",
            mode_paiement="credit_client",
            client_id=client_plafond,
            lignes=[{"article_id": 1, "quantite": 2, "remise_montant": 0}],  # 13 000 > 6 500
        ),
    )
    assert reponse.status_code == 422, reponse.text
    assert "plafond" in reponse.json()["detail"].lower()
    assert _encours(client_plafond) == 0

    # -- Usurpation d'encaisseur (D9) : le champ injecte est IGNORE,
    #    l'encaissement va au compte authentifie ---------------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente("MAG-200009", utilisateur_caisse_id=999),
    )
    assert reponse.status_code == 201, reponse.text
    assert _encaisseur(reponse.json()["vente_id"]) == id_compta  # jamais 999

    # -- Survente : migration 011 — le client A PAYE, la vente passe,
    #    le stock tombe a 0 (jamais negatif), l'ecart est trace pour
    #    l'inventaire ; ce n'est PAS un refus ------------------------------
    reponse = client.post(
        "/ventes",
        headers=entetes_compta,
        json=vente(
            "MAG-200010",
            lignes=[{"article_id": 1, "quantite": 99, "prix_unitaire": _PRIX_CIMENT}],
        ),
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["total_ttc"] == 643500  # 99 x 6 500, facture integralement
    assert _stock(1) == 0  # decrete jusqu'a 0, jamais en dessous
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        nombre_ecarts = conn.execute(
            "SELECT count(*) FROM ecarts_stock_ventes WHERE vente_id = %s",
            (reponse.json()["vente_id"],),
        ).fetchone()[0]
    assert nombre_ecarts == 1  # l'ecart de survente est trace (lien C7)

    # -- Un agent stock ne vend pas (habilitations, migration 008) ---------
    session_stock = se_connecter(client, "magasin.stock", "AgentStockTest123")
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session_stock["jeton"]),
        json=vente("MAG-200011"),
    )
    assert reponse.status_code == 403, reponse.text
