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
    (addendum, point d) — vérifié pour les deux rôles autorisés."""
    for identifiant, mdp in (
        ("magasin.compta", MOT_DE_PASSE_AGENT_COMPTA),
        ("resp", MOT_DE_PASSE_RESPONSABLE),
    ):
        session = se_connecter(client, identifiant, mdp)
        reponse = client.get("/ventes/parametres", headers=entete_autorisation(session["jeton"]))
        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"taux_tva": 19.25}


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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 1")
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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 4")
            assert cur.fetchone()["quantite_stock"] == 0  # jamais négatif

            cur.execute(
                "SELECT quantite_manquante FROM ecarts_stock_ventes WHERE vente_id = %s",
                (corps["vente_id"],),
            )
            assert cur.fetchone()["quantite_manquante"] == 4


def test_credit_client_reste_desactive(client):
    """Point b : pas encore de décision complète sur la vente à crédit —
    la route la refuse avec un message clair, pas une erreur SQL brute."""
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
    assert "crédit" in reponse.json()["detail"].lower()
    assert "addendum" in reponse.json()["detail"].lower()


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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 3")
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
            "vendeur_id": 1,
            "lignes": [{"article_id": 3, "quantite": 1, "prix_unitaire": 800}],
        },
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 2


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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 1")
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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 4")
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
            cur.execute("SELECT quantite_stock FROM articles WHERE id = 4")
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
# cycle 27) — périmètre réduit au socle décidé, voir
# db/migrations/020_facturier_vendeur.sql : PAS de rapport d'écarts de prix
# par vendeur, PAS de liste de vendeurs sans compte (questions 3 et 5 non
# tranchées).
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


def test_lister_vendeurs_du_site_inclut_le_responsable(client):
    """Le comptable du Magasin (site 1) doit pouvoir choisir un vendeur de
    SON site — et toujours le responsable, qui couvre les deux sites."""
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse = client.get("/ventes/vendeurs", headers=entete_autorisation(session["jeton"]))
    assert reponse.status_code == 200, reponse.text
    noms = [v["nom_complet"] for v in reponse.json()["vendeurs"]]
    assert "Awa Franck" in noms  # le responsable (id=1, jeu d'essai)
    assert "Cyr Magasin" in noms  # le comptable connecté lui-même (id=4)
    assert "Dina Comptoir" not in noms  # comptable de l'AUTRE site (id=5)


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
