"""Décisions du propriétaire : seuils cumulés, fraîcheur, confidentialité, verrou."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from threading import Barrier

import psycopg
import pytest
from openpyxl import load_workbook

from conftest import (PG_ADMIN_DSN, MOT_DE_PASSE_RESPONSABLE, MOT_DE_PASSE_AGENT_COMPTA,
                      MOT_DE_PASSE_AGENT_STOCK, se_connecter, entete_autorisation)


def panier(numero="MAG-N10001", **suite):
    return {"site_id": 1, "numero_facturier": numero, "vendeur_id": 1,
            "mode_paiement": "especes", "lignes": [{"article_id": 1, "quantite": 1, "remise_pct": 5}], **suite}


@pytest.mark.parametrize("ligne", [{"remise_pct": 10}, {"remise_montant": 650}, {"prix_unitaire": 5850}])
def test_n1_cumul_et_fausse_approbation_refuses(client, ligne):
    session = se_connecter(client, "magasin.compta", MOT_DE_PASSE_AGENT_COMPTA)
    r = client.post("/ventes", headers=entete_autorisation(session["jeton"]),
                    json=panier(lignes=[{"article_id": 1,"quantite": 1, **ligne}],
                                remise_globale_pct=10, approbation_responsable=True, responsable_id=1))
    assert r.status_code == 403, r.text
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute("SELECT count(*) FROM ventes WHERE numero_facturier='MAG-N10001'").fetchone()[0] == 0


@pytest.mark.parametrize("global_,attendu", [(325,201),(325.01,403)])
def test_n1_borne_cumulee_exacte(client, global_, attendu):
    session = se_connecter(client,"magasin.compta",MOT_DE_PASSE_AGENT_COMPTA)
    r=client.post('/ventes', headers=entete_autorisation(session['jeton']),
                  json=panier(remise_globale_montant=global_))
    assert r.status_code == attendu, r.text


def test_n1_pondere_par_quantites_et_non_par_ligne(client):
    session=se_connecter(client,'magasin.compta',MOT_DE_PASSE_AGENT_COMPTA)
    r=client.post('/ventes',headers=entete_autorisation(session['jeton']),
        json=panier(lignes=[{'article_id':1,'quantite':1,'remise_pct':20},
                           {'article_id':2,'quantite':10,'remise_pct':0}]))
    assert r.status_code==201,r.text  # 1300 / 41500 < 10 %


def test_n1_approbation_authentifiee_atomique_et_immuable(client):
    session=se_connecter(client,'resp',MOT_DE_PASSE_RESPONSABLE)
    r=client.post('/ventes',headers=entete_autorisation(session['jeton']),
                  json=panier(remise_globale_pct=10,approbateur_id=999))
    assert r.status_code==201,r.text
    with psycopg.connect(PG_ADMIN_DSN) as c:
        row=c.execute('SELECT responsable_id,total_catalogue,remise_totale FROM approbations_remises WHERE vente_id=%s',
                      (r.json()['vente_id'],)).fetchone()
        assert row == (session['utilisateur_id'],6500, 942.50)
    with pytest.raises(psycopg.errors.RestrictViolation):
        with psycopg.connect(PG_ADMIN_DSN) as c:
            c.execute('DELETE FROM approbations_remises WHERE vente_id=%s',(r.json()['vente_id'],))
    with psycopg.connect(PG_ADMIN_DSN) as c:
        c.execute('SET LOCAL ROLE qf_agent_comptabilite')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute('INSERT INTO approbations_remises SELECT * FROM approbations_remises')


def test_n1_paiement_incoherent_ne_laisse_aucune_approbation(client):
    session=se_connecter(client,'resp',MOT_DE_PASSE_RESPONSABLE)
    r=client.post('/ventes',headers=entete_autorisation(session['jeton']),
        json=panier(mode_paiement=None,remise_globale_pct=10,
                    paiements=[{'mode_paiement':'especes','montant':1}]))
    assert r.status_code==422
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute('SELECT count(*) FROM approbations_remises').fetchone()[0]==0
        assert c.execute("SELECT count(*) FROM ventes WHERE numero_facturier='MAG-N10001'").fetchone()[0]==0


def test_n1_majoration_autre_ligne_ne_masque_pas_remise(client):
    session=se_connecter(client,'magasin.compta',MOT_DE_PASSE_AGENT_COMPTA)
    r=client.post('/ventes',headers=entete_autorisation(session['jeton']),
        json=panier(lignes=[{'article_id':1,'quantite':1,'remise_pct':20},
                           {'article_id':2,'quantite':1,'prix_unitaire':5000}]))
    assert r.status_code==403,r.text  # remise 1300 / catalogue 10000 >10 %, même avec majoration


def test_n1_catalogue_zero_ne_permet_pas_de_contourner_le_plafond(client):
    with psycopg.connect(PG_ADMIN_DSN) as c:
        c.execute('UPDATE articles SET prix_vente=0 WHERE id=1')
    session=se_connecter(client,'resp',MOT_DE_PASSE_RESPONSABLE)
    r=client.post('/ventes',headers=entete_autorisation(session['jeton']),
        json=panier(lignes=[{'article_id':1,'quantite':1,'prix_unitaire':6500}],remise_globale_pct=5))
    assert r.status_code==422


@pytest.mark.parametrize('age,etat', [(3599,'succes'),(3600,'perime'),(3601,'perime')])
def test_n5_borne_exacte(monkeypatch,age,etat):
    from app.routes import exploitation as e
    now=datetime(2026,10,24,12,tzinfo=timezone.utc)
    monkeypatch.setattr(e,'_maintenant',lambda:now,raising=False)
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':'SUCCES',
        'complete':True,'verifiee':True,'horodatage':(now-timedelta(seconds=age)).isoformat()})
    r=e.etat_sauvegarde(session=object())
    assert r['etat']==etat
    assert r['alerte'] == (age>=3600)
    assert r['age_secondes']==age


@pytest.mark.parametrize('champs',[{}, {'complete':True}, {'complete':True,'verifiee':'true'},
                                 {'complete':False,'verifiee':True}, {'complete':True,'verifiee':False}])
def test_n5_non_verifie_ne_produit_jamais_un_succes(monkeypatch,champs):
    from app.routes import exploitation as e
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':'SUCCES',
                         'horodatage':datetime.now(timezone.utc).isoformat(),**champs})
    r=e.etat_sauvegarde(session=object())
    assert r['etat']!='succes'
    assert r['alerte'] is True


@pytest.mark.parametrize('resultat',['ECHEC','SUCCES'])
def test_n5_nouvel_essai_non_valide_ne_rajeunît_pas_la_preuve(monkeypatch,resultat):
    from app.routes import exploitation as e
    now=datetime(2026,10,24,12,tzinfo=timezone.utc)
    monkeypatch.setattr(e,'_maintenant',lambda:now,raising=False)
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':resultat,
       'horodatage':now.isoformat(),'complete':False,'verifiee':False,
       'derniere_sauvegarde_verifiee':{'horodatage':(now-timedelta(hours=2)).isoformat(),
                                    'complete':True,'verifiee':True}})
    r=e.etat_sauvegarde(session=object())
    assert r['age_secondes']==7200
    assert r['alerte'] is True


@pytest.mark.parametrize('date',['date invalide','2099-01-01T00:00:00Z','2026-10-24T12:00:00'])
def test_n5_date_invalide_future_ou_sans_fuseau_refusee(monkeypatch,date):
    from app.routes import exploitation as e
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':'SUCCES',
                          'horodatage':date,'complete':True,'verifiee':True})
    assert e.etat_sauvegarde(session=object())['etat']!='succes'


def test_n5_preuve_anterieure_contradictoire_ne_rajeunît_pas_un_succes_perime(monkeypatch):
    from app.routes import exploitation as e
    now=datetime(2026,10,24,12,tzinfo=timezone.utc)
    monkeypatch.setattr(e,'_maintenant',lambda:now)
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':'SUCCES',
        'complete':True,'verifiee':True,'horodatage':(now-timedelta(hours=2)).isoformat(),
        'derniere_sauvegarde_verifiee':{'resultat':'ECHEC','complete':True,'verifiee':True,
                                     'horodatage':now.isoformat()}})
    r=e.etat_sauvegarde(session=object())
    assert r['etat']=='perime' and r['age_secondes']==7200 and r['alerte'] is True


def test_n5_etat_http_ne_peut_pas_etre_mis_en_cache(client,monkeypatch):
    from app.routes import exploitation as e
    monkeypatch.setattr(e,'_lire_etat_brut',lambda:{'configure':True,'resultat':'SUCCES',
        'complete':True,'verifiee':True,'horodatage':datetime.now(timezone.utc).isoformat()})
    session=se_connecter(client,'resp',MOT_DE_PASSE_RESPONSABLE)
    r=client.get('/exploitation/etat-sauvegarde',headers=entete_autorisation(session['jeton']))
    assert r.status_code==200 and r.json()['etat']=='succes'
    assert r.headers['cache-control']=='no-store'


def test_c2_cinq_echecs_et_verrou_non_prolonge_puis_expiration(client):
    for i in range(5):
        r=client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'})
        assert r.status_code==401
    with psycopg.connect(PG_ADMIN_DSN) as c:
        n,fin,maintenant=c.execute("SELECT tentatives_echouees,verrouille_jusqua,clock_timestamp() FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()
        assert n==5 and 890 < (fin-maintenant).total_seconds() <=900
    for mdp in ('faux',MOT_DE_PASSE_AGENT_STOCK):
        assert client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':mdp}).status_code==401
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()==(5,fin)
        c.execute("UPDATE utilisateurs SET verrouille_jusqua=clock_timestamp()-interval '1 microsecond' WHERE identifiant='magasin.stock'")
    assert client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':MOT_DE_PASSE_AGENT_STOCK}).status_code==200
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()==(0,None)


def test_c2_succes_romp_la_serie_et_compte_distinct_independant(client):
    for _ in range(4): client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'})
    se_connecter(client,'magasin.stock',MOT_DE_PASSE_AGENT_STOCK)
    for _ in range(4):
        r=client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'})
        assert 'verrouillé' not in r.json()['detail']
    se_connecter(client,'magasin.compta',MOT_DE_PASSE_AGENT_COMPTA)


def test_c2_expiration_nouvel_echec_compte_un_et_pas_six(client):
    for _ in range(5): client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'})
    with psycopg.connect(PG_ADMIN_DSN) as c:
        c.execute("UPDATE utilisateurs SET verrouille_jusqua=clock_timestamp()-interval '1 second' WHERE identifiant='magasin.stock'")
    r=client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'})
    assert r.status_code==401 and 'verrouillé' not in r.json()['detail']
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()==(1,None)


def test_c2_concurrence_sql_sans_compteur_perdu_ni_prolongation(base_reinitialisee):
    barriere=Barrier(10)
    def essai(_):
        with psycopg.connect(PG_ADMIN_DSN) as c:
            c.execute('SET LOCAL ROLE qf_app')
            barriere.wait(timeout=20)
            return c.execute("SELECT ok FROM verifier_connexion('magasin.stock','faux',NULL,'test_concurrent')").fetchone()[0]
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert list(pool.map(essai,range(10))) == [False]*10
    with psycopg.connect(PG_ADMIN_DSN) as c:
        n,fin=c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()
        assert n==5 and fin is not None
        assert c.execute("SELECT count(*) FROM journal_connexions WHERE poste='test_concurrent'").fetchone()[0]==10


def test_c2_limiteur_et_refus_de_deverrouillage_agent(client,app):
    app.state.limiteur_connexion.max_essais=5
    for _ in range(5):
        assert client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':'faux'}).status_code==401
    with psycopg.connect(PG_ADMIN_DSN) as c:
        avant=c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()
    assert client.post('/auth/connexion',json={'identifiant':'magasin.stock','mot_de_passe':MOT_DE_PASSE_AGENT_STOCK}).status_code==429
    s=se_connecter(client,'magasin.compta',MOT_DE_PASSE_AGENT_COMPTA)
    assert client.post('/admin/comptes/2/deverrouiller',headers=entete_autorisation(s['jeton'])).status_code==403
    with psycopg.connect(PG_ADMIN_DSN) as c:
        assert c.execute("SELECT tentatives_echouees,verrouille_jusqua FROM utilisateurs WHERE identifiant='magasin.stock'").fetchone()==avant


@pytest.mark.parametrize('cumul',[False,True])
def test_d1_api_exports_et_acces_indirects_confidentiels(client,cumul):
    if cumul:
        with psycopg.connect(PG_ADMIN_DSN) as c:
            c.execute("INSERT INTO utilisateurs_roles VALUES ((SELECT id FROM utilisateurs WHERE identifiant='magasin.compta'),'agent_stock') ON CONFLICT DO NOTHING")
    s=se_connecter(client,'magasin.compta',MOT_DE_PASSE_AGENT_COMPTA)
    h=entete_autorisation(s['jeton'])
    r=client.get('/articles?role=responsable&prix_achat=true',headers=h)
    assert r.status_code==200
    assert any(a.get('prix_vente')==6500 for a in r.json()['articles'])
    interdits={'prix_achat','cout_revient','marge','valorisation_achat','ancien_prix_achat','nouveau_prix_achat'}
    assert all(not interdits.intersection(a) for a in r.json()['articles'])
    for route in ('/rapports/stock?format=xlsx','/rapports/stock?format=pdf',
                  '/rapports/ecarts-comptage?format=xlsx&date_debut=2026-01-01&date_fin=2026-12-31',
                  '/tableau-bord/credit-client'):
        assert client.get(route,headers=h).status_code==403
    r=client.get('/rapports/articles?format=xlsx',headers=h)
    assert r.status_code==200
    colonnes=next(load_workbook(BytesIO(r.content),read_only=True).active.values)
    assert 'prix_vente' in colonnes and not interdits.intersection(colonnes)
    for role in ('qf_agent_comptabilite','qf_agent_stock') if cumul else ('qf_agent_comptabilite',):
        for requete in ('SELECT prix_achat FROM articles','SELECT * FROM historique_prix_articles'):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(PG_ADMIN_DSN) as c:
                    c.execute('SET LOCAL ROLE '+role)
                    c.execute(requete)
