"""Régressions négatives C2/C3 : plafond, invalidation durable, rôles vivants."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

from conftest import (PG_ADMIN_DSN, MOT_DE_PASSE_RESPONSABLE, MOT_DE_PASSE_AGENT_STOCK,
                      entete_autorisation, se_connecter)
from app.securite import GestionnaireSessions


def test_plafond_480_meme_si_configuration_superieure():
    manager = GestionnaireSessions("cle-test", 999)
    for override in (None, 481, 999):
        token = manager.emettre(utilisateur_id=1, role="responsable", site_id=None,
                               nom_complet="Test", doit_changer_mot_de_passe=False,
                               duree_minutes=override)
        session = manager.verifier(token)
        assert session.expire_a - session.emis_a == 28800


def test_duree_http_plafonnee_sans_modifier_la_decision(client):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("UPDATE parametres SET valeur='481', a_decider=FALSE WHERE cle='duree_session_minutes'")
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert session["expire_dans_secondes"] == 28800


def test_changement_mdp_preserve_session_courante_et_revoque_autres(client):
    a = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    b = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    response = client.post("/auth/changer-mot-de-passe", headers=entete_autorisation(a["jeton"]),
                           json={"mot_de_passe_actuel": MOT_DE_PASSE_AGENT_STOCK,
                                 "nouveau_mot_de_passe": "NouveauSecretTest789"})
    assert response.status_code == 204, response.text
    assert client.get("/moi", headers=entete_autorisation(a["jeton"])).status_code == 200
    assert client.get("/moi", headers=entete_autorisation(b["jeton"])).status_code == 401


def test_ancien_jeton_ne_ressuscite_pas_apres_reset_et_changement(client):
    old = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    admin = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    response = client.patch(f"/admin/comptes/{old['utilisateur_id']}/mot-de-passe",
                            headers=entete_autorisation(admin["jeton"]),
                            json={"mot_de_passe": "TemporaireTest789"})
    assert response.status_code == 200
    assert client.get("/moi", headers=entete_autorisation(old["jeton"])).status_code == 401
    new = se_connecter(client, "magasin.stock", "TemporaireTest789")
    assert client.post("/auth/changer-mot-de-passe", headers=entete_autorisation(new["jeton"]),
                       json={"mot_de_passe_actuel": "TemporaireTest789",
                             "nouveau_mot_de_passe": "DefinitifTest789"}).status_code == 204
    assert client.get("/moi", headers=entete_autorisation(old["jeton"])).status_code == 401


def test_reactivation_ne_revalide_pas_une_ancienne_session(client):
    old = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    admin = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    for actif in (False, True):
        assert client.patch(f"/admin/comptes/{old['utilisateur_id']}/actif",
                            headers=entete_autorisation(admin["jeton"]), json={"actif": actif}).status_code == 200
    assert client.get("/moi", headers=entete_autorisation(old["jeton"])).status_code == 401


def test_retrait_role_effectif_immediat_sans_nouvelle_connexion(client):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("INSERT INTO utilisateurs_roles(utilisateur_id,role) "
                           "SELECT id,'agent_comptabilite' FROM utilisateurs WHERE identifiant='magasin.stock'")
    session = se_connecter(client, "magasin.stock", MOT_DE_PASSE_AGENT_STOCK)
    headers = entete_autorisation(session["jeton"])
    assert client.get("/ventes/parametres", headers=headers).status_code == 200
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("DELETE FROM utilisateurs_roles WHERE role='agent_comptabilite' "
                           "AND utilisateur_id=%s", (session["utilisateur_id"],))
    assert client.get("/ventes/parametres", headers=headers).status_code == 403
    assert client.get("/inventaire/articles-a-compter?moment=matin", headers=headers).status_code == 200


def test_echecs_concurrents_ne_perdent_pas_dincrement(base_reinitialisee):
    barrier = Barrier(2)
    def tentative():
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            barrier.wait(timeout=10)
            return connection.execute("SELECT ok FROM verifier_connexion('magasin.stock','mauvais',NULL,NULL)").fetchone()[0]
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: tentative(), range(2)))
    assert results == [False, False]
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        assert connection.execute("SELECT tentatives_echouees FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()[0] == 2


@pytest.mark.parametrize("secret", ["a" * 73, "é" * 37])
def test_secret_trop_long_refuse_sans_troncature(client,secret):
    response = client.post("/auth/connexion", json={"identifiant":"resp","mot_de_passe":secret})
    assert response.status_code == 422
    from app.securite import hacher_mot_de_passe
    with pytest.raises(ValueError,match="72"):
        hacher_mot_de_passe(secret)


def test_deplacement_de_site_invalide_ancienne_session(client):
    agent = se_connecter(client,"magasin.stock",MOT_DE_PASSE_AGENT_STOCK)
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("UPDATE utilisateurs SET site_id=2 WHERE id=%s",(agent["utilisateur_id"],))
    assert client.get("/articles",headers=entete_autorisation(agent["jeton"])).status_code == 401


def test_journal_roles_trace_et_non_modifiable_par_responsable(client):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("INSERT INTO utilisateurs_roles(utilisateur_id,role) "
                           "SELECT id,'agent_comptabilite' FROM utilisateurs WHERE identifiant='magasin.stock'")
        row = connection.execute("SELECT action,compte_sql FROM journal_securite "
                                 "WHERE action='INSERT_role_agent_comptabilite' ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None and row[1] == "postgres"
    for statement in ("UPDATE journal_securite SET action='efface'", "DELETE FROM journal_securite"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(PG_ADMIN_DSN) as connection:
                connection.execute("SET LOCAL ROLE qf_responsable")
                connection.execute(statement)


def test_jeton_refuse_si_sa_session_absente_de_la_base(client):
    """R3 : invalidation des sessions restaurees (restaurer.ps1, etape 4)."""
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    entetes = entete_autorisation(session["jeton"])
    assert client.get("/moi", headers=entetes).status_code == 200
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("TRUNCATE TABLE sessions_serveur")
    assert client.get("/moi", headers=entetes).status_code == 401


# C-5 : trois routes authentifiées de familles différentes (identité,
# administration, ventes) — chaque requête doit relire la session en base,
# pas seulement vérifier la signature du jeton.
ROUTES_PROTEGEES = ("/moi", "/admin/comptes", "/ventes/parametres")


def _jti(jeton: str) -> str:
    return GestionnaireSessions("0" * 64, 480).verifier(jeton).jti


def _refuser_sur_toutes_les_routes(client, jeton: str, motif: str) -> None:
    for route in ROUTES_PROTEGEES:
        reponse = client.get(route, headers=entete_autorisation(jeton))
        assert reponse.status_code == 401, (
            f"{route} a accepté un jeton {motif} : {reponse.status_code} {reponse.text}"
        )


def test_toute_requete_authentifiee_controle_la_session_en_base(client):
    """C-5 : jeton invalide, révoqué, expiré ou absent (forme d'un dump) → 401.

    Le jeton émis ici est signé avec le même secret que l'application : seule
    la relecture de `sessions_serveur` peut le refuser. Un contrôle limité à
    la signature laisserait donc passer les quatre cas ci-dessous.
    """
    session = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    jeton = session["jeton"]
    entetes = entete_autorisation(jeton)
    for route in ROUTES_PROTEGEES:
        assert client.get(route, headers=entetes).status_code == 200, route

    # 1. Jeton malformé : refusé avant toute lecture de base.
    _refuser_sur_toutes_les_routes(client, "jeton-illisible", "malformé")

    # 2. Jeton correctement signé mais dont le jti n'a jamais été enregistré.
    #    C'est la forme d'un jeton recopié d'un dump dans une base où sa
    #    session n'existe plus : la signature seule ne suffit pas.
    gestionnaire = GestionnaireSessions("0" * 64, 480)
    jamais_enregistre = gestionnaire.emettre(
        utilisateur_id=session["utilisateur_id"], role="responsable", site_id=None,
        nom_complet="Resp", doit_changer_mot_de_passe=False)
    _refuser_sur_toutes_les_routes(client, jamais_enregistre, "non enregistré (dump)")

    # 3. Session expirée EN BASE alors que le jeton n'a pas encore atteint
    #    son `exp` : la décision doit venir de la table, pas du jeton.
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("UPDATE sessions_serveur SET expire_a = clock_timestamp() - interval '1 minute' "
                           "WHERE jti = %s", (_jti(jeton),))
    _refuser_sur_toutes_les_routes(client, jeton, "expiré en base")

    # 4. Session supprimée de la table (invalidation d'une restauration).
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("DELETE FROM sessions_serveur WHERE jti = %s", (_jti(jeton),))
    _refuser_sur_toutes_les_routes(client, jeton, "absent de la base")

    # 5. Déconnexion : le jeton encore valide et enregistré devient révoqué.
    nouveau = se_connecter(client, "resp", MOT_DE_PASSE_RESPONSABLE)
    assert client.get("/moi", headers=entete_autorisation(nouveau["jeton"])).status_code == 200
    assert client.post("/auth/deconnexion",
                       headers=entete_autorisation(nouveau["jeton"])).status_code == 204
    _refuser_sur_toutes_les_routes(client, nouveau["jeton"], "révoqué")


def test_refus_limiteur_est_journalise(app,client):
    from app.securite import LimiteurDebit
    app.state.limiteur_connexion=LimiteurDebit(1,60)
    body={"identifiant":"resp","mot_de_passe":"mauvais"}
    assert client.post("/auth/connexion",json=body).status_code==401
    assert client.post("/auth/connexion",json=body).status_code==429
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        assert connection.execute("SELECT count(*) FROM journal_connexions "
                                  "WHERE poste='api_limitation_debit' AND identifiant_saisi='resp'").fetchone()[0]==1
