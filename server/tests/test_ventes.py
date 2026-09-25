"""Chantier C5 (ventes) — cycle 6.

Prouve par exécution les trois décisions du propriétaire appliquées dans
``server/app/routes/ventes.py`` (addendum, points b/d/e) :
  * une vente à découvert n'est JAMAIS refusée, l'écart est consigné ;
  * la TVA (19,25 %, régime du réel) est calculée sur des prix TTC, arrondie
    sur le TOTAL de la vente ;
  * le crédit client reste explicitement désactivé.
Et une régression déjà couverte ailleurs (C3) mais qu'une route d'écriture
peut réintroduire : un agent ne peut ni écrire sur l'autre site, ni utiliser
une route hors de son rôle.
"""

from __future__ import annotations

from io import BytesIO

import psycopg
from pypdf import PdfReader

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_COMPTA_COMPTOIR,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _texte_pdf(contenu: bytes) -> str:
    lecteur = PdfReader(BytesIO(contenu))
    return "\n".join(page.extract_text() or "" for page in lecteur.pages)


def test_parametres_vente_expose_le_taux_tva_en_vigueur(client):
    """La maquette lit le taux de TVA ici plutôt que de le coder en dur
    (addendum, point d) — vérifié pour les deux rôles autorisés. Depuis la
    migration 045 (point b), cette route expose aussi credit_client_actif,
    lu par vente.html pour proposer ou non le mode de paiement."""
    for identifiant, mdp in (
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
        ("resp", MOT_DE_PASSE_RESPONSABLE),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.get("/ventes/parametres", headers=entete_autorisation(session["jeton"]))
        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"taux_tva": 19.25, "credit_client_actif": True}


def test_vente_normale_decremente_le_stock_et_calcule_la_tva(client):
    """Ciment CIM II 50 kg (site 1, stock 30, prix catalogue 6500) : 2 sacs
    négociés à 6000 FCFA (TTC) pièce. Total TTC = 12000 ; à 19,25 %, la TVA
    extraite du total vaut 1937 (12000*19.25/119.25, arrondi arithmétique),
    le HT vaut 10063 — calculé à la main, indépendamment de la route."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0001",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6000}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()

    assert corps["total_ttc"] == 12000
    assert corps["montant_tva"] == 1937
    assert corps["sous_total_ht"] == 10063
    assert corps["taux_tva"] == 19.25
    assert corps["ecarts"] == []

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 1 AND site_id = 1")
            assert cur.fetchone()["quantite_stock"] == 28  # 30 - 2

            cur.execute(
                "SELECT type, quantite FROM mouvements_stock WHERE article_id = 1 ORDER BY id DESC LIMIT 1"
            )
            mouvement = cur.fetchone()
            assert mouvement == {"type": "sortie", "quantite": 2}

            cur.execute(
                "SELECT type, montant, vente_id FROM transactions WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            transactions = cur.fetchall()
            assert len(transactions) == 1
            assert transactions[0]["type"] == "recette"
            assert transactions[0]["montant"] == 12000

            cur.execute(
                "SELECT count(*) AS n FROM ecarts_stock_ventes WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            assert cur.fetchone()["n"] == 0


def test_vente_a_decouvert_nest_jamais_refusee_et_consigne_lecart(client):
    """Article rare (site 1, stock 1) : on en vend 5. La vente DOIT quand
    même être enregistrée (addendum, point e — jamais de blocage), le stock
    tombe à 0, jamais négatif, et l'écart de 4 est consigné."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "orange_money",
            "numero_facturier": "MAG-TEST0002",
            "vendeur_id": 1,
            "lignes": [{"article_id": 4, "quantite": 5, "prix_unitaire": 2000}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["ecarts"] == [{"article_id": 4, "quantite_manquante": 4}]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 4 AND site_id = 1")
            assert cur.fetchone()["quantite_stock"] == 0  # jamais négatif

            cur.execute(
                "SELECT quantite_manquante FROM ecarts_stock_ventes WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            assert cur.fetchone()["quantite_manquante"] == 4


def test_credit_client_sans_client_id_refuse_message_clair(client):
    """Point b, activé depuis la migration 045 (voir server/tests/test_clients.py
    pour la couverture complète : créance, plafond, FIFO...) — cette route
    refuse toujours une vente à crédit SANS client, avec un message clair,
    pas une erreur SQL brute."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "credit_client",
            "numero_facturier": "MAG-TEST0003",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422
    assert "client" in reponse.json()["detail"].lower()


def test_agent_stock_ne_peut_pas_enregistrer_de_vente(client):
    """Aucun droit sur `ventes` pour l'agent stock (migration 008) : la
    route doit refuser avant même de toucher la base."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0004",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 403


def test_agent_comptabilite_ne_peut_pas_vendre_pour_lautre_site(client):
    """Le comptable du Magasin (site 1) tente de vendre le « Clou 5 cm » du
    Comptoir (site 2), y compris en forçant site_id dans le corps : le site
    vient TOUJOURS de sa session, jamais de la requête. La clé étrangère
    composite (migration 002) refuse ensuite l'article hors site."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "site_id": 2,  # ignoré : le comptable a déjà un site en session
            "mode_paiement": "especes",
            # MAG- (pas CPT-) : le site EFFECTIF de cette vente reste 1 (la
            # session du comptable, pas le site_id ci-dessus, ignoré) — voir
            # server/app/routes/ventes.py.
            "numero_facturier": "MAG-TEST0005",
            "vendeur_id": 1,
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse.status_code == 422
    assert "introuvable" in reponse.json()["detail"].lower()

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 3 AND site_id = 2")
            assert cur.fetchone()["quantite_stock"] == 100  # inchangé


def test_responsable_doit_preciser_le_site(client):
    """Le responsable couvre les deux sites (site_id NULL en session) : sans
    site précisé dans la requête, la vente est refusée AVANT toute écriture,
    avec un message explicite plutôt qu'une erreur de contrainte SQL."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0006",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_responsable_peut_vendre_pour_un_site_precise(client):
    """Le responsable, en précisant le site, peut enregistrer une vente pour
    ce site — la RLS de `ventes`/`ventes_lignes` l'y autorise explicitement
    (`current_user = 'qf_responsable'`, migration 008)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])

    reponse = client.post(
        "/ventes",
        headers=entetes,
        json={
            "site_id": 2,
            "mode_paiement": "mtn_momo",
            "numero_facturier": "CPT-TEST0007",
            "vendeur_id": 2,  # « Employée Comptoir » — l'employé 1 est du Magasin, site 1
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 2


# ---------------------------------------------------------------------------
# Remises (chantier C4/C5, migration 037, addendum point f, décision
# 2026-09-22) — Ciment CIM II 50 kg (article 1) : prix catalogue 6 500 FCFA.
# ---------------------------------------------------------------------------

def _ligne_ventes_lignes(vente_id: int, article_id: int = 1) -> dict:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT prix_unitaire, prix_catalogue, remise_montant FROM ventes_lignes"
                " WHERE vente_id = %s AND article_id = %s",
                (vente_id, article_id),
            )
            return cur.fetchone()


def test_remise_montant_par_ligne_resout_le_prix_paye(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM01", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 500}]},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["remise_totale"] == 500.0
    ligne = _ligne_ventes_lignes(reponse.json()["vente_id"])
    assert float(ligne["prix_catalogue"]) == 6500.0
    assert float(ligne["remise_montant"]) == 500.0
    assert float(ligne["prix_unitaire"]) == 6000.0


def test_remise_pourcentage_par_ligne_resout_le_prix_paye(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM02", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "remise_pct": 10}]},
    )
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_ventes_lignes(reponse.json()["vente_id"])
    assert float(ligne["remise_montant"]) == 650.0  # 10 % de 6 500
    assert float(ligne["prix_unitaire"]) == 5850.0


def test_prix_unitaire_direct_infere_la_remise_automatiquement(client):
    """Comportement historique inchangé (point d) : taper directement le
    prix négocié reste valable — la remise est déduite du prix catalogue
    pour la traçabilité, sans changer la saisie."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM03", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6200}]},
    )
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_ventes_lignes(reponse.json()["vente_id"])
    assert float(ligne["remise_montant"]) == 300.0  # 6 500 - 6 200


def test_prix_unitaire_au_dessus_du_catalogue_naccorde_aucune_remise(client):
    """Un prix négocié AU-DESSUS du catalogue reste légitime (point d,
    jamais interdit) — ce n'est pas une remise négative."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM04", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 7000}]},
    )
    assert reponse.status_code == 201, reponse.text
    ligne = _ligne_ventes_lignes(reponse.json()["vente_id"])
    assert float(ligne["remise_montant"]) == 0.0
    assert float(ligne["prix_unitaire"]) == 7000.0


def test_deux_modes_de_prix_a_la_fois_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM05", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6000, "remise_pct": 10}]},
    )
    assert reponse.status_code == 422


def test_remise_a_100_pourcent_refusee(client):
    """Décision 2026-09-23 : une remise à 100 % relève du mécanisme
    dédié à l'article offert (sous-chantier 4), pas de celui-ci."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM06", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "remise_pct": 100}]},
    )
    assert reponse.status_code == 422, reponse.text
    assert "article offert" in reponse.json()["detail"].lower()


def test_remise_globale_montant_reduit_le_total(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM07", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6500}],
              "remise_globale_montant": 1000},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["total_ttc"] == 12000.0  # (6500*2) - 1000
    assert corps["remise_totale"] == 1000.0


def test_remise_globale_pct_et_montant_a_la_fois_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM08", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
              "remise_globale_montant": 100, "remise_globale_pct": 10},
    )
    assert reponse.status_code == 422


def test_remise_globale_depassant_le_total_refusee(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM09", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
              "remise_globale_montant": 6500},
    )
    assert reponse.status_code == 422, reponse.text
    assert "dépasser" in reponse.json()["detail"].lower()


def test_recu_vente_avec_remise_affiche_catalogue_remise_et_remise_globale(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])
    reponse_vente = client.post(
        "/ventes",
        headers=entetes,
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTREM10", "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": 1, "remise_montant": 500}],
              "remise_globale_montant": 200},
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    reponse = client.get(f"/ventes/{vente_id}/recu", headers=entetes)
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "Catalogue" in texte
    assert "Remise" in texte
    assert "Remise sur la vente" in texte


# ---------------------------------------------------------------------------
# Annulation de vente (chantier C5, cycle 17) — migration 017,
# ``annuler_vente()``. CDC §3.3 : « responsable uniquement ».
# ---------------------------------------------------------------------------

def test_annuler_vente_restitue_le_stock_et_contre_passe_la_recette(client):
    """Vente normale (pas de découvert) : 2 sacs de ciment (site 1, stock 30).
    L'annulation doit restituer EXACTEMENT ces 2 unités, contre-passer la
    recette par une dépense de même montant, et figer le statut."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0008",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6000}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/ventes/{vente_id}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "Erreur de saisie, client jamais venu"},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps == {"vente_id": vente_id, "montant_ttc": 12000, "articles_restitues": 1}

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 1 AND site_id = 1")
            assert cur.fetchone()["quantite_stock"] == 30  # restitué intégralement

            cur.execute(
                "SELECT statut, annulee_par_id, motif_annulation, date_annulation FROM ventes WHERE id = %s",
                (vente_id,),
            )
            vente = cur.fetchone()
            assert vente["statut"] == "annulee"
            assert vente["annulee_par_id"] == 1  # resp
            assert vente["motif_annulation"] == "Erreur de saisie, client jamais venu"
            assert vente["date_annulation"] is not None

            cur.execute(
                "SELECT type, montant FROM transactions WHERE vente_id = %s ORDER BY id",
                (vente_id,),
            )
            transactions = cur.fetchall()
            assert [t["type"] for t in transactions] == ["recette", "depense"]
            assert transactions[0]["montant"] == transactions[1]["montant"] == 12000

            cur.execute(
                "SELECT type, categorie, quantite FROM mouvements_stock "
                "WHERE vente_id = %s ORDER BY id",
                (vente_id,),
            )
            mouvements = cur.fetchall()
            assert mouvements[-1] == {"type": "entree", "categorie": "annulation_vente", "quantite": 2}


def test_annuler_vente_a_decouvert_ne_restitue_que_le_stock_reellement_decremente(client):
    """Article rare (stock réel 1) vendu à découvert pour 3 : seule 1 unité a
    réellement quitté le stock (addendum point e). L'annulation ne doit
    restituer QUE cette unité — jamais la quantité facturée — et régulariser
    d'office l'écart devenu sans objet (cycle 17, lien C5/C7)."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0009",
            "vendeur_id": 1,
            "lignes": [{"article_id": 4, "quantite": 3, "prix_unitaire": 2000}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 4 AND site_id = 1")
            assert cur.fetchone()["quantite_stock"] == 0  # tombé à 0, jamais négatif

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        f"/ventes/{vente_id}/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "Client reparti sans payer, vente annulée"},
    )
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["montant_ttc"] == 6000
    assert corps["articles_restitues"] == 1

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT quantite_stock FROM stocks_sites WHERE article_id = 4 AND site_id = 1")
            assert cur.fetchone()["quantite_stock"] == 1  # pas 3 : seul le réel décrémenté

            cur.execute(
                "SELECT regularise, regularise_par_id, date_regularisation "
                "FROM ecarts_stock_ventes WHERE vente_id = %s",
                (vente_id,),
            )
            ecart = cur.fetchone()
            assert ecart["regularise"] is True
            assert ecart["regularise_par_id"] == 1
            assert ecart["date_regularisation"] is not None


def test_annuler_vente_deja_annulee_refusee(client):
    """Jamais une seconde fois — CDC : irréversible."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0010",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes_resp = entete_autorisation(session_resp["jeton"])
    premiere = client.post(
        f"/ventes/{vente_id}/annuler", headers=entetes_resp, json={"motif": "Test"}
    )
    assert premiere.status_code == 200, premiere.text

    seconde = client.post(
        f"/ventes/{vente_id}/annuler", headers=entetes_resp, json={"motif": "Nouvelle tentative"}
    )
    assert seconde.status_code == 422
    assert "déjà annulée" in seconde.json()["detail"].lower() or "annulée" in seconde.json()["detail"].lower()


def test_annuler_vente_inexistante_refusee(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/ventes/999999/annuler",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"motif": "Test"},
    )
    assert reponse.status_code == 422
    assert "introuvable" in reponse.json()["detail"].lower()


def test_annuler_vente_motif_blanc_refuse(client):
    """Pydantic bloque déjà la chaîne vide ; un motif fait uniquement
    d'espaces passe Pydantic mais est refusé par la base (``btrim``)."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0011",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes_resp = entete_autorisation(session_resp["jeton"])

    assert client.post(
        f"/ventes/{vente_id}/annuler", headers=entetes_resp, json={"motif": ""}
    ).status_code == 422  # bloqué par Pydantic (min_length=1)

    reponse = client.post(
        f"/ventes/{vente_id}/annuler", headers=entetes_resp, json={"motif": "   "}
    )
    assert reponse.status_code == 422  # bloqué par la base (btrim)
    assert "motif" in reponse.json()["detail"].lower()


def test_agent_stock_et_agent_comptabilite_ne_peuvent_pas_annuler_une_vente(client):
    """Seul le responsable annule (CDC §3.3) — aucun GRANT EXECUTE sur
    ``annuler_vente()`` pour les autres rôles (migration 017)."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0012",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    for identifiant, mdp in (
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
        ("magasin.stock", MOT_DE_PASSE_AGENT_STOCK),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.post(
            f"/ventes/{vente_id}/annuler",
            headers=entete_autorisation(session["jeton"]),
            json={"motif": "Test"},
        )
        assert reponse.status_code == 403


# ---------------------------------------------------------------------------
# Reçu de vente imprimable (chantier C5, cycle 19) — CDC §3.3/§7.1.
# ---------------------------------------------------------------------------

def test_recu_vente_pdf_contient_les_lignes_et_totaux(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session_compta["jeton"])
    reponse_vente = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0013",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 2, "prix_unitaire": 6000}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    reponse = client.get(f"/ventes/{vente_id}/recu", headers=entetes)
    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.content[:4] == b"%PDF"

    texte = _texte_pdf(reponse.content)
    assert "Ciment CIM II 50 kg" in texte
    assert "Ets Quincaillerie Franck" in texte  # boutique_nom, jamais un placeholder
    assert "12" in texte and "000" in texte  # total TTC (12 000 FCFA)
    assert "ANNUL" not in texte.upper()  # vente active : pas de mention d'annulation


def test_recu_vente_annulee_porte_la_mention(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0014",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes_resp = entete_autorisation(session_resp["jeton"])
    annulation = client.post(
        f"/ventes/{vente_id}/annuler", headers=entetes_resp, json={"motif": "Erreur de saisie"}
    )
    assert annulation.status_code == 200, annulation.text

    reponse = client.get(f"/ventes/{vente_id}/recu", headers=entetes_resp)
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "ANNUL" in texte.upper()
    assert "Erreur de saisie" in texte


def test_recu_vente_inexistante_refusee(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get(
        "/ventes/999999/recu", headers=entete_autorisation(session_resp["jeton"])
    )
    assert reponse.status_code == 404


def test_agent_stock_ne_peut_pas_obtenir_de_recu(client):
    """Aucun droit sur ``ventes`` pour l'agent stock (migration 008)."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0015",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_stock = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        f"/ventes/{vente_id}/recu", headers=entete_autorisation(session_stock["jeton"])
    )
    assert reponse.status_code == 403


def test_recu_vente_agent_comptabilite_limite_a_son_site(client):
    """Une vente du Magasin (site 1) reste introuvable pour un comptable du
    Comptoir (site 2) — cloisonnement RLS, jamais un refus distinct qui
    révélerait son existence sur l'autre site."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-TEST0016",
            "vendeur_id": 1,
            "lignes": [{"article_id": 2, "quantite": 1, "prix_unitaire": 3500}],
        },
    )
    vente_id = reponse_vente.json()["vente_id"]

    session_comptoir = se_connecter(client, "comptoir.compta", MOT_DE_PASSE_AGENT_COMPTA_COMPTOIR)
    reponse = client.get(
        f"/ventes/{vente_id}/recu", headers=entete_autorisation(session_comptoir["jeton"])
    )
    assert reponse.status_code == 404


# ---------------------------------------------------------------------------
# Numéro de facturier + vendeur (addendum, point c, décidé le 2026-09-13,
# cycle 27 ; question 3 tranchée le 2026-09-25, migration 040) — vendeur_id
# référence désormais une fiche employé (module RH), pas un compte
# utilisateur : un vendeur peut n'avoir jamais eu de compte. PAS de rapport
# d'écarts de prix par vendeur (question 5, toujours non tranchée).
# ---------------------------------------------------------------------------

def test_numero_facturier_obligatoire(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422, reponse.text


def test_vendeur_id_obligatoire(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-SANSVENDEUR",
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422, reponse.text


def test_numero_facturier_prefixe_incorrect_refuse(client):
    """Site effectif = 1 (Magasin, session du comptable) : un numéro
    « CPT- » est refusé, pas parce que le format est mauvais dans l'absolu,
    mais parce qu'il ne correspond pas au site réel de la vente."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "CPT-0001",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422, reponse.text
    assert "MAG-" in reponse.json()["detail"]


def test_numero_facturier_duplique_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    corps = {
        "mode_paiement": "especes",
        "numero_facturier": "MAG-DUPLIQUE",
        "vendeur_id": 1,
        "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
    }
    premiere = client.post("/ventes", headers=entete_autorisation(session["jeton"]), json=corps)
    assert premiere.status_code == 201, premiere.text

    deuxieme = client.post("/ventes", headers=entete_autorisation(session["jeton"]), json=corps)
    assert deuxieme.status_code == 409, deuxieme.text
    assert "MAG-DUPLIQUE" in deuxieme.json()["detail"]


def test_vendeur_id_inexistant_refuse(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-VENDEURINEXISTANT",
            "vendeur_id": 999999,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422, reponse.text
    assert "vendeur" in reponse.json()["detail"].lower()


def test_vendeur_dun_autre_site_refuse(client):
    """Chantier B (migration 040) : l'employé 2 (« Employée Comptoir »,
    site 2) ne peut pas être vendeur d'une vente au Magasin (site 1)."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-VENDEURAUTRESITE",
            "vendeur_id": 2,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 422, reponse.text
    assert "n'appartient pas au site" in reponse.json()["detail"].lower()


def test_vendeur_employe_inactif_refuse(client):
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute("UPDATE employes SET actif = FALSE WHERE id = 1")
        conn.commit()
    try:
        session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
        reponse = client.post(
            "/ventes",
            headers=entete_autorisation(session["jeton"]),
            json={
                "mode_paiement": "especes",
                "numero_facturier": "MAG-VENDEURINACTIF",
                "vendeur_id": 1,
                "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
            },
        )
        assert reponse.status_code == 422, reponse.text
        assert "n'est plus actif" in reponse.json()["detail"].lower()
    finally:
        with psycopg.connect(PG_ADMIN_DSN) as conn:
            conn.execute("UPDATE employes SET actif = TRUE WHERE id = 1")
            conn.commit()


def test_recu_vente_affiche_le_nom_de_lemploye_vendeur(client):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    entetes = entete_autorisation(session["jeton"])
    reponse_vente = client.post(
        "/ventes",
        headers=entetes,
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-VENDEURRECU",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    vente_id = reponse_vente.json()["vente_id"]

    reponse = client.get(f"/ventes/{vente_id}/recu", headers=entetes)
    assert reponse.status_code == 200, reponse.text
    texte = _texte_pdf(reponse.content)
    assert "Employé Essai" in texte


def test_numero_facturier_reellement_enregistre_et_restitue(client):
    """Pas seulement accepté : réellement écrit en base ET renvoyé dans la
    réponse, exactement tel que saisi — jamais reformaté ni tronqué."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={
            "mode_paiement": "especes",
            "numero_facturier": "MAG-0842",
            "vendeur_id": 1,
            "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["numero_facturier"] == "MAG-0842"

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT numero_facturier, vendeur_id FROM ventes WHERE id = %s",
                (reponse.json()["vente_id"],),
            )
            ligne = cur.fetchone()
    assert ligne["numero_facturier"] == "MAG-0842"
    assert ligne["vendeur_id"] == 1


def test_lister_vendeurs_du_site_ne_montre_que_ses_employes(client):
    """Chantier B (migration 040) : le vendeur est une fiche EMPLOYÉ, plus
    un compte utilisateur — le comptable du Magasin (site 1) voit l'employé
    de son site, jamais celui du Comptoir."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get("/ventes/vendeurs", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [v["nom_complet"] for v in reponse.json()["vendeurs"]]
    assert "Employé Essai" in noms  # employé du Magasin (site 1, jeu d'essai)
    assert "Employée Comptoir" not in noms  # employé de l'AUTRE site (site 2)


def test_lister_vendeurs_employe_site_null_couvre_les_deux_sites(client):
    """Un employé site_id NULL (même convention que
    declarations_article_offert.employe_id, migration 039) apparaît quel
    que soit le site consulté."""
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        conn.execute(
            "INSERT INTO employes (nom_complet, poste, site_id) VALUES ('Employé Volant', 'Polyvalent', NULL)"
        )
        conn.commit()
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get("/ventes/vendeurs", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [v["nom_complet"] for v in reponse.json()["vendeurs"]]
    assert "Employé Volant" in noms


def test_lister_vendeurs_responsable_doit_preciser_le_site(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.get("/ventes/vendeurs", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 422, reponse.text


def test_lister_vendeurs_agent_stock_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.get(
        "/ventes/vendeurs", headers=entete_autorisation(session["jeton"]), params={"site_id": 1}
    )
    assert reponse.status_code == 403, reponse.text
