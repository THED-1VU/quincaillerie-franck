"""Contournements SQL et écritures concurrentes sur les paiements (C1)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

from conftest import PG_ADMIN_DSN, MOT_DE_PASSE_AGENT_STOCK, se_connecter, entete_autorisation


def creer(connection, numero, mode="mixte", total=100,site=1):
    return connection.execute(
        "INSERT INTO ventes(site_id,utilisateur_id,statut,mode_paiement,utilisateur_caisse_id,"
        "sous_total_ht,taux_tva,montant_tva,total_ttc,date_encaissement,numero_facturier,vendeur_id) "
        "VALUES(%s,1,'payee',%s,1,%s,0,0,%s,NOW(),%s,1) RETURNING id", (site,mode,total,total,numero)).fetchone()[0]


@pytest.mark.parametrize("mode,composantes", [
    ("mixte", []),
    ("mixte", [("especes",100)]),
    ("especes", [("orange_money",100)]),
    ("credit_client", [("especes",100)]),
    ("especes", []),
])
def test_insert_sql_incoherent_refuse_au_commit(base_reinitialisee,mode,composantes):
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            ident=creer(connection,"MAG-AUDIT001",mode)
            for payment,amount in composantes:
                connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) VALUES(%s,%s,%s)",
                                   (ident,payment,amount))
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        assert connection.execute("SELECT count(*) FROM ventes WHERE numero_facturier='MAG-AUDIT001'").fetchone()[0]==0


def paiement_simple(connection,numero):
    ident=creer(connection,numero,"especes")
    connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) VALUES(%s,'especes',100)",(ident,))
    return ident


def test_modification_du_total_parent_seul_refusee(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        ident=paiement_simple(connection,"MAG-AUDIT002")
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            connection.execute("UPDATE ventes SET sous_total_ht=110,total_ttc=110 WHERE id=%s",(ident,))


def test_deplacement_composante_controle_aussi_ancienne_vente(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        ancien=paiement_simple(connection,"MAG-AUDIT003")
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        nouveau=creer(connection,"MAG-AUDIT004","especes")
        # La destination serait valide ; seule la source perd sa composante.
        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute("UPDATE ventes_paiements SET vente_id=%s WHERE vente_id=%s",(nouveau,ancien))
            connection.commit()
        connection.rollback()


def test_paiements_concurrents_restent_coherents(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        ident=creer(connection,"MAG-AUDIT005")
        connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) "
                           "VALUES(%s,'especes',50),(%s,'orange_money',50)",(ident,ident))
    barriere=Barrier(2)
    def ajouter(mode):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            connection.execute("SET LOCAL lock_timeout='10s'")
            barriere.wait(timeout=10)
            connection.execute("UPDATE ventes SET sous_total_ht=sous_total_ht+10,total_ttc=total_ttc+10 WHERE id=%s",(ident,))
            connection.execute("UPDATE ventes_paiements SET montant=montant+10 WHERE vente_id=%s AND mode_paiement=%s",(ident,mode))
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(ajouter,["especes","orange_money"]))
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        assert connection.execute("SELECT total_ttc FROM ventes WHERE id=%s",(ident,)).fetchone()[0]==120
        assert connection.execute("SELECT sum(montant) FROM ventes_paiements WHERE vente_id=%s",(ident,)).fetchone()[0]==120


def test_rls_composantes_ne_fuit_pas_vers_autre_site(base_reinitialisee):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        ident=creer(connection,"CPT-AUDIT006","especes",site=2)
        connection.execute("INSERT INTO ventes_paiements(vente_id,mode_paiement,montant) VALUES(%s,'especes',100)",(ident,))
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        connection.execute("SET LOCAL ROLE qf_agent_comptabilite")
        connection.execute("SELECT set_config('qf.site_id','1',TRUE)")
        assert connection.execute("SELECT montant FROM ventes_paiements WHERE vente_id=%s",(ident,)).fetchall()==[]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            connection.execute("SET LOCAL ROLE qf_agent_stock")
            connection.execute("SELECT montant FROM ventes_paiements")


@pytest.mark.parametrize("role",["qf_responsable","qf_agent_comptabilite"])
def test_reecriture_document_interdite_aux_roles_metier(base_reinitialisee,role):
    with psycopg.connect(PG_ADMIN_DSN) as connection:
        ident=paiement_simple(connection,"MAG-AUDIT007")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            connection.execute("SET LOCAL ROLE "+role)
            connection.execute("SELECT set_config('qf.site_id','1',TRUE)")
            connection.execute("UPDATE ventes SET total_ttc=200,sous_total_ht=200 WHERE id=%s",(ident,))


def test_identite_session_prime_sur_utilisateur_et_site_fournis(client):
    session=se_connecter(client,"magasin.stock",MOT_DE_PASSE_AGENT_STOCK)
    response=client.get("/moi?utilisateur_id=1&site_id=2",headers=entete_autorisation(session["jeton"]))
    assert response.status_code==200
    assert response.json()["utilisateur_id"]==session["utilisateur_id"]
    assert response.json()["site_id"]==1


def test_table_temporaire_ne_masque_pas_la_vente_reelle(base_reinitialisee):
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(PG_ADMIN_DSN) as connection:
            connection.execute("SET LOCAL ROLE qf_agent_comptabilite")
            connection.execute("SELECT set_config('qf.site_id','1',TRUE)")
            ident=creer(connection,"MAG-TEMP001")
            connection.execute("CREATE TEMP TABLE ventes (LIKE public.ventes)")
            connection.execute("INSERT INTO pg_temp.ventes SELECT * FROM public.ventes WHERE id=%s",(ident,))
            connection.execute("UPDATE pg_temp.ventes SET statut='en_attente'")
            connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
