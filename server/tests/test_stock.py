"""Chantier C4 (articles et stock) — cycle 9 : réception, transfert,
casse, retours. Addendum, points a et f.
"""

from __future__ import annotations

import psycopg

from conftest import (
    MOT_DE_PASSE_AGENT_COMPTA,
    MOT_DE_PASSE_AGENT_STOCK,
    MOT_DE_PASSE_AGENT_STOCK_COMPTOIR,
    MOT_DE_PASSE_RESPONSABLE,
    PG_ADMIN_DSN,
    entete_autorisation,
    se_connecter,
)


def _seuil_et_stock(article_id: int, site_id: int = 1) -> dict:
    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT quantite_stock, seuil_alerte FROM stocks_sites WHERE article_id = %s AND site_id = %s",
                (article_id, site_id),
            )
            return cur.fetchone()


# ---------------------------------------------------------------------------
# Réception (recalcule le seuil — cycle 2, exposée par une route ce cycle)
# ---------------------------------------------------------------------------

def test_reception_recalcule_le_seuil(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "quantite": 50, "motif": "Livraison Cimenterie"},
    )
    assert reponse.status_code == 201, reponse.text
    avant_apres = _seuil_et_stock(1)
    assert avant_apres["quantite_stock"] == 80  # 30 + 50
    assert avant_apres["seuil_alerte"] == 10    # 20 % de 50


def test_reception_ouvre_le_stock_au_site_de_lagent(client):
    """Décision 2026-09-19 : la première réception d'une fiche à un site
    OUVRE sa ligne de stock — un agent du Magasin peut donc réceptionner une
    fiche dont le stock n'existait qu'au Comptoir, pour SON site."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 3, "quantite": 10, "motif": "ouverture du stock magasin"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["site_id"] == 1
    assert reponse.json()["quantite_stock"] == 10
    ligne = _seuil_et_stock(3, site_id=1)
    assert ligne["quantite_stock"] == 10


# ---------------------------------------------------------------------------
# Transfert inter-sites (addendum, point a)
# ---------------------------------------------------------------------------

def test_transfert_normal_ne_recalcule_pas_le_seuil(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "site_origine": 1, "site_destination": 2,
              "quantite": 5, "motif": "réassort comptoir"},
    )
    assert reponse.status_code == 201, reponse.text
    corps = reponse.json()
    assert corps["quantite_stock_origine"] == 25    # 30 - 5
    assert corps["quantite_stock_destination"] == 5  # ligne de destination créée (0 + 5)
    destination = _seuil_et_stock(1, site_id=2)
    assert destination["seuil_alerte"] == 0, "le seuil ne doit JAMAIS être recalculé sur un transfert"


def test_transfert_motif_blanc_refuse_par_la_base(client):
    """Pydantic bloque déjà une chaîne vide (min_length=1) ; un motif
    blanc (espaces) passe la validation applicative mais doit être
    refusé par la base — défense en profondeur, vérifiée ici."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "site_origine": 1, "site_destination": 2,
              "quantite": 1, "motif": "   "},
    )
    assert reponse.status_code == 422
    assert "motif" in reponse.json()["detail"].lower()


def test_transfert_stock_insuffisant_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 4, "site_origine": 1, "site_destination": 2,
              "quantite": 100, "motif": "trop"},
    )
    assert reponse.status_code == 422
    assert "insuffisant" in reponse.json()["detail"].lower()


def test_transfert_vers_le_meme_site_refuse(client):
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "site_origine": 1, "site_destination": 1,
              "quantite": 1, "motif": "même site"},
    )
    assert reponse.status_code == 422
    assert "site" in reponse.json()["detail"].lower()


def test_agent_stock_ne_transfere_que_depuis_son_site(client):
    session_comptoir = se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR)
    reponse = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session_comptoir["jeton"]),
        json={"article_id": 1, "site_origine": 1, "site_destination": 2,
              "quantite": 1, "motif": "depuis comptoir, interdit"},
    )
    assert reponse.status_code == 403

    session_magasin = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse2 = client.post(
        "/stock/transferts",
        headers=entete_autorisation(session_magasin["jeton"]),
        json={"article_id": 1, "site_origine": 1, "site_destination": 2,
              "quantite": 1, "motif": "depuis magasin, autorisé"},
    )
    assert reponse2.status_code == 201, reponse2.text


# ---------------------------------------------------------------------------
# Casse (addendum, point f, décision 2026-09-22) — déclaration -> validation
# ---------------------------------------------------------------------------

def test_casse_declaration_ouverte_validation_reservee_au_responsable(client):
    """La déclaration est ouverte à l'agent stock (constat, sans effet sur
    le stock) ; seule la validation, réservée au responsable, décrémente
    réellement."""
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    avant = _seuil_et_stock(1)
    declaration = client.post(
        "/stock/casse/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 3, "motif": "sac éventré"},
    )
    assert declaration.status_code == 201, declaration.text
    assert declaration.json()["statut"] == "en_attente"
    declaration_id = declaration.json()["declaration_id"]
    # Aucun effet sur le stock tant que non validée.
    pendant = _seuil_et_stock(1)
    assert pendant["quantite_stock"] == avant["quantite_stock"]

    # L'agent qui a déclaré ne peut pas valider lui-même (réservé au responsable).
    refus = client.post(
        f"/stock/casse/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_agent["jeton"]),
        json={},
    )
    assert refus.status_code == 403

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    validation = client.post(
        f"/stock/casse/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]),
        json={},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["quantite_stock"] == avant["quantite_stock"] - 3
    apres = _seuil_et_stock(1)
    assert apres["seuil_alerte"] == avant["seuil_alerte"]


def test_casse_responsable_peut_declarer_et_valider_lui_meme(client):
    """Décision 2026-09-23 : pas de séparation stricte déclarant/validateur
    — un responsable peut valider sa propre déclaration."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    declaration = client.post(
        "/stock/casse/declarations",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "constaté par le responsable"},
    )
    declaration_id = declaration.json()["declaration_id"]
    validation = client.post(
        f"/stock/casse/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]),
        json={},
    )
    assert validation.status_code == 200, validation.text


def test_casse_deja_validee_refuse_une_seconde_validation(client):
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    declaration = client.post(
        "/stock/casse/declarations",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "x"},
    )
    declaration_id = declaration.json()["declaration_id"]
    client.post(
        f"/stock/casse/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    second = client.post(
        f"/stock/casse/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert second.status_code == 422, second.text
    assert "déjà validée" in second.json()["detail"].lower()


def test_casse_liste_les_declarations_en_attente(client):
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    client.post(
        "/stock/casse/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "pour la liste"},
    )
    liste = client.get(
        "/stock/casse/declarations", headers=entete_autorisation(session_agent["jeton"]),
    )
    assert liste.status_code == 200, liste.text
    ligne = next(d for d in liste.json() if d["motif"] == "pour la liste" and d["statut"] == "en_attente")
    # Chantier A (écran de validation) : noms lisibles, pas seulement des
    # identifiants — sans quoi la liste serait inutilisable à l'écran.
    assert ligne["article_nom"] == "Ciment CIM II 50 kg"
    assert ligne["declarant_nom"]


# ---------------------------------------------------------------------------
# Retour client (addendum, point f, décision 2026-09-22) — déclaration ->
# validation, avec issue et état de la marchandise
# ---------------------------------------------------------------------------

def _creer_vente_test(client, numero_facturier: str, quantite: int = 2) -> int:
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": numero_facturier, "vendeur_id": 1,
              "lignes": [{"article_id": 1, "quantite": quantite, "prix_unitaire": 6500}]},
    )
    assert reponse_vente.status_code == 201, reponse_vente.text
    return reponse_vente.json()["vente_id"]


def test_retour_client_agent_ne_peut_pas_valider_seul(client):
    """Validation du responsable obligatoire (décision 2026-09-22) — un
    agent stock ne réintègre jamais seul, même sa propre déclaration."""
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK01")
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    avant = _seuil_et_stock(1)
    declaration = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable", "motif": "produit non conforme"},
    )
    assert declaration.status_code == 201, declaration.text
    declaration_id = declaration.json()["declaration_id"]
    pendant = _seuil_et_stock(1)
    assert pendant["quantite_stock"] == avant["quantite_stock"], "aucun effet tant que non validée"

    refus = client.post(
        f"/stock/retours-client/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_agent["jeton"]), json={},
    )
    assert refus.status_code == 403

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    validation = client.post(
        f"/stock/retours-client/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["quantite_stock"] == avant["quantite_stock"] + 1
    apres = _seuil_et_stock(1)
    assert apres["seuil_alerte"] == avant["seuil_alerte"]


def test_retour_client_vente_inexistante_refuse(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "vente_id": 999999, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable"},
    )
    assert reponse.status_code == 422
    assert "introuvable" in reponse.json()["detail"].lower()


def test_agent_stock_ne_declare_un_retour_client_que_pour_son_site(client):
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK02", quantite=1)
    session_comptoir = se_connecter(client, "comptoir.stock", MOT_DE_PASSE_AGENT_STOCK_COMPTOIR)
    reponse = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_comptoir["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable"},
    )
    assert reponse.status_code == 403


def test_retour_client_article_non_vendu_dans_la_vente_refuse(client):
    """Migration 016 (constat n°2) : l'article 2 (Fer) n'a jamais été vendu
    dans cette vente, qui ne porte que sur l'article 1 (Ciment)."""
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK03", quantite=1)
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 2, "vente_id": vente_id, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable"},
    )
    assert reponse.status_code == 422, reponse.text
    assert "ne fait pas partie" in reponse.json()["detail"].lower()


def test_retour_client_quantite_cumulee_depassee_refuse(client):
    """Deux unités vendues, un premier retour VALIDÉ de deux passe, un
    second retour de une de plus (cumul 3 > 2) est refusé dès la
    déclaration."""
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK04", quantite=2)
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    premiere = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 2,
              "issue": "echange", "etat_marchandise": "revendable"},
    )
    assert premiere.status_code == 201, premiere.text
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        f"/stock/retours-client/declarations/{premiere.json()['declaration_id']}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )

    seconde = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable"},
    )
    assert seconde.status_code == 422, seconde.text
    assert "dépasserait" in seconde.json()["detail"].lower()


def test_retour_client_remboursement_especes_exige_confirmation_explicite(client):
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK05", quantite=1)
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    declaration = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "remboursement_especes", "etat_marchandise": "revendable"},
    )
    declaration_id = declaration.json()["declaration_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    sans_confirmation = client.post(
        f"/stock/retours-client/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert sans_confirmation.status_code == 422, sans_confirmation.text
    assert "confirmation" in sans_confirmation.json()["detail"].lower()

    with_confirmation = client.post(
        f"/stock/retours-client/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"confirmation_remboursement": True},
    )
    assert with_confirmation.status_code == 200, with_confirmation.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT montant FROM transactions WHERE vente_id = %s AND type = 'depense'",
                (vente_id,),
            )
            depense = cur.fetchone()
    assert depense is not None and float(depense["montant"]) == 6500.0


def test_retour_client_invendable_ne_reintegre_jamais_le_stock(client):
    """Cas limite documenté dans l'addendum : marchandise reprise
    invendable -> pas de remise en stock, tracée comme une perte."""
    vente_id = _creer_vente_test(client, "MAG-TESTSTOCK06", quantite=1)
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    avant = _seuil_et_stock(1)
    declaration = client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "avoir_client", "etat_marchandise": "invendable", "motif": "cassé au retour"},
    )
    declaration_id = declaration.json()["declaration_id"]

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    validation = client.post(
        f"/stock/retours-client/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["quantite_stock"] == avant["quantite_stock"], "jamais réintégré"
    apres = _seuil_et_stock(1)
    assert apres["quantite_stock"] == avant["quantite_stock"]


# ---------------------------------------------------------------------------
# Article offert (addendum, point f, décision 2026-09-22/24) — déclaration
# -> validation, distinct d'une remise à 100 % (migration 037, refusée).
# ---------------------------------------------------------------------------

def test_article_offert_declaration_ouverte_agent_comptabilite_validation_responsable(client):
    """Déclaration ouverte à qui vend (agent comptabilité), aucun effet sur
    le stock ; seule la validation, réservée au responsable, décrémente
    réellement — même schéma que la casse."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    avant = _seuil_et_stock(1)
    declaration = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "fidélité client",
              "employe_id": 1},
    )
    assert declaration.status_code == 201, declaration.text
    assert declaration.json()["statut"] == "en_attente"
    declaration_id = declaration.json()["declaration_id"]
    # Aucun effet sur le stock tant que non validée.
    pendant = _seuil_et_stock(1)
    assert pendant["quantite_stock"] == avant["quantite_stock"]

    # Le déclarant ne peut pas valider lui-même (réservé au responsable).
    refus = client.post(
        f"/stock/articles-offerts/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_compta["jeton"]), json={},
    )
    assert refus.status_code == 403

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    validation = client.post(
        f"/stock/articles-offerts/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["quantite_stock"] == avant["quantite_stock"] - 1


def test_article_offert_agent_stock_ne_peut_pas_declarer(client):
    """Contrairement à la casse, la déclaration n'est PAS ouverte à l'agent
    stock — seulement à qui vend (agent comptabilité, responsable)."""
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "x", "employe_id": 1},
    )
    assert reponse.status_code == 403


def test_article_offert_employe_dun_autre_site_refuse(client):
    """« Un article offert est le geste le plus facile à détourner »
    (décision 2026-09-24) : l'employé doit appartenir au site concerné.
    Article 3 n'a de stock qu'au Comptoir (site 2), l'employé 1 est au
    Magasin (site 1)."""
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    reponse = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_resp["jeton"]),
        json={"article_id": 3, "site_id": 2, "quantite": 1, "motif": "mauvais site",
              "employe_id": 1},
    )
    assert reponse.status_code == 422, reponse.text
    assert "n'appartient pas au site" in reponse.json()["detail"].lower()


def test_article_offert_rattache_a_une_vente_optionnelle(client):
    """vente_id est optionnel (décision 2026-09-24) : un article offert peut
    accompagner un achat réel ou être une opération autonome. Ici, rattaché
    à une vente réelle — valeur_normale figée depuis le prix catalogue,
    mouvement de stock relié à la vente."""
    vente_id = _creer_vente_test(client, "MAG-TESTOFFERT01", quantite=1)
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    declaration = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "10 achetés, 1 offert",
              "employe_id": 1, "vente_id": vente_id, "client_nom": "Client fidèle"},
    )
    assert declaration.status_code == 201, declaration.text
    declaration_id = declaration.json()["declaration_id"]

    liste = client.get(
        "/stock/articles-offerts/declarations", headers=entete_autorisation(session_compta["jeton"]),
    )
    ligne = next(d for d in liste.json() if d["declaration_id"] == declaration_id)
    assert ligne["vente_id"] == vente_id
    assert ligne["client_nom"] == "Client fidèle"
    assert ligne["valeur_normale"] == 6500.0  # prix catalogue de l'article 1

    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    validation = client.post(
        f"/stock/articles-offerts/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert validation.status_code == 200, validation.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT categorie, vente_id FROM mouvements_stock"
                " WHERE id = (SELECT mouvement_id FROM declarations_article_offert WHERE id = %s)",
                (declaration_id,),
            )
            mouvement = cur.fetchone()
    assert mouvement["categorie"] == "article_offert"
    assert mouvement["vente_id"] == vente_id


def test_article_offert_vente_id_absent_reste_valide(client):
    """Un pur geste commercial, sans achat associé, reste accepté."""
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    declaration = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "cadeau commercial",
              "employe_id": 1},
    )
    assert declaration.status_code == 201, declaration.text


def test_article_offert_deja_valide_refuse_seconde_validation(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    declaration = client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "x", "employe_id": 1},
    )
    declaration_id = declaration.json()["declaration_id"]
    session_resp = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    client.post(
        f"/stock/articles-offerts/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    second = client.post(
        f"/stock/articles-offerts/declarations/{declaration_id}/valider",
        headers=entete_autorisation(session_resp["jeton"]), json={},
    )
    assert second.status_code == 422, second.text
    assert "déjà validée" in second.json()["detail"].lower()


def test_article_offert_liste_les_declarations_en_attente(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    client.post(
        "/stock/articles-offerts/declarations",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"article_id": 1, "site_id": 1, "quantite": 1, "motif": "pour la liste",
              "employe_id": 1},
    )
    liste = client.get(
        "/stock/articles-offerts/declarations", headers=entete_autorisation(session_compta["jeton"]),
    )
    assert liste.status_code == 200, liste.text
    ligne = next(d for d in liste.json() if d["motif"] == "pour la liste" and d["statut"] == "en_attente")
    assert ligne["article_nom"] == "Ciment CIM II 50 kg"
    assert ligne["employe_nom"] == "Employé Essai"
    assert ligne["declarant_nom"]


def test_retour_client_liste_les_declarations_en_attente(client):
    vente_id = _creer_vente_test(client, "MAG-TESTLISTE01", quantite=1)
    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    client.post(
        "/stock/retours-client/declarations",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"article_id": 1, "vente_id": vente_id, "quantite": 1,
              "issue": "echange", "etat_marchandise": "revendable", "motif": "pour la liste"},
    )
    liste = client.get(
        "/stock/retours-client/declarations", headers=entete_autorisation(session_agent["jeton"]),
    )
    assert liste.status_code == 200, liste.text
    ligne = next(d for d in liste.json() if d["motif"] == "pour la liste" and d["statut"] == "en_attente")
    assert ligne["article_nom"] == "Ciment CIM II 50 kg"
    assert ligne["declarant_nom"]


# ---------------------------------------------------------------------------
# Retour fournisseur (addendum, point f)
# ---------------------------------------------------------------------------

def test_retour_fournisseur_sur_une_vraie_reception(client):
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse_reception = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "quantite": 20, "motif": "Livraison test"},
    )
    assert reponse_reception.status_code == 201, reponse_reception.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'reception_fournisseur' ORDER BY id DESC LIMIT 1"
            )
            mouvement_id = cur.fetchone()["id"]

    avant = _seuil_et_stock(1)
    reponse = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 5, "motif": "sacs abîmés à réception"},
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["article_id"] == 1
    assert reponse.json()["quantite_stock"] == avant["quantite_stock"] - 5


def test_retour_fournisseur_sur_un_mouvement_qui_nest_pas_une_reception(client):
    session_compta = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    reponse_vente = client.post(
        "/ventes",
        headers=entete_autorisation(session_compta["jeton"]),
        json={"mode_paiement": "especes", "numero_facturier": "MAG-TESTSTOCK05", "vendeur_id": 1, "lignes": [{"article_id": 1, "quantite": 1, "prix_unitaire": 6500}]},
    )
    assert reponse_vente.status_code == 201, reponse_vente.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'vente' ORDER BY id DESC LIMIT 1"
            )
            mouvement_id = cur.fetchone()["id"]

    session_agent = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session_agent["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 1},
    )
    assert reponse.status_code == 422
    assert "réception" in reponse.json()["detail"].lower()


def test_retour_fournisseur_quantite_cumulee_depassee_refuse(client):
    """Migration 016 : trois unités reçues, un premier retour de trois
    passe, un second retour de une de plus (cumul 4 > 3) est refusé."""
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    reponse_reception = client.post(
        "/stock/entrees",
        headers=entete_autorisation(session["jeton"]),
        json={"article_id": 1, "quantite": 3, "motif": "Livraison test cumul"},
    )
    assert reponse_reception.status_code == 201, reponse_reception.text

    with psycopg.connect(PG_ADMIN_DSN) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                "SELECT id FROM mouvements_stock WHERE article_id = 1 AND categorie = 'reception_fournisseur' ORDER BY id DESC LIMIT 1"
            )
            mouvement_id = cur.fetchone()["id"]

    premier = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 3},
    )
    assert premier.status_code == 201, premier.text

    second = client.post(
        "/stock/retours-fournisseur",
        headers=entete_autorisation(session["jeton"]),
        json={"mouvement_origine_id": mouvement_id, "quantite": 1},
    )
    assert second.status_code == 422, second.text
    assert "dépasserait" in second.json()["detail"].lower()
